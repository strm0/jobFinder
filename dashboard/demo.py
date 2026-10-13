"""The page an invented ad opens. Only in the public copy.

In the real system a card's link goes to the ad on Platsbanken or on the job site it came
from. The sample ads here are invented and have no page anywhere, so their `webpage_url` is
`/demo/ad/<id>` and this draws the ad text the store holds. Nothing else uses it.
"""

import html
import json
import re

from . import queries

PREFIX = "/demo/ad/"
JOB_ID = re.compile(r"^[A-Za-z0-9-]{1,40}$")

PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{headline}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 17px/1.55 Georgia, serif; max-width: 42rem; margin: 0 auto; padding: 2rem 1rem 4rem; }}
  .note {{ font: 13px/1.4 system-ui, sans-serif; padding: .6rem .8rem; border: 1px solid; border-radius: 6px; opacity: .8; }}
  h1 {{ font-size: 1.6rem; line-height: 1.2; margin: 1.5rem 0 .3rem; }}
  .meta {{ font: 14px/1.5 system-ui, sans-serif; opacity: .75; margin: 0 0 1.5rem; }}
  .text {{ white-space: pre-wrap; }}
</style>
</head>
<body>
<p class="note">Demo data. This ad and its employer are invented. In the real system this
link opens the ad on the job site it came from.</p>
<h1>{headline}</h1>
<p class="meta">{meta}</p>
<div class="text">{text}</div>
</body>
</html>
"""


def ad_page(conn, job_id):
    if not JOB_ID.match(job_id):
        raise queries.NotFound("That is not a job id.")
    row = conn.execute("SELECT payload FROM ads WHERE id = ? AND is_tombstone = 0",
                       (job_id,)).fetchone()
    if row is None:
        raise queries.NotFound("There is no such ad in the store.")
    ad = json.loads(row["payload"])
    place = (ad.get("workplace_address") or {}).get("municipality")
    meta = ", ".join(x for x in ((ad.get("employer") or {}).get("name"), place,
                                 (ad.get("employment_type") or {}).get("label")) if x)
    return PAGE.format(
        lang=html.escape(ad.get("identified_language") or "sv"),
        headline=html.escape(ad.get("headline") or "Untitled ad"),
        meta=html.escape(meta),
        text=html.escape((ad.get("description") or {}).get("text") or ""),
    ).encode("utf-8")
