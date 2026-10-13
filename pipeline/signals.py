"""The regex half of the soft signals. No API, no cost, free to re-run.

    python -m pipeline.signals rebuild   # drop and rebuild `signals`
    python -m pipeline.signals verify    # check the transform held
    python -m pipeline.signals status    # hit counts per signal

`soft_signals` in 02_search_config.yaml splits cleanly in two. Most entries are term
lists, and matching those locally is free, deterministic and rebuildable, so sending
them to the model would be paying per ad for something grep does. The rest are
judgements about what the role actually is, and those go to the model in pass 1:
whether selling is the core of the job rather than mentioned, what the stated salary
means, whether the process is a slow multi-stage one.

This module does the first half only, and reports the second half rather than
pretending to cover it.

`signals` is derived, like `postings` and `prefilter`. It gets its own
table rather than a column on `classifications`, so a rebuild here can never touch
what Haiku was paid to produce.

The config's own warning applies and is why this is not the whole matcher: an
enumerated term list loses recall silently as wording changes. These weights sort,
they never filter, and the model's `want` rating is what carries the judgement the
term lists cannot reach.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

from . import store

ROOT = Path(__file__).resolve().parent.parent
CONFIG_YAML = ROOT / "context" / "02_search_config.yaml"

# Entries with no term list. Listed by name so they are visibly delegated rather than
# quietly dropped. Anything here that the model does not cover either is a gap.
RULE_ONLY = {
    "salary_stated_above_floor": "model reads the salary text",
    "below_floor_salary": "model reads the salary text",
    "slow_process": "deadline half computed here, process half goes to the model",
    "cs_degree_hard_requirement": "model judges requirement against merit",
}

# Why cs_degree_hard_requirement is delegated rather than matched. The config's
# phrases, "civilingenjörsexamen krävs", "examen inom datateknik krävs" and "computer
# science degree required", are dead: no Swedish ad writes the requirement that
# literally, so they match nothing. Loosening them to the bare words "civilingenjör"
# or "computer science" would fire on hundreds of ads, and most of those say
# "civilingenjör eller motsvarande", which is a merit and not a bar. Requirement
# against merit is a judgement, so it goes to the model as `cs_degree_required`.
# The terms stay in the config as a record of intent; nothing reads them.

# slow_process, the half that is a date rather than a judgement.
SLOW_PROCESS_WEEKS = 6

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id           TEXT NOT NULL,
    signal_id    TEXT NOT NULL,
    polarity     TEXT NOT NULL,        -- positive | negative
    weight       INTEGER NOT NULL,
    hits         TEXT,                 -- JSON array of the terms that matched
    rule_version TEXT NOT NULL,
    PRIMARY KEY (id, signal_id)
);

CREATE INDEX IF NOT EXISTS signals_signal ON signals(signal_id);
"""


def _term_pattern(term):
    """One config term as a regex.

    Terms are plain phrases, not patterns, so they are escaped: `5+ years` and
    `0-2 years` both appear in the config and would otherwise be read as quantifiers.
    Word boundaries are applied only where the term actually starts or ends on a word
    character, so `0-2 years` still anchors correctly.
    """
    body = re.escape(term.strip())
    lead = r"\b" if term[:1].isalnum() else ""
    tail = r"\b" if term[-1:].isalnum() else ""
    return f"{lead}{body}{tail}"


def load_signals(path=CONFIG_YAML):
    """Compile every soft signal that carries a term list. Returns a list of
    (signal_id, polarity, weight, terms, compiled)."""
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = []
    for polarity in ("positive", "negative"):
        for entry in cfg["soft_signals"][polarity]:
            terms = []
            for key, value in entry.items():
                if key == "terms" or key.startswith("terms_"):
                    terms.extend(value)
            if entry["id"] in RULE_ONLY:
                continue  # delegated, even if the config still carries dead terms
            if not terms:
                if entry["id"] not in RULE_ONLY:
                    raise SystemExit(
                        f"soft signal {entry['id']} has no terms and is not in "
                        f"RULE_ONLY. Add it there and say who covers it, or give it "
                        f"terms. Silently dropping a signal is the failure this stops."
                    )
                continue
            pattern = "|".join(_term_pattern(t) for t in terms)
            out.append((entry["id"], polarity, int(entry["weight"]), terms,
                        re.compile(pattern, re.I)))
    return out


def rule_version(compiled):
    import hashlib
    h = hashlib.sha256()
    for sid, polarity, weight, terms, _ in compiled:
        h.update(f"{sid}|{polarity}|{weight}|{'|'.join(terms)}\n".encode())
    h.update(f"slow_process_weeks={SLOW_PROCESS_WEEKS}\n".encode())
    return f"sg1-{h.hexdigest()[:8]}"


def rebuild(conn):
    compiled = load_signals()
    version = rule_version(compiled)

    conn.execute("DROP TABLE IF EXISTS signals")
    conn.executescript(SCHEMA)

    cutoff = (datetime.now(timezone.utc) + timedelta(weeks=SLOW_PROCESS_WEEKS)).date().isoformat()
    slow = dict(conn.execute(
        """SELECT id, weight FROM (
             SELECT id, ? weight FROM postings
             WHERE application_deadline IS NOT NULL AND application_deadline > ?
           )""",
        (-5, cutoff),
    ).fetchall())

    src = conn.execute(
        """SELECT p.id, p.headline, a.payload
           FROM postings p JOIN ads a ON a.id = p.id"""
    )

    batch, seen = [], 0
    for r in src:
        ad = json.loads(r["payload"])
        text = f"{r['headline'] or ''}\n{(ad.get('description') or {}).get('text') or ''}"
        for sid, polarity, weight, _terms, rx in compiled:
            found = rx.findall(text)
            if not found:
                continue
            hits = sorted({m.lower() for m in found})
            batch.append((r["id"], sid, polarity, weight, json.dumps(hits, ensure_ascii=False),
                          version))
        if r["id"] in slow:
            batch.append((r["id"], "slow_process", "negative", -5,
                          json.dumps([f"deadline more than {SLOW_PROCESS_WEEKS} weeks out"]),
                          version))
        seen += 1
        if len(batch) >= 5000:
            _flush(conn, batch); batch = []
    _flush(conn, batch)
    conn.commit()

    n = conn.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"]
    print(f"signals rebuilt: {n} hits across {seen} postings, rule_version {version}")
    print(f"  {len(compiled)} term-matched signals, "
          f"{len(RULE_ONLY)} delegated:")
    for sid, who in RULE_ONLY.items():
        print(f"    {sid}: {who}")
    return n


def _flush(conn, batch):
    if batch:
        conn.executemany(
            """INSERT OR REPLACE INTO signals
               (id, signal_id, polarity, weight, hits, rule_version)
               VALUES (?, ?, ?, ?, ?, ?)""",
            batch,
        )


CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn)); return fn
    return deco


@check("every config signal is either matched here or delegated")
def _c1(conn):
    cfg = yaml.safe_load(CONFIG_YAML.read_text(encoding="utf-8"))
    all_ids = {e["id"] for p in ("positive", "negative") for e in cfg["soft_signals"][p]}
    matched = {sid for sid, *_ in load_signals()}
    missing = all_ids - matched - set(RULE_ONLY)
    return not missing, f"{len(all_ids)} signals, {len(matched)} matched, " \
                        f"{len(RULE_ONLY)} delegated, {len(missing)} unaccounted for"


@check("the compiled rules still match the config")
def _c2(conn):
    stored = conn.execute("SELECT rule_version FROM signals LIMIT 1").fetchone()
    if stored is None:
        return False, "table is empty, run rebuild"
    live = rule_version(load_signals())
    ok = stored["rule_version"] == live
    return ok, (f"stored {stored['rule_version']}, config {live}"
                + ("" if ok else "  <- the config changed, rebuild"))


@check("every signal fired at least once")
def _c3(conn):
    """A signal that never fires is a term list that does not match Swedish job ad
    wording. It is not an error, but it means that signal is doing nothing."""
    fired = {r["signal_id"] for r in conn.execute("SELECT DISTINCT signal_id FROM signals")}
    expected = {sid for sid, *_ in load_signals()}
    dead = sorted(expected - fired)
    return not dead, (f"{len(expected & fired)} of {len(expected)} term signals fired"
                      + (f", never fired: {', '.join(dead)}" if dead else ""))


@check("weights carry the sign of their polarity")
def _c4(conn):
    bad = conn.execute(
        """SELECT COUNT(*) c FROM signals
           WHERE (polarity = 'positive' AND weight < 0)
              OR (polarity = 'negative' AND weight > 0)"""
    ).fetchone()["c"]
    return bad == 0, f"{bad} rows with a weight fighting its polarity"


@check("no posting matched every single signal")
def _c5(conn):
    """A pattern that matches everything is the classic escaping bug. If one ad hits
    nearly every signal, a term compiled to something like `.` or an empty branch."""
    total = len({sid for sid, *_ in load_signals()})
    worst = conn.execute(
        "SELECT COUNT(*) c FROM signals GROUP BY id ORDER BY c DESC LIMIT 1"
    ).fetchone()
    n = worst["c"] if worst else 0
    return n < total, f"busiest ad hits {n} of {total} signals"


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
    version = conn.execute("SELECT rule_version FROM signals LIMIT 1").fetchone()
    print(f"rule_version  {version['rule_version'] if version else 'none, run rebuild'}\n")
    print(f"{'signal':<32} {'wt':>4} {'open ads':>9} {'of kept':>8}")
    rows = conn.execute(
        """SELECT s.signal_id, s.polarity, s.weight,
                  COUNT(*) n,
                  SUM(CASE WHEN f.verdict = 'keep' THEN 1 ELSE 0 END) kept
           FROM signals s
           JOIN postings p ON p.id = s.id AND p.removed = 0
           LEFT JOIN prefilter f ON f.id = s.id
           GROUP BY s.signal_id ORDER BY s.polarity DESC, n DESC"""
    ).fetchall()
    for r in rows:
        print(f"{r['signal_id']:<32} {r['weight']:>4} {r['n']:>9} {r['kept'] or 0:>8}")
    print("\ndelegated to the model in pass 1:")
    for sid, who in RULE_ONLY.items():
        print(f"  {sid:<30} {who}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["rebuild", "verify", "status"])
    args = ap.parse_args()

    conn = store.connect()
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
