---
description: Re-render letter.pdf from letter.md as it stands, without changing the text
---

Re-render the letter in the current application folder from `letter.md` exactly as it is now.

This is the public demo version of the command.

Paths below are relative to the application folder, `applications/<company> - <job title> - <ad
number>/`, which is where this runs. Same convention as `/letter`.

The candidate has edited `letter.md` by hand, and that text is final for this render. The
renderer is deterministic and has no model in it, so this command only runs it.

1. If `letter.md` is not in the current directory, stop and say so.
2. Run `python3 ../../render/render.py letter.md`.
3. If it fails, show the error it printed and stop. Do not try to fix `letter.md`.
4. Otherwise reply with one line: `letter.pdf` re-rendered.

Do not read, check, edit or rewrite `letter.md`, and do not comment on the content. Do not run
the checks from `/letter`, and do not touch `notes.md` or the blocks. HTML comments in
`letter.md` are notes for the next revision turn, not instructions for this command. The
renderer strips them, so they never reach the PDF.
