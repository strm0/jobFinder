"""What the dashboard reads from the store, and the two things it writes there.

The ranking comes from `scores` and nothing here computes a score: the rule `tools/top.py`
follows, and its version and staleness checks are imported rather than copied. Lanes, page
sizes and the Stockholm area come from `context/02_search_config.yaml` and are never copied
here.

Two page designs read this. An earlier page design that is not in this repository gets the
rules it was built with, and every keyword argument below defaults to them. The new design also gets the location switch, the New filter, the newer rule for
what counts as new, and the rejected, applied and removed views; the server asks for those under
/api/v2/.

The store also holds ads from other job sites, through JobAd Links. The new design mixes them
into every list with a tag and a switch between all, Platsbanken and other sites. The
earlier design stays Platsbanken only.

The writes are the user's own and nothing else. A star is `posting_state.status =
'shortlisted'` and an applied mark is `'applied'`, statuses the config's posting schema already
names, so both land in the table `pipeline/archive.py` snapshots. A removal is
`posting_state.dismissed_utc`, a column in the same table, so the snapshot keeps it too and a
star survives it. A visit is a row in
`dashboard_visits`, which decides what counts as new. `classifications` is never written, so
no paid row can be touched from here.
"""

import json
import math
import re
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import links  # noqa: E402  the reader flags, one copy
DB = ROOT / "data" / "postings.db"
CONFIG = ROOT / "context" / "02_search_config.yaml"
APPLICATIONS = ROOT / "applications"

sys.path.insert(0, str(ROOT / "tools"))
import top  # noqa: E402  current_version and check_scores, one copy of each

# Visits closer together than this are one sitting, so reloading the page does not clear the
# new marks: new means new since the user last looked.
SITTING = timedelta(hours=2)
NEVER = "9999"          # a baseline no timestamp is later than
STARRED = "shortlisted"
APPLIED = "applied"
LIST_VIEWS = ("top", "lanes", "phd", "favourites")
PLACES = ("all", "stockholm", "outside")
# Where an ad came from, `postings.source`. Other is every job site JobAd Links lists.
SOURCES = ("all", "platsbanken", "other")
SPECIMEN_SOURCE = "platsbanken"
SWEDEN = "199"          # JobTech's country_code for Sverige
NEEDED = ("ads", "postings", "classifications", "scores", "signals", "posting_state",
          "pipeline_runs")

# What makes a job new, named by the column that says when it arrived. The earlier design counts a
# job from when it was fetched. The new design counts it from when it was classified, so that
# new covers every run since the user last looked. The two differ whenever one run fetches and
# a later one classifies: the first rule then misses every job fetched before the last visit
# and classified after it.
SPECIMEN_RULE = "first_seen"
CURRENT_RULE = "classified_at"
NEW_RULES = {SPECIMEN_RULE: "p.first_seen", CURRENT_RULE: "c.classified_at"}

VISITS = """
CREATE TABLE IF NOT EXISTS dashboard_visits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_utc   TEXT NOT NULL,
    last_seen_utc TEXT NOT NULL
);
"""

# Open, eligible and not a folded repost: what `tools/top.py` lists, as SQL.
SHOWN = """
    FROM classifications c
    JOIN scores s ON s.id = c.id
    JOIN postings p ON p.id = c.id
    LEFT JOIN posting_state st ON st.id = c.id
    WHERE c.classifier_version = :version AND p.removed = 0
      AND s.eligible = 1 AND s.repost_of IS NULL"""

# Every starred job, closed ones included, so a job that closes after it is starred shows as
# closed instead of silently disappearing.
FAVOURITES = """
    FROM posting_state st
    JOIN postings p ON p.id = st.id
    LEFT JOIN classifications c ON c.id = st.id AND c.classifier_version = :version
    LEFT JOIN scores s ON s.id = st.id
    WHERE st.status = :starred"""

# The rejected view: open jobs the model read and put in no lane, with no hard filter or pay
# rule against them. It is for looking past what the system knows about the candidate, so the
# jobs a hard filter stopped and the ones never sent to the model stay out. Reposts are
# deliberately not folded here.
REJECTED = """
    FROM classifications c
    JOIN scores s ON s.id = c.id
    JOIN postings p ON p.id = c.id
    LEFT JOIN posting_state st ON st.id = c.id
    WHERE c.classifier_version = :version AND p.removed = 0
      AND s.reject_reason = 'no_lane_matched'"""

# Every job marked applied, closed ones included, as Saved keeps them. A job is saved or
# applied, never both, since both are `posting_state.status`, so a saved job marked applied moves
# here.
APPLIED_LIST = """
    FROM posting_state st
    JOIN postings p ON p.id = st.id
    LEFT JOIN classifications c ON c.id = st.id AND c.classifier_version = :version
    LEFT JOIN scores s ON s.id = st.id
    WHERE st.status = :applied"""

# In the new design an applied job shows in Applied only, so the ranked lists leave it out.
NOT_APPLIED = "\n      AND COALESCE(st.status, '') != :applied"

# Removed, in the new design only: the jobs taken off the lists with a card's x, closed ones
# included, as Saved keeps them. A job waits here until a run starts after its removal, and from
# then on it shows nowhere, so Removed holds only what was removed since the last run. A removal
# is its own column rather than a status, so Restore puts a saved job back in Saved. The page
# says Removed and the code says dismissed, because `removed` already means JobTech closed the
# ad.
DISMISSED_LIST = """
    FROM posting_state st
    JOIN postings p ON p.id = st.id
    LEFT JOIN classifications c ON c.id = st.id AND c.classifier_version = :version
    LEFT JOIN scores s ON s.id = st.id
    WHERE st.dismissed_utc >= :cleared"""

# Every other list leaves out every removed job, including those gone for good.
NOT_DISMISSED = "\n      AND st.dismissed_utc IS NULL"

# The store predates removals, so the dashboard adds the column when it starts.
# `pipeline/normalise.py` creates it in a new store.
DISMISSED_COLUMN = "ALTER TABLE posting_state ADD COLUMN dismissed_utc TEXT"

IN_LANE = """
      AND EXISTS (SELECT 1 FROM json_each(c.matched_lanes) j
                  WHERE json_extract(j.value, '$.id') = :lane_id)"""

COLUMNS = """p.id, c.track, c.matched_lanes, c.want, c.reach, c.want_why, c.reach_why,
    c.summary, s.recommend, p.headline, p.employer_name, p.municipality,
    p.region_concept_id, p.country_code, p.employment_type, p.application_deadline,
    p.first_seen, c.classified_at, p.removed, p.webpage_url, st.status, st.updated_at,
    st.dismissed_utc, p.source, p.source_site"""


class StoreError(Exception):
    """The store cannot answer: a table is missing or nothing is classified yet."""


class NotFound(Exception):
    """No such job in the store."""


class BadRequest(Exception):
    """A view, lane or place the dashboard does not have."""


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def connect():
    if not DB.exists():
        raise StoreError(f"There is no store at {DB}. See the README.")
    conn = sqlite3.connect(DB, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def prepare(conn):
    """Check the store holds what the dashboard reads, and create the visits table and the
    removal column."""
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    missing = [t for t in NEEDED if t not in have]
    if missing:
        raise StoreError(f"The store has no {', '.join(missing)} table. "
                         "Run `python -m pipeline.nightly run` first.")
    if "source" not in {r[1] for r in conn.execute("PRAGMA table_info(postings)")}:
        raise StoreError("The store's postings predate ads from other job sites. Rebuild them, "
                         "free: python -m pipeline.normalise rebuild")
    conn.executescript(VISITS)
    if "dismissed_utc" not in {r[1] for r in conn.execute("PRAGMA table_info(posting_state)")}:
        conn.execute(DISMISSED_COLUMN)
        conn.commit()


def cleared_since(conn):
    """When the last run started. A job removed before then is gone for good, and one removed
    after it waits in Removed. Before the first run nothing is cleared."""
    run = conn.execute("SELECT started_utc FROM pipeline_runs ORDER BY id DESC LIMIT 1").fetchone()
    if run is None:
        return ""
    started = datetime.fromisoformat(run["started_utc"]).astimezone(timezone.utc)
    return started.replace(microsecond=0).isoformat()


_config = {"mtime": None, "value": None}
_config_lock = threading.Lock()


def config():
    """The parsed config, read again only when the file has changed."""
    mtime = CONFIG.stat().st_mtime
    with _config_lock:
        if _config["mtime"] != mtime:
            _config["value"] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
            _config["mtime"] = mtime
        return _config["value"]


def lanes(cfg, short_names=False):
    """The lanes from the config. The new design also gets each lane's card-sized `short`
    label, falling back to the full name; the earlier design's answers do not carry it."""
    rows = []
    for lane in cfg["lanes"]:
        row = {"code": lane["id"].split("_")[0], "id": lane["id"], "name": lane["name"]}
        if short_names:
            row["short"] = lane.get("short") or lane["name"]
        rows.append(row)
    return rows


def page_size(cfg, view):
    views = {v["id"]: v for v in cfg["dashboard"]["views"]}
    key = {"top": "top_picks", "lanes": "by_lane", "phd": "phd",
           "favourites": "top_picks", "rejected": "rejected", "applied": "applied",
           "dismissed": "dismissed"}[view]
    return int(views[key]["page_size"])


def stockholm_regions(cfg):
    try:
        return list(cfg["dashboard"]["location_switch"]["stockholm_regions"])
    except (KeyError, TypeError):
        raise StoreError("The config has no dashboard.location_switch.stockholm_regions, "
                         "so the location switch cannot tell where Stockholm is.") from None


def location_warning(conn):
    """A sentence when a Stockholm region in the config matches no ad or a different county,
    either of which would quietly file every Stockholm job under outside. Otherwise None."""
    try:
        regions = stockholm_regions(config())
    except StoreError as err:
        return str(err)
    problems = []
    for region in regions:
        found = conn.execute("SELECT region FROM postings WHERE region_concept_id = ? LIMIT 1",
                             (region["id"],)).fetchone()
        if found is None:
            problems.append(f"{region['id']} matches no ad in the store")
        elif found["region"] != region["name"]:
            problems.append(f"{region['id']} is {found['region']} in the store, "
                            f"not {region['name']}")
    if not regions:
        problems.append("it names no region")
    if not problems:
        return None
    return ("The location switch will misfile jobs. In dashboard.location_switch in the config, "
            + "; ".join(problems) + ".")


def place_filter(cfg, place):
    """SQL and parameters that narrow a list to Stockholm or to outside it; nothing for all.

    A card is wherever any of its cities is, the open reposts folded into it included, so a
    job posted in Stockholm and Malmö is in both. Every open ad has a county or no place at
    all. With none, a foreign country means abroad, which is outside, and Sweden means the ad
    gives no place, which shows in both so that a missing field never hides a job."""
    if place not in PLACES:
        raise BadRequest(f"There is no place called {place!r}.")
    if place == "all":
        return "", {}
    ids = [str(region["id"]) for region in stockholm_regions(cfg)]
    if not ids:
        raise StoreError("The config names no Stockholm region, so the location switch "
                         "cannot tell where Stockholm is.")
    params = {f"region{i}": rid for i, rid in enumerate(ids)}
    marks = ", ".join(f":{name}" for name in params)
    params["sweden"] = SWEDEN

    def flags(t):
        inside = f"COALESCE({t}.region_concept_id IN ({marks}), 0)"
        outside = (f"CASE WHEN {t}.region_concept_id IS NOT NULL "
                   f"THEN {t}.region_concept_id NOT IN ({marks}) "
                   f"ELSE COALESCE({t}.country_code, :sweden) != :sweden END")
        return inside, outside

    def anywhere(own, folded):
        # Not correlated, so SQLite works the reposts out once per query, not once per card.
        # A copy from another job site folded under a Platsbanken card is the same job, not
        # another city, so only reposts from the card's own source count.
        return (f"({own} OR p.id IN (SELECT r.repost_of FROM scores r "
                f"JOIN postings q ON q.id = r.id JOIN postings t ON t.id = r.repost_of "
                f"WHERE r.repost_of IS NOT NULL AND q.removed = 0 AND q.source = t.source "
                f"AND {folded}))")

    own_in, own_out = flags("p")
    folded_in, folded_out = flags("q")
    has_in, has_out = anywhere(own_in, folded_in), anywhere(own_out, folded_out)
    wanted, other = (has_in, has_out) if place == "stockholm" else (has_out, has_in)
    return f"\n      AND ({wanted} OR NOT {other})", params


def source_filter(source):
    """SQL that narrows a list to Platsbanken or to other job sites; nothing for all."""
    if source not in SOURCES:
        raise BadRequest(f"There is no source called {source!r}.")
    if source == "all":
        return ""
    return f"\n      AND p.source {'=' if source == 'other' else '!='} 'links'"


def reader_flags(conn):
    """The job sites whose reader has stopped finding the ad text, from `pipeline/links.py`,
    so the page can say which one needs fixing. A reader can only be fixed once something
    flags it."""
    return [{"site": f["site"], "tried": f["tried"], "found": f["found"],
             "heldBack": f["held_back"]} for f in links.flagged(conn)]


def folder_key(job_id):
    """How a job's id ends its application folder's name. A Links id is 32 characters, so
    its first 10 stand for it, a length no Platsbanken ad number has."""
    return job_id if len(job_id) <= 12 else job_id[:10]


def new_filter(rule, only_new):
    return f"\n      AND {NEW_RULES[rule]} > :baseline" if only_new else ""


def version(conn):
    try:
        return top.current_version(conn)
    except SystemExit as stop:
        raise StoreError(str(stop)) from None


def staleness(conn, current):
    """`tools/top.py`'s staleness checks, as plain text the page can show, or None."""
    try:
        warning = top.check_scores(conn, current)
    except SystemExit as stop:
        return str(stop)
    if not warning:
        return None
    return re.sub(r"^> ?", "", warning, flags=re.M).replace("**", "").replace("`", "").strip()


def record_visit(conn, rule=SPECIMEN_RULE):
    """Log this visit and return the moment after which a job counts as new."""
    now = now_utc()
    last = conn.execute(
        "SELECT id, last_seen_utc FROM dashboard_visits ORDER BY id DESC LIMIT 1").fetchone()
    if last and now - datetime.fromisoformat(last["last_seen_utc"]) < SITTING:
        sitting = last["id"]
        conn.execute("UPDATE dashboard_visits SET last_seen_utc = ? WHERE id = ?",
                     (now.isoformat(), sitting))
    else:
        sitting = conn.execute(
            "INSERT INTO dashboard_visits (started_utc, last_seen_utc) VALUES (?, ?)",
            (now.isoformat(), now.isoformat())).lastrowid
    conn.commit()
    before = conn.execute(
        "SELECT last_seen_utc FROM dashboard_visits WHERE id < ? ORDER BY id DESC LIMIT 1",
        (sitting,)).fetchone()
    if before:
        return before["last_seen_utc"]
    # The very first visit: whatever the last nightly run brought in counts as new. Under the
    # classified rule that is the last run that classified anything, because a run without
    # --yes brings ads in and leaves them unclassified.
    only = " WHERE classified_new > 0" if rule == CURRENT_RULE else ""
    run = conn.execute(
        f"SELECT started_utc FROM pipeline_runs{only} ORDER BY id DESC LIMIT 1").fetchone()
    return run["started_utc"] if run else None


def overview(conn, baseline, rule=SPECIMEN_RULE, place="all", short_names=False,
             rejected_view=False, applied_view=False, dismissed_view=False,
             source=SPECIMEN_SOURCE):
    """The counts around the list: lanes, new marks, favourites, the rejected, applied and removed
    views when asked for, and the last run. With a place, every count but the last run's is for
    that place only. With the applied view, an applied job counts in Applied and nowhere else, and
    with the removed view a removed job counts in Removed until the next run, then nowhere."""
    cfg = config()
    where, place_params = place_filter(cfg, place)
    where += source_filter(source)
    everywhere = place == "all" and source == "all"
    current = version(conn)
    params = {"version": current, "baseline": baseline or NEVER, "applied": APPLIED,
              **place_params}
    arrived = NEW_RULES[rule]
    kept = NOT_DISMISSED if dismissed_view else ""
    hidden = (NOT_APPLIED if applied_view else "") + kept

    def count(extra, source=SHOWN, **more):
        n, fresh = conn.execute(
            f"SELECT COUNT(*), COALESCE(SUM({arrived} > :baseline), 0) "
            f"{source} {extra}{hidden}{where}",
            {**params, **more}).fetchone()
        return n, fresh

    top_n, top_new = count("AND c.track = 'industry'")
    phd_n, phd_new = count("AND c.track = 'phd'")
    lane_rows = []
    for lane in lanes(cfg, short_names):
        n, fresh = count("AND c.track = 'industry'" + IN_LANE, lane_id=lane["id"])
        lane_rows.append({**lane, "count": n, "newCount": fresh})
    if everywhere:
        favourites = starred_total(conn, dismissed_view)
    else:
        favourites = conn.execute(
            f"SELECT COUNT(*) {FAVOURITES}{kept}{where}",
            {**params, "starred": STARRED}).fetchone()[0]
    run = conn.execute(
        """SELECT id, started_utc, ads_added, ads_closed, ads_open
           FROM pipeline_runs ORDER BY id DESC LIMIT 1""").fetchone()
    result = {
        "classifierVersion": current,
        "warning": staleness(conn, current),
        "lanes": lane_rows,
        "counts": {"top": top_n, "phd": phd_n, "favourites": favourites},
        "newCounts": {"top": top_new, "phd": phd_new},
        "run": None if run is None else {
            "id": run["id"], "startedUtc": run["started_utc"], "added": run["ads_added"] or 0,
            "removed": run["ads_closed"] or 0, "open": run["ads_open"] or 0,
        },
    }
    if rejected_view:
        result["counts"]["rejected"], result["newCounts"]["rejected"] = count("", source=REJECTED)
    if applied_view:
        if everywhere:
            result["counts"]["applied"] = applied_total(conn)
        else:
            result["counts"]["applied"] = conn.execute(
                f"SELECT COUNT(*) {APPLIED_LIST}{where}", params).fetchone()[0]
    if dismissed_view:
        if everywhere:
            result["counts"]["dismissed"] = dismissed_total(conn)
        else:
            result["counts"]["dismissed"] = conn.execute(
                f"SELECT COUNT(*) {DISMISSED_LIST}{where}",
                {**params, "cleared": cleared_since(conn)}).fetchone()[0]
    return result


def jobs(conn, view, lane_code, page, baseline, rule=SPECIMEN_RULE, place="all",
         only_new=False, short_names=False, rejected_view=False, applied_view=False,
         dismissed_view=False, offset=None, source=SPECIMEN_SOURCE):
    """One page of one list, ranked the way `dashboard.views` in the config says, narrowed to
    a place and to the new jobs when asked. Neither narrowing changes the order. With the
    applied view, an applied job shows in Applied and in no other list, and with the removed
    view a removed job shows in Removed until the next run, then nowhere. An `offset` starts the
    page at that job rather than at a page boundary, so a page that has taken a removed job out
    of what it shows can ask for the next ten without skipping one."""
    known = (LIST_VIEWS + (("rejected",) if rejected_view else ())
             + (("applied",) if applied_view else ())
             + (("dismissed",) if dismissed_view else ()))
    if view not in known:
        raise BadRequest(f"There is no view called {view!r}.")
    sources = source
    cfg = config()
    where, place_params = place_filter(cfg, place)
    current = version(conn)
    size = page_size(cfg, view)
    names = {lane["id"]: lane for lane in lanes(cfg, short_names)}
    params = {"version": current, "baseline": baseline or NEVER, "starred": STARRED,
              "applied": APPLIED, **place_params}

    if view == "favourites":
        source, order = FAVOURITES, "p.removed ASC, s.recommend DESC, p.publication_date DESC"
    elif view == "applied":
        source, order = APPLIED_LIST, "st.updated_at DESC, p.publication_date DESC"
    elif view == "dismissed":
        source, order = DISMISSED_LIST, "st.dismissed_utc DESC, p.publication_date DESC"
        params["cleared"] = cleared_since(conn)
    elif view == "rejected":
        source, order = REJECTED, "s.recommend DESC, p.publication_date DESC"
    elif view == "phd":
        source = SHOWN + " AND c.track = 'phd'"
        order = "s.recommend DESC, p.application_deadline ASC"
    else:
        source = SHOWN + " AND c.track = 'industry'"
        order = "s.recommend DESC, p.publication_date DESC"
        if view == "lanes":
            lane = next((l for l in names.values() if l["code"] == lane_code), None)
            if lane is None:
                raise BadRequest(f"There is no lane called {lane_code!r}.")
            source += IN_LANE
            params["lane_id"] = lane["id"]
    if applied_view and view not in ("favourites", "applied", "dismissed"):
        source += NOT_APPLIED
    if dismissed_view and view != "dismissed":
        source += NOT_DISMISSED
    source += new_filter(rule, only_new) + where + source_filter(sources)

    total = conn.execute(f"SELECT COUNT(*) {source}", params).fetchone()[0]
    pages = max(1, math.ceil(total / size))
    if offset is None:
        page = min(max(1, page), pages)
        offset = (page - 1) * size
    else:
        offset = max(0, offset)
        page = min(offset // size + 1, pages)
    rows = conn.execute(
        f"SELECT {COLUMNS} {source} ORDER BY {order} LIMIT :limit OFFSET :offset",
        {**params, "limit": size, "offset": offset}).fetchall()
    others = other_cities(conn, [r["id"] for r in rows])
    leads = lead_cities(conn, cfg, rows, place)
    folders = application_folders()
    return {
        "view": view, "total": total, "page": page, "pages": pages, "pageSize": size,
        "jobs": [card(r, names, others, baseline,
                      None if view in ("favourites", "applied", "dismissed") else offset + i + 1,
                      rule, leads.get(r["id"]), short_names, folders, applied_view,
                      dismissed_view, sources_view=short_names)
                 for i, r in enumerate(rows)],
    }


def application_folders():
    """Every folder in `applications/`, by the job it belongs to. A folder is a job's when its
    name ends in " - " and the job id, or is the id alone, so everything before the id can be
    renamed by hand and the folder is still found."""
    if not APPLICATIONS.is_dir():
        return {}
    return {folder.name.rsplit(" - ", 1)[-1]: folder
            for folder in APPLICATIONS.iterdir() if folder.is_dir()}


def other_cities(conn, ids):
    """The cities of the exact reposts folded into each card, per `scores.repost_of`."""
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    cities = {}
    for r in conn.execute(
            f"""SELECT s.repost_of, p.municipality FROM scores s JOIN postings p ON p.id = s.id
                JOIN postings t ON t.id = s.repost_of
                WHERE s.repost_of IN ({marks}) AND p.removed = 0 AND p.source = t.source""",
            ids):
        if r["municipality"]:
            cities.setdefault(r["repost_of"], set()).add(r["municipality"])
    return cities


def lead_cities(conn, cfg, rows, place):
    """With a place chosen, each card's cities with one inside that place first. A card sits
    wherever any of its cities is, so a Stockholm list reads "Solna and 2 more", not "Malmö and
    2 more". Nothing for all, and nothing for a card whose ad gives no place."""
    if place == "all" or not rows:
        return {}
    stockholm = {str(region["id"]) for region in stockholm_regions(cfg)}

    def fits(region, country):
        if place == "stockholm":
            return region in stockholm
        if region is not None:
            return region not in stockholm
        return (country or SWEDEN) != SWEDEN

    ids = [r["id"] for r in rows]
    places = {r["id"]: [(r["municipality"], r["region_concept_id"], r["country_code"])] for r in rows}
    marks = ",".join("?" * len(ids))
    for r in conn.execute(
            f"""SELECT s.repost_of, p.municipality, p.region_concept_id, p.country_code
                FROM scores s JOIN postings p ON p.id = s.id
                JOIN postings t ON t.id = s.repost_of
                WHERE s.repost_of IN ({marks}) AND p.removed = 0 AND p.source = t.source""",
            ids):
        places[r["repost_of"]].append((r["municipality"], r["region_concept_id"], r["country_code"]))
    leads = {}
    for job_id, found in places.items():
        named = [p for p in found if p[0]]
        first = next((p for p in named if fits(p[1], p[2])), None)
        if first is not None:
            leads[job_id] = (first[0], sorted({p[0] for p in named} - {first[0]}))
    return leads


def card(row, names, others, baseline, rank, rule=SPECIMEN_RULE, lead=None, short_names=False,
         folders=None, applied_view=False, dismissed_view=False, sources_view=False):
    matched = json.loads(row["matched_lanes"] or "[]")
    kind = row["employment_type"]
    arrived = row[rule]
    city = row["municipality"]
    other = sorted(others.get(row["id"], set()) - {city})
    if lead is not None:
        city, other = lead
    lane_rows = []
    for lane in matched:
        known = names.get(lane["id"], {})
        item = {"code": lane["id"].split("_")[0], "name": known.get("name", lane["id"]),
                "fit": lane.get("fit")}
        if short_names:
            item["short"] = known.get("short", item["name"])
        lane_rows.append(item)
    result = {
        "id": row["id"],
        "rank": rank,
        "title": row["headline"] or "Untitled",
        "employer": row["employer_name"],
        "city": city,
        "otherCities": other,
        "lanes": lane_rows,
        "summary": row["summary"],
        "score": None if row["recommend"] is None else round(row["recommend"], 2),
        "want": row["want"],
        "reach": row["reach"],
        "wantWhy": row["want_why"],
        "reachWhy": row["reach_why"],
        "applyBy": (row["application_deadline"] or "")[:10] or None,
        "employmentType": re.sub(r"\s*\(.*\)\s*$", "", kind) if kind else None,
        "url": row["webpage_url"]
               or f"/demo/ad/{row['id']}",
        "isNew": bool(baseline and arrived and arrived > baseline),
        "starred": row["status"] == STARRED,
        "closed": bool(row["removed"]),
        "hasApplication": folder_key(row["id"]) in (application_folders() if folders is None
                                                    else folders),
    }
    if sources_view:
        result["source"] = row["source"]
        result["site"] = row["source_site"]
    if applied_view:
        result["applied"] = row["status"] == APPLIED
        result["appliedAt"] = row["updated_at"] if result["applied"] else None
    if dismissed_view:
        result["dismissed"] = row["dismissed_utc"] is not None
    return result


def starred_total(conn, dismissed_view=False):
    """Every starred job wherever it is, so an empty Favourites can tell "nothing starred" apart
    from "nothing starred in this place". With the removed view a removed job is not counted."""
    kept = " AND dismissed_utc IS NULL" if dismissed_view else ""
    return conn.execute(
        f"SELECT COUNT(*) FROM posting_state WHERE status = ?{kept}", (STARRED,)).fetchone()[0]


def set_star(conn, job_id, starred):
    if conn.execute("SELECT 1 FROM postings WHERE id = ?", (job_id,)).fetchone() is None:
        raise NotFound(f"There is no job {job_id} in the store.")
    conn.execute(
        """INSERT INTO posting_state (id, status, updated_at) VALUES (?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET status = excluded.status,
                                         updated_at = excluded.updated_at""",
        (job_id, STARRED if starred else "new", now_utc().isoformat()))
    conn.commit()
    return {"id": job_id, "starred": starred}


def applied_total(conn):
    """Every applied job wherever it is, so an empty Applied can tell "nothing applied yet" apart
    from "nothing applied in this place"."""
    return conn.execute(
        "SELECT COUNT(*) FROM posting_state WHERE status = ?", (APPLIED,)).fetchone()[0]


def set_applied(conn, job_id, applied):
    """Mark a job applied, or undo it. Applied and saved share `posting_state.status`, so a saved
    job marked applied leaves Saved, and undoing makes it an ordinary job again rather than a
    saved one. Undoing only touches a job that is applied, so it can never clear a star. An
    applied job is never removed, so marking one applied restores it."""
    if conn.execute("SELECT 1 FROM postings WHERE id = ?", (job_id,)).fetchone() is None:
        raise NotFound(f"There is no job {job_id} in the store.")
    now = now_utc().isoformat()
    if applied:
        conn.execute(
            """INSERT INTO posting_state (id, status, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET status = excluded.status,
                                             updated_at = excluded.updated_at,
                                             dismissed_utc = NULL""",
            (job_id, APPLIED, now))
    else:
        conn.execute(
            "UPDATE posting_state SET status = 'new', updated_at = ? WHERE id = ? AND status = ?",
            (now, job_id, APPLIED))
    conn.commit()
    return {"id": job_id, "applied": applied, "appliedAt": now if applied else None}


def dismissed_total(conn):
    """Every job in Removed wherever it is, so an empty Removed can tell "nothing removed" apart
    from "nothing removed in this place"."""
    return conn.execute("SELECT COUNT(*) FROM posting_state WHERE dismissed_utc >= ?",
                        (cleared_since(conn),)).fetchone()[0]


def set_dismissed(conn, job_id, dismissed):
    """Take a job off the lists into Removed, or restore it. The removal is its own column, so a
    star is kept through both and a saved job restored is saved again. A job still removed when
    the next run starts is gone for good: it stays in the store with its removal, so the nightly
    fetch never brings it back as new. An applied job has no x and cannot be removed."""
    if conn.execute("SELECT 1 FROM postings WHERE id = ?", (job_id,)).fetchone() is None:
        raise NotFound(f"There is no job {job_id} in the store.")
    now = now_utc().isoformat()
    if dismissed:
        state = conn.execute("SELECT status FROM posting_state WHERE id = ?", (job_id,)).fetchone()
        if state is not None and state["status"] == APPLIED:
            raise BadRequest("An applied job cannot be removed. Undo Mark applied first.")
        conn.execute(
            """INSERT INTO posting_state (id, status, updated_at, dismissed_utc)
               VALUES (?, 'new', ?, ?)
               ON CONFLICT(id) DO UPDATE SET dismissed_utc = excluded.dismissed_utc""",
            (job_id, now, now))
    else:
        conn.execute("UPDATE posting_state SET dismissed_utc = NULL WHERE id = ?", (job_id,))
    conn.commit()
    return {"id": job_id, "dismissed": dismissed}
