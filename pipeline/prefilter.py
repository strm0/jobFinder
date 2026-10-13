"""The pre-LLM filter. No API, no cost, free to re-run.

    python -m pipeline.prefilter rebuild   # drop and rebuild `prefilter`
    python -m pipeline.prefilter verify    # check the rules still hold
    python -m pipeline.prefilter status    # what is in the table
    python -m pipeline.prefilter unknown   # groups missing from the table

Runs between the store and Haiku, never at the fetch: JobStream takes no filters and
ingestion is free, so filtering at the fetch would save nothing and lose ads for good.

Three steps, in order:

    0. Skip an ad from another job site that is a job already on Platsbanken, a twin,
       from `links.find_twins`, so one job is never paid for twice. Checked
       first, so a twin found after its Links copy was classified is still known as one
       and `score.py` can fold it under the Platsbanken card.
    1. Skip by occupation group, from the verdicts in
       context/occupation_groups.md. 96 of 159 groups.
    2. Return any skipped ad whose headline names one of the candidate's lanes and
       does not hit the narrow veto, from `prefilter.headline_rescue` in
       context/02_search_config.yaml.

Neither list is duplicated here. Both files are hand-maintained and authoritative,
and this module compiles them. Together they let roughly four in ten open ads reach
the model.

`prefilter` is derived, like `postings`. Dropped and rebuilt at will, never holds
anything paid for. A skipped ad is never deleted: it keeps its reason and shows in
the dashboard's rejected view, so a wrong verdict is visible rather than silent.

THE ONE RULE THAT MATTERS: a group missing from the table defaults to KEEP. Failing
open costs a tenth of a cent per ad. Failing closed loses ads and says nothing.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

import yaml

from . import links, store

ROOT = Path(__file__).resolve().parent.parent
GROUPS_MD = ROOT / "context" / "occupation_groups.md"
CONFIG_YAML = ROOT / "context" / "02_search_config.yaml"

# The verdict table is hand-edited prose. If an edit breaks the markdown the parser
# would quietly return nothing, every group would fall through to the default, and
# every ad in the store would reach the model and be paid for. Refuse to run instead.
MIN_EXPECTED_GROUPS = 100

# The twin rule's tag, in rule_version so rows from before and after a change to
# `links.find_twins` can be told apart. The rule itself lives there, in one copy.
TWIN_RULE = "t1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS prefilter (
    id           TEXT PRIMARY KEY,
    verdict      TEXT NOT NULL,          -- keep | skip
    reason       TEXT NOT NULL,          -- why, in a form the rejected view can show
    rule_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS prefilter_verdict ON prefilter(verdict);
CREATE INDEX IF NOT EXISTS prefilter_version ON prefilter(rule_version);
"""


def load_verdicts(path=GROUPS_MD):
    """Parse the verdict column out of the markdown table. Nothing else is read."""
    verdicts = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # | ads | occupation group | mostly from | verdict | note |
        if len(cells) < 4 or not cells[0].rstrip("-:").isdigit():
            continue  # header and separator rows
        verdict = cells[3].strip("`")
        if verdict in ("keep", "skip"):
            verdicts[cells[1]] = verdict
    if len(verdicts) < MIN_EXPECTED_GROUPS:
        raise SystemExit(
            f"only {len(verdicts)} group verdicts parsed from {path.name}, expected at "
            f"least {MIN_EXPECTED_GROUPS}. The table is probably malformed. Refusing to "
            f"run rather than defaulting every group to keep."
        )
    return verdicts


def load_rescue(path=CONFIG_YAML):
    """Compile the headline rescue terms and the veto. Case-insensitive, headline only."""
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    hr = cfg["prefilter"]["headline_rescue"]
    terms = [(t, re.compile(t, re.I)) for t in hr["terms"]]
    veto = [(t, re.compile(t, re.I)) for t in hr["veto"]]
    return terms, veto


def rule_version(verdicts, terms, veto):
    """A version that changes when either source file's rules change.

    The classifier stores `classifier_version` so a reclassify can target what is
    stale. The same argument applies here: after an edit to either list, the rows
    written under the old rules need to be identifiable.
    """
    h = hashlib.sha256()
    for group, verdict in sorted(verdicts.items()):
        h.update(f"{group}={verdict}\n".encode())
    for src, _ in terms:
        h.update(f"rescue:{src}\n".encode())
    for src, _ in veto:
        h.update(f"veto:{src}\n".encode())
    h.update(f"twins={TWIN_RULE}\n".encode())
    return f"pf1-{h.hexdigest()[:8]}"


def decide(headline, group, verdicts, terms, veto):
    """One ad's verdict. Returns (verdict, reason).

    Order is fixed: group first, then the rescue, which only ever adds
    ads back. An unrecognised group is kept and says so, so `unknown` can find it.
    """
    verdict = verdicts.get(group)
    if verdict is None:
        return "keep", f"group_unknown:{group}"
    if verdict == "keep":
        return "keep", f"group_keep:{group}"

    headline = headline or ""
    hit = next((src for src, rx in terms if rx.search(headline)), None)
    if hit is None:
        return "skip", f"group_skip:{group}"

    blocked = next((src for src, rx in veto if rx.search(headline)), None)
    if blocked is not None:
        return "skip", f"veto:{blocked}"
    return "keep", f"rescue:{hit}"


def rebuild(conn):
    verdicts = load_verdicts()
    terms, veto = load_rescue()
    version = rule_version(verdicts, terms, veto)

    conn.execute("DROP TABLE IF EXISTS prefilter")
    conn.executescript(SCHEMA)

    # Every posting gets a verdict, closed ones included. The classifier selects on
    # removed = 0 itself; carrying the verdict anyway costs nothing and means a
    # reopened ad is already decided.
    rows = conn.execute(
        "SELECT id, headline, occupation_group_label FROM postings"
    ).fetchall()
    twins = links.find_twins(conn)

    batch = []
    for r in rows:
        if r["id"] in twins:
            batch.append((r["id"], "skip", f"twin:{twins[r['id']]}", version))
            continue
        v, reason = decide(r["headline"], r["occupation_group_label"],
                           verdicts, terms, veto)
        batch.append((r["id"], v, reason, version))
    conn.executemany(
        "INSERT INTO prefilter (id, verdict, reason, rule_version) VALUES (?, ?, ?, ?)",
        batch,
    )
    conn.commit()

    print(f"prefilter rebuilt: {len(batch)} rows, rule_version {version}")
    print(f"  {len(verdicts)} group verdicts, "
          f"{sum(1 for x in verdicts.values() if x == 'skip')} skip, "
          f"{sum(1 for x in verdicts.values() if x == 'keep')} keep")
    print(f"  {len(terms)} rescue terms, {len(veto)} veto terms")
    print(f"  {len(twins)} ads from other sites skipped as twins of a Platsbanken ad")
    return len(batch)


# --------------------------------------------------------------------------
# Checks, in two kinds, and the split matters.
#
# RULE CHECKS assert exact values, because they catch an edit to a source file
# and a source file does not change on its own. A wrong group count or a
# changed rule_version is always worth stopping for.
#
# RATE CHECKS assert a proportion inside a band, because the store grows every
# night and absolute counts cannot survive that. One night's `stream` can bring
# in over a thousand ads, and a check that asserted the previous day's counts
# would then fail while nothing had actually changed. A check that fails every
# night is a check that gets ignored, and a real failure then hides inside the
# noise it made.
#
# Neither kind reports a trend. "What changed since last night" is a different
# question from "is anything broken", it is the one worth asking every day, and
# it is answered by `pipeline/nightly.py report` off the `pipeline_runs` table.
# --------------------------------------------------------------------------

# The rates these bands are drawn around: about 40 % of open ads kept, a little
# under 1 % of the ads the group list skipped rescued, and about a third of the
# rescue hits vetoed. That is a comment and not a constant on purpose. Printing
# a fixed baseline in every check's detail line is noise, because nobody needs
# to compare each run against one old measurement. The comparison that is
# useful every day is tonight against last night, and it lives in
# `pipeline/nightly.py report`, which is where a delta belongs.

# How far a rate may drift from its baseline before it is worth stopping for.
# Wide on purpose. These exist to catch a rule edited by accident, a term list
# widened until it matches everything, or a rescue that has stopped firing.
# They are not there to notice that the Swedish job market had a quiet week.
KEEP_RATE_BAND    = (0.30, 0.50)   # share of open ads reaching the model
RESCUE_RATE_BAND  = (0.002, 0.030)  # share of group-skipped ads pulled back
VETO_SHARE_BAND   = (0.10, 0.60)   # share of rescue hits the veto blocks

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn)); return fn
    return deco


def _open_counts(conn):
    return dict(conn.execute(
        """SELECT f.verdict, COUNT(*) c FROM prefilter f
           JOIN postings p ON p.id = f.id
           WHERE p.removed = 0 GROUP BY f.verdict"""
    ).fetchall())


@check("every posting has a verdict")
def _c1(conn):
    p = conn.execute("SELECT COUNT(*) c FROM postings").fetchone()["c"]
    f = conn.execute("SELECT COUNT(*) c FROM prefilter").fetchone()["c"]
    return p == f, f"{p} postings, {f} verdicts"


@check("one rule_version across the table")
def _c2(conn):
    n = conn.execute("SELECT COUNT(DISTINCT rule_version) c FROM prefilter").fetchone()["c"]
    return n == 1, f"{n} distinct versions (a rebuild writes exactly one)"


@check("the compiled rules still match the source files")
def _c3(conn):
    stored = conn.execute("SELECT rule_version FROM prefilter LIMIT 1").fetchone()
    if stored is None:
        return False, "table is empty, run rebuild"
    verdicts = load_verdicts()
    terms, veto = load_rescue()
    live = rule_version(verdicts, terms, veto)
    ok = stored["rule_version"] == live
    return ok, (f"stored {stored['rule_version']}, source {live}"
                + ("" if ok else "  <- a source file changed, rebuild"))


@check("96 groups skipped, 63 kept, 159 in the table")
def _c4(conn):
    v = load_verdicts()
    skip = sum(1 for x in v.values() if x == "skip")
    keep = sum(1 for x in v.values() if x == "keep")
    ok = (skip, keep, len(v)) == (96, 63, 159)
    return ok, f"{skip} skip, {keep} keep, {len(v)} total"


def _reason_count(conn, prefix):
    return conn.execute(
        """SELECT COUNT(*) c FROM prefilter f JOIN postings p ON p.id = f.id
           WHERE p.removed = 0 AND f.reason LIKE ?""", (prefix + "%",)
    ).fetchone()["c"]


@check("the headline rescue still fires, at a sane rate")
def _c5(conn):
    """Rate, not a count. Zero means the terms have stopped matching Swedish job ad
    wording, which is silent. A large share means a term was widened until it matches
    everything."""
    rescued = _reason_count(conn, "rescue:")
    vetoed = _reason_count(conn, "veto:")
    skipped_by_group = _reason_count(conn, "group_skip:")
    pool = skipped_by_group + rescued + vetoed      # everything the group list skipped
    rate = rescued / pool if pool else 0
    lo, hi = RESCUE_RATE_BAND
    return lo <= rate <= hi, (
        f"{rescued} of {pool} group-skipped ads rescued, {rate * 100:.2f} %, "
        f"band {lo * 100:.1f} to {hi * 100:.1f} %")


@check("the veto still blocks a minority of what the rescue picks up")
def _c6(conn):
    """The veto is meant to catch selling and teaching contexts the rescue terms sweep
    in. Blocking nothing means it has stopped matching; blocking nearly everything
    means it has swallowed the rescue it exists to narrow."""
    rescued = _reason_count(conn, "rescue:")
    vetoed = _reason_count(conn, "veto:")
    hits = rescued + vetoed
    share = vetoed / hits if hits else 0
    lo, hi = VETO_SHARE_BAND
    return lo <= share <= hi, (
        f"{vetoed} of {hits} rescue hits blocked, {share * 100:.1f} %, "
        f"band {lo * 100:.0f} to {hi * 100:.0f} %")


@check("the share of open ads reaching the model is stable")
def _c7(conn):
    """The headline number, as a rate. It is what the monthly bill is proportional to,
    so a jump in either direction is worth a look: up means the group list stopped
    applying, down means it started eating a field it should not."""
    c = _open_counts(conn)
    keep, skip = c.get("keep", 0), c.get("skip", 0)
    total = keep + skip
    rate = keep / total if total else 0
    lo, hi = KEEP_RATE_BAND
    return lo <= rate <= hi, (
        f"{keep} of {total} open ads, {rate * 100:.1f} %, "
        f"band {lo * 100:.0f} to {hi * 100:.0f} %")


@check("nothing kept out of a skipped group without a rescue")
def _c8(conn):
    """The failure this catches is a rescue term widened by accident."""
    n = conn.execute(
        """SELECT COUNT(*) c FROM prefilter
           WHERE verdict = 'keep' AND reason NOT LIKE 'group_keep:%'
             AND reason NOT LIKE 'group_unknown:%' AND reason NOT LIKE 'rescue:%'"""
    ).fetchone()["c"]
    return n == 0, f"{n} kept for an unrecognised reason"


@check("a twin is an ad from another site, pointing at a Platsbanken ad")
def _c10(conn):
    rows = conn.execute(
        """SELECT f.verdict, p.source, q.source twin_source FROM prefilter f
           JOIN postings p ON p.id = f.id
           LEFT JOIN postings q ON q.id = SUBSTR(f.reason, 6)
           WHERE f.reason LIKE 'twin:%'""").fetchall()
    bad = sum(1 for r in rows if r["verdict"] != "skip" or r["source"] != "links"
              or r["twin_source"] != "platsbanken")
    return bad == 0, f"{len(rows)} twins, {bad} not a skipped Links ad with a Platsbanken twin"


@check("an unrecognised group is kept, never skipped")
def _c9(conn):
    n = conn.execute(
        "SELECT COUNT(*) c FROM prefilter WHERE reason LIKE 'group_unknown:%' AND verdict = 'skip'"
    ).fetchone()["c"]
    unknown = conn.execute(
        "SELECT COUNT(*) c FROM prefilter WHERE reason LIKE 'group_unknown:%'"
    ).fetchone()["c"]
    return n == 0, f"{unknown} ads in unrecognised groups, {n} of them wrongly skipped"


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


def unknown(conn):
    """Groups the verdict table does not carry. These are kept and cost money, so
    they are the thing to look at after a stream brings in a new taxonomy value."""
    rows = conn.execute(
        """SELECT REPLACE(f.reason, 'group_unknown:', '') grp, COUNT(*) c
           FROM prefilter f JOIN postings p ON p.id = f.id
           WHERE p.removed = 0 AND f.reason LIKE 'group_unknown:%'
           GROUP BY grp ORDER BY c DESC"""
    ).fetchall()
    if not rows:
        print("no unrecognised occupation groups")
        return 0
    print(f"{len(rows)} unrecognised group(s), all kept, all reaching the model:\n")
    for r in rows:
        print(f"  {r['c']:>5}  {r['grp']}")
    print("\nAdd them to the table in context/occupation_groups.md, then rebuild.")
    return len(rows)


def status(conn):
    c = _open_counts(conn)
    keep, skip = c.get("keep", 0), c.get("skip", 0)
    total = keep + skip
    version = conn.execute("SELECT rule_version FROM prefilter LIMIT 1").fetchone()
    print(f"rule_version      {version['rule_version'] if version else 'none, run rebuild'}")
    print(f"open postings     {total}")
    print(f"  reach model     {keep}  ({keep / total * 100:.1f} %)" if total else "")
    print(f"  skipped         {skip}")
    print("\nby reason, open ads only:")
    rows = conn.execute(
        """SELECT CASE
                    WHEN f.reason LIKE 'group_keep:%'    THEN 'kept by group'
                    WHEN f.reason LIKE 'group_skip:%'    THEN 'skipped by group'
                    WHEN f.reason LIKE 'group_unknown:%' THEN 'kept, group unrecognised'
                    WHEN f.reason LIKE 'rescue:%'        THEN 'rescued by headline'
                    WHEN f.reason LIKE 'veto:%'          THEN 'rescued then vetoed'
                    WHEN f.reason LIKE 'twin:%'          THEN 'another site, on Platsbanken too'
                  END bucket, COUNT(*) c
           FROM prefilter f JOIN postings p ON p.id = f.id
           WHERE p.removed = 0 GROUP BY bucket ORDER BY c DESC"""
    ).fetchall()
    for r in rows:
        print(f"  {r['c']:>6}  {r['bucket']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["rebuild", "verify", "status", "unknown"])
    args = ap.parse_args()

    conn = store.connect()
    if args.mode == "rebuild":
        rebuild(conn)
        print()
        sys.exit(1 if verify(conn) else 0)
    elif args.mode == "verify":
        sys.exit(1 if verify(conn) else 0)
    elif args.mode == "unknown":
        unknown(conn)
    else:
        status(conn)


if __name__ == "__main__":
    main()
