# Block bank: schema and generation contract

This file defines what a block is, what fields it carries, how `/cv` and `/letter` use the
blocks, and what they are not allowed to do. Read it before touching any file in `blocks/`.

The format and the rules are the ones the real system uses. The blocks in this folder are
not: they describe Maren Kjeldsen, an invented candidate, and every fact in them comes from
`context/candidate_brief.md`.

---

## 1. Why a block bank

A CV written by a model from a free description of a person drifts. A number gets rounded, a
tool the person has touched once becomes a skill, a project gains a method it never used. Each
drift is small and each one is checkable in an interview.

The bank is the answer to that. Every claim the candidate is willing to sign is written once,
as a short block, with the evidence behind it and the question it invites. A CV is assembled
from those blocks and from nothing else. What the bank does not hold cannot appear.

## 2. The generation loop

1. The candidate clicks "Write brief" on a job in the dashboard. The dashboard writes
   `brief.md` into a new folder in `applications/`, named for the company, the job title and
   the ad number. The brief holds the posting text verbatim, the matched lanes, the score, the
   two ratings with the model's reasons, the signals hit and the hard filter hits. No API call
   is made at click time: everything in the brief was stored by the nightly run.

   The brief also has a "Suggested blocks" table. It is empty. A pass that suggests blocks for
   each well-scored ad was designed and is not built, so `/cv` chooses from `INDEX.md` itself.

2. The candidate opens Claude Code in that folder and runs `/cv`. The first turn produces
   `cv.md` and renders `cv.pdf`. There is no selection conversation. The draft is the first
   thing the candidate sees.

   `/cv` is a slash command defined once at `.claude/commands/cv.md`. It reads `brief.md`,
   this file and `INDEX.md`, loads only the source files the blocks it wants live in, writes
   `cv.md` and runs the render script.

3. The candidate reads the PDF, edits `cv.md` directly where the fix is obvious, and writes
   comments into it where it is not. Comments can be vague, for example "this bullet is doing
   nothing".

4. On the next turn the model reads `cv.md`, treats the edits as final and the comments as
   instructions, rewrites and re-renders.

5. If a fix shows that a block is wrong, and not just wrongly chosen, the model edits the
   block in `blocks/` so the fix reaches every later application, then re-runs
   `tools/build_index.py`. This is the only way the bank improves.

**Render is deterministic, revision is not.** `cv.md` to `cv.pdf` is a template step with no
model in it, so a hand edit can be re-rendered at once with `/rerendercv`. Deciding what
`cv.md` should say is model work every time.

**Blocks must be sendable as written.** There is no guaranteed adaptation pass. A block that
only works after rewriting is a broken block.

**A person reads every draft.** Nothing is sent by the system. The `interview_exposure` field
below only makes sense because a human signs and sends each application.

---

## 3. Block types

| type | What it is | Length |
|---|---|---|
| `role_summary` | The one or two lines under a role header in Experience. Varies by lane. | 1 to 2 lines |
| `bullet` | A single achievement bullet under a role or project. | 1 to 2 lines |
| `project` | A Selected projects entry: what it is, and what is hard about it. | 2 to 3 lines |
| `skill_term` | A line of terms for the Skills section, or a fixed line such as the contact details or a degree. | phrase |
| `profile_anchor` | Not text to insert. See section 6. | paragraph |

---

## 4. The format of a block

A block is a level 3 heading, a fenced `yaml` block directly under it, then the body.

````
### pipeline-nightly
```yaml
type: bullet
source: energy_advice
lanes: [L1, L2]
competency: [data_pipelines, python, sql]
register: [technical, commercial]
strength: strong
numbers: [3]
evidence: "context/candidate_brief.md, What she can do, Data pipelines, end to end"
interview_exposure: "How large is the data. Small, on one server. Say so."
```
**short:** One or two lines, ready to paste into a CV.

**long:** The fuller variant, for when this block is carrying the application.
````

`tools/build_index.py` reads this with regular expressions, not a YAML parser, so the shape
is strict:

- The heading is `### ` followed by the id and nothing else. The id may contain letters,
  digits, hyphens and underscores.
- The line after the heading is exactly three backticks and `yaml`. No blank line between.
- Each key sits on one line. Lists are written inline in square brackets.
- The text after `**short:**` on the same line is what goes into the index, cut at 160
  characters.
- A block ends at the next level 3 or level 2 heading.

A block that breaks the shape is skipped silently, so check the block count the tool prints
after every edit.

### Fields

- **id.** Not a field. It is the heading, which is where the tool reads it from. It must stay
  stable, because briefs, notes and sent applications refer to it. It is what makes "which
  version of this claim went to that employer" answerable six weeks later.
- **`type`.** One of the five types above. A CV has several granularities and a bullet cannot
  fill a projects entry.
- **`source`.** Groups blocks under one CV entry. The generator assembles by role, not by
  lane, so blocks need to group. Blocks with the same source may live in different files.
- **`lanes`.** What a posting's matched lanes are joined on. Written as `L1` to `L7`, the
  prefixes of the lane ids in `context/02_search_config.yaml`, plus `phd` for the doctoral
  track. These are the same tags the brief prints under "Matched lanes".
- **`competency`.** A small controlled vocabulary. Posting requirements are matched against
  these words, not against prose. The index lists the whole vocabulary. Keep it small.
- **`register`.** Any of `commercial`, `technical`, `academic`. The registers a block carries
  without rewriting. It is a capability tag, not a set of written variants: a bullet about a
  usability study reads fine to a research group and to a product team, a bullet about dbt
  tests does not belong in an academic CV.
- **`strength`.** `strong`, `adequate` or `thin`. Thin blocks stay in the bank, flagged.
  Sometimes a thin block is the only evidence a lane has, and using it knowingly is different
  from using it blind. The index counts evidence per lane by strength, which shows at a glance
  which lanes the candidate can actually support.
- **`numbers`.** Every figure that appears in the text. Figures are what gets misremembered
  and paraphrased wrong. Listing them makes one audit possible.
- **`evidence`.** Where the claim comes from. In this demo every pointer is to a section of
  `context/candidate_brief.md`. It answers "can I defend this" in one lookup.
- **`interview_exposure`.** The question a competent interviewer asks after reading the block,
  and the honest answer. Used for interview preparation and by `/letter`. Never rendered into
  the CV.

**Required, and where.** `competency` is required on `role_summary`, `bullet` and `project`,
the three types that are matched against a posting. An empty list on one of them makes the
block unreachable. It may be empty on `skill_term`, where the terms are their own keywords.

`profile_anchor` carries `type`, `lanes` and `register` and nothing else. It is a calibration
example and not a claim, so the other fields have nothing to point at. It has no `**short:**`
line either, so its claim column in the index is empty.

**Deliberately not fields.** Usage history and last-used date: that is application state and
belongs with the applications, and a bank that tracks state rots. Language variants: the bank
is in English and translation happens when the CV is drafted.

---

## 5. Not claimed here

Every block file ends with a level 2 section called `## Not claimed here`. It lists what the
blocks in that file do not say and must not be made to say.

It exists because the pressure in CV writing runs one way. A posting asks for Spark. The
candidate has a nightly pipeline in Python and SQL. A model asked to tailor the CV will find a
phrasing that leans toward the posting, such as "large-scale data processing", and each such
step looks harmless. A rule that says "use only what the blocks say" does not stop it, because
the phrasing is an inference from a block and not a quotation of anything false.

Writing the limit down next to the claim does stop it. "No Spark, no Kafka, no cloud data
platform in production. Small data on one server" leaves nothing to infer.

Rules for the section:

- It is binding. `/cv` and `/letter` read it in every file they open and treat each line as a
  prohibition, not a suggestion.
- Write what was true and close to the claim. Things nobody would assume do not need a line.
- Give the reason where it helps, and the honest wording to use in its place if there is one.
- When a posting requires something on the list, the gap goes into `notes.md` for the
  candidate to see. It is never papered over in the CV.

The section is a level 2 heading and holds no blocks, so the index tool ignores it. It is read
from the source file, which is one reason the source file must be opened before a block from
it is used.

---

## 6. The profile paragraph is generated, not selected

The opening paragraph is the only part of the CV written fresh against each posting. It is
where the reader forms an impression, and its whole job is to name the competencies this
posting asks for. Choosing one of a few pre-written paragraphs wastes the most valuable
sentence on the page.

`profile_anchor` blocks are therefore not insertable text. They show the register, the
sentence rhythm and the claim density the candidate will sign. The generator writes a new
paragraph against the posting with them as examples.

Constraints on the generated paragraph:

- It never asserts a technology, number, date or authorship that appears in no block.
  Everything else is free.
- No em dashes.
- None of "passionate", "thrive", "wear many hats", "hit the ground running",
  "results-driven", "proven track record". The same list is in `.claude/commands/cv.md`. Keep
  the two in sync.
- Three to four lines. Shorter reads better.

---

## 7. How blocks are selected into a CV

1. Read the posting text in `brief.md`, the requirements language and not just the title.
2. Read `INDEX.md` whole. Take the blocks whose `lanes` include the posting's matched lanes
   and whose `competency` words answer something the posting asks for.
3. Lead with the lane the posting actually is, not the lane with the most blocks.
4. Open the source files those blocks live in. Read the long variants, the
   `interview_exposure` notes and the "Not claimed here" section.
5. Assemble by `source`: one Experience or Selected projects entry per source, a
   `role_summary` chosen for the lane, then the bullets.

**A source appears once per CV.** A source may have several `role_summary` blocks, one per
lane cluster, and may have both a `role_summary` and a `project` block. The generator picks
one. Placing the same work twice is the most likely way this design produces an obviously bad
CV, so the check is explicit.

**Work with an employer behind it goes in Experience. Work with none goes in Selected
projects.**

Section order for industry postings: Profile, Experience, Selected projects, Education,
Skills, Languages. For academic postings and the doctoral track: Profile, Experience,
Publications, Education, Selected projects, Skills, Languages.

Experience is ordered by reverse chronology, not by relevance. Relevance is expressed through
which bullets are chosen and how long they are.

---

## 8. What the generator may and may not do

**May.** Choose which blocks appear and in what order. Cut a long variant to a short one.
Align vocabulary to the posting, for example writing "systemförvaltning" where the block says
"internal tooling". Translate. Write the profile paragraph fresh. Reorder or omit whole
sections. Leave out anything unflattering. Emphasise freely.

**May not.** Change a number. Change a technology. Change authorship or attribution. Assert a
method, tool or credential that appears in no block. Write anything a "Not claimed here"
section rules out.

The line: specifics are checkable in the room and must be right. Framing, emphasis, omission
and level of detail are the candidate's to set.

---

## 9. Files

```
blocks/
  SCHEMA.md              this file
  INDEX.md               generated by tools/build_index.py, one row per block
  identity.md            name, contact line, languages, eligibility, profile anchors
  meter_pipeline.md      the nightly pipeline, dbt models, scheduling, dashboards, reports
  followup_tool.md       the advisers' follow-up tool and the system integrations
  agency.md              three years of web development at an agency
  thesis.md              thesis tool, the test with households, paper, education, teaching
  district_map.md        the public map and custom charts
  skills.md              skill_term blocks and the rule for assembling the Skills section
```

Seven files is a sample. A real bank has one file per employer or project and runs to a hundred
blocks or so.

The generator loads `INDEX.md` whole, then reads only the source files it needs. Run
`python3 tools/build_index.py` from the repository root after changing any block. Do not edit
`INDEX.md` by hand.
