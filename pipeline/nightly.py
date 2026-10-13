"""The daily run. One command, in the order the stages depend on each other.

    python -m pipeline.nightly run          # free: everything except classify
    python -m pipeline.nightly run --yes    # spends, classifies what is new
    python -m pipeline.nightly auto         # what a schedule calls. Free without --yes
    python -m pipeline.nightly auto --yes   # the same, and classifies what is new. Spends.
    python -m pipeline.nightly report       # tonight against last night
    python -m pipeline.nightly history      # the last runs, as a table

This exists because the system is not a one-off pass. It runs every day for as long as
the job search lasts, so the question it has to answer is not "how does this compare to
the day the rules were set" but "what changed since last night, and what did it cost".

    ingest stream       new, changed and closed ads from JobStream          free
    links run           ads from other job sites, with their full text      free
    normalise rebuild   `postings` from `ads`                               free
    prefilter rebuild   `prefilter` from the group verdicts and the rescue  free
    signals rebuild     `signals`, the 15 term-matched soft signals         free
    classify --pending  ONLY ads never classified, however many              SPENDS
    score rebuild       `recommend` over whatever is classified             free

**The classify step is the only one that spends, and it never pays for an ad twice.**
It classifies every kept, open ad that has never been classified, with no cap on how
many, because a ceiling stops the run that follows a few unrun days of ordinary
arrivals. Ads made stale by an edit to the brief or the prompt are not new. They are
counted, reported and skipped, because re-buying all the paid rows is a decision to make
by hand and never one for a schedule.

**Ads from other job sites wait at a gate.** The links step fetches them and reads each
one's full text from its site, free, and the classify step leaves them alone until
`links.classify` in the config is true. A site whose reader stops finding text is flagged
in the report.

Every run writes a row to `pipeline_runs`, which is what makes `report` possible. The
derived rebuilds are idempotent, so a failed run is re-run rather than repaired, and a
run without `--yes` has still done all the free work.

**The schedule is "the first time each day the laptop is on power".** The system
scheduler, launchd, calls `auto` every 15 minutes and at login. It does nothing, silently,
unless the laptop is on power and no run has finished today, and it waits 30 minutes after
an attempt that did not finish. A run holds the laptop awake while it is on power, and only
one runs at a time: a manual `run` takes the same lock. The run is not tied to a fixed hour
because a laptop that is asleep at that hour never runs it, and a run started in a brief
wake on battery either crawls or loses its connection mid-download.

TIMING: `signals` takes most of the time the four rebuilds need, because it regex-scans
every ad's full description text. That is proportional to the whole store rather than to
what arrived overnight. Fine at this size and worth knowing before the store is several
times larger.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import requests

from . import classify, ingest, jobtech, links, normalise, prefilter, score, signals, store

SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    started_utc        TEXT NOT NULL,
    ended_utc          TEXT,
    ads_total          INTEGER,
    ads_open           INTEGER,
    ads_added          INTEGER,   -- inserted by this run's stream
    ads_closed         INTEGER,   -- closed by this run's stream
    reach_model        INTEGER,   -- kept by the pre-filter, open
    pending_before     INTEGER,   -- unclassified at the current version, before classify
    classified_new     INTEGER,   -- rows actually written by this run
    classify_usd       REAL,
    classifier_version TEXT,      -- what the sources hashed to during this run
    score_version      TEXT,
    note               TEXT
);
"""

# Added by ALTER rather than in the CREATE above, so a `pipeline_runs` table that already
# holds rows gains them. `ads_added` and `ads_closed` count both sources; these say how
# much of each came from other job sites.
LINKS_COLUMNS = {
    "links_added": "INTEGER",     # ads from other sites written to the store this run
    "links_closed": "INTEGER",
    "links_held": "INTEGER",      # open ads let in with no full text after this run
    "links_flags": "TEXT",        # JSON, the sites whose reader is flagged
    "held_at_gate": "INTEGER",    # kept, unclassified ads from other sites, gate closed
}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# One run at a time, and when the last one was tried. The file holds the start of the last
# attempt; the lock on it is the kernel's and goes when the process ends, however it ends,
# so a crashed run never leaves it stuck. Gitignored with the rest of data/.
LOCK_PATH = store.DB_PATH.parent / "nightly.lock"
WAIT_AFTER_ATTEMPT = 30 * 60   # seconds before `auto` tries again after a run that did not finish


def _take_lock():
    """The open lock file and the last attempt's start, or (None, None) if a run holds it."""
    import fcntl  # here, not at the top: it does not exist on Windows, and seed imports this module
    f = os.fdopen(os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o644), "r+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None, None
    return f, (f.read().split() or [None])[0]


def _mark_attempt(lock):
    lock.seek(0)
    lock.truncate()
    lock.write(f"{_now()} pid {os.getpid()}\n")
    lock.flush()


def _hold_awake():
    # -s holds off sleep only while the laptop is on power, which is the rule `auto` runs on.
    # -w ends it with this process. Unplugged mid-run, the laptop may sleep; the run then
    # resumes at the next wake, or fails and is tried again.
    try:
        subprocess.Popen(["caffeinate", "-s", "-w", str(os.getpid())])
    except FileNotFoundError:
        pass  # not macOS: nothing to hold awake with, and the run does not depend on it


def _on_power():
    out = subprocess.run(["pmset", "-g", "ps"], capture_output=True, text=True).stdout
    return "'AC Power'" in out.partition("\n")[0]


# The note a run leaves when it found new ads and was not allowed to spend on them.
UNSPENT = "not run without --yes"


def _finished_today(conn):
    """Whether the last recorded run ended on today's date, in the laptop's own time zone. A
    run that crashed wrote no row, so it does not count, and nor does a free run that left
    new ads unclassified."""
    row = conn.execute(
        "SELECT ended_utc FROM pipeline_runs WHERE COALESCE(note, '') NOT LIKE ? "
        "ORDER BY id DESC LIMIT 1", (f"%{UNSPENT}%",)).fetchone()
    if row is None or row["ended_utc"] is None:
        return False
    return datetime.fromisoformat(row["ended_utc"]).astimezone().date() == datetime.now().date()


def ensure_schema(conn):
    conn.executescript(SCHEMA)
    have = {r["name"] for r in conn.execute("PRAGMA table_info(pipeline_runs)")}
    for name, kind in LINKS_COLUMNS.items():
        if name not in have:
            conn.execute(f"ALTER TABLE pipeline_runs ADD COLUMN {name} {kind}")
    conn.commit()


def _spend_at(conn, version, since_utc):
    """What this run actually paid, read back from the rows it wrote rather than from
    an estimate. Same arithmetic `classify status` uses."""
    # GROUP BY via_batch, not MAX(via_batch). Batch rows are billed at half and direct
    # rows are not, so one discount over a mixed set is wrong. A single run only ever
    # uses one path, but a version accumulates rows from several runs, and pricing that
    # mix with the batch discount throughout understates what was paid.
    rows = conn.execute(
        """SELECT COALESCE(via_batch, 0)             batched,
                  COUNT(*)                           n,
                  COALESCE(SUM(input_tokens), 0)     uncached,
                  COALESCE(SUM(cache_read_tokens), 0)  reads,
                  COALESCE(SUM(cache_write_tokens), 0) writes,
                  COALESCE(SUM(output_tokens), 0)      out
           FROM classifications
           WHERE classifier_version = ? AND classified_at >= ?
           GROUP BY COALESCE(via_batch, 0)""",
        (version, since_utc),
    ).fetchall()
    total_n = sum(r["n"] for r in rows)
    usd = sum(classify.billed_cost(r["uncached"], r["reads"], r["writes"], r["out"],
                                   r["batched"]) for r in rows)
    return total_n, usd


def run(conn, spend=False, max_ads=None, batched=False):
    ensure_schema(conn)
    started = _now()
    cfg = classify.load_config()
    version = classify.classifier_version(cfg)

    before = store.summary(conn)
    print(f"=== nightly run, {started} ===")
    print(f"classifier_version, from the brief and prompt as they stand: {version}\n")

    print("--- 1/7 ingest stream")
    counts = ingest.stream(conn)
    notes = []

    print("\n--- 2/7 links")
    # A bad night at Links or at a job site must not cost the Platsbanken half of the run.
    try:
        other = links.run(conn)
    except (requests.RequestException, jobtech.JobTechError) as err:
        print(f"! the links step stopped: {err}. Platsbanken carries on.", file=sys.stderr)
        notes.append(f"links step failed: {str(err)[:120]}")
        other = {"added": 0, "closed": 0, "held_back": links.held_back_total(conn),
                 "flags": links.flagged(conn)}
    if other["flags"]:
        notes.append("reader flagged: " + ", ".join(f["site"] for f in other["flags"]))

    print("\n--- 3/7 normalise")
    normalise.rebuild(conn)
    print("\n--- 4/7 prefilter")
    prefilter.rebuild(conn)
    print("\n--- 5/7 signals")
    signals.rebuild(conn)

    print("\n--- 6/7 classify")
    pending = classify.pending_count(conn, version)
    stale = classify.stale_count(conn, version)
    held = classify.held_at_gate(conn, version, cfg)
    rows = classify.fetch_pending(conn, version, limit=max_ads)
    classified, usd = 0, 0.0
    if held:
        notes.append(f"{held} from other sites held at the gate")
        print(f"{held} kept ads from other job sites wait at the gate, `links.classify` in the "
              f"config, and are not classified.")

    if stale:
        # Never spent by this step. See classify.fetch_pending.
        notes.append(f"{stale} stale after a brief or prompt edit, skipped")
        print(f"NOTE: {stale} kept open ads were classified under an older brief or prompt "
              f"and are stale at {version}.\n"
              f"      Skipped. Re-buying them is a funded decision, made by hand: "
              f"classify run --pending --include-stale --yes")
    if not rows:
        notes.append("nothing new")
        print(f"nothing new to classify at {version}.")
    elif not spend:
        e = classify.estimate(conn, cfg, rows, batched=batched, cached=True)
        notes.append(f"{len(rows)} new, {UNSPENT}")
        print(f"{len(rows)} new ads. Classifying them would cost about {e['usd']:.2f} USD.")
        print("Not spending. Re-run with --yes.")
    else:
        e = classify.estimate(conn, cfg, rows, batched=batched, cached=True)
        print(f"{len(rows)} new ads, about {e['usd']:.2f} USD. Running.")
        if batched:
            classify.run_batch(conn, cfg, rows)
            notes.append("batch submitted, collect it before the next run")
        else:
            classify.run_direct(conn, cfg, rows)
        classified, usd = _spend_at(conn, version, started)
    note = "; ".join(notes) or None

    print("\n--- 7/7 score")
    score.rebuild(conn)
    failed = score.verify(conn)
    print()
    failed += links.verify(conn)

    after = store.summary(conn)
    reach = conn.execute(
        """SELECT COUNT(*) c FROM prefilter f JOIN postings p ON p.id = f.id
           WHERE p.removed = 0 AND f.verdict = 'keep'"""
    ).fetchone()["c"]
    sv = conn.execute("SELECT rule_version FROM scores LIMIT 1").fetchone()

    conn.execute(
        """INSERT INTO pipeline_runs
           (started_utc, ended_utc, ads_total, ads_open, ads_added, ads_closed,
            reach_model, pending_before, classified_new, classify_usd,
            classifier_version, score_version, note, links_added, links_closed,
            links_held, links_flags, held_at_gate)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (started, _now(), after["total"], after["open"], counts["inserted"] + other["added"],
         counts["closed"] + other["closed"], reach, pending, classified, usd, version,
         sv["rule_version"] if sv else None, note, other["added"], other["closed"],
         other["held_back"], json.dumps([f["site"] for f in other["flags"]]), held),
    )
    conn.commit()

    print()
    report(conn)
    return failed


def auto(spend=False):
    """What a scheduler calls, every 15 minutes and at login. Runs the first time each day the
    laptop is on power, and is silent otherwise so the log only grows when a run does. It
    classifies only when started with --yes: a schedule that spends is an explicit choice,
    made where the schedule is set up, and never the default. macOS only, because it reads
    the power state with pmset. There is no battery fallback: after days on battery the run
    is started by hand."""
    if not _on_power():
        return False
    lock, last = _take_lock()
    if lock is None:
        return False
    conn = store.connect()
    ensure_schema(conn)
    if _finished_today(conn):
        return False
    if last and (datetime.now(timezone.utc)
                 - datetime.fromisoformat(last)).total_seconds() < WAIT_AFTER_ATTEMPT:
        return False
    _mark_attempt(lock)
    _hold_awake()
    print(f"auto, {_now()}: on power and no run has finished today. Starting.")
    if not spend:
        print("auto was started without --yes, so the classify step will report its cost "
              "and spend nothing.")
    return run(conn, spend=spend)


def report(conn):
    """Tonight against last night. This is the output that matters day to day, and it
    is deliberately a delta rather than a comparison against a fixed date: after the
    first week nobody cares what the numbers were when the rules were set."""
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT 2"
    ).fetchall()
    if not rows:
        print("no runs recorded yet. Run `nightly run` first.")
        return
    now, prev = rows[0], (rows[1] if len(rows) > 1 else None)

    def delta(field, fmt="{:+d}"):
        if prev is None or prev[field] is None or now[field] is None:
            return ""
        d = now[field] - prev[field]
        return f"   {fmt.format(d)} since last run" if d else "   unchanged"

    print(f"=== run {now['id']}, {now['started_utc']} ===")
    if prev:
        print(f"    previous run {prev['id']}, {prev['started_utc']}")
    print()
    print(f"  ads in store        {now['ads_total']:>7,}{delta('ads_total')}")
    print(f"  open                {now['ads_open']:>7,}{delta('ads_open')}")
    print(f"    arrived           {now['ads_added']:>7,}")
    print(f"    closed            {now['ads_closed']:>7,}")
    print(f"  reaching the model  {now['reach_model']:>7,}{delta('reach_model')}")
    if now["links_added"] is not None:
        print("  from other sites")
        print(f"    arrived           {now['links_added']:>7,}")
        print(f"    closed            {now['links_closed']:>7,}")
        print(f"    held back         {now['links_held']:>7,}   no full text read")
        print(f"    at the gate       {now['held_at_gate']:>7,}   kept, not classified while "
              f"links.classify is false")
        for site in json.loads(now["links_flags"] or "[]"):
            print(f"    FLAG  {site}: its reader is finding too little text. "
                  f"`pipeline.links status`, then fix it in pipeline/links.py.")
    print()
    print(f"  pending before      {now['pending_before']:>7,}")
    print(f"  classified this run {now['classified_new']:>7,}")
    print(f"  spent this run      {now['classify_usd'] or 0:>10.4f} USD")
    total = conn.execute(
        "SELECT COALESCE(SUM(classify_usd), 0) s FROM pipeline_runs"
    ).fetchone()["s"]
    print(f"  spent over all runs {total:>10.4f} USD")
    print()
    print(f"  classifier_version  {now['classifier_version']}")
    if prev and prev["classifier_version"] != now["classifier_version"]:
        print(f"    CHANGED from {prev['classifier_version']}. The brief or the prompt "
              f"was edited, so\n    every ad classified under the old one is stale.")
    print(f"  score rule_version  {now['score_version']}")
    if now["note"]:
        print(f"\n  note: {now['note']}")


def history(conn, limit=14):
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    if not rows:
        print("no runs recorded yet.")
        return
    print(f"{'run':>4} {'started':<20} {'open':>7} {'+new':>6} {'-closed':>8} "
          f"{'kept':>7} {'clsfd':>6} {'USD':>8}  classifier")
    for r in rows:
        print(f"{r['id']:>4} {r['started_utc'][:19]:<20} {r['ads_open'] or 0:>7,} "
              f"{r['ads_added'] or 0:>6,} {r['ads_closed'] or 0:>8,} "
              f"{r['reach_model'] or 0:>7,} {r['classified_new'] or 0:>6,} "
              f"{r['classify_usd'] or 0:>8.4f}  {r['classifier_version'] or ''}")
    total = conn.execute(
        "SELECT COALESCE(SUM(classify_usd), 0) s FROM pipeline_runs"
    ).fetchone()["s"]
    print(f"\ntotal spent across {len(rows)} shown runs and any older ones: {total:.4f} USD")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["run", "auto", "report", "history"])
    ap.add_argument("--yes", action="store_true",
                    help="allow the classify step to spend. Without it everything else "
                         "still runs and the cost is reported.")
    ap.add_argument("--max", type=int,
                    help="classify at most this many new ads. No limit by default: every "
                         "new ad is classified, however many.")
    ap.add_argument("--batch", action="store_true",
                    help="use the Batch API. Only for the full pass, "
                         "because it is a queue and results land hours later.")
    ap.add_argument("--limit", type=int, default=14, help="history: how many runs")
    args = ap.parse_args()

    if args.mode == "auto":
        sys.exit(1 if auto(spend=args.yes) else 0)
    conn = store.connect()
    if args.mode == "run":
        lock, _ = _take_lock()
        if lock is None:
            sys.exit("another nightly run is going. `pgrep -fl pipeline.nightly` shows it.")
        _mark_attempt(lock)
        _hold_awake()
        sys.exit(1 if run(conn, spend=args.yes, max_ads=args.max,
                          batched=args.batch) else 0)
    elif args.mode == "report":
        report(conn)
    else:
        history(conn, args.limit)


if __name__ == "__main__":
    main()
