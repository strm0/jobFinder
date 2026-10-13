# jobFinder

![The jobFinder dashboard on the sample data: ranked job cards in two columns on the left, and one job opened on the right with its apply-by date, score, place in the list, the Write brief, Open posting and Save buttons, and the reasons for its want and reach ratings](docs/dashboard.png)

This is a public demonstration copy of jobFinder, the system I built for my own job search.
The version I use every day reads real job ads and has Claude Haiku rate each one through the
Anthropic API. This copy has the same code, but its job ads and its candidate are invented and
the ratings were generated in advance, so it runs without an API key and without my data.

The case study, with the reasoning behind the design, is at
[oscarstrom.com/job-search](https://oscarstrom.com/job-search/).

## What it does

- Collects new job ads every day from Arbetsförmedlingen's JobTech API and from JobAd Links,
  which covers other Swedish job sites.
- Skips the ads that are plainly out of scope before any model sees them: 96 of 159
  occupation groups are skipped, so about 40 percent of ads reach the model.
- Has a model give each remaining ad two ratings: want, how much the candidate would want the
  job, and reach, how likely they are to get it.
- Ranks the ads by one score that is not an average of the two. Want counts most and reach
  only discounts it.
- Shows the ranking in a dashboard on localhost, and writes a brief for any job so a CV and a
  cover letter can be drafted from a bank of checked claims.

## Run it

You need Python 3.13 and Node.js. No API key and no account.

```sh
python3.13 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m pipeline.seed
```

The seed command builds a SQLite store in `data/` from the files in `sample/`, runs the free
stages over it and prints each stage's own checks. Then, for the ranking in the terminal:

```sh
python tools/top.py --limit 15
```

And for the dashboard, build the page once and start the server:

```sh
(cd dashboard/standard && npm install && npm run build)
python -m dashboard.serve --open
```

It serves on http://127.0.0.1:8787 and nowhere else. Saved, Applied and Removed are written
to your local store. `python -m pipeline.seed --force` resets it.

## Things to try

Everything except the ratings is free to rebuild, which is the point of the design.

- **Change the ranking.** The four constants of the score are in
  `context/02_search_config.yaml` under `scoring.recommend_rules.constants`. Edit them and run
  `python -m pipeline.score rebuild`. To compare without writing anything:
  `python -m pipeline.score preview --floor 0.3 --slope 0.07`.
- **Break a rule on purpose.** Put `reach_floor: 0.3` and `reach_slope: 0.07` in the config and
  run `python -m pipeline.score verify`. The check that a job the candidate wants always
  outranks one they do not fails, over every possible pair of ratings and not only the ones in
  the store.
- **See what the pre-filter did.** `python -m pipeline.prefilter status` shows what was kept,
  skipped, rescued by its headline and vetoed. The group verdicts are in
  `context/occupation_groups.md`.
- **Make the ratings stale.** Edit a line in `context/candidate_brief.md` and run
  `python -m pipeline.score verify`. The ratings were produced for the brief as it was, and the
  system says so instead of ranking on them silently. `git checkout` the file to undo it.
- **Ask what a real run would cost.** `python -m pipeline.classify estimate --n 50` prints the
  estimate without a key and without spending.
- **Run the tests.** `python -m unittest -v`.

## What is real here and what is not

| | In this copy | In the version I use |
|---|---|---|
| Code | The same pipeline, scoring and dashboard | |
| Job ads | 231 invented ads, in Swedish and English, with invented employers | Real ads, fetched every day |
| Candidate | Maren Kjeldsen, an invented person with her own background and preferences | Me |
| Ratings | Generated once, in advance, and shipped in `sample/` | Claude Haiku 4.5 rates each new ad through the Anthropic API |
| API key | Not needed | Read from the macOS Keychain inside the process |
| Schedule | None. You run the seed command | Once a day, started automatically |
| Dashboard | The standard design | The same |

**How the ratings were made.** I ran this repository's own classifier, `pipeline/classify.py`,
once over the invented ads with Claude Haiku 4.5, using the prompt in
`pipeline/prompts/classify_v1.md` and the invented candidate's brief in
`context/candidate_brief.md`. 100 of the 231 ads were rated: every ad the pre-filter kept, and
a few it skipped so that the rejected views have something in them. The ratings in
`sample/classifications.jsonl` are the model's output, with real place names corrected where it
confused an invented employer with a real one. That was two summaries: an invented region and
an invented hospital had each been given the name of the town the ad is placed in. Nothing else is edited, the model's mistakes included, and each row carries the
token counts of its call.

**What I changed for this copy.** The candidate is invented, and not a copy of me with the
name changed: her background, her limits, what she wants and what she avoids, her lanes, the
soft signals and the salary numbers are made up for this copy. The classifier prompt keeps its
structure, the order in which the fields are decided, the two ratings and the hard filter ids;
its lane descriptions, calibration examples and rating guidance are rewritten for her. The
classifier reads its key from the `ANTHROPIC_API_KEY` environment variable instead of the
Keychain. `pipeline/seed.py`, `dashboard/demo.py`, the tests and `sample/` exist only here.
The first of the two dashboard designs is left out. Comments that named real employers are
reworded. The occupation group verdicts, the scoring rule and its constants and the pre-filter
are the real ones.

**The paid path is still here.** `pipeline/classify.py` is the module that spends money in the
real system, and it is worth reading for that reason: the system prompt is cached, every
spending mode prints an estimate first, and nothing is sent without `--yes`. That holds for the
scheduled run too: `python -m pipeline.nightly auto` classifies only when it is started with
`--yes`. Without a key the classifier stops and says so.

**Three commands contact real services, and the demo needs none of them.**
`python -m pipeline.ingest` and `python -m pipeline.links` fetch real job ads from JobTech's
public APIs and from job sites, and `python -m pipeline.nightly run` runs both. They need no
key and cost nothing, but they put real ads in your local store next to the invented ones.

**Platforms.** The seed command, the free stages, the tests and the dashboard use nothing
specific to one operating system. `pipeline.nightly auto` is macOS only.

## Where things are

```
pipeline/     the stages: ingest, links, normalise, prefilter, signals, classify, score
              nightly.py runs them in order; seed.py builds the demo store
dashboard/    serve.py and queries.py, the local server; standard/ is the page
context/      the config, the candidate's brief, the occupation group verdicts
sample/       the invented ads and the ratings generated for them
blocks/       the claim bank a CV is assembled from, with sample blocks
render/       Typst templates and the script that renders a CV or a letter to PDF
tools/        top.py prints the ranking; lettercheck.py checks a letter draft
tests/        a smoke test over the free path
.claude/      the /cv and /letter commands, run with Claude Code in a job's folder
DESIGN.md     the dashboard's design system
```

## Built with

Python 3.13, SQLite, Claude Haiku 4.5, React 19, Vite, TypeScript and Typst. Job data in the
real system comes from Arbetsförmedlingen through JobTech Dev, and from JobAd Links. The
dashboard's design process used Impeccable, the typeface is Newsreader and the icons are
lucide.

I started it on 4 September 2026 and it has been in daily use since 14 September 2026.

The code is written with Claude Code from my design.

## Licence

MIT. See `LICENSE`.
