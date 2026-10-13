"""The normalised posting schema, derived from ads already in the store.

    python -m pipeline.normalise rebuild    # drop and rebuild `postings`
    python -m pipeline.normalise verify     # check the transform held
    python -m pipeline.normalise status     # what is in the derived tables

Derived from the stored payloads, never from the API and never from `posting_schema`
in 02_search_config.yaml, which is only a pointer. The measured field mapping is
context/jobtech_fields.md.

Tables, split by who owns the data and what it costs to lose:

    postings          derived from `ads`. Dropped and rebuilt at will. Free.
    prefilter         derived, pipeline/prefilter.py. Free.
    signals           derived, pipeline/signals.py. Free.
    classifications   what Haiku was paid to produce. A rebuild never touches it.
    posting_state     what the user typed. A rebuild never touches it.

That split is the point of the file. If classification shared a table with the derived
schema, then fixing a column mistake here would destroy a paid classification pass.
Same reasoning as keeping the raw payloads in `ads`: make the expensive thing immune
to mistakes in the cheap thing.

`description.text` is deliberately NOT copied here. It is most of the store's size and
nothing in the dashboard renders it in full, so it stays in `ads` and the classifier
and brief writer read it on demand. Keeps `postings` small enough to query freely.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone

from . import store

# Ads whose occupation_field is outside the seven are kept. The sweep retrieved them
# deliberately and re-filtering by field here would silently drop real ads.
# See context/jobtech_fields.md section 5.

SCHEMA = """
CREATE TABLE IF NOT EXISTS postings (
    id                       TEXT PRIMARY KEY,
    headline                 TEXT,

    occupation_label         TEXT,
    occupation_concept_id    TEXT,
    occupation_group_label   TEXT,
    occupation_group_id      TEXT,
    occupation_field_label   TEXT,
    occupation_field_id      TEXT,

    employer_name            TEXT,
    employer_workplace       TEXT,
    employer_org_number      TEXT,
    employer_url             TEXT,

    municipality             TEXT,
    municipality_concept_id  TEXT,
    region                   TEXT,
    region_concept_id        TEXT,
    country                  TEXT,
    country_code             TEXT,
    longitude                REAL,
    latitude                 REAL,

    employment_type          TEXT,
    duration                 TEXT,
    working_hours_type       TEXT,
    scope_min                INTEGER,
    scope_max                INTEGER,
    salary_type              TEXT,
    salary_description       TEXT,
    number_of_vacancies      INTEGER,

    experience_required      INTEGER,
    driving_license_required INTEGER,
    access_to_own_car        INTEGER,
    must_have_languages      TEXT,
    identified_language      TEXT,

    webpage_url              TEXT,
    publication_date         TEXT,
    last_publication_date    TEXT,
    application_deadline     TEXT,
    last_updated             TEXT,
    source_type              TEXT,

    removed                  INTEGER NOT NULL DEFAULT 0,
    removed_date             TEXT,
    first_seen               TEXT,
    last_seen                TEXT,

    -- Where the ad came from: 'platsbanken', through JobStream or JobSearch, or 'links', a
    -- job site JobAd Links lists, with the site in source_site.
    source                   TEXT NOT NULL DEFAULT 'platsbanken',
    source_site              TEXT
);

CREATE INDEX IF NOT EXISTS postings_group    ON postings(occupation_group_id);
CREATE INDEX IF NOT EXISTS postings_field    ON postings(occupation_field_id);
CREATE INDEX IF NOT EXISTS postings_removed  ON postings(removed);
CREATE INDEX IF NOT EXISTS postings_muni     ON postings(municipality);
CREATE INDEX IF NOT EXISTS postings_pubdate  ON postings(publication_date);
CREATE INDEX IF NOT EXISTS postings_deadline ON postings(application_deadline);
CREATE INDEX IF NOT EXISTS postings_source   ON postings(source);
"""

# Durable. Created here so the boundary is explicit; other modules write the rows.
#
# `want` and `reach` are the model's own judgement and are stored separately rather
# than pre-blended into one score. The dashboard sorts on one number, but that number
# is derived in pipeline/score.py and re-deriving it is arithmetic over data already
# on disk. Store the blend only, and every change to how the two are weighted is a
# paid reclassify. Same argument as the table split above.
#
# `min_years_experience` and `seniority_language` are extracted for two seniority
# rules that are not applied yet. Having them here means both rules can be tested
# against classified ads for free, instead of needing another paid pass to answer.
#
# The token counts are here so the prompt caching question has a measured answer
# rather than an assumed one before a full pass over the store is paid for.
#
# Regex-matched soft signals are NOT here. They are free to recompute, so they live
# in their own derived table and a rebuild is allowed to drop them.
DURABLE = """
CREATE TABLE IF NOT EXISTS classifications (
    id                     TEXT NOT NULL,
    classifier_version     TEXT NOT NULL,
    pass_no                INTEGER NOT NULL DEFAULT 1,
    classified_at          TEXT NOT NULL,
    model                  TEXT,

    summary                TEXT,
    track                  TEXT,
    matched_lanes          TEXT,       -- JSON [{"id": ..., "fit": 1..3}]
    want                   INTEGER,    -- 0-10, how much the candidate would want it
    want_why               TEXT,
    reach                  INTEGER,    -- 0-10, how likely the candidate is to get it
    reach_why              TEXT,
    hard_filter_hits       TEXT,       -- JSON array, empty means eligible
    min_years_experience   INTEGER,
    seniority_language     INTEGER,
    sales_is_the_whole_job INTEGER,
    cs_degree_required     INTEGER,

    judgement              TEXT NOT NULL,   -- the full raw response, verbatim
    input_tokens           INTEGER,         -- uncached input only
    output_tokens          INTEGER,
    cache_read_tokens      INTEGER,         -- billed at 0.1x, NOT part of input_tokens
    cache_write_tokens     INTEGER,         -- billed at 1.25x
    via_batch              INTEGER,         -- 1 if it went through the Batch API at half price
    PRIMARY KEY (id, classifier_version, pass_no)
);

CREATE INDEX IF NOT EXISTS classifications_track ON classifications(track);
CREATE INDEX IF NOT EXISTS classifications_want  ON classifications(want);

CREATE TABLE IF NOT EXISTS posting_state (
    id            TEXT PRIMARY KEY,
    status        TEXT NOT NULL DEFAULT 'new',
    notes         TEXT,
    updated_at    TEXT NOT NULL,
    dismissed_utc TEXT              -- removed on the dashboard; see dashboard/queries.py
);
"""


def ensure_durable(conn):
    """Create the durable tables, migrating `classifications` only while it is empty.

    `classifications` is the one table in this file that costs money to refill, so it
    is never dropped silently. While it holds nothing, a shape change is free and is
    applied. Once it holds a paid pass, this refuses and the migration becomes a
    deliberate, hand-written ALTER rather than something that happened during a
    routine rebuild. That is the table split enforced in code rather than in a comment.
    """
    existing = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='classifications'"
    ).fetchone()

    # Adding a column is not destructive, so it never needs the empty-table guard.
    # Anything already paid for keeps its row and gets NULL in the new column, which
    # is recoverable from `judgement` because the raw response is stored verbatim.
    if existing is not None and "want" in existing["sql"]:
        have = {r["name"] for r in conn.execute("PRAGMA table_info(classifications)")}
        for col in ("cs_degree_required", "cache_write_tokens", "via_batch"):
            if col not in have:
                conn.execute(f"ALTER TABLE classifications ADD COLUMN {col} INTEGER")
                print(f"classifications: added column {col}")

    if existing is not None and "want" not in existing["sql"]:
        n = conn.execute("SELECT COUNT(*) c FROM classifications").fetchone()["c"]
        if n:
            raise SystemExit(
                f"`classifications` has the shape from before want and reach and holds {n} rows "
                f"that were paid for. Refusing to drop it. Migrate by hand with ALTER "
                f"TABLE, or export the rows first."
            )
        conn.execute("DROP TABLE classifications")
        print("classifications: empty, migrated to the want/reach schema")
    conn.executescript(DURABLE)


def _nested(ad, key, sub="label"):
    return (ad.get(key) or {}).get(sub)


def _coords(addr):
    """JobTech gives [longitude, latitude], GeoJSON order, the reverse of how it is
    usually written. Many ads carry [null, null], so both elements are checked.
    """
    c = addr.get("coordinates") or []
    if len(c) != 2 or c[0] is None or c[1] is None:
        return None, None
    return c[0], c[1]


def _iso_from_ms(ms):
    """`timestamp` is epoch milliseconds while every other date field is ISO 8601."""
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="seconds")


def _bool(v):
    return None if v is None else int(bool(v))


def row_from(ad, meta):
    addr = ad.get("workplace_address") or {}
    lon, lat = _coords(addr)
    langs = [l.get("label") for l in ((ad.get("must_have") or {}).get("languages") or [])]
    scope = ad.get("scope_of_work") or {}
    return (
        ad["id"],
        ad.get("headline"),
        _nested(ad, "occupation"), _nested(ad, "occupation", "concept_id"),
        _nested(ad, "occupation_group"), _nested(ad, "occupation_group", "concept_id"),
        _nested(ad, "occupation_field"), _nested(ad, "occupation_field", "concept_id"),
        _nested(ad, "employer", "name"), _nested(ad, "employer", "workplace"),
        _nested(ad, "employer", "organization_number"), _nested(ad, "employer", "url"),
        addr.get("municipality"), addr.get("municipality_concept_id"),
        addr.get("region"), addr.get("region_concept_id"),
        addr.get("country"), addr.get("country_code"),
        lon, lat,
        _nested(ad, "employment_type"), _nested(ad, "duration"),
        _nested(ad, "working_hours_type"), scope.get("min"), scope.get("max"),
        _nested(ad, "salary_type"), ad.get("salary_description"),
        ad.get("number_of_vacancies"),
        _bool(ad.get("experience_required")),
        _bool(ad.get("driving_license_required")),
        _bool(ad.get("access_to_own_car")),
        ", ".join(x for x in langs if x) or None,
        ad.get("identified_language"),
        ad.get("webpage_url"),
        ad.get("publication_date"), ad.get("last_publication_date"),
        ad.get("application_deadline"),
        _iso_from_ms(ad.get("timestamp")),
        ad.get("source_type"),
        # Removal is recorded on the `ads` column, never in the payload: a JobStream
        # tombstone is sparse and would destroy the ad text if written over it. So the
        # stored payload of a closed ad still says removed: false. Read the column.
        _bool(meta["removed"]) or 0,
        meta["removed_date"],
        meta["first_seen"], meta["last_seen"],
        # An ad from another job site is written to `ads` by pipeline/links.py in JobTech's
        # shape, so the only difference here is where it says it came from.
        "links" if meta["source"] == "links" else "platsbanken",
        (ad.get("links") or {}).get("site"),
    )


COLUMNS = """id, headline, occupation_label, occupation_concept_id,
    occupation_group_label, occupation_group_id, occupation_field_label,
    occupation_field_id, employer_name, employer_workplace, employer_org_number,
    employer_url, municipality, municipality_concept_id, region, region_concept_id,
    country, country_code, longitude, latitude, employment_type, duration,
    working_hours_type, scope_min, scope_max, salary_type, salary_description,
    number_of_vacancies, experience_required, driving_license_required,
    access_to_own_car, must_have_languages, identified_language, webpage_url,
    publication_date, last_publication_date, application_deadline, last_updated,
    source_type, removed, removed_date, first_seen, last_seen, source, source_site"""


def rebuild(conn):
    ensure_durable(conn)
    conn.execute("DROP TABLE IF EXISTS postings")
    conn.executescript(SCHEMA)

    n_placeholders = ",".join("?" * len(COLUMNS.split(",")))
    sql = f"INSERT INTO postings ({COLUMNS}) VALUES ({n_placeholders})"

    # Tombstone-only rows have nine keys and no ad content. They stay in `ads` so the
    # id is known, and never become a posting.
    src = conn.execute(
        """SELECT payload, first_seen, last_seen, removed, removed_date, source
           FROM ads WHERE is_tombstone = 0"""
    )
    batch, total, bad = [], 0, 0
    for r in src:
        try:
            batch.append(row_from(json.loads(r["payload"]), r))
        except Exception as e:  # a malformed payload must not abort the rebuild
            bad += 1
            print(f"  ! skipped one payload: {e}", file=sys.stderr)
            continue
        if len(batch) >= 1000:
            conn.executemany(sql, batch); total += len(batch); batch = []
    if batch:
        conn.executemany(sql, batch); total += len(batch)
    conn.commit()
    print(f"postings rebuilt: {total} rows" + (f", {bad} payloads skipped" if bad else ""))
    return total


CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn)); return fn
    return deco


@check("every non-tombstone ad became a posting")
def _c1(conn):
    a = conn.execute("SELECT COUNT(*) c FROM ads WHERE is_tombstone = 0").fetchone()["c"]
    p = conn.execute("SELECT COUNT(*) c FROM postings").fetchone()["c"]
    return a == p, f"{a} ads, {p} postings"


@check("no tombstone leaked into postings")
def _c2(conn):
    n = conn.execute(
        "SELECT COUNT(*) c FROM postings p JOIN ads a ON a.id = p.id WHERE a.is_tombstone = 1"
    ).fetchone()["c"]
    return n == 0, f"{n} tombstones in postings"


@check("coordinates were swapped, not copied")
def _c3(conn):
    # Sweden spans roughly lon 11-24, lat 55-69. Stockholm is lon 18.07, lat 59.33.
    r = conn.execute(
        """SELECT COUNT(*) c, AVG(longitude) lon, AVG(latitude) lat FROM postings
           WHERE municipality = 'Stockholm' AND longitude IS NOT NULL"""
    ).fetchone()
    ok = r["c"] > 0 and 17.0 < r["lon"] < 19.5 and 58.5 < r["lat"] < 60.0
    return ok, f"{r['c']} Stockholm rows, mean lon {r['lon']:.3f}, lat {r['lat']:.3f}"


@check("no coordinate pair half populated")
def _c4(conn):
    n = conn.execute(
        """SELECT COUNT(*) c FROM postings
           WHERE (longitude IS NULL) != (latitude IS NULL)"""
    ).fetchone()["c"]
    return n == 0, f"{n} half populated pairs"


@check("last_updated parsed out of epoch milliseconds")
def _c5(conn):
    r = conn.execute(
        "SELECT MIN(last_updated) lo, MAX(last_updated) hi, COUNT(*) c FROM postings"
    ).fetchone()
    ok = r["lo"] is not None and r["lo"].startswith("20") and r["hi"] > r["lo"]
    return ok, f"{r['lo']} to {r['hi']}"


@check("headline and webpage_url present on every row")
def _c6(conn):
    n = conn.execute(
        "SELECT COUNT(*) c FROM postings WHERE headline IS NULL OR webpage_url IS NULL"
    ).fetchone()["c"]
    return n == 0, f"{n} rows missing one"


@check("ads outside the seven occupation fields were kept")
def _c7(conn):
    seven = ("apaJ_2ja_LuF", "X82t_awd_Qyc", "RPTn_bxG_ExZ", "MVqp_eS8_kDZ",
             "6Hq3_tKo_V57", "kJeN_wmw_9wX", "9puE_nYg_crq")
    q = ",".join("?" * len(seven))
    n = conn.execute(
        f"SELECT COUNT(*) c FROM postings WHERE occupation_field_id NOT IN ({q})", seven
    ).fetchone()["c"]
    return n > 0, f"{n} kept (dropping these would be the bug)"


@check("every ad from another job site kept its source and site")
def _c9(conn):
    a = conn.execute("SELECT COUNT(*) c FROM ads WHERE source = 'links' AND is_tombstone = 0").fetchone()["c"]
    p = conn.execute(
        "SELECT COUNT(*) c FROM postings WHERE source = 'links' AND source_site IS NOT NULL"
    ).fetchone()["c"]
    return a == p, f"{a} in ads, {p} in postings with a site"


@check("removed flag survived the transform")
def _c8(conn):
    a = conn.execute("SELECT COUNT(*) c FROM ads WHERE removed=1 AND is_tombstone=0").fetchone()["c"]
    p = conn.execute("SELECT COUNT(*) c FROM postings WHERE removed = 1").fetchone()["c"]
    return a == p, f"{a} in ads, {p} in postings"


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
    def one(q, *a):
        return conn.execute(q, a).fetchone()[0]
    today = datetime.now(timezone.utc).date().isoformat()
    print(f"postings          {one('SELECT COUNT(*) FROM postings')}")
    print(f"  open            {one('SELECT COUNT(*) FROM postings WHERE removed = 0')}")
    print(f"  open, in date   "
          f"{one('SELECT COUNT(*) FROM postings WHERE removed = 0 AND application_deadline >= ?', today)}")
    print(f"  distinct groups {one('SELECT COUNT(DISTINCT occupation_group_id) FROM postings')}")
    print(f"  geocoded        {one('SELECT COUNT(*) FROM postings WHERE latitude IS NOT NULL')}")
    print(f"classifications   {one('SELECT COUNT(*) FROM classifications')}")
    print(f"posting_state     {one('SELECT COUNT(*) FROM posting_state')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["rebuild", "verify", "status"])
    args = ap.parse_args()

    conn = store.connect()
    ensure_durable(conn)
    if args.mode == "rebuild":
        rebuild(conn)
        print()
        sys.exit(1 if verify(conn) else 0)
    elif args.mode == "verify":
        sys.exit(1 if verify(conn) else 0)
    else:
        status(conn)


if __name__ == "__main__":
    main()
