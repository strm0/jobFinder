"""Pass 1 classification. The only module here that spends money.

    python -m pipeline.classify sample --n 20 --out ads.md   # free
    python -m pipeline.classify estimate --n 400            # free
    python -m pipeline.classify run --ids A,B,C --yes       # spends
    python -m pipeline.classify batch --n 400 --yes         # spends
    python -m pipeline.classify collect --batch-id ...      # free
    python -m pipeline.classify run --pending --yes         # spends, nightly
    python -m pipeline.classify status                      # free

`--pending` is the nightly selection and the one to use on a schedule: kept, open, and
never classified at any version. An ad is never paid for twice, and there is no cap on
how many new ads it takes. An ad made stale by an edit to the brief or the prompt is NOT
new and is skipped unless `--include-stale` is passed, because after an edit that is
every paid ad, and the whole store is paid for again. Re-buying them is a funded
decision, never a side effect of a scheduled run.

Nothing here spends without `--yes`, and every spending mode prints an estimate and
the current spend first. That is deliberate: the key is not restricted to Haiku and
is not restricted to a model at all, so the only real ceiling is the prepaid balance
and discipline.

**The key is read from the ANTHROPIC_API_KEY environment variable and from nowhere else.**
Never from a file, and this module never writes it anywhere. Set it for the one command
that needs it, `ANTHROPIC_API_KEY=... python -m pipeline.classify run ...`, rather than
exporting it, so no other process in the shell ever sees it. The version this copy was made
from reads the key from the macOS Keychain inside the process instead.

Two paths. **Use `run` for everything except a full pass over the store.**

    run     the Messages API directly. Immediate, full price.
    batch   the Batch API at half price, but it is a queue, not a fast lane.

The saving is not worth the wait at test sizes: at 400 ads the difference is about 70
cents against hours in the queue, and a two-ad batch can still take many minutes,
because almost all of it is waiting to reach the front. Batch earns its keep
only on a full pass over the store, where half the bill is real money and nobody is
sitting watching. `batch` warns below BATCH_WORTH_IT ads.

Both write the same rows. `classifier_version` is a hash of the prompt, the candidate
brief, the model id and the output schema, so any edit to any of them produces a new
version and a later reclassify can target exactly what is stale.

The system prompt is identical for every ad and is marked for caching, which is the
single largest cost lever at the volume of a full pass: the brief and the lane
descriptions are a larger share of each request than the ad is. Whether the cache
actually holds across a batch window is measured, not assumed: every row stores its own
token counts and `status` reports the hit rate.
"""

import argparse
import hashlib
import json
import random
import re
import os
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import store

ROOT = Path(__file__).resolve().parent.parent
CONFIG_YAML = ROOT / "context" / "02_search_config.yaml"
BRIEF_MD = ROOT / "context" / "candidate_brief.md"
PROMPT_MD = ROOT / "pipeline" / "prompts" / "classify_v1.md"

MODEL = "claude-haiku-4-5"     # alias, never a dated snapshot.
# A ceiling, not a target, so a high value costs nothing on an ordinary ad, and a low one
# cuts a long response off mid-string. Not part of classifier_version, and correctly so:
# a truncated response is never stored, so no row on disk was shaped by the limit.
# `_parse` names a truncation instead of calling it unparseable.
MAX_TOKENS = 1500
TEMPERATURE = 0                # see request_params. Not a preference, a bug fix.
PASS_NO = 1

# USD per million tokens. Haiku 4.5 list is 1.00 in, 5.00 out; the Batch API is half.
RATE_IN, RATE_OUT = 1.00, 5.00
BATCH_DISCOUNT = 0.5
CACHE_READ_MULTIPLIER = 0.1
CACHE_WRITE_MULTIPLIER = 1.25

# Chars per token on Swedish ad text. Used only for the free estimate.
CHARS_PER_TOKEN = 3.5

# Output tokens per ad, for the free estimate. The measured average over a full pass of
# the store, not a guess: the quote is what a run prints before it spends, and a lower
# figure makes every quote come in low. A number read before spending that under-reports
# is the wrong kind of wrong.
OUTPUT_TOKENS_PER_AD = 190

KEY_VARIABLE = "ANTHROPIC_API_KEY"

# Below this, the Batch API's 50 percent discount is not worth its queue time. See the
# module docstring. At 400 ads it saves 70 cents and costs hours of waiting.
BATCH_WORTH_IT = 1000

# There is no ceiling on new ads. A cap on the number of pending ads cannot tell the two
# large cases apart: a few unrun days of real arrivals, which should be classified, and the
# whole keep set gone stale after an edit to the brief, which should not. So every new ad
# is classified however many there are, and the expensive case is caught by what it is
# rather than by its size. An ad with a row at an older version is stale, not new, and
# `fetch_pending` leaves it out unless asked.


# --------------------------------------------------------------------------
# Prompt assembly
# --------------------------------------------------------------------------

def _strip_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S).lstrip()


def load_config():
    return yaml.safe_load(CONFIG_YAML.read_text(encoding="utf-8"))


def lane_ids(cfg):
    return [lane["id"] for lane in cfg["lanes"]]


def hard_filter_ids(cfg):
    return [hf["id"] for hf in cfg["hard_filters"]]


def output_schema(cfg):
    """The JSON the model must return. Lane and hard filter ids come from the config,
    so the prompt cannot drift into naming a lane that no longer exists."""
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "track": {"type": "string", "enum": ["industry", "phd", "neither"]},
            "lanes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "enum": lane_ids(cfg)},
                        # Ranges are expressed as enums, not as minimum/maximum.
                        # Structured outputs reject min/max on an integer type:
                        # "For 'integer' type, properties maximum, minimum are not
                        # supported".
                        "fit": {"type": "integer", "enum": [1, 2, 3]},
                    },
                    "required": ["id", "fit"],
                    "additionalProperties": False,
                },
            },
            "want": {"type": "integer", "enum": list(range(11))},
            "want_why": {"type": "string"},
            "reach": {"type": "integer", "enum": list(range(11))},
            "reach_why": {"type": "string"},
            "hard_filter_hits": {
                "type": "array",
                "items": {"type": "string", "enum": hard_filter_ids(cfg)},
            },
            "min_years_experience": {"type": ["integer", "null"]},
            "seniority_language": {"type": "boolean"},
            "sales_is_the_whole_job": {"type": "boolean"},
            "cs_degree_required": {"type": "boolean"},
        },
        "required": [
            "summary", "track", "lanes", "want", "want_why", "reach", "reach_why",
            "hard_filter_hits", "min_years_experience", "seniority_language",
            "sales_is_the_whole_job", "cs_degree_required",
        ],
        "additionalProperties": False,
    }


def system_prompt(cfg):
    """The cached prefix. Identical on every request, so it must not carry anything
    per-ad, per-run or time-dependent. A timestamp in here would silently cost the
    whole cache."""
    prompt = _strip_comments(PROMPT_MD.read_text(encoding="utf-8"))
    brief = _strip_comments(BRIEF_MD.read_text(encoding="utf-8"))

    missing = [lid for lid in lane_ids(cfg) if lid not in prompt]
    if missing:
        raise SystemExit(
            f"the prompt does not describe these lanes from the config: "
            f"{', '.join(missing)}. Either add them or remove them from the config; "
            f"a lane the model is never told about can never be matched."
        )
    return prompt.replace("{{CANDIDATE_BRIEF}}", brief)


def classifier_version(cfg):
    h = hashlib.sha256()
    h.update(system_prompt(cfg).encode())
    h.update(MODEL.encode())
    # Temperature changes the output, so it changes the version. Left out of the hash,
    # a temperature change would produce rows indistinguishable from the old ones.
    h.update(f"temp={TEMPERATURE}".encode())
    h.update(json.dumps(output_schema(cfg), sort_keys=True).encode())
    return f"c1-{h.hexdigest()[:8]}"


def render_ad(row, payload):
    """The per-ad half of the request. Deliberately compact: everything here is paid
    for on every single ad."""
    ad = json.loads(payload)
    text = (ad.get("description") or {}).get("text") or ""
    bits = [
        f"HEADLINE: {row['headline']}",
        f"EMPLOYER: {row['employer_name'] or 'not stated'}",
        f"LOCATION: {', '.join(x for x in (row['municipality'], row['region'], row['country']) if x) or 'not stated'}",
        f"EMPLOYMENT: {row['employment_type'] or 'not stated'}"
        + (f", {row['duration']}" if row["duration"] else "")
        + (f", {row['working_hours_type']}" if row["working_hours_type"] else ""),
        f"OCCUPATION (assigned upstream, often wrong): {row['occupation_label'] or 'none'}",
        f"DEADLINE: {row['application_deadline'] or 'not stated'}",
    ]
    if row["salary_description"]:
        bits.append(f"SALARY: {row['salary_description']}")
    if row["must_have_languages"]:
        bits.append(f"REQUIRED LANGUAGES: {row['must_have_languages']}")
    bits.append(f"\nDESCRIPTION:\n{text}")
    return "\n".join(bits)


AD_COLUMNS = """p.id, p.headline, p.employer_name, p.municipality, p.region, p.country,
    p.employment_type, p.duration, p.working_hours_type, p.occupation_label,
    p.application_deadline, p.salary_description, p.must_have_languages,
    p.occupation_field_label, p.occupation_group_label"""


def billed_cost(uncached_in, cache_reads, cache_writes, out, batched):
    """What a set of stored rows actually cost, from their own token counts.

    One copy, because a second copy of this arithmetic is a second place to get it wrong.
    **`input_tokens` from the API is the UNCACHED input only.** Cache reads and cache
    writes are reported separately and are NOT a subset of it, so they are added here,
    never subtracted. Subtracting them produces a negative cost.
    """
    discount = BATCH_DISCOUNT if batched else 1.0
    return (uncached_in / 1e6 * RATE_IN
            + cache_reads / 1e6 * RATE_IN * CACHE_READ_MULTIPLIER
            + cache_writes / 1e6 * RATE_IN * CACHE_WRITE_MULTIPLIER
            + out / 1e6 * RATE_OUT) * discount


def links_gate(cfg=None):
    """SQL that leaves out the ads from other job sites while `links.classify` in the config
    is false, and nothing once it is true. Those ads are fetched and read for free every
    night, and nothing is spent on them until a sample of them has been read and the
    backlog approved by setting that flag. Reads `ads.source`, which every store has, so
    it holds even before `postings` is rebuilt with a source of its own."""
    cfg = cfg or load_config()
    if (cfg.get("links") or {}).get("classify"):
        return ""
    return ("\n              AND NOT EXISTS (SELECT 1 FROM ads x WHERE x.id = p.id "
            "AND x.source = 'links')")


def held_at_gate(conn, version, cfg=None):
    """Kept open ads from other job sites, never classified, waiting for the gate. Zero
    once the gate is open, because they are then ordinary pending ads."""
    if not links_gate(cfg):
        return 0
    return conn.execute(
        """SELECT COUNT(*) c FROM postings p
           JOIN prefilter f ON f.id = p.id
           JOIN ads a ON a.id = p.id AND a.source = 'links'
           WHERE p.removed = 0 AND f.verdict = 'keep'
             AND NOT EXISTS (SELECT 1 FROM classifications c
                             WHERE c.id = p.id AND c.classifier_version = ?)""",
        (version,),
    ).fetchone()["c"]


def fetch_pending(conn, version, limit=None, include_stale=False):
    """The nightly selection. Kept, open, with no row at `version`, and by default never
    classified at any version either. Ads from other job sites only once the gate in the
    config is open, see `links_gate`.

    The predicate is written against the CURRENT classifier_version, so an ad classified
    this morning under the current sources is done and is never paid for twice. What that
    leaves splits in two, and the halves are treated differently.
    A new ad has no row at all and is always selected, however many there are. A stale ad
    has a row at an older version, which only happens after the brief or the prompt was
    edited. It is left out unless `include_stale`, because re-buying the
    paid rows is a deliberate, funded act and never something a schedule does.

    Ordered oldest publication first so a truncated run leaves the newest ads for the
    next one rather than a random hole in the middle.
    """
    rows = conn.execute(
        f"""SELECT {AD_COLUMNS}, a.payload FROM postings p
            JOIN ads a ON a.id = p.id
            JOIN prefilter f ON f.id = p.id
            WHERE p.removed = 0 AND f.verdict = 'keep'
              AND NOT EXISTS (SELECT 1 FROM classifications c
                              WHERE c.id = p.id AND c.classifier_version = ?)
              AND (? OR NOT EXISTS (SELECT 1 FROM classifications o WHERE o.id = p.id)){links_gate()}
            ORDER BY p.publication_date""",
        (version, int(include_stale)),
    ).fetchall()
    return rows[:limit] if limit else rows


def pending_count(conn, version):
    """What `fetch_pending` would select with stale ads included. Ads held at the links
    gate are not pending; `held_at_gate` counts them."""
    return conn.execute(
        f"""SELECT COUNT(*) c FROM postings p
           JOIN prefilter f ON f.id = p.id
           WHERE p.removed = 0 AND f.verdict = 'keep'
             AND NOT EXISTS (SELECT 1 FROM classifications c
                             WHERE c.id = p.id AND c.classifier_version = ?){links_gate()}""",
        (version,),
    ).fetchone()["c"]


def stale_count(conn, version):
    """Kept open ads classified at an older version but not at `version`. Zero unless
    the brief or the prompt changed after they were bought. See fetch_pending."""
    return conn.execute(
        f"""SELECT COUNT(*) c FROM postings p
           JOIN prefilter f ON f.id = p.id
           WHERE p.removed = 0 AND f.verdict = 'keep'
             AND NOT EXISTS (SELECT 1 FROM classifications c
                             WHERE c.id = p.id AND c.classifier_version = ?)
             AND EXISTS (SELECT 1 FROM classifications o WHERE o.id = p.id){links_gate()}""",
        (version,),
    ).fetchone()["c"]


def fetch_ads(conn, ids=None, n=None, seed=20260910, include_skipped=0):
    """A random sample, for development and for reviewing ratings before a larger run.

    NOT the nightly selection: this does not consult `classifications` and will happily
    hand back ads already paid for. That is correct for a sample, where the point is a
    representative slice, and wrong for a scheduled run. Use `fetch_pending` for that.
    """
    if ids:
        q = ",".join("?" * len(ids))
        rows = conn.execute(
            f"""SELECT {AD_COLUMNS}, a.payload FROM postings p
                JOIN ads a ON a.id = p.id WHERE p.id IN ({q})""", ids
        ).fetchall()
        found = {r["id"] for r in rows}
        for missing in set(ids) - found:
            print(f"  ! no such posting: {missing}", file=sys.stderr)
        return rows

    rng = random.Random(seed)

    def pick(verdict, count):
        rows = conn.execute(
            f"""SELECT {AD_COLUMNS}, a.payload FROM postings p
                JOIN ads a ON a.id = p.id
                JOIN prefilter f ON f.id = p.id
                WHERE p.removed = 0 AND f.verdict = ?""", (verdict,)
        ).fetchall()
        return rng.sample(rows, min(count, len(rows)))

    return pick("keep", n) + (pick("skip", include_skipped) if include_skipped else [])


# --------------------------------------------------------------------------
# Cost, before anything is spent
# --------------------------------------------------------------------------

def estimate(conn, cfg, rows, batched, cached):
    sys_tokens = len(system_prompt(cfg)) / CHARS_PER_TOKEN
    ad_tokens = sum(len(render_ad(r, r["payload"])) for r in rows) / CHARS_PER_TOKEN
    out_tokens = len(rows) * OUTPUT_TOKENS_PER_AD

    d = BATCH_DISCOUNT if batched else 1.0
    if cached:
        prefix = (sys_tokens * CACHE_WRITE_MULTIPLIER
                  + sys_tokens * CACHE_READ_MULTIPLIER * (len(rows) - 1))
    else:
        prefix = sys_tokens * len(rows)

    cost_in = (prefix + ad_tokens) / 1e6 * RATE_IN * d
    cost_out = out_tokens / 1e6 * RATE_OUT * d
    return {
        "ads": len(rows),
        "system_tokens_each": int(sys_tokens),
        "ad_tokens_total": int(ad_tokens),
        "prefix_tokens_billed": int(prefix),
        "output_tokens": int(out_tokens),
        "usd": cost_in + cost_out,
    }


def print_estimate(e, label):
    print(f"{label}")
    print(f"  ads                      {e['ads']}")
    print(f"  system prompt, each      {e['system_tokens_each']:,} tokens")
    print(f"  system prompt, billed    {e['prefix_tokens_billed']:,} tokens")
    print(f"  ad text                  {e['ad_tokens_total']:,} tokens")
    print(f"  output                   {e['output_tokens']:,} tokens")
    print(f"  ESTIMATED COST           {e['usd']:.4f} USD")


# --------------------------------------------------------------------------
# The API
# --------------------------------------------------------------------------

def api_key():
    """Read the key from the environment into this process only.

    Never written to a file and never printed. With no key there is nothing to spend, so
    this says where the demo data is instead of failing somewhere inside the SDK.
    """
    key = os.environ.get(KEY_VARIABLE, "").strip()
    if not key:
        raise SystemExit(
            f"{KEY_VARIABLE} is not set, so nothing was sent and nothing was spent.\n\n"
            f"This copy does not need a key. The ratings for its sample ads were generated\n"
            f"in advance and are loaded by `python -m pipeline.seed`. The free stages and the\n"
            f"dashboard run on those.\n\n"
            f"To rate ads yourself, set the key for this one command only:\n"
            f"  {KEY_VARIABLE}=... python -m pipeline.classify run --pending --yes\n"
            f"`python -m pipeline.classify estimate --pending` prints the cost first, free."
        )
    return key


def client():
    try:
        import anthropic
    except ImportError:
        raise SystemExit("pip install anthropic first "
                         "(pip install -r requirements.txt)")
    return anthropic.Anthropic(api_key=api_key())


def request_params(cfg, row, for_batch=False):
    """The request body for one ad.

    `for_batch` exists for one reason. `temperature` has to reach the wire, and the two
    paths need it packaged differently: `messages.create` takes SDK-level options like
    `extra_body` and merges them into the body, while the Batch API puts this dict onto
    the wire verbatim, so an `extra_body` key arrives as a literal field and the request
    is rejected with "extra_body: Extra inputs are not permitted". Every request in the
    batch fails validation that way at once. Nothing is billed for it, but it is the
    reason to smoke-test the batch path on two ads before sending anything larger.
    """
    params = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        # Classification, so no sampling. At the default temperature the same ad with
        # an unchanged prompt can come back want 9, want 9, then want 1, with a want_why
        # on the third run that argues from the ad asking for ten years, which is a
        # reach fact. Variance leaks reach into want.
        # Reproducibility also matters here beyond quality: `classifier_version` claims
        # a row is reproducible from the stored prompt, and at temperature 1 it is not.
        #
        # Sent through extra_body because the Python SDK dropped `temperature` from the
        # named parameters of messages.create in 1.x, the sampling controls having been
        # removed on the 4.6-and-later models. Haiku 4.5 still accepts it on the wire.
        **({"temperature": TEMPERATURE} if for_batch
           else {"extra_body": {"temperature": TEMPERATURE}}),
        "system": [{
            "type": "text",
            "text": system_prompt(cfg),
            "cache_control": {"type": "ephemeral"},
        }],
        "messages": [{"role": "user", "content": render_ad(row, row["payload"])}],
        "output_config": {"format": {"type": "json_schema", "schema": output_schema(cfg)}},
    }
    return params


def store_result(conn, ad_id, version, model, parsed, raw, usage, via_batch=False):
    conn.execute(
        """INSERT OR REPLACE INTO classifications
           (id, classifier_version, pass_no, classified_at, model, summary, track,
            matched_lanes, want, want_why, reach, reach_why, hard_filter_hits,
            min_years_experience, seniority_language, sales_is_the_whole_job,
            cs_degree_required, judgement, input_tokens, output_tokens,
            cache_read_tokens, cache_write_tokens, via_batch)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            ad_id, version, PASS_NO, datetime.now(timezone.utc).isoformat(timespec="seconds"),
            model,
            parsed.get("summary"), parsed.get("track"),
            json.dumps(parsed.get("lanes", []), ensure_ascii=False),
            parsed.get("want"), parsed.get("want_why"),
            parsed.get("reach"), parsed.get("reach_why"),
            json.dumps(parsed.get("hard_filter_hits", []), ensure_ascii=False),
            parsed.get("min_years_experience"),
            int(bool(parsed.get("seniority_language"))),
            int(bool(parsed.get("sales_is_the_whole_job"))),
            int(bool(parsed.get("cs_degree_required"))),
            raw,
            usage.get("input_tokens"), usage.get("output_tokens"),
            usage.get("cache_read_input_tokens"),
            usage.get("cache_creation_input_tokens"),
            int(via_batch),
        ),
    )


class Truncated(Exception):
    """The response hit MAX_TOKENS. Kept apart from a malformed response because the fix
    is different: the model's output was fine and the caller's limit cut it off."""


def _parse(message):
    if message.stop_reason == "max_tokens":
        raise Truncated(f"response cut off at max_tokens={MAX_TOKENS}, not malformed. "
                        f"Raise MAX_TOKENS; it is not part of classifier_version.")
    raw = next((b.text for b in message.content if b.type == "text"), "")
    return json.loads(raw), raw


def run_direct(conn, cfg, rows):
    """Messages API, one ad at a time. For the small runs while the prompt is moving."""
    import anthropic
    cl = client()
    version = classifier_version(cfg)
    ok = failed = 0
    for i, row in enumerate(rows, 1):
        try:
            msg = cl.messages.create(**request_params(cfg, row))
            parsed, raw = _parse(msg)
        except anthropic.APIStatusError as e:
            print(f"  [{i}/{len(rows)}] {row['id']} API {e.status_code}: {e.message}",
                  file=sys.stderr)
            failed += 1
            continue
        except Truncated as e:
            print(f"  [{i}/{len(rows)}] {row['id']} {e}", file=sys.stderr)
            failed += 1
            continue
        except (json.JSONDecodeError, StopIteration) as e:
            print(f"  [{i}/{len(rows)}] {row['id']} unparseable response: {e}",
                  file=sys.stderr)
            failed += 1
            continue
        store_result(conn, row["id"], version, msg.model, parsed, raw, {
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
            "cache_read_input_tokens": getattr(msg.usage, "cache_read_input_tokens", None),
            "cache_creation_input_tokens": getattr(msg.usage, "cache_creation_input_tokens", None),
        })
        conn.commit()
        ok += 1
        lanes = ", ".join(f"{l['id'].split('_')[0]}:{l['fit']}" for l in parsed["lanes"]) or "none"
        print(f"  [{i}/{len(rows)}] want {parsed['want']:>2}  reach {parsed['reach']:>2}  "
              f"{lanes:<14} {parsed['summary'][:56]}")
    print(f"\n{ok} classified, {failed} failed, classifier_version {version}")
    return failed


def run_batch(conn, cfg, rows):
    """Batch API. Half price, up to 24 hours. Returns the batch id to collect with."""
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    cl = client()
    batch = cl.messages.batches.create(requests=[
        Request(custom_id=row["id"],
                params=MessageCreateParamsNonStreaming(**request_params(cfg, row, for_batch=True)))
        for row in rows
    ])
    conn.execute(
        """CREATE TABLE IF NOT EXISTS classify_batches (
               batch_id TEXT PRIMARY KEY, classifier_version TEXT, n INTEGER,
               submitted_utc TEXT, collected_utc TEXT)"""
    )
    conn.execute(
        "INSERT OR REPLACE INTO classify_batches (batch_id, classifier_version, n, submitted_utc) "
        "VALUES (?, ?, ?, ?)",
        (batch.id, classifier_version(cfg), len(rows),
         datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
    conn.commit()
    print(f"batch submitted: {batch.id}, {len(rows)} ads, status {batch.processing_status}")
    print(f"\ncollect it with:\n"
          f"  python -m pipeline.classify collect --batch-id {batch.id}")
    return batch.id


def collect(conn, cfg, batch_id):
    cl = client()
    batch = cl.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        c = batch.request_counts
        print(f"batch {batch_id} is {batch.processing_status}: "
              f"{c.processing} processing, {c.succeeded} succeeded, {c.errored} errored")
        print("not ready. Most batches finish within an hour, the maximum is 24.")
        return 1

    version = classifier_version(cfg)
    ok = failed = 0
    for result in cl.messages.batches.results(batch_id):
        # Results arrive in any order. Keyed by custom_id, never by position.
        if result.result.type != "succeeded":
            print(f"  ! {result.custom_id}: {result.result.type}", file=sys.stderr)
            failed += 1
            continue
        msg = result.result.message
        try:
            parsed, raw = _parse(msg)
        except Truncated as e:
            print(f"  ! {result.custom_id}: {e}", file=sys.stderr)
            failed += 1
            continue
        except (json.JSONDecodeError, StopIteration) as e:
            print(f"  ! {result.custom_id}: unparseable, {e}", file=sys.stderr)
            failed += 1
            continue
        store_result(conn, result.custom_id, version, msg.model, parsed, raw, {
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
            "cache_read_input_tokens": getattr(msg.usage, "cache_read_input_tokens", None),
            "cache_creation_input_tokens": getattr(msg.usage, "cache_creation_input_tokens", None),
        }, via_batch=True)
        ok += 1
    conn.execute("UPDATE classify_batches SET collected_utc = ? WHERE batch_id = ?",
                 (datetime.now(timezone.utc).isoformat(timespec="seconds"), batch_id))
    conn.commit()
    print(f"{ok} stored, {failed} failed, classifier_version {version}")
    return 1 if failed else 0


# --------------------------------------------------------------------------
# Free modes
# --------------------------------------------------------------------------

def sample(conn, n, out, include_skipped, ids=None):
    """Dump ads to a markdown file for reading. No API call.

    This is what prompt development works from: the prompt gets developed by reading
    real ads and arguing about what the right answer is.

    `ids` hand-picks. The sample should span the lanes including ones that
    should be rejected, and a random draw does not reliably span anything: twenty
    random ads can be fifteen Data/IT ads and no L5, L6 or L7 at all.
    """
    rows = fetch_ads(conn, ids=ids, n=n, include_skipped=include_skipped)
    parts = [f"# {len(rows)} ads for prompt development\n",
             f"Drawn {datetime.now(timezone.utc).date().isoformat()}. "
             f"{n} kept by the pre-filter, {include_skipped} skipped by it.\n"]
    for i, r in enumerate(rows, 1):
        verdict = conn.execute(
            "SELECT verdict, reason FROM prefilter WHERE id = ?", (r["id"],)
        ).fetchone()
        hits = conn.execute(
            "SELECT signal_id, weight FROM signals WHERE id = ? ORDER BY weight DESC",
            (r["id"],)
        ).fetchall()
        parts.append(
            f"\n---\n\n## {i}. {r['headline']}\n\n"
            f"- id `{r['id']}`\n"
            f"- employer: {r['employer_name'] or 'not stated'}\n"
            f"- field / group: {r['occupation_field_label']} / {r['occupation_group_label']}\n"
            f"- prefilter: `{verdict['verdict']}` via `{verdict['reason']}`\n"
            f"- regex signals: "
            + (", ".join(f"{h['signal_id']} ({h['weight']:+d})" for h in hits) or "none")
            + f"\n\n```\n{render_ad(r, r['payload'])}\n```\n"
        )
    Path(out).write_text("".join(parts), encoding="utf-8")
    print(f"wrote {len(rows)} ads to {out}")


def status(conn, cfg):
    version = classifier_version(cfg)
    print(f"classifier_version, current sources   {version}")
    rows = conn.execute(
        """SELECT classifier_version v, model, COUNT(*) n,
                  SUM(input_tokens) tin, SUM(output_tokens) tout,
                  SUM(COALESCE(cache_read_tokens, 0)) tcache,
                  SUM(COALESCE(cache_write_tokens, 0)) twrite,
                  COALESCE(via_batch, 0) batched,
                  MIN(classified_at) first, MAX(classified_at) last
           FROM classifications GROUP BY classifier_version, model, COALESCE(via_batch, 0)
           ORDER BY last DESC"""
    ).fetchall()
    if not rows:
        print("\nnothing classified yet.")
        return
    print()
    grand = 0.0
    for r in rows:
        stale = "" if r["v"] == version else "   <- stale, sources have changed since"
        via = "batch" if r["batched"] else "direct"
        print(f"{r['v']}  {r['model']}  {r['n']} ads via {via}{stale}")
        print(f"    {r['first']} to {r['last']}")
        # `input_tokens` is the UNCACHED input only. Cache reads and cache writes are
        # reported separately and are NOT a subset of it, so they are added, never
        # subtracted. Getting this backwards produces a negative cost.
        tin, tout = r["tin"] or 0, r["tout"] or 0
        tread, twrite = r["tcache"] or 0, r["twrite"] or 0
        total_in = tin + tread + twrite
        # Batch rows were billed at half. Applying list rates to them would report
        # close to twice what they cost.
        cost = billed_cost(tin, tread, twrite, tout, r["batched"])
        grand += cost
        print(f"    input {total_in:,} tokens = {tin:,} uncached "
              f"+ {tread:,} cache reads + {twrite:,} cache writes")
        if total_in:
            print(f"    cache hit rate {tread / total_in * 100:.1f} % of input tokens")
        print(f"    output {tout:,} tokens")
        print(f"    cost {cost:.4f} USD at {via} rates")
    print(f"\n  TOTAL SPENT, all versions   {grand:.4f} USD")

    print("\nwant / reach distribution, this version:")
    dist = conn.execute(
        """SELECT want, COUNT(*) n FROM classifications
           WHERE classifier_version = ? GROUP BY want ORDER BY want DESC""", (version,)
    ).fetchall()
    for d in dist:
        print(f"  want {d['want']:>2}  {'#' * min(d['n'], 60)} {d['n']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["sample", "estimate", "run", "batch", "collect", "status"])
    ap.add_argument("--n", type=int, default=20, help="how many kept ads")
    ap.add_argument("--skipped", type=int, default=0,
                    help="also draw this many ads the pre-filter skipped")
    ap.add_argument("--ids", help="comma separated posting ids, instead of a sample")
    ap.add_argument("--pending", action="store_true",
                    help="the nightly selection: every kept open ad never classified, "
                         "however many. Never re-pays for an ad.")
    ap.add_argument("--include-stale", action="store_true",
                    help="with --pending, also re-buy ads classified under an older brief "
                         "or prompt. After an edit that is every paid ad.")
    ap.add_argument("--max", type=int, default=None,
                    help="with --pending, classify at most this many. No limit by default.")
    ap.add_argument("--out", default="sample.md", help="sample: where to write")
    ap.add_argument("--batch-id", help="collect: which batch")
    ap.add_argument("--yes", action="store_true", help="required before spending")
    args = ap.parse_args()

    conn = store.connect()
    cfg = load_config()

    if args.mode == "status":
        status(conn, cfg)
        return
    if args.mode == "sample":
        sample(conn, args.n, args.out, args.skipped,
               ids=[x.strip() for x in args.ids.split(",")] if args.ids else None)
        return
    if args.mode == "collect":
        if not args.batch_id:
            raise SystemExit("collect needs --batch-id")
        sys.exit(collect(conn, cfg, args.batch_id))

    if args.pending:
        if args.ids or args.skipped:
            raise SystemExit("--pending selects for itself; do not combine it with "
                             "--ids or --skipped.")
        version = classifier_version(cfg)
        stale = stale_count(conn, version)
        if stale and not args.include_stale:
            # Reported, never spent. See fetch_pending.
            print(f"NOTE: {stale} kept open ads were classified under an older brief or "
                  f"prompt and are stale at {version}.\n"
                  f"      They are skipped. Re-buying them is a funded decision: "
                  f"--include-stale.\n")
        rows = fetch_pending(conn, version, limit=args.max, include_stale=args.include_stale)
        if not rows:
            print(f"nothing new to classify at {version}.")
            return
    else:
        ids = [x.strip() for x in args.ids.split(",")] if args.ids else None
        rows = fetch_ads(conn, ids=ids, n=args.n, include_skipped=args.skipped)
    if not rows:
        raise SystemExit("no ads selected")

    batched = args.mode == "batch"
    e = estimate(conn, cfg, rows, batched=batched, cached=True)
    print_estimate(e, f"{args.mode}, {'batch' if batched else 'direct'} rates, "
                      f"assuming the system prompt caches")
    worst = estimate(conn, cfg, rows, batched=batched, cached=False)
    print(f"  if the cache never hits    {worst['usd']:.4f} USD")
    print(f"  classifier_version         {classifier_version(cfg)}")

    if args.mode == "estimate":
        # `estimate` is not a run, so it has no rate of its own. Quote both, or the
        # number read here is off by exactly a factor of two from what batch charges.
        print("\n                            cached      uncached")
        for label, b in (("direct  ", False), ("batch   ", True)):
            lo = estimate(conn, cfg, rows, batched=b, cached=True)["usd"]
            hi = estimate(conn, cfg, rows, batched=b, cached=False)["usd"]
            print(f"  {label}                  {lo:8.4f}      {hi:8.4f}  USD")
        return
    if not args.yes:
        print("\nthis spends money. Re-run with --yes if that is what you want.")
        sys.exit(1)

    print()
    if batched:
        if len(rows) < BATCH_WORTH_IT:
            saving = estimate(conn, cfg, rows, batched=False, cached=True)["usd"] - e["usd"]
            print(f"NOTE: {len(rows)} ads is below the {BATCH_WORTH_IT} where batch is worth")
            print(f"      its queue time. Batch saves {saving:.2f} USD here and can take")
            print(f"      hours. `run` instead gives the same rows in about a minute.\n")
        run_batch(conn, cfg, rows)
    else:
        sys.exit(1 if run_direct(conn, cfg, rows) else 0)


if __name__ == "__main__":
    main()
