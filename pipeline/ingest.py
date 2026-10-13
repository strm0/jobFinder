"""JobTech ingestion. Two modes, no key, no model, no cost.

    python -m pipeline.ingest backfill    # every currently open ad
    python -m pipeline.ingest stream      # everything changed since last run
    python -m pipeline.ingest status      # what is in the store

Backfill uses JobSearch and is a one-off. Stream uses JobStream and is what runs
nightly. Both are idempotent: ads upsert by id, so running either twice is harmless.

Why backfill slices by date: JobSearch reaches at most 2,100 ads per query (limit 100,
offset 2000) and five of the seven occupation fields hold more. Each field's date range
is bisected until every slice fits under the cap.
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone

from . import jobtech, store

# Ads expire, so nothing open was published more than about a year ago. Two years
# of range is slack, and empty slices cost one count call each.
BACKFILL_FROM = datetime(2024, 9, 1, tzinfo=timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _slices(field_id, lo, hi, depth=0):
    """Bisect [lo, hi) until each window holds fewer ads than JobSearch can reach."""
    n = jobtech.count(field_id, _iso(lo), _iso(hi))
    if n == 0:
        return
    if n <= jobtech.REACHABLE:
        yield lo, hi, n
        return
    if (hi - lo) < timedelta(hours=2):
        # Pathological: too many ads in a two hour window. Take what is reachable
        # and say so rather than silently dropping the rest.
        print(f"    ! {n} ads in a <2h window, only {jobtech.REACHABLE} reachable",
              file=sys.stderr)
        yield lo, hi, n
        return
    mid = lo + (hi - lo) / 2
    yield from _slices(field_id, lo, mid, depth + 1)
    yield from _slices(field_id, mid, hi, depth + 1)


def backfill(conn):
    run_id = store.start_run(conn, "backfill", "JobSearch, seven occupation fields")
    counts = {"seen": 0, "inserted": 0, "updated": 0, "closed": 0}
    hi = datetime.now(timezone.utc) + timedelta(days=1)

    for field_id, label in jobtech.FIELDS.items():
        total = jobtech.count(field_id)
        print(f"\n{label}  ({field_id})  {total} open")
        windows = list(_slices(field_id, BACKFILL_FROM, hi))
        if len(windows) > 1:
            print(f"  {len(windows)} date slices, largest {max(w[2] for w in windows)}")

        got = 0
        for lo, whi, n in windows:
            offset = 0
            while offset < min(n, jobtech.REACHABLE):
                hits = jobtech.search_page(field_id, offset,
                                           published_after=_iso(lo),
                                           published_before=_iso(whi))
                if not hits:
                    break
                for ad in hits:
                    counts[store.upsert(conn, ad, "jobsearch")] += 1
                    counts["seen"] += 1
                    got += 1
                conn.commit()
                offset += len(hits)
            print(f"  {_iso(lo)[:10]} to {_iso(whi)[:10]}  {n:5} expected, {got:5} cumulative")

        print(f"  -> {got} stored for {label}")

    store.finish_run(conn, run_id, counts)
    return counts


def stream(conn, hours=None):
    cursor = store.get_cursor(conn)
    if hours is not None:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
    elif cursor:
        # Overlap by ten minutes. Upserts are idempotent, so re-reading a few ads is
        # free, while a gap loses them permanently.
        since = datetime.fromisoformat(cursor) - timedelta(minutes=10)
    else:
        since = datetime.now(timezone.utc) - timedelta(hours=24)

    started = datetime.now(timezone.utc)
    run_id = store.start_run(conn, "stream", f"since {_iso(since)}")
    print(f"JobStream since {_iso(since)} ...")

    events = jobtech.stream(_iso(since))
    counts = {"seen": 0, "inserted": 0, "updated": 0, "closed": 0}
    skipped = 0
    for ad in events:
        field = (ad.get("occupation_field") or {}).get("concept_id")
        # Removals carry a field id, so they are still matched against the seven.
        if field not in jobtech.FIELDS:
            skipped += 1
            continue
        counts[store.upsert(conn, ad, "jobstream")] += 1
        counts["seen"] += 1
    conn.commit()

    store.finish_run(conn, run_id, counts)
    store.set_cursor(conn, _iso(started))
    print(f"{len(events)} events, {skipped} outside the seven fields, "
          f"{counts['seen']} applied")
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["backfill", "stream", "status"])
    ap.add_argument("--hours", type=int, help="stream: override the stored cursor")
    args = ap.parse_args()

    conn = store.connect()
    if args.mode == "backfill":
        counts = backfill(conn)
        print(f"\nbackfill: {counts}")
    elif args.mode == "stream":
        counts = stream(conn, args.hours)
        print(f"stream: {counts}")

    print(f"store: {store.summary(conn)}")


if __name__ == "__main__":
    main()
