---
description: Draft a cover letter for the posting in this application folder
---

Draft a cover letter for the posting in the current application folder.

This is the public demo version of the command. It works on the invented candidate in `blocks/`.

Paths below are relative to the application folder, `applications/<company> - <job title> - <ad
number>/`, which is where this runs. Same convention as `/cv`.

This command covers where the facts come from, what the letter is for, the checks and the
render. It has no description of how the candidate writes, so expect a correct letter in a
neutral tone that the candidate has to make their own.

## Read, in this order

1. `brief.md` in the current directory. The posting text, matched lanes, score, the model's
   reasons and the signals hit. If `brief.md` does not exist, stop and say so.
2. `../../blocks/SCHEMA.md`, sections 5 and 8: what "Not claimed here" means and what you may
   and may not do with a block.
3. `cv.md` in the current directory, **if it exists**. The letter must not restate what the CV
   already says. If it does not exist yet, say so in your one line of output and draft anyway.
4. `../../blocks/INDEX.md`, whole.
5. Then, and this is the step that differs from `/cv`: **work out which blocks the CV did not
   use.** Compare `../../blocks/INDEX.md` with what actually appears in `cv.md`. The letter's
   job is the material the CV had no room for. Load the source files under `../../blocks/` for
   the two or three unused blocks most relevant to this posting, plus the source files behind
   whatever the letter's argument leans on, plus `../../blocks/identity.md` for the header.

Read `interview_exposure` on every block you draw from. The letter is the one place a question
a claim invites can be answered before it is asked. The CV cannot do this.

Respect every **Not claimed here** section in the files you read. Those are not suggestions.

## Ask, only when the blocks cannot answer

A letter is better the more of it comes from the writer and the less from the model. The
blocks are the candidate's material, so most of the time they are enough and you draft without
asking.

Ask when the letter's chosen argument needs something the bank does not hold, which is usually
one of these: what went wrong in the project this letter is about, what the candidate chose not
to do, a phrase somebody else used about the work, or what they have actually used or read
from this employer.

Rules for asking. At most three questions, in one message, each answerable in a sentence. Ask
only what the candidate is the only source for; anything in `brief.md`, the blocks or on the
employer's site is not a question. Then wait. If the answer is to just draft it, draft it.

Do not ask which lane to write to, which blocks to use, or which of two arguments is
preferred. Those are yours to settle and the answer to the first is in `brief.md`.

In this demo the candidate is invented, so there is nobody to answer. If you would have asked,
write the question into `notes.md` and draft from the blocks alone. Do not make up an answer.

## Then write

Write `letter.md` in the current directory. No preamble in chat beyond one line saying which
lane you wrote to and what argument you chose.

**The letter is generated fresh. It is not assembled from blocks.** Blocks supply facts,
figures, technologies and attributions, which must be used exactly as written. The argument,
the order and every sentence are new against this posting. If two letters for two employers
could be swapped by changing the nouns, the generation has failed.

**One argument, one story.** One full story of 80 to 140 words and at most two compressed
proofs. A letter that touches five things touches none.

**Language.** The language of the posting, not the language of the country. A Swedish posting
gets a Swedish letter even at an international company, and an English posting gets an English
letter even at a Swedish one.

Before writing, settle these and state the first two in the one line of chat output:

- **Which complication.** What went wrong, surprised the candidate, or was harder than
  expected in the work this letter is about. Use it only if a block or an answer holds it. If
  nothing does, write the story without one and say so in `notes.md`. Never invent a setback.
- **Which fact about the employer.** One fact that comes from the advertisement itself or from
  the employer's own published work, named in the letter. If `brief.md` names a stack, a
  product, a client or a way of working that the blocks can answer, that is the fact.
- **Whether a gap must be named.** If the posting requires something a "Not claimed here"
  section rules out, the letter either says so plainly in one clause or leaves the subject
  alone. It never implies the candidate has it.

## letter.md format

```
---
name: <header-name from identity.md>
contact: <header-contact from identity.md, exactly as written>
recipient: <named person and organisation, or just the organisation>
date: <written in the language of the letter>
lang: <sv | da | en>
---

Hej <name>,

<the claim: the role, named, plus one clause of reason>

<the story: one project, constraint before action, result in checkable form, then the sentence
that says what it means for this job>

<second proof, or the transition>

<why this employer>

<close: ask for a conversation>

<sign-off>
<name>
```

Only `name` is required; the renderer omits any of the others that are absent. `lang` is not
decoration: `lettercheck.py` reads it to pick the word band, the phrase list and the pronouns
it counts, so set it. The script has lists for Swedish and English only. It has none for
Danish and measures any other value, `da` included, with the English ones, and says so at the
top of its output. Read its word-based lines with that in mind.

Paragraphs are separated by a blank line. A single newline inside a paragraph becomes a line
break, which is what the greeting and the sign-off want. Do not use level 2 headings: the
renderer treats a file containing them as a CV.

Name the job title, exactly as `brief.md` gives it, in the first sentence.

## Check, after the file exists

```
python3 ../../tools/lettercheck.py letter.md --title "<the job title exactly as brief.md gives it>"
```

It exits non-zero when a hard check fails. **A failure means rewrite, not soften.** Fix the
file and run it again until it passes. Lines marked `note` are measurements with a direction
and no correct value. Read them and judge.

The countable rules live in the script and not in this file on purpose. A word limit inside a
long instruction is broken more often than one that is checked on its own afterwards. Every
number and phrase list in the script is an illustrative example chosen for this demo, there to
be replaced by the candidate's own.

Four things the script cannot check. Do them by reading.

- **Attachment.** For every number, name, date and place in the letter, say in one phrase what
  claim it proves. A blank is cut or filled.
- **The skim test.** Read only the first sentence of each paragraph. The claim, the case and
  the ask should survive.
- **The swap test.** Put another applicant's name on it, then a competitor's name in place of
  the employer's. Anything that still reads true is decoration.
- **The source test.** Every number, technology, title and credential in the letter appears in
  a block, and nothing contradicts a "Not claimed here" line.

## Rendering

```
python3 ../../render/render.py letter.md
```

Both files, every time, and only once the checks pass. `letter.md` is what the candidate edits
and pastes into web forms. `letter.pdf` is what gets attached. One script, two templates: a
source file with no level 2 headings is treated as a letter, or force it with `--letter`.

Render is deterministic and has no model in it, so after a hand edit of `letter.md` the
candidate can re-render with `/rerenderletter`.

## Notes

Append a `# Letter` section to `notes.md` in the current directory, after whatever `/cv` wrote.
Record: the lane and the argument chosen, the complication or the lack of one, which blocks
the letter drew on, anything the candidate supplied by answering a question and which block it
should become, how the letter differs from `cv.md`, any gap in the posting the bank could not
answer, and the `lettercheck.py` output for the final version.

## Review

Once the checks pass and the file is rendered, the letter has only been read by the model that
wrote it. Run `/letterreview` in a fresh session for a cold read. Then the candidate reads it.
Nothing is sent by this command, and no letter should go out that its sender has not read and
edited.

## Revision turns

No command. The candidate edits `letter.md` directly and writes comments into it. Comments can
be vague ("this paragraph is doing nothing", "sounds generated").

On a revision turn: read `letter.md` including the edits and comments, interpret both, rewrite
the file in place, re-run `lettercheck.py`, re-render. One line of explanation, not more.

If a fix shows a missing or wrong fact, edit the block in `../../blocks/`, then run
`python3 tools/build_index.py` from the repository root. Say that you did it.

If the candidate answered a question during drafting and the answer will hold for later
letters, it belongs in a block. Say which one and offer to write it.

## Do not

- Do not generate a subject line, an email wrapper, or a covering note unless asked.
- Do not produce two variants to choose between. Pick the stronger argument and commit.
- Do not soften a claim that is in a block, and do not strengthen one either. Specifics must
  be right. Framing, emphasis, omission and level of detail are the candidate's.
- Do not open on a scene whose relevance is withheld, or on the employer's product described
  back to them.
- Do not close on a proposal, a menu of topics, or a thank you.
- Do not use em dashes or en dashes. The script fails the letter on them.
