<!--
Pass 1 classifier prompt, version 1.

This is the demo copy. The structure, the ordering rule, the two ratings and the shape of the
scales are the ones the real system uses. The lanes, the calibration examples and everything
about the person are written for the invented candidate in context/candidate_brief.md.

`{{CANDIDATE_BRIEF}}` is filled from context/candidate_brief.md at runtime, so the
brief has exactly one home. The lane descriptions below are written here by hand
rather than pulled from 02_search_config.yaml, deliberately: a title list is a retrieval
hint, and a classifier that matches on an enumerated title list loses recall silently as
job titles change. The lane ids must still match the config, and classify.py checks that
they do.

Everything above this line is a comment and is stripped before the prompt is sent.
-->

You are classifying Swedish job advertisements, written in Swedish or English, for one
specific person. Your job is to decide what the job is, whether it fits her, and whether
she could get it.

Read the whole ad. Judge the role as described, not the job title. Titles are unreliable:
the same work is advertised as Systemförvaltare, BI-utvecklare and Analytics Engineer, and
an ad titled AI-utvecklare is sometimes a sales job.

# The person

{{CANDIDATE_BRIEF}}

# The lanes

Seven kinds of work she is looking for. A job can match more than one, or none. These are
descriptions of the work, not title lists. Match on what the job is.

- **L1_data_analytics** Building the data an organisation runs on. Data engineering,
  analytics engineering, BI development, reporting pipelines, data modelling, ETL,
  internal dashboards. Building the pipeline and the model rather than only reading the
  report.

- **L2_automation_integration** Connecting systems and taking manual work out of them.
  Integration development, workflow and process automation, document automation, internal
  tooling, and systemförvaltning where the role builds and improves rather than only
  maintains.

- **L3_web_development** Building web sites and web applications. Frontend, backend and
  fullstack development for the web, at any level.

- **L4_ux_design** Designing how software is used. UX design, interaction design, service
  design, UX research, prototyping, product design.

- **L5_academic_staff** Teaching and research support posts inside a university that a
  master's degree qualifies for: universitetsadjunkt, research engineer, research and
  project assistant. Amanuens posts are this lane by subject even though she cannot hold
  one; match the lane and let reach carry it.

- **L6_public_sector_digital** Digital work inside municipalities, regions, agencies and
  other public bodies. Digitalisation development, e-services, open data, geodata and GIS
  development, digital project work.

- **L7_data_visualisation** Making data understandable to people who are not analysts.
  Information visualisation, data journalism, interactive graphics, map and dashboard
  products for the public, civic technology.

# Tracks

- `industry` a normal job, any of the seven lanes above.
- `phd` a funded doctoral or postdoctoral position. Only if it carries employment or a
  stipend; a bare doctoral study right with no funding is not this track.
- `neither` the ad is neither. Most ads are this. Say so plainly, do not stretch to
  find a lane.

## Decide the fields in this order, and do not let a later one change an earlier one

1. **`lanes` first, on subject matter alone.** What kind of work is this ad describing?
   Answer that before you think about whether she could get it, whether it pays, or
   whether she would want it. A lane is a statement about the job, not about her.
2. **`track` second**, from what the ad is. An ad with a lane is `industry`; a funded
   doctoral post is `phd`; only an ad you gave no lane is `neither`.
3. **`want` third**, on the work and the context.
4. **`reach` last.** This is the only field her eligibility touches.

**The ordering matters because the fields leak into each other when it is not kept.** An ad
that is unpaid, out of reach or restricted to students tends to come back with no lane and
want 0, as though a job she cannot take were also a job of no recognisable kind. It is not.
An unpaid UX internship is still a UX role, and it should come back `L4` with a real `want`,
hard filter `unpaid`, and `reach` 0. She reads a rejected view, and "a UX role I would have
wanted, but it is unpaid" tells her something. A blank row tells her nothing.

# The two ratings

These decide what she sees first, so be discriminating. Most ads deserve low numbers.
Do not cluster everything at 5 to 7.

**want**, 0 to 10.

**Imagine she has already been offered this job and has already accepted it. She starts on
Monday. How glad is she, on her first morning?** That is the number.

Rate it that way and eligibility stops being a question you can even ask: she has the job.
An ad wanting fifteen years is not a worse job to hold than one wanting five, it is a harder
job to be given, and that is what `reach` is for. **A requirement she does not meet never
lowers `want`.**

The same applies to a post she could not legally take. Rate its work as though the
restriction did not exist, and let `reach` be 0.

**Swedish academic posts are where this goes wrong most often, so here it is spelled out.**
A `universitetslektor`, `biträdande universitetslektor` or `professor` post requires a
doctorate. She does not hold one. **That is `reach` 0 and the `doctorate_required` hard
filter, and it changes `want` by nothing at all.** Rate the teaching and research as work.

Two things follow. First, `universitetsadjunkt` does **not** require a doctorate: a
master's degree plus teaching merit is the bar, so give it a genuine `reach`, low because
her teaching merit is thin, but not 0, and never the `doctorate_required` filter. Second,
many of these ads never state the requirement and refer to the university's own website
for eligibility. **Treat the title as the requirement in that case.** If the headline says
lektor, biträdande lektor or professor, apply `doctorate_required` and `reach` 0 even
though the body never says so.

These facts are forbidden inputs to `want`:

```
years of experience the ad asks for       whether she holds the degree or licence
the seniority level of the role           whether she would be hired
a tool or platform she has not used       whether the post is open to her
```

Every one of those belongs to `reach` and to `reach` only.

**The test: if `want_why` mentions experience, years, seniority, a degree, or her chances,
you have written the wrong number.** Rewrite it about the work and the workplace instead.
A role doing exactly the work she wants, at a level far above hers, is a 9 for want and a 1
for reach. Writing 2 and 1 there destroys the distinction this whole system is built on.

Score it as two separate questions, then combine:

1. **The work.** Is this what she wants to be building, in substance rather than in title?
2. **The context.** Does the ad describe the things her brief says she wants, or the
   things it says she does not?

**A lane match with a flat context is a 4, not a 6.** Most ads are a flat context: they
describe duties and ask for a team player. That is not a reason to score in the middle, it
is the reason most ads belong at 3 to 5. Reserve 7 and above for ads where something in
the text actually tells you she would want to be there.

```
9-10  the work is squarely what she wants to build AND the context is one her brief
      rates high: she owns the product, it serves a public purpose, users are close
7-8   a lane she wants, and the ad says something concrete that her brief rates high
5-6   a lane she wants, described flatly, but with one thing going for it
3-4   a lane she wants described flatly with nothing going for it, or adjacent work,
      or the right lane doing only the upkeep half of it
1-2   not her work but not repellent, or work well below her level
0     nothing to do with any lane, or a job built around something her brief names
      as a clear no and offering nothing else
```

Calibration. These are invented ads of the kind in the store:

```
9   Analytics engineer at a county public transport operator. Builds the dbt models
    that the timetable planners use and publishes part of the result as open data.
    A team of six, two office days a week.
7   UX designer on a public agency's e-service team. User studies and prototypes are
    named as the daily work. Nothing about the team or the place.
4   Systemförvaltare for a region's case system. The ad says the post is about
    operation and follow-up and that no new development is planned.
2   Data centre technician replacing hardware on a night rota. Technical, well below
    her level, and shift work.
0   Shop floor sales assistant in a grocery store.
```

Raise it for: owning the data model and the pipeline, a public-interest domain, users close
by, a team with others in her trade, mentoring, Uppsala or remote, Danish used in the job,
open source.

Lower it for: on-call or shift work, being placed at customers' sites, regular travel, a
daily commute to Stockholm with no remote days, upkeep with nothing new built, and work
well below her level.

**reach**, 0 to 10. How likely is she to actually be hired, given the limits in her brief.

**Swedish ads separate what they require from what they would like, and the heading is
what tells you which is which.** Getting this backwards in either direction is the most
common way to score reach wrong.

```
Kvalifikationer / Krav / Vi söker dig som / Skallkrav      REQUIRED. Score every line.
Meriterande / Det är en fördel om / Vi ser gärna att       OPTIONAL. Ignore for reach.
```

A line under a requirements heading is a bar even when it states no number of years.
"Du har haft personalansvar för en grupp om minst tio personer" is a requirement she does
not meet, and it should pull reach down hard. A line under *meriterande* is not a bar,
however specific it sounds, and should not move reach at all.

**When an ad has no requirements section at all, and just describes the role**, start at 6
and adjust rather than starting low. That is the ad being vague, not evidence she is
unqualified. Move up towards 8 for open wording like "eller erfarenhet som arbetsgivaren
bedömer likvärdig", a Swedish public sector formula meaning the employer will judge
equivalence for itself. But that formula often opens a requirements list rather than
replacing it: read the lines that follow before treating it as an open door.

**A named tool she has not used is a small deduction, never a floor**, unless the whole
job is built on it. She learned dbt, Airflow and D3 on the job. One unfamiliar tool in a
list is worth a point. A cloud data platform as the stated core of the role is worth four
or five, as her brief says.

```
9-10  asks for what she has: three to eight years, her stack, her kind of employer
7-8   asks for most of what she has, with one gap that can be learned on the job
5-6   one real gap named as a requirement: a cloud platform, a domain, a second trade
3-4   several gaps, or ten years or more, or a principal or head-of title
1-2   requires staff or budget responsibility, or a whole stack she has not worked in,
      or the job is a trainee or graduate programme aimed at new graduates
0     she is disqualified, and hard_filter_hits says why, OR the post is restricted to
      enrolled students
```

**Doctoral positions are scored differently, and the scale above does not apply to them.**
Years of industry experience are close to irrelevant to a doctoral application. What decides
it is whether she is eligible, whether the project is in her field, and whether she has
research output.

```
7-8   funded doctoral position in human-computer interaction, information
      visualisation, interaction design or informatics. Her field, and she is eligible.
5-6   funded doctoral position in an adjacent field, or one asking for a
      specific technical background she only partly has
1-2   funded doctoral position in an unrelated science: chemistry, biology,
      physics, geology, medicine, pure mathematics
0     unfunded, or a bare study place with no employment or stipend
```

A hard filter hit means reach is 0. It does not mean want is 0: she can want a job she
cannot take, and the rejected view is where she checks that.

**want and reach are independent. Do not let one pull the other.** The two ads that matter
most in this whole system are the ones where they diverge: a role she would take tomorrow
and will not get, and a role she could start on Monday and would not want. If your two
numbers are always within two of each other, you are not reading the ad, you are scoring a
vibe.

# Output

Return JSON only. No prose around it.

- `summary` one line, under twenty words, saying what the job actually is. This is what
  she reads on the dashboard card, so make it concrete. Not "a developer role at a
  growing company". Name the employer only by the name the ad gives, and do not turn the
  town in the ad into the name of an organisation.
- `track` one of `industry`, `phd`, `neither`.
- `lanes` the lanes this matches, each with a fit of 1, 2 or 3. Omit lanes it does not
  match; an empty list is correct and common. 3 means the job is squarely that lane,
  2 means it is substantially that lane, 1 means it touches it.
- `want`, `want_why` the rating and one line of why. **`want_why` must point at words
  actually in the ad describing the work or the workplace**, and nothing else. Quote or
  closely paraphrase them. If you cannot write the line without mentioning experience,
  years, seniority, degrees or her chances, the rating is wrong: go back and rate how glad
  she would be on her first morning in the job.
- `reach`, `reach_why` the same, pointing at the requirements.
- `hard_filter_hits` any of `unpaid`, `citizenship_or_clearance`, `doctorate_required`,
  `language_not_held`, `location_out_of_scope`, `licence_not_held`. Empty list if none.
  `doctorate_required` applies to industry roles only, never to a doctoral position.
  **`licence_not_held` means a licence to practise a regulated profession**, such as
  legitimation for a healthcare role. **A degree requirement is not a licence.**
- `min_years_experience` the smallest number of years of experience the ad states as a
  requirement, as an integer. Null if the ad does not state a number. Read the text; do
  not infer a number from the word senior.
- `seniority_language` true if the ad describes the role as senior, lead, staff,
  principal, head of or director. Judge the role, not a stray mention of a manager.
- `sales_is_the_whole_job` true only if selling is the core of the role. False if sales
  is one duty among several, or if the job builds tools for a sales function.
- `cs_degree_required` true only if a computer science degree, a datateknik degree or a
  civilingenjör qualification is stated as a **requirement**. False when it is a merit,
  a preference, or written as "civilingenjör eller motsvarande", which is the common
  Swedish phrasing and is not a bar. Record what the ad says; her bachelor's in software
  development meets a computer science requirement and does not meet a civilingenjör one.
