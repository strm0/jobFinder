"""Read the classified postings. No API, no cost, no writes to the store.

    python3 tools/top.py                     # top 25, ranked, industry track
    python3 tools/top.py --track phd         # the doctoral track, by recommendation
    python3 tools/top.py --lane L1           # one lane
    python3 tools/top.py --limit 50 --full   # more rows, with the model's reasons
    python3 tools/top.py --rejected          # what was dropped, and why
    python3 tools/top.py --out top.md        # write markdown instead of printing

This exists because the results of classification live in `data/postings.db`, which is
gitignored and binary. Everything the model judged is on disk and none of it is readable
without a tool. `02_search_config.yaml` calls for "query scripts over the postings store
that Claude Code can call" and this is one of them.

Standard library only, so plain `python3` runs it, like build_index.py and render.py.

RANKING. This reads `recommend` from the `scores` table and computes nothing. The formula
lives in one place: the constants are in `02_search_config.yaml` under
`scoring.recommend_rules.constants` and the only code that reads them is
`pipeline/score.py`. A second copy of the formula here would drift from it.

If `scores` is missing or stale, this says so and stops. Rebuilding it is free:

    python -m pipeline.score rebuild
"""

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "postings.db"


def connect():
    if not DB.exists():
        sys.exit(f"no store at {DB}. Run the ingest and normalise steps first; "
                 f"see the README.")
    # Opened read-write on purpose, though this tool only ever SELECTs. A `mode=ro`
    # URI connection cannot open a WAL database: SQLite needs to write the -shm
    # sidecar to read one, and the store runs in WAL mode.
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def current_version(conn):
    """The newest classifier_version. Older rows are stale by definition: the prompt or
    the candidate brief changed after they were written."""
    row = conn.execute(
        "SELECT classifier_version FROM classifications ORDER BY classified_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        sys.exit("nothing classified yet. Run the classify step first; see the README.")
    return row["classifier_version"]


def check_scores(conn, version):
    """`scores` must exist and must not be silently behind the classifications.

    This tool is standard library only, so it cannot hash the brief and the prompt to
    find out what the CURRENT classifier version is. It does not pretend to. What it can
    do is two things that catch the real cases: refuse if `scores` is behind
    `classifications`, and read the version the last `nightly run` saw in the source
    files, which `pipeline_runs` records. If that disagrees with what the scores were
    built from, the ranking is stale and says so instead of looking fine.
    """
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'scores'"
    ).fetchone()
    if exists is None:
        sys.exit("no `scores` table. Building it is free:\n"
                 "    python -m pipeline.score rebuild")
    stale = conn.execute(
        """SELECT COUNT(*) c FROM scores s
           WHERE NOT EXISTS (SELECT 1 FROM classifications c
                             WHERE c.id = s.id AND c.classifier_version = ?)""",
        (version,),
    ).fetchone()[0]
    if stale:
        sys.exit(f"{stale} scored postings were classified under an older prompt than "
                 f"{version}. Rescoring is free:\n"
                 f"    python -m pipeline.score rebuild")
    return source_version_warning(conn, version)


def source_version_warning(conn, version):
    """Is the ranking stale, answered from two columns written in the same instant.

    `scores` carries both the `classifier_version` it scored and the `source_version` the
    brief and prompt hashed to at that rebuild. If they differ, somebody edited the brief
    or the prompt after these judgements were bought.

    **Asking `pipeline_runs` for the source version instead would be wrong**, because a
    run row is a record of one moment and goes stale itself. Comparing fresh scores
    against an older dry run's row reports a perfectly current ranking as stale. Two
    columns written by the same code at the same moment cannot drift apart that way.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(scores)")}
    if "source_version" not in cols:
        return None                      # scores predate the column; say nothing
    row = conn.execute(
        "SELECT classifier_version, source_version FROM scores LIMIT 1"
    ).fetchone()
    if row is None or row["classifier_version"] == row["source_version"]:
        return None
    return (f"> **This ranking is stale.** These postings were judged under "
            f"`{row['classifier_version']}`,\n> but when they were last scored the "
            f"candidate brief and classifier prompt hashed to\n> "
            f"`{row['source_version']}`. Somebody edited one of them, so every want and "
            f"reach\n> below answers a question that has since changed. Reclassifying is "
            f"NOT free:\n> check what it will cost before doing anything about it.\n")


def fetch(conn, version, track=None, lane=None, rejected=False):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(scores)")}
    folds = "repost_of" in cols          # a `scores` table from before reposts were folded lacks it
    # Open ads only, in both views. `scores` keeps rows for ads that have since closed,
    # and a job that can no longer be applied to is noise in either list.
    where = ["c.classifier_version = ?", "p.removed = 0"]
    args = [version]
    if rejected:
        where.append("s.eligible = 0")
    else:
        where.append("s.eligible = 1")
        if folds:
            # An exact repost is folded into the card it repeats, so it is not listed
            # twice. The rule is in pipeline/score.py.
            where.append("s.repost_of IS NULL")
        where.append("c.track = ?")
        args.append(track or "industry")
    dropped = "s.dropped_hits" if folds else "NULL dropped_hits"
    rows = conn.execute(
        f"""SELECT c.*, s.recommend, s.eligible, s.reject_reason, {dropped},
                   p.headline, p.employer_name, p.municipality, p.webpage_url,
                   p.application_deadline, p.occupation_group_label, f.verdict, f.reason
            FROM classifications c
            JOIN scores s ON s.id = c.id
            JOIN postings p ON p.id = c.id
            LEFT JOIN prefilter f ON f.id = c.id
            WHERE {' AND '.join(where)}""", args
    ).fetchall()
    out = []
    for r in rows:
        lanes = json.loads(r["matched_lanes"] or "[]")
        if lane and not any(l["id"].startswith(lane) for l in lanes):
            continue
        out.append((r["recommend"], r, lanes))
    # Both tracks sort on `recommend`. Sorting the PhD view on deadline buries the best
    # call under weakly wanted ones that happen to close sooner. **The deadline is a
    # warning, not an ordering**, so it shows on the card with an expiring-soon marker
    # and stays only as the tie-break: between two calls wanted equally, the one closing
    # first is the one to write today.
    out.sort(key=lambda t: (-t[0], t[1]["application_deadline"] or "9999"))
    return out


EXPIRING_SOON_DAYS = 14


def _deadline_note(deadline):
    """The expiring-soon marker the config asks for. Both views sort on `recommend`,
    so the deadline has to carry its own urgency on the card instead of being the
    sort order. Returns a suffix, or empty."""
    if not deadline:
        return ""
    try:
        left = (date.fromisoformat(deadline[:10]) - date.today()).days
    except ValueError:
        return ""
    if left < 0:
        return "  **CLOSED**"
    if left == 0:
        return "  **TODAY**"
    if left <= EXPIRING_SOON_DAYS:
        return f"  **{left} day{'s' if left != 1 else ''} left**"
    return ""


def render(rows, version, limit, full, rejected, track):
    L = []
    head = {"phd": "Doctoral track, by recommendation",
            "industry": "Industry track, by recommendation"}.get(track, "Rejected")
    if rejected:
        head = "Rejected: no lane, a hard filter, or skipped before the model saw it"
    L.append(f"# {head}\n")
    L.append(f"`{version}` · {len(rows)} matching · showing {min(limit, len(rows))}\n")
    for score, r, lanes in rows[:limit]:
        lanestr = " ".join(f"{l['id'].split('_')[0]}:{l['fit']}" for l in lanes) or "-"
        dropped = json.loads(r["dropped_hits"] or "[]")
        hf = [h for h in json.loads(r["hard_filter_hits"] or "[]") if h not in dropped]
        deadline = (r["application_deadline"] or "")[:10]
        L.append(f"\n## {r['headline']}\n")
        L.append(f"- **{r['employer_name'] or 'employer not stated'}**"
                 f"{', ' + r['municipality'] if r['municipality'] else ''}"
                 f" · apply by **{deadline or 'not stated'}**"
                 f"{_deadline_note(deadline)}")
        L.append(f"- want **{r['want']}** · reach **{r['reach']}** · recommend **{score:.1f}**"
                 f" · {lanestr}")
        if hf:
            L.append(f"- **disqualifying:** {', '.join(hf)}")
        if dropped:
            L.append(f"- not applied: {', '.join(dropped)}, the ad names no real bar")
        if r["reject_reason"]:
            L.append(f"- **rejected:** `{r['reject_reason']}`")
        L.append(f"- {r['summary']}")
        L.append(f"- <{r['webpage_url']}>")
        if full:
            L.append(f"\n  - *want:* {r['want_why']}")
            L.append(f"  - *reach:* {r['reach_why']}")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--track", default="industry", choices=["industry", "phd"])
    ap.add_argument("--lane", help="filter to one lane, e.g. L1")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--full", action="store_true", help="include the model's reasons")
    ap.add_argument("--rejected", action="store_true", help="show what was dropped instead")
    ap.add_argument("--out", help="write markdown to this file instead of printing")
    args = ap.parse_args()

    conn = connect()
    version = current_version(conn)
    warning = check_scores(conn, version)
    rows = fetch(conn, version, args.track, args.lane, args.rejected)
    text = render(rows, version, args.limit, args.full, args.rejected, args.track)
    if warning:
        # Above the listing, not below it. A caveat under forty postings is a caveat
        # nobody reads.
        text = text.split("\n", 1)
        text = text[0] + "\n\n" + warning + "\n" + text[1]

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {min(args.limit, len(rows))} of {len(rows)} postings to {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
