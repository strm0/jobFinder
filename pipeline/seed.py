"""Build the demo store from the sample data. Free, no API, no key. Only in the public copy.

    python -m pipeline.seed            # build data/postings.db from sample/
    python -m pipeline.seed --force    # throw the store away and build it again

The real system fills its store from JobTech every day and pays a model to rate what is
new. This copy ships about 230 invented ads and the ratings generated for them in advance,
and this command puts both into a fresh store and then runs the free stages over them,
the same code a daily run uses:

    sample/ads.jsonl              -> `ads`, through store.upsert, as an ingest would
    normalise rebuild             -> `postings`
    prefilter rebuild             -> `prefilter`
    signals rebuild               -> `signals`
    sample/classifications.jsonl  -> `classifications`, the part that costs money for real
    score rebuild                 -> `scores`

**Dates are relative.** The sample files say "published 9 days ago, closes in 21 days", and
the dates are worked out when the store is built, so the demo does not turn into a list of
expired jobs a month after it was written. Build it again to move it forward.

**The ratings are stored, not recomputed.** Each row carries the `classifier_version` it was
produced under, which is a hash of the prompt, the brief, the model id and the output
schema. Edit `context/candidate_brief.md` and `python -m pipeline.score verify` will say
the ranking is stale, which is the real behaviour and is worth trying.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import links, nightly, normalise, prefilter, score, signals, store

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample"
ADS = SAMPLE / "ads.jsonl"
CLASSIFICATIONS = SAMPLE / "classifications.jsonl"
STATE = SAMPLE / "state.json"

# The two runs the demo store remembers. The dashboard counts a job as new when it was
# classified after the last run started, and reads "added" and "closed" from that run's row.
PREVIOUS_RUN_HOURS_AGO = 38
LAST_RUN_HOURS_AGO = 14


def _lines(path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def _iso(when):
    """A date the way JobTech writes it: local time, no zone."""
    return when.replace(microsecond=0, tzinfo=None).isoformat()


def _utc(when):
    return when.astimezone(timezone.utc).isoformat(timespec="seconds")


def load_ads(conn, now):
    """Write every sample ad as an ingest would, then set the columns an ingest fills in
    over several days: when the ad was first seen and whether it has closed since."""
    last_run = now - timedelta(hours=LAST_RUN_HOURS_AGO)
    counts = {"open": 0, "closed": 0, "links": 0, "added_last_run": 0, "closed_last_run": 0}
    new = set()
    for row in _lines(ADS):
        ad, demo = row["ad"], row["demo"]
        published = now - timedelta(days=demo["published_days_ago"], hours=demo.get("hour", 3))
        ad["publication_date"] = _iso(published)
        ad["timestamp"] = int(published.timestamp() * 1000)
        if demo.get("deadline_days") is not None:
            closes = (now + timedelta(days=demo["deadline_days"])).replace(
                hour=23, minute=59, second=59)
            ad["application_deadline"] = _iso(closes)
            ad["last_publication_date"] = _iso(closes)
        store.upsert(conn, ad, demo["source"])

        # A new ad arrives in the last run; every other one was seen the day it was published.
        seen = (last_run + timedelta(minutes=2) if demo.get("new")
                else published + timedelta(hours=20))
        conn.execute("UPDATE ads SET first_seen = ?, last_seen = ? WHERE id = ?",
                     (_utc(seen), _utc(last_run), ad["id"]))
        if demo.get("new"):
            new.add(ad["id"])
            counts["added_last_run"] += 1
        counts["links"] += demo["source"] == links.SOURCE

        if demo.get("closed_days_ago") is not None:
            closed = now - timedelta(days=demo["closed_days_ago"])
            conn.execute("UPDATE ads SET removed = 1, removed_date = ? WHERE id = ?",
                         (_iso(closed), ad["id"]))
            counts["closed"] += 1
            counts["closed_last_run"] += closed >= last_run
        else:
            counts["open"] += 1
    conn.commit()
    return counts, new


def load_classifications(conn, now, new):
    """The ratings, as `pipeline/archive.py restore` would put them back, with one change:
    `classified_at` is worked out from the two runs above instead of read from the file."""
    previous = now - timedelta(hours=PREVIOUS_RUN_HOURS_AGO)
    last_run = now - timedelta(hours=LAST_RUN_HOURS_AGO)
    columns = [r[1] for r in conn.execute("PRAGMA table_info(classifications)")]
    n = fresh = 0
    for row in _lines(CLASSIFICATIONS):
        run = last_run if row["id"] in new else previous
        row["classified_at"] = _utc(run + timedelta(minutes=5, seconds=n))
        usable = {k: v for k, v in row.items() if k in columns}
        conn.execute(
            f"INSERT INTO classifications ({', '.join(usable)}) "
            f"VALUES ({', '.join('?' * len(usable))})", list(usable.values()))
        n += 1
        fresh += row["id"] in new
    conn.commit()
    return n, fresh


def record_runs(conn, now, counts, classified, fresh):
    """Two rows in `pipeline_runs`, so the dashboard has a last run to report and a moment
    to count new jobs from. Written after the ratings are in and before scoring."""
    nightly.ensure_schema(conn)
    version = conn.execute(
        "SELECT classifier_version FROM classifications ORDER BY classified_at DESC LIMIT 1"
    ).fetchone()["classifier_version"]
    reach = conn.execute(
        """SELECT COUNT(*) c FROM prefilter f JOIN postings p ON p.id = f.id
           WHERE p.removed = 0 AND f.verdict = 'keep'""").fetchone()["c"]
    total = counts["open"] + counts["closed"]
    runs = (
        (PREVIOUS_RUN_HOURS_AGO, total - counts["added_last_run"],
         counts["open"] - counts["added_last_run"] + counts["closed_last_run"],
         total - counts["added_last_run"], counts["closed"] - counts["closed_last_run"],
         classified - fresh),
        (LAST_RUN_HOURS_AGO, total, counts["open"], counts["added_last_run"],
         counts["closed_last_run"], fresh),
    )
    for hours, ads_total, ads_open, added, closed, rated in runs:
        started = now - timedelta(hours=hours)
        conn.execute(
            """INSERT INTO pipeline_runs
               (started_utc, ended_utc, ads_total, ads_open, ads_added, ads_closed,
                reach_model, pending_before, classified_new, classify_usd,
                classifier_version, note, links_added, links_closed, links_held,
                links_flags, held_at_gate)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (_utc(started), _utc(started + timedelta(minutes=9)), ads_total, ads_open, added,
             closed, reach, rated, rated, 0.0, version,
             "demo run, written by pipeline.seed", 0, 0, 0, "[]", 0))
    conn.commit()


def load_state(conn, now):
    """A few jobs already saved and one applied to, so those views are not empty."""
    state = json.loads(STATE.read_text(encoding="utf-8"))
    for status, ids in (("shortlisted", state["starred"]), ("applied", state["applied"])):
        for i, job_id in enumerate(ids):
            conn.execute(
                "INSERT INTO posting_state (id, status, updated_at) VALUES (?, ?, ?)",
                (job_id, status, _utc(now - timedelta(hours=30 + i))))
    conn.commit()


def seed(force=False):
    missing = [p.name for p in (ADS, CLASSIFICATIONS, STATE) if not p.is_file()]
    if missing:
        raise SystemExit(f"sample/ is missing {', '.join(missing)}.")
    db = store.DB_PATH
    if db.exists():
        if not force:
            raise SystemExit(
                f"There is already a store at {db}.\n"
                f"`python -m pipeline.seed --force` throws it away, with any stars and "
                f"applied marks in it, and builds the demo store again.")
        for path in (db, db.with_name(db.name + "-wal"), db.with_name(db.name + "-shm")):
            path.unlink(missing_ok=True)

    now = datetime.now().astimezone()
    conn = store.connect(db)
    print("--- 1/6 ads, from sample/ads.jsonl")
    counts, new = load_ads(conn, now)
    print(f"{counts['open'] + counts['closed']} ads, {counts['open']} open, "
          f"{counts['closed']} closed, {counts['links']} from other job sites")

    print("\n--- 2/6 normalise")
    normalise.rebuild(conn)
    links.ensure(conn)
    print("\n--- 3/6 prefilter")
    prefilter.rebuild(conn)
    print("\n--- 4/6 signals")
    signals.rebuild(conn)

    print("\n--- 5/6 ratings, from sample/classifications.jsonl")
    classified, fresh = load_classifications(conn, now, new)
    print(f"{classified} ratings loaded, generated in advance. Nothing was sent or spent.")
    record_runs(conn, now, counts, classified, fresh)
    load_state(conn, now)

    print("\n--- 6/6 score")
    score.rebuild(conn)

    print("\n=== checks ===")
    failed = 0
    for name, module in (("normalise", normalise), ("prefilter", prefilter),
                         ("signals", signals), ("score", score)):
        print(f"\n{name}")
        failed += module.verify(conn)
    conn.close()

    print()
    if failed:
        print(f"{failed} check(s) failed. The store was built, but something above is wrong.")
        return 1
    print("The demo store is built. Next:\n"
          "  python tools/top.py --limit 15      the ranking, in the terminal\n"
          "  python -m dashboard.serve --open    the dashboard")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true",
                    help="replace an existing store, losing any stars and marks in it")
    args = ap.parse_args()
    sys.exit(seed(args.force))


if __name__ == "__main__":
    main()
