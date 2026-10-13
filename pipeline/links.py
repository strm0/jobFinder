"""Ads from other job sites, through JobAd Links. Free: no key, no model.

    python -m pipeline.links run        # fetch, read and store. What nightly runs
    python -m pipeline.links fetch      # the Links list only: new, changed, closed
    python -m pipeline.links read       # full text for the ads that have none
    python -m pipeline.links status     # per site: listed, let in, read, held back
    python -m pipeline.links verify     # checks
    python -m pipeline.links try URL    # what each reader finds on one page

**What the source is.** JobAd Links, run by Arbetsförmedlingen with several Swedish job
boards, lists ads found on other sites. Most of them are on Platsbanken too, and those are
dropped at the fetch with `exclude_source`, because JobStream already brings them in. What
is left is the ads in the seven occupation fields that are only on other sites.

**Full text or nothing.** Links cuts every ad to about 250 characters on purpose, and a
ranking read off that would clutter the dashboard with half-judged cards. So each ad's page
on the original site is read once, and the ad reaches the store only with its full text. An
ad with no text is held back: never classified and never shown, only counted, and tried
again on later runs, so a reader fixed later picks it up. Reading the original page is the
one exception to the rule that Swedish job sites are not scraped, a rule that is about
Platsbanken: one read per ad, one page at a time, and only pages the site's robots.txt
allows.

**A broken reader is flagged by site.** Sites redesign their pages, and a reader that
stops finding text holds back every new ad from that site without failing loudly. Every
read pass records, per site, pages tried and texts found, and a site whose reader finds
text on fewer than `links.flag_below` of the pages it tried is named in `nightly report`,
in `verify` and on the dashboard. `try URL` shows what each reader makes of one page, which
is where fixing one starts.

**How an ad travels.** `links_ads` holds every ad Links lists, whether or not it is let in
or read, so the next fetch can tell new from known and notice an ad Links stops listing.
An ad let in and read is written to `ads` with `source = 'links'`, shaped like a JobTech
payload, so `normalise`, `prefilter`, `signals`, `classify` and `score` take it without
knowing where it came from. Twins, the same job on Platsbanken under a different employer
spelling, are found by `find_twins` and skipped by the pre-filter before anything is paid.

**Nothing is classified until the gate in the config opens**, `links.classify`, which is
set by hand once a sample of the ads has been read. See `classify.links_gate`.
"""

import argparse
import html
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
import yaml

from . import jobtech, store

ROOT = Path(__file__).resolve().parent.parent
CONFIG_YAML = ROOT / "context" / "02_search_config.yaml"

API = "https://links.api.jobtechdev.se/joblinks"
PLATSBANKEN = "arbetsformedlingen.se"          # the source label Links gives Platsbanken
SOURCE = "links"                               # `ads.source` for everything written here

# An honest name. Every site with a reader answers it.
USER_AGENT = "Mozilla/5.0 (compatible; personal job search, one reader per ad)"
PAUSE = 1.5            # seconds between two page reads, whichever sites they are on
MIN_TEXT = 300         # characters. Less than this is a teaser, not the ad.
MAX_ATTEMPTS = 5       # reads of one ad before it is left alone until `read --retry`
NETWORK_WAIT = 30      # a run started at wake can beat the network back, as in jobtech.py

# The sites with a reader, in the order one is chosen when an ad is on several. Each maps to
# the readers tried on its pages, in order:
#   jsonld          the schema.org JobPosting sites publish for Google. The whole ad, several
#                   thousand characters on thehub.io. studentjob.se has it on every ad it takes
#                   applications for.
#   microdata       the section marked itemprop="description". studentjob.se's ads marked
#                   "Inaktiv jobbannons" have no JSON-LD but keep the text here. That mark does
#                   not mean closed: such an ad can still be open on the employer's own career
#                   page.
#   offentligajobb  the page's assignment section, which also gives the last day to apply.
SITES = {
    "thehub.io": ("jsonld",),
    "ledigajobb.se": ("jsonld",),
    "ingenjorsjobb.se": ("jsonld",),
    "api.workmatch.io": ("jsonld",),
    "studentjob.se": ("jsonld", "microdata"),
    "offentligajobb.se": ("offentligajobb",),
}

# Sites Links lists that have no reader, and why. Their ads are held back as having none.
# A site Links starts listing that is in neither table is also held back, and `status` and
# the nightly report name it, so a new source is seen rather than silently dropped.
NO_READER = {
    "intenso.se": "loads its text with JavaScript; JSON-LD gives only a teaser",
    "jobbdirekt.se": "links to a blank WordPress page",
    "lararguiden.se": "links to a blank WordPress page",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS links_ads (
    id               TEXT PRIMARY KEY,    -- the Links id, 32 hex characters
    payload          TEXT NOT NULL,       -- the Links hit, verbatim
    field_id         TEXT,                -- occupation field, for closing ads by absence
    publication_date TEXT,
    site             TEXT,                -- the source read for the text, see SITES
    url              TEXT,                -- that source's page
    admitted         INTEGER NOT NULL,    -- let in when first listed, see `admit`
    admit_reason     TEXT NOT NULL,       -- admitted | too_old | abroad, by address or language
    first_seen       TEXT NOT NULL,
    last_seen        TEXT NOT NULL,
    removed          INTEGER NOT NULL DEFAULT 0,
    removed_date     TEXT,
    text             TEXT,                -- the full ad text from the page, NULL until read
    text_status      TEXT NOT NULL,       -- unread | read | failed | gone | robots | no_reader
                                          -- | skipped, when the pre-filter would skip it
    reader           TEXT,                -- which reader found the text
    extra            TEXT,                -- JSON, what the page adds: a deadline
    read_attempts    INTEGER NOT NULL DEFAULT 0,
    read_utc         TEXT,
    read_error       TEXT
);

CREATE INDEX IF NOT EXISTS links_ads_open ON links_ads(removed, admitted, text_status);

-- One row per site per read pass. What the flags and the nightly report are read from.
CREATE TABLE IF NOT EXISTS links_reads (
    pass_utc   TEXT NOT NULL,
    site       TEXT NOT NULL,
    tried      INTEGER NOT NULL,   -- pages answered, whether or not text was found
    found      INTEGER NOT NULL,
    failed     INTEGER NOT NULL,   -- answered, and no reader found the ad in it
    gone       INTEGER NOT NULL,   -- 404 or 410: the ad is gone from the site
    held_back  INTEGER NOT NULL,   -- open ads let in from this site with no text, after it
    flagged    INTEGER NOT NULL,
    PRIMARY KEY (pass_utc, site)
);
"""


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def settings():
    cfg = yaml.safe_load(CONFIG_YAML.read_text(encoding="utf-8"))
    links = cfg.get("links")
    if not isinstance(links, dict):
        raise SystemExit("the config has no `links` section.")
    return links


def ensure(conn):
    conn.executescript(SCHEMA)


# --------------------------------------------------------------------------
# Fetching the Links list
# --------------------------------------------------------------------------

def _labels(hit):
    return [s.get("label") or "" for s in hit.get("source_links") or []]


def choose_site(hit):
    """The source whose page is read: the first in SITES order, else the first Links names.
    Returns (label, url), with a label that may have no reader."""
    links = {s.get("label"): s.get("url") for s in hit.get("source_links") or []
             if s.get("label") != PLATSBANKEN}
    for label in SITES:
        if links.get(label):
            return label, links[label]
    for label, url in links.items():
        if url:
            return label, url
    return None, None


def admit(hit, first_seen, days):
    """Let in when first listed, or not. An ad let in stays in until Links stops listing it,
    so crossing the age line later never closes it."""
    addresses = hit.get("workplace_addresses") or []
    if addresses and all((a.get("country") or "Sverige") != "Sverige" for a in addresses):
        return 0, "abroad"
    published = (hit.get("publication_date") or "")[:10]
    if published:
        age = datetime.fromisoformat(first_seen).date() - datetime.fromisoformat(published).date()
        if age > timedelta(days=days):
            return 0, "too_old"
    return 1, "admitted"


def _get_json(params):
    for wait in (NETWORK_WAIT, NETWORK_WAIT * 2, None):
        try:
            r = requests.get(API, params=params, timeout=90,
                             headers={"accept": "application/json", "User-Agent": USER_AGENT})
            break
        except (requests.ConnectionError, requests.Timeout):
            if wait is None:
                raise
            time.sleep(wait)
    if r.status_code != 200:
        raise jobtech.JobTechError(f"{API} returned {r.status_code}: {r.text[:200]}")
    return r.json()


def fetch_field(field_id):
    """Every ad Links lists in one occupation field that is not on Platsbanken. Returns
    (hits, complete). Incomplete means the field holds more than one query can reach, and
    then nothing in it is closed by absence."""
    hits, offset = [], 0
    while True:
        data = _get_json({"occupation-field": field_id, "exclude_source": PLATSBANKEN,
                          "limit": jobtech.MAX_LIMIT, "offset": offset,
                          "sort": "pubdate-desc"})
        total = data["total"]["value"]
        page = data.get("hits") or []
        hits.extend(page)
        offset += len(page)
        time.sleep(jobtech.PAUSE)
        if not page or offset >= total or offset > jobtech.MAX_OFFSET:
            break
    return hits, total <= jobtech.REACHABLE and len(hits) >= total


def fetch(conn):
    """Bring `links_ads` in line with what Links lists tonight. Free. Returns counts."""
    ensure(conn)
    days = int(settings().get("admit_days", 60))
    ts = now_utc()
    counts = Counter()
    open_before = dict(conn.execute(
        "SELECT field_id, COUNT(*) FROM links_ads WHERE removed = 0 GROUP BY field_id"
    ).fetchall())

    for field_id, label in jobtech.FIELDS.items():
        hits, complete = fetch_field(field_id)
        seen = set()
        for hit in hits:
            if PLATSBANKEN in _labels(hit):
                continue            # exclude_source did not hold; never take a Platsbanken ad
            seen.add(hit["id"])
            counts["listed"] += 1
            row = conn.execute("SELECT removed FROM links_ads WHERE id = ?",
                               (hit["id"],)).fetchone()
            site, url = choose_site(hit)
            payload = json.dumps(hit, ensure_ascii=False)
            if row is None:
                admitted, reason = admit(hit, ts, days)
                status = "unread" if site in SITES else "no_reader"
                conn.execute(
                    """INSERT INTO links_ads (id, payload, field_id, publication_date, site, url,
                           admitted, admit_reason, first_seen, last_seen, text_status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (hit["id"], payload, field_id, hit.get("publication_date"), site, url,
                     admitted, reason, ts, ts, status))
                counts["new"] += 1
                counts["new_admitted"] += admitted
            else:
                conn.execute(
                    """UPDATE links_ads SET payload = ?, field_id = ?, publication_date = ?,
                           url = CASE WHEN site = ? THEN ? ELSE url END,
                           last_seen = ?, removed = 0, removed_date = NULL
                       WHERE id = ?""",
                    (payload, field_id, hit.get("publication_date"), site, url, ts, hit["id"]))
                counts["reopened"] += row["removed"]

        # Links has no change feed, so an ad it stops listing is closed. Only over a field
        # read completely, and never when a field that held ads comes back empty, which is
        # far likelier to be the API having a bad night than every ad closing at once.
        if not complete:
            print(f"  ! {label}: more ads than one query reaches, nothing closed in it",
                  file=sys.stderr)
            continue
        if not seen and open_before.get(field_id, 0) > 20:
            print(f"  ! {label}: Links listed nothing where {open_before[field_id]} were "
                  f"open. Nothing closed; check the API.", file=sys.stderr)
            counts["suspect_fields"] += 1
            continue
        held = [r["id"] for r in conn.execute(
            "SELECT id FROM links_ads WHERE field_id = ? AND removed = 0", (field_id,))]
        gone = [i for i in held if i not in seen]
        conn.executemany("UPDATE links_ads SET removed = 1, removed_date = ? WHERE id = ?",
                         [(ts, i) for i in gone])
        counts["closed"] += len(gone)
        conn.commit()
    conn.commit()
    return counts


# --------------------------------------------------------------------------
# Reading the full text
# --------------------------------------------------------------------------

BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "section",
         "article", "tr", "table", "header", "footer", "blockquote", "pre", "dd", "dt", "dl"}
VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "area", "base", "col",
        "embed", "param", "track"}
HIDDEN = {"script", "style", "noscript", "template", "svg", "button", "select", "iframe"}


class _Text(HTMLParser):
    """Text out of HTML, with paragraphs and list items kept as lines.

    With `match`, only the first element it accepts is read, and its end is found by counting
    that element's own tag name alone. Pages leave `<p>` and `<li>` unclosed often enough that
    counting every tag runs the capture on past the element; a `<div>` is closed reliably."""

    def __init__(self, match=None):
        super().__init__(convert_charrefs=True)
        self.match = match
        self.name = None
        self.depth = 0 if match else 1
        self.hidden = 0
        self.done = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if self.match and self.name is None:
            if self.match(tag, dict(attrs)):
                self.name, self.depth = tag, 1
            return
        if tag in HIDDEN:
            self.hidden += 1
        if tag == self.name:
            self.depth += 1
        if tag in BLOCK:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("- ")

    def handle_startendtag(self, tag, attrs):
        if not self.done and self.depth and tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.done or not self.depth:
            return
        if tag in HIDDEN and self.hidden:
            self.hidden -= 1
        if tag in BLOCK:
            self.parts.append("\n")
        if self.name and tag == self.name:
            self.depth -= 1
            if self.depth == 0:
                self.done = True

    def handle_data(self, data):
        if self.depth and not self.hidden and not self.done:
            self.parts.append(data)

    def text(self):
        raw = "".join(self.parts).replace("\xa0", " ")
        lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in raw.split("\n")]
        out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
        return re.sub(r"^- *$", "", out, flags=re.M).strip()


def html_to_text(markup, match=None):
    parser = _Text(match)
    parser.feed(markup or "")
    parser.close()
    return parser.text()


def _has_class(attrs, name):
    return name in (attrs.get("class") or "").split()


def _job_postings(node):
    if isinstance(node, list):
        for item in node:
            yield from _job_postings(item)
    elif isinstance(node, dict):
        kind = node.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if "JobPosting" in kinds:
            yield node
        for key in ("@graph", "mainEntity", "itemListElement"):
            if key in node:
                yield from _job_postings(node[key])


def read_jsonld(page):
    """The description of the first schema.org JobPosting in the page's JSON-LD."""
    for block in re.finditer(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>",
                             page, re.S | re.I):
        try:
            data = json.loads(block.group(1).strip(), strict=False)
        except json.JSONDecodeError:
            continue
        for posting in _job_postings(data):
            description = posting.get("description") or ""
            if "<" not in description and "&lt;" in description:
                description = html.unescape(description)      # escaped twice by the site
            text = html_to_text(description)
            if text:
                return text, {}
    return None, {}


def read_microdata(page):
    """The element marked itemprop="description"."""
    text = html_to_text(page, lambda tag, attrs: attrs.get("itemprop") == "description")
    return text or None, {}


def read_offentligajobb(page):
    """The assignment section, and the last day to apply from the facts beside it."""
    text = html_to_text(page, lambda tag, attrs: tag == "div" and _has_class(attrs, "assignment"))
    deadline = re.search(r'id="ctl00_cphBody_txtLastAppDate"[^>]*>\s*(\d{4}-\d{2}-\d{2})', page)
    return text or None, ({"application_deadline": deadline.group(1)} if deadline else {})


READERS = {"jsonld": read_jsonld, "microdata": read_microdata,
           "offentligajobb": read_offentligajobb}


def extract(site, page, brief=None):
    """Run the site's readers in order. Returns (text, reader, extra), or (None, None, {}).

    Text is taken when it is long enough to be an ad, or when it is at least as long as the
    brief Links gave, since then the brief was never cut: an ad for a short gig
    can be under MIN_TEXT from first word to last. A teaser shorter than the brief is
    not the ad."""
    for name in SITES.get(site, ()):
        text, extra = READERS[name](page)
        if enough(text, brief):
            return text, name, extra
    return None, None, {}


def enough(text, brief=None):
    floor = min(MIN_TEXT, int(len((brief or "").strip()) * 0.9) or MIN_TEXT)
    return bool(text) and len(text) >= floor


class NetworkDown(Exception):
    pass


class Reader:
    """One read pass: a session, robots.txt per host, and the pause between pages."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "sv,en"})
        self.robots = {}
        self.last = 0.0

    def _wait(self):
        pause = PAUSE - (time.monotonic() - self.last)
        if pause > 0:
            time.sleep(pause)
        self.last = time.monotonic()

    def _request(self, url):
        for wait in (NETWORK_WAIT, None):
            self._wait()
            try:
                return self.session.get(url, timeout=30, allow_redirects=True)
            except (requests.ConnectionError, requests.Timeout) as err:
                if wait is None:
                    raise NetworkDown(str(err)) from None
                time.sleep(wait)

    def allowed(self, url):
        """robots.txt, read once per host. A missing file allows everything; a file that
        cannot be read at all allows nothing, as the robots.txt convention has it."""
        parts = urlparse(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self.robots:
            rules = RobotFileParser()
            response = self._request(f"{host}/robots.txt")
            if response.status_code >= 500:
                rules.disallow_all = True
            elif response.status_code >= 400:
                rules.allow_all = True
            else:
                rules.parse(response.text.splitlines())
            self.robots[host] = rules
        return self.robots[host].can_fetch(USER_AGENT, url)

    def read(self, site, url, brief=None):
        """Returns (status, text, reader, extra, error)."""
        if not self.allowed(url):
            return "robots", None, None, {}, "robots.txt disallows this page"
        response = self._request(url)
        if response.status_code in (404, 410):
            return "gone", None, None, {}, f"HTTP {response.status_code}"
        if response.status_code != 200:
            return "failed", None, None, {}, f"HTTP {response.status_code}"
        text, reader, extra = extract(site, response.text, brief)
        if text is None:
            return "failed", None, None, {}, f"no text found by {', '.join(SITES[site])}"
        return "read", text, reader, extra, None


def read(conn, retry=False, limit=None):
    """Read the full text of every open ad let in that has none yet, newest first. Free.
    Returns the per-site counts of this pass. With `retry`, ads left alone after
    MAX_ATTEMPTS are tried again, for after a reader is fixed."""
    # Imported here, not at the top: the pre-filter imports this module for its twins.
    from . import prefilter

    ensure(conn)
    cfg = settings()
    cap = "" if retry else f" AND read_attempts < {MAX_ATTEMPTS}"
    candidates = conn.execute(
        f"""SELECT id, site, url, payload, text_status FROM links_ads
            WHERE removed = 0 AND admitted = 1 AND text IS NULL
              AND text_status IN ('unread', 'failed', 'skipped'){cap}
            ORDER BY publication_date DESC""").fetchall()

    # A page is read only for an ad the pre-filter would send to the model. The group
    # verdicts skip close to half of the ads let in, and reading their pages would be asking
    # job sites for text nothing uses. Worked out again on every pass, so an edit to the
    # verdicts or the rescue brings an ad back to be read.
    verdicts = prefilter.load_verdicts()
    terms, veto = prefilter.load_rescue()
    rows = []
    for row in candidates:
        hit = json.loads(row["payload"])
        verdict, _ = prefilter.decide(hit.get("headline"),
                                      (hit.get("occupation_group") or {}).get("label"),
                                      verdicts, terms, veto)
        wanted = verdict == "keep"
        if not wanted and row["text_status"] != "skipped":
            conn.execute("UPDATE links_ads SET text_status = 'skipped' WHERE id = ?", (row["id"],))
        elif wanted and row["text_status"] == "skipped":
            conn.execute("UPDATE links_ads SET text_status = 'unread' WHERE id = ?", (row["id"],))
        if wanted:
            rows.append(row)
    conn.commit()
    rows = rows[:limit] if limit else rows
    pass_utc = now_utc()
    reader = Reader()
    per_site = defaultdict(Counter)
    down = None

    for i, row in enumerate(rows, 1):
        try:
            brief = json.loads(row["payload"]).get("brief")
            status, text, name, extra, error = reader.read(row["site"], row["url"], brief)
        except NetworkDown as err:
            down = str(err)
            break
        per_site[row["site"]][status] += 1
        conn.execute(
            """UPDATE links_ads SET text_status = ?, text = ?, reader = ?, extra = ?,
                   read_attempts = read_attempts + 1, read_utc = ?, read_error = ?
               WHERE id = ?""",
            (status, text, name, json.dumps(extra) if extra else None, pass_utc, error,
             row["id"]))
        conn.commit()
        if i % 25 == 0 or i == len(rows):
            print(f"  read {i} of {len(rows)}")
    if down:
        print(f"  ! the network went away mid-pass, stopped: {down}", file=sys.stderr)

    below, least = float(cfg.get("flag_below", 0.5)), int(cfg.get("flag_min", 3))
    held = dict(conn.execute(
        """SELECT site, COUNT(*) FROM links_ads
           WHERE removed = 0 AND admitted = 1 AND text IS NULL AND text_status != 'skipped'
           GROUP BY site""").fetchall())
    result = {}
    for site, c in per_site.items():
        tried = c["read"] + c["failed"]
        flagged = int(tried >= least and c["read"] / tried < below)
        # A page gone or disallowed says nothing about the reader, so a pass with only those
        # is recorded with nothing tried and neither raises nor clears a flag.
        conn.execute(
            """INSERT INTO links_reads (pass_utc, site, tried, found, failed, gone, held_back,
                                        flagged) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (pass_utc, site, tried, c["read"], c["failed"], c["gone"], held.get(site, 0),
             flagged))
        result[site] = {"tried": tried, "found": c["read"], "failed": c["failed"],
                        "gone": c["gone"], "robots": c["robots"], "flagged": flagged}
    conn.commit()
    return result


# --------------------------------------------------------------------------
# Into the store
# --------------------------------------------------------------------------

def payload_for(row):
    """A JobTech-shaped payload, so everything downstream reads a Links ad as it reads a
    Platsbanken one. The Links hit rides along under `links`."""
    hit = json.loads(row["payload"])
    extra = json.loads(row["extra"] or "{}")
    addresses = hit.get("workplace_addresses") or []
    place = next((a for a in addresses if (a.get("country") or "Sverige") == "Sverige"),
                 addresses[0] if addresses else {})
    group = hit.get("occupation_group") or {}
    return {
        "id": row["id"],
        "headline": hit.get("headline"),
        "description": {"text": row["text"]},
        "employer": {"name": (hit.get("employer") or {}).get("name")},
        "occupation": {"label": group.get("label"), "concept_id": group.get("concept_id")},
        "occupation_group": group,
        "occupation_field": hit.get("occupation_field") or {},
        "workplace_address": {
            "municipality": place.get("municipality"),
            "municipality_concept_id": place.get("municipality_concept_id"),
            "region": place.get("region"),
            "region_concept_id": place.get("region_concept_id"),
            "country": place.get("country"),
            # JobTech's code for Sverige, which the dashboard's location switch reads.
            "country_code": "199" if place.get("country") == "Sverige" else None,
        },
        "webpage_url": row["url"],
        "publication_date": hit.get("publication_date"),
        "application_deadline": extra.get("application_deadline"),
        "source_type": SOURCE,
        "links": {"site": row["site"], "reader": row["reader"], "brief": hit.get("brief"),
                  "source_links": hit.get("source_links"), "workplace_addresses": addresses},
    }


# Words Dutch job ads are full of and Swedish and English ones never use. studentjob.se
# lists Dutch jobs from Dutch job boards and a Dutch staffing firm with no place in Links and
# "SE" as the country on the page, so the address rule lets them in. A Dutch text has at
# least 8 of these words, making up 2 percent of all its words; a Swedish or English text
# has at most one, so the two thresholds in `dutch` separate them cleanly.
DUTCH = {"een", "jouw", "wij", "onze", "naar", "bij", "zijn", "worden", "werkzaamheden",
         "ervaring", "functie", "bedrijf", "wordt", "ben", "heb", "hebt", "kun", "kunt", "binnen",
         "gaat", "meer", "uur", "salaris"}


def dutch(text):
    words = re.findall(r"\w+", (text or "").lower())
    n = sum(1 for w in words if w in DUTCH)
    return n >= 8 and n / max(1, len(words)) >= 0.02


def publish(conn):
    """Write every open ad let in and read to `ads`, and close the ones Links closed. Only
    ads with full text ever reach `ads`. An ad whose text turns out to be a Dutch job is not let
    in after all, and leaves `ads` if it had reached it. Returns counts."""
    counts = Counter()
    for row in conn.execute(
            "SELECT * FROM links_ads WHERE admitted = 1 AND text IS NOT NULL").fetchall():
        if dutch(row["text"]):
            conn.execute("UPDATE links_ads SET admitted = 0, admit_reason = 'abroad' WHERE id = ?",
                         (row["id"],))
            counts["abroad"] += 1
            counts["withdrawn"] += conn.execute("DELETE FROM ads WHERE id = ? AND source = ?",
                                                (row["id"], SOURCE)).rowcount
            continue
        known = conn.execute("SELECT removed FROM ads WHERE id = ?", (row["id"],)).fetchone()
        if row["removed"]:
            if known is not None and not known["removed"]:
                store.upsert(conn, {"id": row["id"], "removed": True,
                                    "removed_date": row["removed_date"]}, SOURCE)
                counts["closed"] += 1
            continue
        counts[store.upsert(conn, payload_for(row), SOURCE)] += 1
        if known is not None and known["removed"]:
            # Links listed it again. JobStream never reopens an ad, so `upsert` does not either.
            conn.execute("UPDATE ads SET removed = 0, removed_date = NULL WHERE id = ?",
                         (row["id"],))
            counts["reopened"] += 1
    conn.commit()
    return counts


def run(conn):
    """What the nightly run calls: fetch, read, publish. Returns a summary dict."""
    print("Links, not on Platsbanken, seven fields ...")
    fetched = fetch(conn)
    print(f"{fetched['listed']} listed, {fetched['new']} new of which {fetched['new_admitted']} "
          f"let in, {fetched['closed']} closed")
    reads = read(conn)
    found = sum(s["found"] for s in reads.values())
    tried = sum(s["tried"] for s in reads.values())
    print(f"full text found on {found} of {tried} pages read")
    published = publish(conn)
    print(f"{published['inserted']} new ads in the store, {published['closed']} closed")
    flags = flagged(conn)
    for f in flags:
        print(f"FLAG  {f['site']}: text on {f['found']} of {f['tried']} pages. Its reader "
              f"needs fixing: `pipeline.links try <url>`.")
    held = held_back(conn)
    if held:
        print("held back, no full text: "
              + ", ".join(f"{n} {why}" for why, n in sorted(held.items())))
    for site in unknown_sites(conn):
        print(f"NEW SITE with no reader: {site['site']}, {site['n']} ads held back")
    return {"added": published["inserted"], "closed": published["closed"],
            "held_back": sum(held.values()), "flags": flags}


# --------------------------------------------------------------------------
# Twins
# --------------------------------------------------------------------------

# Words that name what kind of employer it is rather than which one. One town written with
# "stad" and with "kommun" is one employer; two regions that share only "Region" are two.
GENERIC = {"ab", "aktiebolag", "publ", "kommun", "kommuns", "stad", "stads", "region",
           "regionen", "län", "lans", "sverige", "sweden", "sverige", "i", "och", "of", "the",
           "group", "nordic", "nordics", "förvaltning", "förvaltningen", "kommunstyrelsens",
           "universitet", "university", "högskola", "högskolan", "hb", "kb", "se", "international",
           "it", "avdelningen", "enheten", "koncernkontoret", "huvudkontoret"}
TWIN_DAYS = 60     # a Platsbanken ad published further apart than this is another round


def _words(text):
    return re.findall(r"\w+", (text or "").lower())


def _employer_words(name):
    return {w for w in _words(name) if w not in GENERIC and len(w) >= 3}


def find_twins(conn):
    """{links id: Platsbanken id} for every Links ad that is a job already on Platsbanken.

    Links drops an ad it knows is on Platsbanken, and misses about one in nine, public-sector
    ads above all, where the employer is written differently. A twin has the
    same title, an employer sharing a distinctive word, and was published within TWIN_DAYS of
    the Platsbanken ad, open or closed. Read from `postings`, so it needs `source` there."""
    rows = conn.execute(
        """SELECT id, headline, employer_name, publication_date, source FROM postings"""
    ).fetchall()
    platsbanken = defaultdict(list)
    for r in rows:
        if r["source"] != SOURCE:
            platsbanken[" ".join(_words(r["headline"]))].append(r)
    twins = {}
    for r in rows:
        if r["source"] != SOURCE:
            continue
        mine = _employer_words(r["employer_name"])
        published = (r["publication_date"] or "")[:10]
        best = None
        for other in platsbanken.get(" ".join(_words(r["headline"])), ()):
            if not mine & _employer_words(other["employer_name"]):
                continue
            theirs = (other["publication_date"] or "")[:10]
            if published and theirs:
                apart = abs((datetime.fromisoformat(published)
                             - datetime.fromisoformat(theirs)).days)
                if apart > TWIN_DAYS:
                    continue
            if best is None or (other["publication_date"] or "") > (best["publication_date"] or ""):
                best = other
        if best is not None:
            twins[r["id"]] = best["id"]
    return twins


# --------------------------------------------------------------------------
# Reporting, flags and checks
# --------------------------------------------------------------------------

def _latest_pass(conn):
    ensure(conn)
    row = conn.execute("SELECT MAX(pass_utc) p FROM links_reads").fetchone()
    return row["p"] if row else None


def flagged(conn):
    """The sites whose reader is flagged, for the report, `verify` and the dashboard.

    Judged on each site's own latest pass that answered a page, not on the latest pass
    overall: a night that read nothing from a site says nothing about its reader, so a flag
    stays until a pass that reads that site again finds its text."""
    ensure(conn)
    return [dict(r) for r in conn.execute(
        """SELECT r.site, r.tried, r.found, r.held_back, r.pass_utc FROM links_reads r
           WHERE r.flagged = 1 AND r.pass_utc = (
               SELECT MAX(o.pass_utc) FROM links_reads o
               WHERE o.site = r.site AND o.tried > 0)
           ORDER BY r.site""")]


def held_back(conn):
    """Open ads let in that the pre-filter would keep and that have no text, by why: failed,
    gone, robots, no_reader, and unread for the ones no pass has reached yet. An ad the
    pre-filter skips is not held back, it is never wanted; `status` counts those apart."""
    ensure(conn)
    return dict(conn.execute(
        """SELECT text_status, COUNT(*) FROM links_ads
           WHERE removed = 0 AND admitted = 1 AND text IS NULL AND text_status != 'skipped'
           GROUP BY text_status""").fetchall())


def held_back_total(conn):
    return sum(held_back(conn).values())


def unknown_sites(conn):
    """Sites Links lists that have neither a reader nor a reason for having none."""
    ensure(conn)
    return [dict(r) for r in conn.execute(
        """SELECT site, COUNT(*) n FROM links_ads
           WHERE removed = 0 AND admitted = 1 AND text_status = 'no_reader'
           GROUP BY site ORDER BY n DESC""")
            if r["site"] not in NO_READER]


def status(conn):
    ensure(conn)
    print(f"{'site':<20} {'open':>6} {'let in':>7} {'skipped':>8} {'read':>6} {'held':>6}"
          f"  held back why")
    rows = conn.execute(
        """SELECT COALESCE(site, '(none)') site, COUNT(*) open,
                  SUM(admitted) admitted,
                  SUM(admitted AND text IS NULL AND text_status = 'skipped') skipped,
                  SUM(admitted AND text IS NOT NULL) read,
                  SUM(admitted AND text IS NULL AND text_status != 'skipped') held,
                  GROUP_CONCAT(CASE WHEN admitted AND text IS NULL AND text_status != 'skipped'
                                    THEN text_status END) why
           FROM links_ads WHERE removed = 0 GROUP BY site ORDER BY open DESC""").fetchall()
    for r in rows:
        why = ", ".join(f"{n} {s}" for s, n in Counter((r["why"] or "").split(",")).items() if s)
        print(f"{r['site']:<20} {r['open']:>6} {r['admitted']:>7} {r['skipped']:>8} "
              f"{r['read']:>6} {r['held']:>6}  {why}")
    print("skipped: let in, but the pre-filter would skip it, so its page is not read")
    reasons = dict(conn.execute(
        "SELECT admit_reason, COUNT(*) FROM links_ads WHERE removed = 0 GROUP BY admit_reason"))
    print(f"\nnot let in: {reasons.get('too_old', 0)} too old, {reasons.get('abroad', 0)} abroad")
    in_store = conn.execute("SELECT COUNT(*) c FROM ads WHERE source = ? AND removed = 0",
                            (SOURCE,)).fetchone()["c"]
    print(f"open in the store: {in_store}")
    last = _latest_pass(conn)
    if last:
        print(f"\nlatest read pass, {last}:")
        for r in conn.execute("SELECT * FROM links_reads WHERE pass_utc = ? ORDER BY site",
                              (last,)):
            print(f"  {r['site']:<20} text on {r['found']} of {r['tried']}, {r['gone']} gone"
                  + ("   FLAGGED" if r["flagged"] else ""))
    for site in unknown_sites(conn):
        print(f"\nNEW SITE with no reader: {site['site']}, {site['n']} ads held back")


def try_url(url, site=None):
    """What each reader makes of one page. Where fixing a reader starts."""
    site = site or next((s for s in SITES if s.split(".")[-2] in urlparse(url).netloc), None)
    reader = Reader()
    print(f"site {site or 'unknown'}, robots.txt {'allows' if reader.allowed(url) else 'DISALLOWS'} it")
    response = reader._request(url)
    print(f"HTTP {response.status_code}, {len(response.text):,} characters\n")
    for name, fn in READERS.items():
        text, extra = fn(response.text)
        length = len(text or "")
        mark = "enough" if length >= MIN_TEXT else "too short" if length else "nothing"
        print(f"--- {name}: {length} characters, {mark} {extra or ''}")
        if text:
            print(textwrap_preview(text))


def textwrap_preview(text, chars=600):
    return text[:chars] + (" ..." if len(text) > chars else "")


CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn)); return fn
    return deco


@check("no Platsbanken ad came in through Links")
def _c1(conn):
    n = sum(1 for (payload,) in conn.execute("SELECT payload FROM links_ads")
            if PLATSBANKEN in _labels(json.loads(payload)))
    return n == 0, f"{n} Links ads list Platsbanken as a source"


@check("every ad from other sites in the store has its full text")
def _c2(conn):
    short = 0
    for (payload,) in conn.execute("SELECT payload FROM ads WHERE source = ?", (SOURCE,)):
        ad = json.loads(payload)
        short += not enough((ad.get("description") or {}).get("text"),
                            (ad.get("links") or {}).get("brief"))
    n = conn.execute("SELECT COUNT(*) c FROM ads WHERE source = ?", (SOURCE,)).fetchone()["c"]
    return short == 0, f"{n} in the store, {short} without full text"


@check("an ad held back or not let in never reached the store")
def _c3(conn):
    n = conn.execute(
        """SELECT COUNT(*) c FROM ads a JOIN links_ads l ON l.id = a.id
           WHERE l.admitted = 0 OR l.text IS NULL""").fetchone()["c"]
    return n == 0, f"{n} in the store that should not be"


@check("an ad Links closed is closed in the store")
def _c4(conn):
    n = conn.execute(
        """SELECT COUNT(*) c FROM ads a JOIN links_ads l ON l.id = a.id
           WHERE l.removed != a.removed""").fetchone()["c"]
    return n == 0, f"{n} open in one and closed in the other"


@check("no site's reader is flagged in the latest read pass")
def _c5(conn):
    flags = flagged(conn)
    detail = "; ".join(f"{f['site']} found text on {f['found']} of {f['tried']}" for f in flags)
    return not flags, detail or "none flagged"


@check("every site Links lists has a reader or a reason for having none")
def _c6(conn):
    new = unknown_sites(conn)
    return not new, (", ".join(f"{s['site']} ({s['n']} ads)" for s in new)
                     or f"{len(SITES)} with a reader, {len(NO_READER)} without, none new")


def verify(conn):
    ensure(conn)
    failed = 0
    for name, fn in CHECKS:
        try:
            ok, detail = fn(conn)
        except Exception as e:
            ok, detail = False, f"raised {e}"
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")
        failed += not ok
    print(f"\n{len(CHECKS) - failed}/{len(CHECKS)} checks passed")
    return failed


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["run", "fetch", "read", "status", "verify", "try"])
    ap.add_argument("url", nargs="?", help="try: the page to read")
    ap.add_argument("--retry", action="store_true",
                    help=f"read: also ads left alone after {MAX_ATTEMPTS} attempts, for after "
                         f"a reader is fixed")
    ap.add_argument("--limit", type=int, help="read: at most this many pages")
    args = ap.parse_args()

    if args.mode == "try":
        if not args.url:
            raise SystemExit("try needs a URL")
        try_url(args.url)
        return
    conn = store.connect()
    ensure(conn)
    if args.mode == "run":
        run(conn)
        print()
        sys.exit(1 if verify(conn) else 0)
    elif args.mode == "fetch":
        print(dict(fetch(conn)))
    elif args.mode == "read":
        for site, c in sorted(read(conn, retry=args.retry, limit=args.limit).items()):
            print(f"  {site:<20} {c}")
        print(f"held back, by why: {held_back(conn)}")
    elif args.mode == "verify":
        sys.exit(1 if verify(conn) else 0)
    else:
        status(conn)


if __name__ == "__main__":
    main()
