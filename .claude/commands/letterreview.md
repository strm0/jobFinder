---
description: Review a finished letter.md as a cold reader, with no knowledge of why it was written that way
---

Review the `letter.md` in the current application folder. **Do not rewrite it.** Reviewing and
revising are different jobs, and doing both in one pass recreates the problem this command
exists to solve.

This is the public demo version of the command.

## Why this command exists

`/letter` runs its own checks on its own draft, moments after writing it, against the criteria
it just used to write it. A model marking its own homework passes. The faults that survive
`/letter` are the ones that are invisible from the inside: a letter that ends twice, a clever
line that reads badly to someone who did not think of it, a paragraph that satisfies a rule's
wording while missing its point.

You are the cold reader. You did not write this and you have no stake in any sentence in it.
Run this in a fresh session, not in the one that wrote the letter.

## Pass one: read as the recruiter, before anything else

Read, in this order, and **nothing else yet**:

1. `letter.md` in the current directory.
2. `brief.md` in the current directory, for the posting text. Read the full advertisement, not
   just the matcher output.

**Do not open `notes.md`.** It records why the author made each choice and it will talk you
into the letter. **Do not open the blocks yet.** Judge what is on the page, not what was
available.

Now answer these, in order, and quote the sentence you are judging every time.

1. **Twenty seconds.** Read only until you would stop if you had two hundred more of these.
   What job is this person applying for, and what is the one reason they say they fit? If you
   cannot answer both, say so and stop there; that is the finding.
2. **The skim test.** Read only the first sentence of each paragraph. Do the claim, the case
   and the ask survive?
3. **The ad.** List every explicit instruction in the advertisement about what to send or what
   to tell them. For each one, quote where the letter answers it, or write NOT ANSWERED.
4. **The employer.** What, specifically, does this letter show its writer knows about this
   employer? A fact from their own advertisement or their own work counts. A fact about the
   writer does not, however specific it is.
5. **Attachment.** Take every number, name, date and place. For each, write in one phrase the
   claim it proves. Blanks are the faults.
6. **The close.** Does the final paragraph ask for a conversation? An offer to show something
   if invited is not an ask. Does the letter end once?
7. **The swap tests.** Put another applicant's name on it. Then put a competitor's name in
   place of this employer's. What still reads true is decoration.
8. **Read it aloud.** Name every sentence whose stress you could not place on the first pass,
   and every sentence a person would not say to a hiring manager's face.
9. **The cleverness check.** Name any line that is doing more work for the writer than for the
   reader: a number the reader cannot calibrate, a joke that needs the writer's context, a
   phrase that sounds good and proves nothing.

## Pass two: now check the facts

Only now open `../../blocks/INDEX.md`, the block source files the letter draws on, and
`notes.md`.

- Every number, technology, title, attribution and credential in the letter must appear in a
  block. List any that does not.
- Nothing may contradict a **Not claimed here** section in any of those files. Check each line
  of each section against the letter, including what the letter implies without saying.
- Anything the candidate supplied by hand during drafting, which `notes.md` records, is a fact
  that should become a block. Name it.

## Pass three: the script

```
python3 ../../tools/lettercheck.py letter.md --title "<the job title from brief.md>"
```

Give its output. Where it passes and your reading disagrees, your reading wins and you say so;
the script only carries what can be settled by counting, and its thresholds and phrase lists
are illustrative examples chosen for this demo. It has lists for Swedish and English and
measures any other language with the English ones.

## Output

One page, in this order:

1. **Verdict**, in one sentence: send it, fix these things first, or start again.
2. **What works**, at most three items, each quoting the sentence. Be brief; this section is
   for telling the author what not to break.
3. **Faults**, ordered by what they cost, each with the quoted sentence, the reason, and a
   concrete replacement or the question the candidate must answer to write one.
4. **What the advertisement asked for and did not get.**
5. **Facts to verify or add as blocks.**

No preamble. Do not soften a fault because the letter is good elsewhere, and do not invent
faults to balance the review. If the letter is ready, say so in one line and stop.

## Then

The candidate chooses what to change. If asked to apply the fixes, apply them in `letter.md`,
re-run `lettercheck.py`, re-render with `python3 ../../render/render.py letter.md`, and say in
one line what changed.

If a fault is one `/letter` should have prevented, say which instruction in
`.claude/commands/letter.md` failed, so it can be fixed there and not only in this letter.
