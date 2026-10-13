"""Export and restore the tables nobody can rebuild. Free, no API, no model.

    python -m pipeline.archive export    # write a portable snapshot
    python -m pipeline.archive status    # what snapshots exist
    python -m pipeline.archive verify    # newest snapshot against the store
    python -m pipeline.archive restore --file <path>   # put it back

**Why this exists.** Everything else in `data/postings.db` is derived and free to rebuild:
`postings`, `prefilter`, `signals`, `scores`. Two tables are not. `classifications` is what
Haiku was paid to produce, and `posting_state` is what the user typed. Without a snapshot
both live in exactly one gitignored binary file with no copy anywhere.

That matters because **only new ads go through Haiku**. An ad is classified once and never
paid for again, so the stored rows are an asset to be preserved rather than a cache to be
refilled, and re-earning them means paying for every ad a second time.

**What a snapshot protects against and what it does not.** It survives a corrupted store, a
mistaken `DROP TABLE`, a migration that goes wrong, and a rebuild that reaches further than
it should. It does not survive losing the folder, because it sits next to the database.
`data/` is gitignored, so a git remote does not carry it and an off-machine copy is a
deliberate act: copy `data/archive/` somewhere else and the paid work is genuinely safe.

**Format is JSON Lines, gzipped.** One row per line, column names in every row, so it stays
readable by anything and survives a schema change: `restore` matches on column name and
reports what it could not place rather than failing on column order. A snapshot is
append-only and immutable. Never edit one; take a new one.
"""

import argparse
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import store

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT / "data" / "archive"

# The tables that cost money or attention to produce. Everything else is derived.
# `postings`, `prefilter`, `signals` and `scores` are deliberately NOT here: they
# rebuild from `ads` in seconds and archiving them would bloat the snapshot with data
# that regenerates for free.
DURABLE = ("classifications", "posting_state")


def _now():
    return datetime.now(timezone.utc)


def _rows(conn, table):
    cur = conn.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    for r in cur:
        yield dict(zip(cols, r))


def export(conn, out_dir=ARCHIVE_DIR, label=None):
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _now().strftime("%Y%m%dT%H%M%SZ")
    versions = [r[0] for r in conn.execute(
        "SELECT DISTINCT classifier_version FROM classifications "
        "ORDER BY classifier_version")]
    newest = conn.execute(
        "SELECT classifier_version FROM classifications "
        "ORDER BY classified_at DESC LIMIT 1").fetchone()
    name = label or (newest[0] if newest else "empty")
    path = out_dir / f"classifications-{name}-{stamp}.jsonl.gz"

    counts, digest = {}, hashlib.sha256()
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        header = {
            "_meta": "jobFinder durable snapshot",
            "written_utc": _now().isoformat(timespec="seconds"),
            "tables": list(DURABLE),
            "classifier_versions": versions,
            "newest_classifier_version": name,
        }
        fh.write(json.dumps(header, ensure_ascii=False) + "\n")
        for table in DURABLE:
            n = 0
            for row in _rows(conn, table):
                line = json.dumps({"_table": table, **row}, ensure_ascii=False,
                                  sort_keys=True)
                fh.write(line + "\n")
                digest.update(line.encode())
                n += 1
            counts[table] = n

    size = path.stat().st_size
    print(f"wrote {path.name}")
    print(f"  {path}")
    for t, n in counts.items():
        print(f"  {n:>6} rows  {t}")
    print(f"  {size / 1e6:.1f} MB gzipped, content sha256 {digest.hexdigest()[:16]}")
    print(f"\nThis is the only copy of work that cost money. `data/` is gitignored, so")
    print(f"copy data/archive/ off this machine to make it genuinely safe.")
    return path, counts


def _read(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        for line in fh:
            yield json.loads(line)
    return header


def _stamp(path):
    """The UTC time a snapshot was written, read from the end of its name.

    Sorting on the whole name is wrong, because the label comes before the stamp. A
    snapshot labelled `post-...` sorts after a later one labelled `c1-...`, so the older
    file would be taken for the newest, checked against a store that has gained rows since
    it was written, and reported as a failure that is not there."""
    return path.name.rsplit("-", 1)[-1]


def snapshots(out_dir=ARCHIVE_DIR):
    """Every snapshot, oldest first by the time it was written."""
    return sorted(out_dir.glob("classifications-*.jsonl.gz"), key=_stamp)


def newest_snapshot(out_dir=ARCHIVE_DIR):
    files = snapshots(out_dir)
    return files[-1] if files else None


def status(conn, out_dir=ARCHIVE_DIR):
    live = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in DURABLE}
    print("in the store right now:")
    for t, n in live.items():
        print(f"  {n:>6} rows  {t}")
    print()
    files = snapshots(out_dir)
    if not files:
        print("NO SNAPSHOTS. Run `archive export`. The paid classifications have no copy.")
        return 1
    print(f"{len(files)} snapshot(s) in {out_dir}:")
    for f in files:
        print(f"  {f.stat().st_size / 1e6:>6.1f} MB  {f.name}")
    return 0


def verify(conn, path=None, out_dir=ARCHIVE_DIR):
    """Does the newest snapshot actually contain what the store contains.

    Counts per table, and the set of row keys, because a snapshot that is merely the
    right size is not a snapshot that restores.
    """
    path = Path(path) if path else newest_snapshot(out_dir)
    if path is None:
        print("FAIL  no snapshot to verify")
        return 1
    print(f"verifying {path.name}\n")
    seen = {t: set() for t in DURABLE}
    for row in _read(path):
        t = row.get("_table")
        if t == "classifications":
            seen[t].add((row["id"], row["classifier_version"], row["pass_no"]))
        elif t == "posting_state":
            seen[t].add((row["id"],))
    failed = 0
    for t in DURABLE:
        if t == "classifications":
            live = {tuple(r) for r in conn.execute(
                "SELECT id, classifier_version, pass_no FROM classifications")}
        else:
            live = {tuple(r) for r in conn.execute("SELECT id FROM posting_state")}
        missing, extra = live - seen[t], seen[t] - live
        ok = not missing
        failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {t}: {len(seen[t])} in snapshot, "
              f"{len(live)} in store, {len(missing)} store rows absent from the snapshot"
              + (f", {len(extra)} snapshot rows no longer in the store" if extra else ""))
    print(f"\n{len(DURABLE) - failed}/{len(DURABLE)} tables verified")
    return failed


def restore(conn, path, dry_run=False):
    """Put a snapshot back, without ever destroying a row that is already there.

    INSERT OR IGNORE, never REPLACE. Restoring is a recovery action taken when rows are
    missing, and a restore that overwrote a newer row with an older one would be the
    exact failure this module exists to prevent.
    """
    path = Path(path)
    cols = {t: [d[1] for d in conn.execute(f"PRAGMA table_info({t})")] for t in DURABLE}
    added, skipped, unplaceable = {t: 0 for t in DURABLE}, 0, set()
    for row in _read(path):
        t = row.pop("_table", None)
        if t not in DURABLE:
            continue
        usable = {k: v for k, v in row.items() if k in cols[t]}
        unplaceable |= set(row) - set(usable)
        if dry_run:
            added[t] += 1
            continue
        names = ", ".join(usable)
        marks = ", ".join("?" * len(usable))
        cur = conn.execute(f"INSERT OR IGNORE INTO {t} ({names}) VALUES ({marks})",
                           list(usable.values()))
        added[t] += cur.rowcount
        skipped += 1 - cur.rowcount
    if not dry_run:
        conn.commit()
    verb = "would insert" if dry_run else "inserted"
    for t, n in added.items():
        print(f"  {verb} {n} rows into {t}")
    if not dry_run:
        print(f"  {skipped} rows already present and left untouched")
    if unplaceable:
        print(f"  columns in the snapshot with no home in the current schema: "
              f"{', '.join(sorted(unplaceable))}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["export", "status", "verify", "restore"])
    ap.add_argument("--file", help="restore/verify: which snapshot")
    ap.add_argument("--label", help="export: name the snapshot something memorable")
    ap.add_argument("--dry-run", action="store_true", help="restore: report, change nothing")
    args = ap.parse_args()

    conn = store.connect()
    if args.mode == "export":
        # Verify the file just written, by its path, not whichever snapshot looks newest.
        path, _ = export(conn, label=args.label)
        print()
        sys.exit(1 if verify(conn, path) else 0)
    elif args.mode == "status":
        sys.exit(status(conn))
    elif args.mode == "verify":
        sys.exit(1 if verify(conn, args.file) else 0)
    else:
        if not args.file:
            raise SystemExit("restore needs --file. `archive status` lists what exists.")
        sys.exit(restore(conn, args.file, args.dry_run))


if __name__ == "__main__":
    main()
