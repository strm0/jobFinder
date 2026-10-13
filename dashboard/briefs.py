"""The brief the Generate buttons write. No API call, no model, nothing spent.

Fills the format of `applications/_TEMPLATE/brief.md`, which `/cv` and `/letter` read, from
what the nightly run already recorded: the ad text JobTech published, and the classifier's
and scorer's output for it. For an ad from another job site the text is the one the nightly
run read from that site's page, so the full ad is already in the store and nothing is fetched
at click time.

The folder is named for the company, the job title and the ad number, as in
`applications/Cylvenor Consulting - Data Engineer - Stockholm - 90101808/`, so an application can be found in
Finder later. The number comes last and is what finds the folder again, so the rest of the
name can be changed by hand. An ad from another job site has a 32 character id, so its folder
ends in the first 10, `queries.folder_key`.

Never overwrites. If a folder for the job exists under any name it says so and leaves
everything in it alone, because what is there may have been edited by hand.
"""

import json
import re
import shlex
import unicodedata
from datetime import date

from . import queries

NO_BLOCKS = ("The matcher's block suggestion pass is not built yet, so nothing is suggested "
             "here. Choose from `blocks/INDEX.md`.")

COMPANY_LENGTH = 40
TITLE_LENGTH = 50
# A trailing legal form, repeated so "Cylvenor Consulting Aktiebolag (publ)" loses both.
LEGAL_FORM = re.compile(r"(?:[\s,]+(?:AB|Aktiebolag|\(publ\.?\)))+\s*$", re.IGNORECASE)
# What reads as a break inside a title or a name: a slash, a pipe, a colon, or a dash with
# spaces round it. Each becomes a comma, so " - " stays free to divide the folder name.
BREAK = re.compile(r"\s*[/|:\\–—]\s*|\s+-\s+")
KEPT = set(" -,.&()'+#%_@")


def folder_name(job_id, employer, title):
    return (f"{name_part(employer, COMPANY_LENGTH, legal=True) or 'Employer not stated'} - "
            f"{name_part(title, TITLE_LENGTH) or 'Untitled'} - {queries.folder_key(job_id)}")


def name_part(text, length, legal=False):
    """One part of a folder name: safe in Finder and inside the copied `cd` command, and cut
    on a word. Letters such as å, ä and ö are kept; emoji, `!`, `?`, quotes and `$` are not."""
    text = unicodedata.normalize("NFC", text or "").replace("‑", "-")
    text = "".join(" " if c.isspace() else c for c in text)
    if legal:
        text = LEGAL_FORM.sub("", text)
        if text.upper() == text and len(text.split()) > 1:  # an all-caps name of several words, not a one-word acronym
            text = text.title()
    text = BREAK.sub(", ", text)
    text = "".join(c for c in text if c.isalnum() or c in KEPT)
    text = re.sub(r"\s*,[\s,]*", ", ", re.sub(r"\s+", " ", text)).strip(" ,.-")
    if len(text) > length:
        cut = text[:length + 1].rsplit(" ", 1)[0] if " " in text[:length + 1] else text[:length]
        text = cut.rstrip(" ,.-&(")
    return text


def located(folder):
    return {"path": f"applications/{folder.name}/",
            "command": f"cd {shlex.quote(str(folder))} && claude"}


def write(conn, job_id):
    existing = queries.application_folders().get(queries.folder_key(job_id))
    if existing is not None:
        return {**located(existing), "status": "exists"}

    current = queries.version(conn)
    row = conn.execute(
        """SELECT p.id, p.headline, p.employer_name, p.municipality, p.region, p.country,
                  p.employment_type, p.duration, p.working_hours_type, p.salary_type,
                  p.salary_description, p.webpage_url, p.publication_date,
                  p.application_deadline, p.identified_language, p.source, p.source_site,
                  a.payload,
                  c.track, c.matched_lanes, c.want, c.reach, c.want_why, c.reach_why,
                  c.summary, c.hard_filter_hits, s.recommend, s.dropped_hits
           FROM postings p
           JOIN ads a ON a.id = p.id
           LEFT JOIN classifications c ON c.id = p.id AND c.classifier_version = ?
           LEFT JOIN scores s ON s.id = p.id
           WHERE p.id = ?""", (current, job_id)).fetchone()
    if row is None:
        raise queries.NotFound(f"There is no job {job_id} in the store.")
    signals = conn.execute(
        """SELECT signal_id, weight, hits FROM signals WHERE id = ? AND weight != 0
           ORDER BY ABS(weight) DESC, signal_id""", (job_id,)).fetchall()
    names = {lane["id"]: lane for lane in queries.lanes(queries.config())}
    text = render(row, signals, names, date.today())

    folder = queries.APPLICATIONS / folder_name(row["id"], row["employer_name"], row["headline"])
    try:
        folder.mkdir()
    except FileExistsError:      # appeared between the check and now: still never overwrite
        return {**located(folder), "status": "exists"}
    (folder / "brief.md").write_text(text, encoding="utf-8")
    return {**located(folder), "status": "created",
            "path": f"applications/{folder.name}/brief.md"}


def joined(*parts, sep=", "):
    return sep.join(p for p in parts if p)


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(row, signals, names, today):
    ad = json.loads(row["payload"])
    text = ((ad.get("description") or {}).get("text") or "").strip()
    title = row["headline"] or "Untitled"
    employer = row["employer_name"] or "Employer not stated"
    deadline = (row["application_deadline"] or "")[:10]
    url = row["webpage_url"] or f"/demo/ad/{row['id']}"
    elsewhere = row["source"] == "links"
    site = row["source_site"] or "another job site"
    if elsewhere:
        written = (f"from the store, ad {row['id']}, whose text the nightly run read from "
                   f"{site}")
        source_line = f"{site}, through JobAd Links, ad {row['id']}"
        deadline_line = (f"{deadline}, as {site} gives it." if deadline
                         else f"not stated by JobAd Links. Check the posting on {site}.")
    else:
        written = f"from the JobTech store, ad {row['id']}"
        source_line = f"JobTech Platsbanken, ad {row['id']}"
        deadline_line = (f"{deadline}. JobTech gives the day the ad comes down here, so "
                         "check the posting for a deadline of its own." if deadline
                         else "not stated")

    matched = sorted(json.loads(row["matched_lanes"] or "[]"), key=lambda l: -(l.get("fit") or 0))
    lanes_line = ", ".join(
        f"{lane['id'].split('_')[0]} {names.get(lane['id'], {}).get('name', lane['id'])}"
        f" (fit {lane.get('fit')} of 3)" for lane in matched) or "none"

    if row["recommend"] is None:
        score_line = "not scored at the current classifier version."
    else:
        score_line = (f"{row['recommend']:.1f}, from want {row['want']} and reach "
                      f"{row['reach']}. Every dashboard view sorts on this number.")

    hits = json.loads(row["hard_filter_hits"] or "[]")
    dropped = json.loads(row["dropped_hits"] or "[]")
    applied = [h for h in hits if h not in dropped]
    filters_line = (f"{', '.join(applied)}. Not eligible." if applied
                    else "none. Eligible.")

    out = [
        f"# Brief: {title}, {employer}",
        "",
        f"Written by the dashboard on {today.day} {today:%B %Y} {written}, with no API call. "
        "The matcher output is what the nightly classifier and scorer recorded for this ad.",
        "",
        "---",
        "",
        "## Posting",
        "",
        f"**Employer:** {employer}",
        f"**Title:** {title}",
        f"**Location:** {joined(row['municipality'], row['region'], row['country']) or 'not stated'}",
        f"**Employment:** {joined(row['employment_type'], row['duration'], row['working_hours_type']) or 'not stated'}",
        f"**Salary:** {joined(row['salary_type'], row['salary_description'], sep=': ') or 'not stated'}",
        f"**Source:** {source_line}",
        f"**URL:** {url}",
        f"**Published:** {(row['publication_date'] or '')[:10] or 'not stated'}",
        f"**Deadline:** {deadline_line}",
        f"**Language of the posting:** {row['identified_language'] or ('not identified' if elsewhere else 'not identified by JobTech')}",
        "",
        "### Full text",
        "",
        text or "The store holds no description text for this ad. Read it at the URL above.",
        "",
        "---",
        "",
        "## Matcher output",
        "",
        f"**Track:** {row['track'] or 'not classified at the current version'}",
        "",
        f"**Matched lanes:** {lanes_line}",
        "",
        f"**Score:** {score_line}",
        "",
    ]
    if row["summary"]:
        out += [f"**Summary:** {row['summary']}", ""]
    if row["want"] is not None:
        out += [f"**Want {row['want']}:** {row['want_why'] or 'no reason recorded'}", ""]
    if row["reach"] is not None:
        out += [f"**Reach {row['reach']}:** {row['reach_why'] or 'no reason recorded'}", ""]

    if signals:
        out += ["**Signals hit:**", "", "| signal | weight | matched |", "|---|---|---|"]
        for s in signals:
            terms = ", ".join(json.loads(s["hits"] or "[]"))
            out.append(f"| `{s['signal_id']}` | {s['weight']:+d} | {cell(terms)} |")
        out.append("")
    else:
        out += ["**Signals hit:** none matched in the ad text.", ""]

    out += [f"**Hard filter hits:** {filters_line}", ""]
    if dropped:
        out += [f"**Not applied:** {', '.join(dropped)}. The model reported it, but the ad "
                "names no real bar.", ""]

    out += [
        "---",
        "",
        "## Suggested blocks",
        "",
        NO_BLOCKS,
        "",
        "| block id | reason |",
        "|---|---|",
        "| | |",
        "",
        "## Considered and dropped",
        "",
        "| block id | reason |",
        "|---|---|",
        "| | |",
        "",
        "---",
        "",
        "## Notes",
        "",
        "<anything you know about this employer that is not in the posting>",
        "",
    ]
    return "\n".join(out)
