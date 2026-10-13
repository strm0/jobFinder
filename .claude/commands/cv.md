---
description: Generate a tailored CV from a job brief and the block bank
---

Generate a CV for the application in the current working directory.

This is the public demo version of the command. It works on the invented candidate in `blocks/`.

Paths below are relative to the application folder, `applications/<company> - <job title> - <ad
number>/`, which is where this runs.

## Steps

1. Read `brief.md` in the current directory. It contains the posting text, the matched lanes, the score and the model's reasons. If `brief.md` does not exist, stop and say so.
2. Read `../../blocks/SCHEMA.md`. It defines what a block is and what you may and may not do. Follow it exactly.
3. Read `../../blocks/INDEX.md` whole.
4. Read only the block source files that contain blocks you intend to use. Do not read all of them. Always read `../../blocks/identity.md`, which holds the header, the contact line and the profile anchors.
5. Write the profile paragraph fresh against this posting. The anchors in `identity.md` show the register. Do not paste one.
6. Write `cv.md` in the current directory, in the format below.
7. Run `python3 ../../render/render.py cv.md` to produce `cv.pdf`. It needs Typst installed.
8. Write `notes.md` in the current directory: which blocks you used, which strong-looking blocks you left out and why, anything in the posting the bank could not answer, and any `interview_exposure` note attached to a block you used.
9. Say in two or three lines: lanes matched, sections included, and the single weakest thing about this application. Do not summarise the CV back at the candidate, who is about to read the PDF.

## Selection rules

- The "Suggested blocks" table in `brief.md` is usually empty, because the suggestion pass is not built. Choose from `INDEX.md`. If the table has rows, treat them as candidates, not instructions.
- Lead with the lane the posting actually is, not the lane with the most blocks.
- One page unless the posting is academic. Cut rather than shrink.
- A source appears once. Never both as an Experience entry and as a Selected projects entry, and never two role summaries for the same source.
- Order Experience by reverse chronology, not by relevance. Relevance is expressed through which bullets are chosen and how long they are.
- Where a block has a `long` and a `short` variant, use `short` for bullets on a one page CV and `long` only where the block is carrying the application.
- Respect every "Not claimed here" section in the files you read. Those are not suggestions.
- If the posting asks for Danish or for Nordic languages, move languages into the profile paragraph.
- Add no link the bank does not hold.
- Write the CV in the language of the posting. The blocks are in English. Translate the sentences and leave numbers, technologies and names exactly as they are.

## cv.md format

```
---
name: <header-name>
title: <written for this posting, see header-title in identity.md>
contact: <header-contact, exactly as written>
---

## Profile

<one paragraph, three to four lines, written fresh>

## Experience

### <Role> | <Organisation, City>
*<Mmm YYYY to Mmm YYYY, only if a block gives the dates>*
<optional summary line>
- <bullet>
- <bullet>

## Selected projects

### <Name>
<one or two lines>

## Education

### <Degree>
*<year>*

## Skills

Methods: <terms separated by commas>

Tools: <terms separated by commas>

## Languages

<line>
```

Sections may be reordered or omitted. For academic and L5 applications add a `## Publications` section and move `## Selected projects` below Education, as SCHEMA.md section 7 says.

The renderer reads this shape and nothing else: level 2 headings are sections, level 3 headings are entries with the role before the pipe and the organisation after it, an italic line directly under a level 3 heading is the date range, lines starting with `- ` are bullets. A section with no level 3 heading renders as plain paragraphs.

## Revision turns

On later turns the candidate will have edited `cv.md` directly or left comments in it, including HTML comments. Read the whole file, treat the edits as final and the comments as instructions, rewrite, re-render. Comments are stripped by the renderer, so they never reach the PDF.

If a revision shows that a block itself is wrong and not just wrongly selected, edit the block in `../../blocks/` so the fix reaches later applications, then run `python3 tools/build_index.py` from the repository root. Say that you did it.

If the candidate tells you a fact the bank does not hold, it becomes a block first and goes into the CV second. Say which file it belongs in and offer to write it.

## Hard rules

- No em dashes anywhere in the output.
- Never assert a technology, number, date or authorship that appears in no block.
- Never write "passionate", "thrive", "wear many hats", "hit the ground running", "results-driven", "proven track record".
- If the posting requires something the candidate does not have, do not paper over it. Note it in `notes.md`.
- Nothing is sent by this command. The candidate reads the PDF and decides.
