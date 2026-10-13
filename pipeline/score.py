"""`recommend`, the one number both dashboard views sort on. Free to re-run.

    python -m pipeline.score rebuild    # drop and rebuild `scores`
    python -m pipeline.score verify     # the must_hold rules, as checks
    python -m pipeline.score status     # what is in the table
    python -m pipeline.score preview    # reorder in memory, write nothing

No API, no key, no cost. Every input is already on disk: `want` and `reach` from
`classifications`, the term hits from `signals`, the lane weights from the config. A
wrong formula here is a free re-run, which is the whole reason the model's paid
judgement is kept in its own table.

ELIGIBILITY, which decides the rejected view, reads three more things, all free: the ad
text, to drop a citizenship hit when the ad names no real bar; `salary_type`, to reject
commission-only pay; and the ad text again, to fold exact reposts into one card. None of
it touches `classifications`. An ad from another job site found to be a Platsbanken twin
after it was classified folds under the Platsbanken card the same way; see `fold_twins`.

THE FORMULA, and its four constants live in 02_search_config.yaml under
`scoring.recommend_rules.constants`, never here. There is one copy:

    recommend = want
              * (reach_floor + reach_slope * reach)          <- reach discounts
              * (1 + clamp(signal_total / divisor, -b, +b))  <- signals nudge

want-dominant, multiplicative. DO NOT AVERAGE want AND reach. The config carries the
two worked ads that prove why, and `verify` asserts the four must_hold rules over the
whole 0-10 by 0-10 grid rather than over the rows that happen to be classified today.

WHY THE REACH FLOOR IS 0.5 and not lower. A formula such as
`want * (0.3 + 0.07 * reach)` fails must_hold rule two: a want 6 reach 0 ad scores 1.80
while a want 2 reach 10 ad scores 2.00, so the job the candidate barely wants wins. That
is the retail sales assistant failure at want 2 instead of want 0. It can go unnoticed
on real data, because a store may hold no want 6 ad at reach 0. A 0.5 floor makes the
same pair 3.00 against 2.00 and lets rule two be a check that fails the build. Full
reasoning, including why `reach` is deliberately weighted light, is in the config next
to the constants.

NOT CALIBRATED, deliberately. The constants are meant to be fitted against the user's
own verdicts on a fully classified store, not before. `preview --floor X --slope Y`
reorders in memory and writes nothing, so two candidate orderings can be read side by
side first.

`scores` is derived, like `postings`, `prefilter` and `signals`. Dropped and rebuilt
at will, never holds anything paid for, never a column on `classifications`.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import yaml

from . import classify, store

ROOT = Path(__file__).resolve().parent.parent
CONFIG_YAML = ROOT / "context" / "02_search_config.yaml"

# Eligibility beyond the model's own hard filters. The tag goes into rule_version, so rows
# scored before and after a change to these rules can be told apart, the same way a change
# to the constants can.
ELIGIBILITY_RULES = "e3"
CITIZENSHIP = "citizenship_or_clearance"
COMMISSION_ONLY = "Rörlig ackords- eller provisionslön"   # postings.salary_type, verbatim
REPOST_OVERLAP = 0.8      # share of five-word runs two ads must have in common to be one

SCHEMA = """
CREATE TABLE IF NOT EXISTS scores (
    id            TEXT PRIMARY KEY,
    recommend     REAL NOT NULL,
    want          INTEGER,
    reach         INTEGER,
    signal_total  INTEGER NOT NULL DEFAULT 0,
    lane_weight   INTEGER NOT NULL DEFAULT 0,
    eligible      INTEGER NOT NULL,        -- 0 means the rejected view, not merely low
    reject_reason TEXT,                    -- why, in a form the rejected view can show
    rule_version  TEXT NOT NULL,           -- the scoring constants these rows came from
    classifier_version TEXT NOT NULL,      -- the judgement they were computed over
    source_version     TEXT NOT NULL,      -- what the brief and prompt hashed to at the
                                           -- moment of the rebuild. The two together are
                                           -- what makes staleness answerable by a reader
                                           -- that cannot hash the source files itself.
    dropped_hits       TEXT,               -- JSON: hard filter hits the ad text does not
                                           -- support, so not obeyed. See supported_hits.
    repost_of          TEXT                -- the shown card this exact repost folds into.
                                           -- NULL on every card that is itself shown.
);

CREATE INDEX IF NOT EXISTS scores_recommend ON scores(recommend DESC);
CREATE INDEX IF NOT EXISTS scores_eligible  ON scores(eligible);
"""


class Rules:
    """The constants, read from the config and carried as one object.

    Loaded rather than hardcoded so that changing the ranking is a config edit and a
    free rebuild. `preview` overrides them in memory without touching the file.
    """

    def __init__(self, floor, slope, divisor, band, lane_weights, bar_terms=()):
        self.floor = float(floor)
        self.slope = float(slope)
        self.divisor = float(divisor)
        self.band = float(band)
        self.lane_weights = lane_weights
        self.bar_terms = tuple(bar_terms)

    @classmethod
    def load(cls, path=CONFIG_YAML):
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        c = cfg["scoring"]["recommend_rules"]["constants"]
        missing = {"reach_floor", "reach_slope", "signal_divisor", "signal_band"} - set(c)
        if missing:
            raise SystemExit(
                f"scoring.recommend_rules.constants is missing {sorted(missing)}. The "
                f"scorer reads its constants from the config and keeps no copy of its "
                f"own, so it refuses to guess."
            )
        weights = {l["id"]: int(l.get("weight", 0)) for l in cfg["lanes"]}
        # The words for a real citizenship or clearance bar. See supported_hits.
        cit = next((h for h in cfg["hard_filters"] if h["id"] == CITIZENSHIP), {})
        bar = [t.lower() for t in cit.get("match_terms_sv", []) + cit.get("match_terms_en", [])]
        if not bar:
            raise SystemExit(
                f"hard_filters.{CITIZENSHIP} carries no match terms. The scorer drops that "
                f"filter when an ad names none of them, so an empty list would drop it on "
                f"every ad. Refusing rather than guessing."
            )
        return cls(c["reach_floor"], c["reach_slope"], c["signal_divisor"],
                   c["signal_band"], weights, bar)

    def replace(self, floor=None, slope=None, divisor=None, band=None):
        return Rules(self.floor if floor is None else floor,
                     self.slope if slope is None else slope,
                     self.divisor if divisor is None else divisor,
                     self.band if band is None else band,
                     self.lane_weights, self.bar_terms)

    def version(self):
        h = hashlib.sha256()
        h.update(f"{self.floor}|{self.slope}|{self.divisor}|{self.band}\n".encode())
        for lane, w in sorted(self.lane_weights.items()):
            h.update(f"{lane}={w}\n".encode())
        h.update(f"{ELIGIBILITY_RULES}|{'|'.join(sorted(self.bar_terms))}\n".encode())
        return f"sc1-{h.hexdigest()[:8]}"

    def reach_multiplier(self, reach):
        return self.floor + self.slope * (reach or 0)

    def signal_multiplier(self, signal_total):
        raw = (signal_total or 0) / self.divisor
        return 1 + max(-self.band, min(self.band, raw))

    def recommend(self, want, reach, signal_total=0):
        """One posting's score. want None means unclassified, which scores 0 rather
        than raising: an ad the model has not seen yet is not a recommendation."""
        if not want:
            return 0.0
        return want * self.reach_multiplier(reach) * self.signal_multiplier(signal_total)


def lane_weight(rules, matched_lanes_json):
    """The tie-break. Highest weight among the ad's matched lanes, ignoring per-lane
    fit, because a lane is a label on the card and not a ranking."""
    lanes = json.loads(matched_lanes_json or "[]")
    return max((rules.lane_weights.get(l.get("id"), 0) for l in lanes), default=0)


def source_version():
    """What the brief, the prompt, the model id and the schema hash to RIGHT NOW.

    This is the authority on what is current, and getting it from the source files
    rather than from the table is the whole point. Asking `classifications` for its
    newest row compares the table to itself and can never notice that the brief moved
    on: after an edit to the brief the sources hash to one version, every stored row
    carries another, and everything would be reported as current while ranking on
    judgements the brief has already superseded. A staleness check that reads the
    thing it is checking is not a staleness check.
    """
    return classify.classifier_version(classify.load_config())


def current_version(conn):
    """The version the rows on disk were actually written under, newest first.

    Kept separate from `source_version` on purpose: the difference between the two IS
    the staleness, and collapsing them would hide it. `rebuild` scores
    whatever is newest on disk and then `verify` says whether that matches the sources.
    """
    row = conn.execute(
        "SELECT classifier_version FROM classifications ORDER BY classified_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise SystemExit("nothing classified yet.")
    return row["classifier_version"]


def fetch(conn, version):
    """Every classified posting at the current version, with everything the score
    needs. The pre-filter verdict comes along so a skipped ad can say so."""
    return conn.execute(
        """SELECT c.id, c.want, c.reach, c.track, c.matched_lanes, c.hard_filter_hits,
                  p.headline, p.employer_name, p.publication_date, p.salary_type,
                  p.removed, p.municipality,
                  f.verdict prefilter_verdict, f.reason prefilter_reason,
                  COALESCE(
                      (SELECT SUM(s.weight) FROM signals s WHERE s.id = c.id), 0
                  ) signal_total
           FROM classifications c
           JOIN postings p  ON p.id = c.id
           LEFT JOIN prefilter f ON f.id = c.id
           WHERE c.classifier_version = ?""",
        (version,),
    ).fetchall()


def ad_text(conn, ad_id):
    """Headline and description, read on demand. `postings` deliberately does not copy
    the description (see pipeline/normalise.py), so the few rules below that need it go
    to `ads`."""
    row = conn.execute(
        """SELECT p.headline, a.payload FROM postings p JOIN ads a ON a.id = p.id
           WHERE p.id = ?""",
        (ad_id,),
    ).fetchone()
    ad = json.loads(row["payload"])
    return f"{row['headline'] or ''}\n{(ad.get('description') or {}).get('text') or ''}"


def supported_hits(conn, row, bar_terms):
    """The model's hard filter hits, split into the ones that stand and the ones the ad
    text does not support.

    Only `citizenship_or_clearance` is ever dropped, and only when the ad contains none
    of the config's terms for a real bar. A noticeable share of the ads the model
    rejects on this filter name no such bar: it reads one into a public-sector
    employer, a background check, "EU-medborgarskap", a mention of a work visa or a
    kommun checking ID at interview, none of which is a Swedish citizenship or
    clearance requirement. The paid hit stays in `classifications` untouched; this
    only decides whether it is obeyed.

    Substring matching, not whole words, so Swedish inflections and compounds still
    count as the bar they are: säkerhetsklassad, säkerhetsprövningen.
    """
    hits = json.loads(row["hard_filter_hits"] or "[]")
    if CITIZENSHIP not in hits:
        return hits, []
    text = ad_text(conn, row["id"]).lower()
    if any(term in text for term in bar_terms):
        return hits, []
    return [h for h in hits if h != CITIZENSHIP], [CITIZENSHIP]


def eligibility(row, hits):
    """Why a posting is in the rejected view, or None if it is not.

    The config defines rejected four ways and they are computed once, here, rather
    than in every caller. Order matters only for which reason gets shown, and it runs
    hardest first: a hard filter is a fact about the job, the others are judgements.
    `hits` are the hard filter hits that stand, from `supported_hits`.

    Commission-only pay is rejected here because the model is never shown
    `salary_type`, so without this rule an on-demand, commission-paid role can reach
    the top of the ranking. It is a fact about the job, so it sits next to the hard
    filters. Fixed pay with a variable part is not caught by it.
    """
    if hits:
        return "hard_filter:" + ",".join(hits)
    if row["salary_type"] == COMMISSION_ONLY:
        return "pay:commission_only"
    if row["prefilter_verdict"] == "skip":
        return f"prefilter:{row['prefilter_reason']}"
    if row["track"] == "neither":
        return "no_lane_matched"
    return None


def _shingles(text):
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i:i + 5]) for i in range(max(0, len(words) - 4))}


def _overlap(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def repost_key(employer, headline, municipality):
    """What two ads must share before their text is compared: the employer, and the
    title with the ad's own city taken off its end.

    Employers post one job in several cities with the city at the end of the title, "Data
    Engineer - Stockholm" against "Data Engineer - Göteborg", and almost always with
    near-identical text. The text rule still decides, so a pair whose text differs stays
    apart.
    """
    title = (headline or "").strip().lower()
    city = (municipality or "").strip().lower()
    if city:
        title = re.sub(rf"\s*(?:[-–—,|/(]|\bi\b)\s*{re.escape(city)}\)?\s*$", "", title)
    return (employer or "").strip().lower(), title


def find_reposts(conn, cards):
    """Exact reposts, folded into one card. Returns {repost_id: shown_id}.

    Same employer, same title and near-identical ad text, all three, because each
    narrower rule joins jobs that are different. Employer and title alone joins
    different jobs that share a title, such as one company's two Software Engineer ads.
    Similar text alone joins different doctoral positions at one university that share
    boilerplate. The city is left out on purpose: a consultancy that posts one
    identical ad in Stockholm and Örebro has one job to apply to. A city at the end of
    the title does not count either; see `repost_key`.

    `cards` are open, eligible rows as dicts carrying their `recommend`. The card shown
    is the highest scoring in its group, then the newest.
    """
    groups = defaultdict(list)
    for r in cards:
        groups[repost_key(r["employer_name"], r["headline"], r["municipality"])].append(r)

    folded = {}
    for rows in groups.values():
        if len(rows) < 2:
            continue
        text = {r["id"]: _shingles(ad_text(conn, r["id"])) for r in rows}
        parent = {r["id"]: r["id"] for r in rows}

        def root(x):
            while parent[x] != x:
                x = parent[x]
            return x

        for a, b in combinations(rows, 2):
            if _overlap(text[a["id"]], text[b["id"]]) >= REPOST_OVERLAP:
                parent[root(a["id"])] = root(b["id"])

        clusters = defaultdict(list)
        for r in rows:
            clusters[root(r["id"])].append(r)
        for members in clusters.values():
            if len(members) < 2:
                continue
            members.sort(key=lambda r: r["publication_date"] or "", reverse=True)
            members.sort(key=lambda r: -r["recommend"])     # stable, so newest wins a tie
            for r in members[1:]:
                folded[r["id"]] = members[0]["id"]
    return folded


def fold_twins(scored, folded):
    """{links id: shown id} for ads from other job sites that turned out to be a job already
    on Platsbanken after they were classified. The Platsbanken card wins, so the Links copy
    folds under it the way an exact repost does, and shows nowhere if that card is not shown
    either. The pre-filter found the twin; see `links.find_twins`.

    Only a copy whose one reason for rejection is being a twin folds. One the model rejected
    for its own reasons stays rejected."""
    shown = {r["id"] for r, reason, _, _ in scored
             if not reason and not r["removed"] and r["id"] not in folded}
    twins = {}
    for r, reason, _, _ in scored:
        why = r["prefilter_reason"] or ""
        if not why.startswith("twin:") or reason != f"prefilter:{why}" or r["removed"]:
            continue
        target = why[len("twin:"):]
        root = folded.get(target, target)
        if root in shown:
            twins[r["id"]] = root
    return twins


def rebuild(conn, rules=None):
    rules = rules or Rules.load()
    version = rules.version()
    classifier = current_version(conn)
    live = source_version()
    if classifier != live:
        print(f"NOTE: scoring rows written under {classifier}, but the brief and prompt "
              f"now hash to {live}.\n"
              f"      The ranking below is the best available and it is stale. Re-buying "
              f"it is `classify run --pending --include-stale --yes`.\n")

    conn.execute("DROP TABLE IF EXISTS scores")
    conn.executescript(SCHEMA)

    scored = []
    for r in fetch(conn, classifier):
        hits, dropped = supported_hits(conn, r, rules.bar_terms)
        scored.append((dict(r), eligibility(r, hits), dropped,
                       round(rules.recommend(r["want"], r["reach"], r["signal_total"]), 4)))
    # Reposts are folded among the cards that can actually be shown, so a closed or
    # rejected copy can never hide an open one.
    folded = find_reposts(conn, [dict(r, recommend=score)
                                 for r, reason, _, score in scored
                                 if not reason and not r["removed"]])
    folded.update(fold_twins(scored, folded))

    batch = [(
        r["id"], score, r["want"], r["reach"], r["signal_total"],
        lane_weight(rules, r["matched_lanes"]),
        1 if r["id"] in folded else 0 if reason else 1,
        None if r["id"] in folded else reason, version, classifier, live,
        json.dumps(dropped) if dropped else None, folded.get(r["id"]),
    ) for r, reason, dropped, score in scored]
    conn.executemany(
        """INSERT INTO scores (id, recommend, want, reach, signal_total, lane_weight,
                               eligible, reject_reason, rule_version, classifier_version,
                               source_version, dropped_hits, repost_of)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        batch,
    )
    conn.commit()

    eligible = sum(1 for b in batch if b[6])
    print(f"scores rebuilt: {len(batch)} rows, rule_version {version}")
    print(f"  classifier      {classifier}")
    print(f"  recommend = want * ({rules.floor} + {rules.slope} * reach) "
          f"* (1 + clamp(signals/{rules.divisor:g}, +/-{rules.band}))")
    print(f"  {eligible} eligible, {len(batch) - eligible} in the rejected view")
    print(f"  {sum(1 for b in batch if b[11])} citizenship hits dropped for naming no real "
          f"bar, {sum(1 for b in batch if b[7] == 'pay:commission_only')} rejected for "
          f"commission-only pay, {len(folded)} reposts folded into another card")
    return len(batch)


def ranked(conn, rules, rows=None, eligible_only=True, track="industry"):
    """The ordering, computed in memory. `rebuild` writes it; `preview` does not."""
    rows = rows if rows is not None else fetch(conn, current_version(conn))
    out = []
    for r in rows:
        if eligible_only and eligibility(r, supported_hits(conn, r, rules.bar_terms)[0]):
            continue
        if track and r["track"] != track:
            continue
        out.append((rules.recommend(r["want"], r["reach"], r["signal_total"]),
                    lane_weight(rules, r["matched_lanes"]),
                    r["publication_date"] or "", r))
    # Two stable sorts rather than one key, because the third term is a date string
    # and has to run descending while the first two run descending numerically.
    out.sort(key=lambda t: t[2], reverse=True)   # publication date, newest first
    out.sort(key=lambda t: (-t[0], -t[1]))       # stable, so the date order survives
    return out


# --------------------------------------------------------------------------
# Checks. The four must_hold rules from the config, written as properties over
# every possible want and reach rather than over the rows currently on disk. A
# check that only holds for the rows classified so far is not a check: a 0.3
# reach floor can pass on the stored rows and still fail on the grid, which is
# exactly the failure this catches.
# --------------------------------------------------------------------------

GRID = range(0, 11)

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn)); return fn
    return deco


@check("must_hold 1: want 0 scores 0, whatever reach and signals do")
def _c1(conn):
    rules = Rules.load()
    worst = max(abs(rules.recommend(0, r, s))
                for r in GRID for s in (-1000, -50, 0, 50, 1000))
    return worst == 0, f"largest recommend at want 0 is {worst}"


@check("must_hold 2: want 6+ / reach 2- always outranks want 2- / reach 7+")
def _c2(conn):
    """The band the config names. Signals are pushed to both edges, so the check is
    over the whole input space and not over the totals that happen to occur."""
    rules = Rules.load()
    lo = min(rules.recommend(w, r, -10_000) for w in range(6, 11) for r in range(0, 3))
    hi = max(rules.recommend(w, r, +10_000) for w in range(0, 3) for r in range(7, 11))
    return lo > hi, (f"worst want>=6 ad {lo:.2f}, best want<=2 ad {hi:.2f}"
                     + ("" if lo > hi else "  <- the constants break want dominance"))


@check("must_hold 3: reach only ever discounts, never raises")
def _c3(conn):
    rules = Rules.load()
    bad = [(w, r) for w in GRID for r in GRID
           if w * rules.reach_multiplier(r) > w + 1e-9]
    top = rules.reach_multiplier(10)
    return not bad, (f"reach multiplier spans {rules.reach_multiplier(0):.2f} to "
                     f"{top:.2f}, {len(bad)} pairs above want")


@check("must_hold 4: a hard filter hit lands in the rejected view, not merely low")
def _c4(conn):
    """The join is pinned to the current classifier_version. Without that it picks up
    the rows left behind by superseded prompts, and a hard filter a stale prompt found
    makes a currently-eligible posting look wrongly scored.

    A citizenship hit the ad text does not support is dropped rather than obeyed, so
    what must reach the rejected view is the hits that stand: the model's hits minus
    `dropped_hits`. Whether each drop was right is the next check."""
    rows = conn.execute(
        """SELECT c.hard_filter_hits, s.dropped_hits FROM scores s
           JOIN classifications c ON c.id = s.id AND c.classifier_version = ?
           WHERE c.hard_filter_hits != '[]' AND s.eligible = 1""",
        (current_version(conn),),
    ).fetchall()
    n = sum(1 for r in rows
            if set(json.loads(r["hard_filter_hits"])) - set(json.loads(r["dropped_hits"] or "[]")))
    hit = conn.execute(
        "SELECT COUNT(*) c FROM scores WHERE reject_reason LIKE 'hard_filter:%'"
    ).fetchone()["c"]
    return n == 0, (f"{hit} postings carry a hard filter hit that stands, "
                    f"{n} of them still eligible")


@check("a citizenship hit is dropped only when the ad names no real bar")
def _c4b(conn):
    """Read from the ad text and the config, not from the reasons the table gives
    itself. Both directions: every dropped hit has no bar term in its ad, every
    citizenship rejection that stands has one, and nothing but citizenship is dropped."""
    bar = Rules.load().bar_terms
    rows = conn.execute(
        """SELECT id, dropped_hits FROM scores
           WHERE dropped_hits IS NOT NULL OR reject_reason LIKE ?""",
        (f"%{CITIZENSHIP}%",),
    ).fetchall()
    wrong = other = 0
    for r in rows:
        dropped = json.loads(r["dropped_hits"] or "[]")
        named = any(t in ad_text(conn, r["id"]).lower() for t in bar)
        other += bool(set(dropped) - {CITIZENSHIP})
        wrong += bool(dropped) == named
    n_dropped = sum(1 for r in rows if r["dropped_hits"])
    return wrong == 0 and other == 0, (
        f"{n_dropped} dropped, {len(rows) - n_dropped} standing, {wrong} contradicted by "
        f"the ad text, {other} other filters dropped")


@check("commission-only pay never reaches the main views")
def _c4c(conn):
    """Guarded against the label changing upstream: if no posting carries it any more,
    this fails rather than passing on nothing."""
    n = conn.execute(
        """SELECT COUNT(*) c FROM scores s JOIN postings p ON p.id = s.id
           WHERE s.eligible = 1 AND p.salary_type = ?""",
        (COMMISSION_ONLY,),
    ).fetchone()["c"]
    carried = conn.execute(
        "SELECT COUNT(*) c FROM postings WHERE salary_type = ?", (COMMISSION_ONLY,)
    ).fetchone()["c"]
    rejected = conn.execute(
        "SELECT COUNT(*) c FROM scores WHERE reject_reason = 'pay:commission_only'"
    ).fetchone()["c"]
    return n == 0 and carried > 0, (
        f"{rejected} rejected for it, {n} still eligible, {carried} postings carry the label"
        + ("" if carried else "  <- label not found, JobTech may have renamed it"))


@check("no two cards on show are exact reposts of each other")
def _c4d(conn):
    """Recomputed from the ad text over the cards actually shown, so a repost the
    folding missed is caught, and every fold has to point at a card that is shown."""
    shown = conn.execute(
        """SELECT s.id, p.employer_name, p.headline, p.municipality FROM scores s
           JOIN postings p ON p.id = s.id
           WHERE s.eligible = 1 AND s.repost_of IS NULL AND p.removed = 0"""
    ).fetchall()
    groups = defaultdict(list)
    for r in shown:
        groups[repost_key(r["employer_name"], r["headline"], r["municipality"])].append(r["id"])
    missed = 0
    for ids in groups.values():
        if len(ids) < 2:
            continue
        text = {i: _shingles(ad_text(conn, i)) for i in ids}
        missed += sum(1 for a, b in combinations(ids, 2)
                      if _overlap(text[a], text[b]) >= REPOST_OVERLAP)
    dangling = conn.execute(
        """SELECT COUNT(*) c FROM scores s LEFT JOIN scores t ON t.id = s.repost_of
           WHERE s.repost_of IS NOT NULL
             AND (t.id IS NULL OR t.eligible = 0 OR t.repost_of IS NOT NULL)"""
    ).fetchone()["c"]
    folded = conn.execute(
        "SELECT COUNT(*) c FROM scores WHERE repost_of IS NOT NULL"
    ).fetchone()["c"]
    return missed == 0 and dangling == 0, (
        f"{folded} reposts folded, {missed} pairs on show still identical, "
        f"{dangling} folds pointing at a card that is not shown")


@check("the stored constants still match the config")
def _c5(conn):
    stored = conn.execute("SELECT rule_version FROM scores LIMIT 1").fetchone()
    if stored is None:
        return False, "table is empty, run rebuild"
    live = Rules.load().version()
    ok = stored["rule_version"] == live
    return ok, (f"stored {stored['rule_version']}, config {live}"
                + ("" if ok else "  <- the config changed, rebuild"))


@check("the scored rows were judged by the brief and prompt as they stand now")
def _c6(conn):
    """The real staleness check, and it reads the SOURCE FILES, not the table.

    Two failures are possible and they are different. Rows scored under a mixture of
    classifier versions is an internal inconsistency. Rows all at one version that is
    not what the sources hash to means the brief or the prompt has been edited since,
    and the ranking on screen is answering a question that has been superseded.
    """
    rows = conn.execute(
        "SELECT DISTINCT classifier_version v FROM scores"
    ).fetchall()
    if not rows:
        return False, "table is empty, run rebuild"
    live = source_version()
    stored = {r["v"] for r in rows}
    if len(stored) > 1:
        return False, f"{len(stored)} classifier versions mixed into one ordering"
    have = stored.pop()
    ok = have == live
    pending = classify.pending_count(conn, live)
    return ok, (f"scored at {have}, sources hash to {live}"
                + ("" if ok else
                   f"  <- the brief or the prompt changed. {pending} kept open ads are "
                   f"unclassified at the new version. Re-buying them is a funded decision: "
                   f"`classify run --pending --include-stale --yes`"))


@check("the config's two worked ads still order correctly")
def _c7(conn):
    """The regression case. A dream job against an easy job is the pair the whole rule
    was written for, and it is the one thing here checked against worked ads."""
    rules = Rules.load()
    dream_job = rules.recommend(9, 1)
    easy_job = rules.recommend(0, 8)
    ok = dream_job > easy_job and easy_job == 0
    return ok, (f"Staff Data Visualisation Engineer (9,1) {dream_job:.2f} vs "
                f"retail sales assistant (0,8) {easy_job:.2f}")


@check("nothing scores below 0")
def _c8(conn):
    """The only invariant here. A negative recommend would mean the signal multiplier
    went below zero, which is the escaping-style bug this catches.

    What is NOT asserted, on purpose: that no eligible posting scores exactly 0. A few
    can, such as a pure sales role the model correctly rates want 0 while `track`
    still says industry. The config is explicit that weights sort and never filter and
    that only a hard filter removes a posting, so those belong at the bottom of the
    list rather than hidden from it. `status` counts them so they stay visible. A
    threshold that moved them into the rejected view would be a change to the
    eligibility rules, not something to smuggle in as a check."""
    neg = conn.execute("SELECT COUNT(*) c FROM scores WHERE recommend < 0").fetchone()["c"]
    zero = conn.execute(
        "SELECT COUNT(*) c FROM scores WHERE eligible = 1 AND recommend <= 0"
    ).fetchone()["c"]
    return neg == 0, f"{neg} below 0, and {zero} eligible postings at exactly 0"


def verify(conn):
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


def status(conn):
    row = conn.execute("SELECT rule_version FROM scores LIMIT 1").fetchone()
    if row is None:
        print("scores is empty, run rebuild")
        return
    rules = Rules.load()
    print(f"rule_version      {row['rule_version']}")
    print(f"formula           recommend = want * ({rules.floor} + {rules.slope} * reach)"
          f" * (1 + clamp(signals/{rules.divisor:g}, +/-{rules.band}))")

    n = conn.execute("SELECT COUNT(*) c FROM scores").fetchone()["c"]
    e = conn.execute("SELECT COUNT(*) c FROM scores WHERE eligible = 1").fetchone()["c"]
    print(f"scored            {n}")
    print(f"  eligible        {e}")
    print(f"  rejected        {n - e}")

    print("\nrejected, by reason:")
    for r in conn.execute(
        """SELECT CASE
                    WHEN reject_reason LIKE 'hard_filter:%' THEN 'hard filter'
                    WHEN reject_reason LIKE 'prefilter:twin:%' THEN 'twin of a Platsbanken ad not shown'
                    WHEN reject_reason LIKE 'prefilter:%'   THEN 'never sent to the model'
                    ELSE reject_reason
                  END bucket, COUNT(*) c
           FROM scores WHERE eligible = 0 GROUP BY bucket ORDER BY c DESC"""
    ):
        print(f"  {r['c']:>6}  {r['bucket']}")

    dropped = conn.execute(
        "SELECT COUNT(*) c FROM scores WHERE dropped_hits IS NOT NULL").fetchone()["c"]
    folded = conn.execute(
        "SELECT COUNT(*) c FROM scores WHERE repost_of IS NOT NULL").fetchone()["c"]
    print(f"\n{dropped} citizenship hits dropped for naming no real bar, "
          f"{folded} reposts folded into another card")

    print("\neligible postings by track, and what the top of each looks like:")
    for track in ("industry", "phd"):
        rows = conn.execute(
            """SELECT s.recommend, s.want, s.reach, s.signal_total, p.headline
               FROM scores s
               JOIN classifications c ON c.id = s.id AND c.classifier_version = ?
               JOIN postings p ON p.id = s.id
               WHERE s.eligible = 1 AND s.repost_of IS NULL AND c.track = ?
               ORDER BY s.recommend DESC, s.lane_weight DESC, p.publication_date DESC
               LIMIT 5""",
            (current_version(conn), track),
        ).fetchall()
        print(f"\n  {track}, {len(rows)} shown")
        for r in rows:
            print(f"    {r['recommend']:5.2f}  want {r['want']} reach {r['reach']} "
                  f"sig {r['signal_total']:+4d}  {r['headline'][:52]}")

    print("\ndistribution of recommend, eligible postings:")
    buckets = conn.execute(
        """SELECT CAST(recommend AS INTEGER) b, COUNT(*) c
           FROM scores WHERE eligible = 1 GROUP BY b ORDER BY b DESC"""
    ).fetchall()
    for r in buckets:
        print(f"  {r['b']:>2} to {r['b'] + 1:<2} {'#' * min(r['c'], 60)} {r['c']}")


def preview(conn, rules, limit, track):
    """Reorder in memory and write nothing. This exists because the constants are not
    calibrated and cannot be judged in the abstract: two candidate orderings read
    side by side answer the question that arguing about floors does not."""
    rows = ranked(conn, rules, eligible_only=True, track=track)
    print(f"recommend = want * ({rules.floor} + {rules.slope} * reach)"
          f" * (1 + clamp(signals/{rules.divisor:g}, +/-{rules.band}))")
    print(f"{len(rows)} eligible {track} postings, showing {min(limit, len(rows))}. "
          f"Nothing written.\n")
    for score, weight, pub, r in rows[:limit]:
        print(f"  {score:5.2f}  want {r['want']} reach {r['reach']} "
              f"sig {r['signal_total']:+4d}  {(r['headline'] or '')[:50]:<50} "
              f"{(r['employer_name'] or '')[:24]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["rebuild", "verify", "status", "preview"])
    ap.add_argument("--floor", type=float, help="override reach_floor, preview only")
    ap.add_argument("--slope", type=float, help="override reach_slope, preview only")
    ap.add_argument("--band", type=float, help="override signal_band, preview only")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--track", default="industry", choices=["industry", "phd"])
    args = ap.parse_args()

    overridden = any(x is not None for x in (args.floor, args.slope, args.band))
    if overridden and args.mode != "preview":
        sys.exit("--floor, --slope and --band are preview only. To change the stored "
                 "ranking, edit scoring.recommend_rules.constants in "
                 "context/02_search_config.yaml and rebuild, so there is one copy.")

    conn = store.connect()
    rules = Rules.load()

    if args.mode == "rebuild":
        rebuild(conn, rules)
        print()
        sys.exit(1 if verify(conn) else 0)
    elif args.mode == "verify":
        sys.exit(1 if verify(conn) else 0)
    elif args.mode == "preview":
        preview(conn, rules.replace(args.floor, args.slope, None, args.band),
                args.limit, args.track)
    else:
        status(conn)


if __name__ == "__main__":
    main()
