"""JobTech Dev API client. Sweden only.

All endpoints are public and unauthenticated. No key, no account, no cost.
Measured behaviour is recorded in context/jobtech_fields.md.

Pagination caps: limit maxes at 100 and offset at 2000, so a single query reaches at
most 2,100 ads. Five of the seven occupation fields searched hold more than that, which
is why backfill slices by publication date.
"""

import time

import requests

SEARCH = "https://jobsearch.api.jobtechdev.se/search"
STREAM = "https://jobstream.api.jobtechdev.se/stream"
TAXONOMY = "https://taxonomy.api.jobtechdev.se/v1/taxonomy/main/concepts"

MAX_LIMIT = 100
MAX_OFFSET = 2000
REACHABLE = MAX_LIMIT + MAX_OFFSET

# The seven of twenty-one occupation fields that map to the candidate's lanes.
# Concept IDs as the taxonomy API returns them.
FIELDS = {
    "apaJ_2ja_LuF": "Data/IT",
    "X82t_awd_Qyc": "Administration, ekonomi, juridik",
    "RPTn_bxG_ExZ": "Försäljning, inköp, marknadsföring",
    "MVqp_eS8_kDZ": "Pedagogik",
    "6Hq3_tKo_V57": "Yrken med teknisk inriktning",
    "kJeN_wmw_9wX": "Naturvetenskap",
    "9puE_nYg_crq": "Kultur, media, design",
}

PAUSE = 0.15  # be a polite client of a free public API


class JobTechError(RuntimeError):
    pass


# A scheduled run can start the moment the laptop wakes, before the network is back, so a
# connection failure is retried after a pause instead of ending the run at its first
# request. An HTTP error is not retried, because the API answered.
#
# A connection that drops halfway through the body is retried too. requests raises that as
# ChunkedEncodingError, which is not a ConnectionError, so it has to be named. It happens
# at the stream when the laptop sleeps mid-download and JobTech has reset the connection
# by the next wake.
RETRY_WAITS = (30, 60, 120)
RETRIED = (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError)


def _get(url, params, timeout=60):
    for wait in RETRY_WAITS + (None,):
        try:
            r = requests.get(url, params=params, timeout=timeout,
                             headers={"accept": "application/json"})
            break
        except RETRIED:
            if wait is None:
                raise
            time.sleep(wait)
    if r.status_code != 200:
        raise JobTechError(f"{url} returned {r.status_code}: {r.text[:200]}")
    return r.json()


def occupation_fields():
    """All 21 occupation-field concepts, live from the taxonomy API."""
    data = _get(TAXONOMY, {"type": "occupation-field"})
    return {c["taxonomy/id"]: c["taxonomy/preferred-label"] for c in data}


def count(field_id, published_after=None, published_before=None):
    params = {"occupation-field": field_id, "limit": 0}
    if published_after:
        params["published-after"] = published_after
    if published_before:
        params["published-before"] = published_before
    time.sleep(PAUSE)
    return _get(SEARCH, params)["total"]["value"]


def search_page(field_id, offset, limit=MAX_LIMIT,
                published_after=None, published_before=None):
    params = {"occupation-field": field_id, "limit": limit, "offset": offset}
    if published_after:
        params["published-after"] = published_after
    if published_before:
        params["published-before"] = published_before
    time.sleep(PAUSE)
    return _get(SEARCH, params)["hits"]


def stream(since_iso):
    """Every ad created, updated or removed since `since_iso` (UTC, no timezone suffix).

    Returns a flat list across all occupation fields; filter after. Removals are
    more than half of what comes back and are sparse tombstones, not full ads.
    """
    return _get(STREAM, {"date": since_iso}, timeout=300)
