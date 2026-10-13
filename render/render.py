#!/usr/bin/env python3
"""Render a cv.md into cv.pdf, or a letter.md into letter.pdf. No model
involved. Deterministic.

Usage:
    python3 render/render.py "applications/<folder>/cv.md"
    python3 render/render.py "applications/<folder>/cv.md" --keep-typ
    python3 render/render.py "applications/<folder>/letter.md"

Expected cv.md structure:

    ---
    name: Firstname Lastname
    title: A one-line headline
    contact: City, Country | +00 000 000 000 | name@example.com
    ---

    ## Profile

    One paragraph.

    ## Experience

    ### Role title | Organisation, City
    *Jan 2024 to Jun 2025*
    Optional summary line.
    - bullet
    - bullet

    ## Selected projects

    ### Project name
    Description paragraph, or bullets.

    ## Education
    ...

    ## Skills
    ...

    ## Languages
    ...

Rules:
  - Level 2 headings become section rules, in the order they appear.
  - Level 3 headings become entries. Text before the pipe is the role, after it
    the organisation. The pipe is optional.
  - An italic line directly under a level 3 heading is the date range.
  - Lines starting with "- " are bullets. Everything else is a summary line.
  - Sections with no level 3 headings render as plain paragraphs, which is what
    Skills and Languages want.

Comments in cv.md written as HTML comments are stripped, so notes to the model
never reach the PDF.

Letters take the same pipeline and a different template. A source file with no
level 2 headings is treated as a letter, or force it with --letter.

    ---
    name: Firstname Lastname
    contact: City, Country | +00 000 000 000 | name@example.com
    recipient: Someone, Some Company
    date: 7 September 2026
    lang: sv
    ---

    Hej Someone,

    One paragraph per blank-line-separated block. A single newline inside a
    block becomes a line break, which is what a sign-off wants.

    Med vaenliga haelsningar
    Firstname Lastname

Only `name` is required. Everything else is optional and is omitted from the
letterhead when absent.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().parent / "cv-template.typ"
LETTER_TEMPLATE = Path(__file__).resolve().parent / "letter-template.typ"


def esc(s: str) -> str:
    """Escape Typst markup characters, for text placed in content mode [...]."""
    for a, b in (
        ("\\", "\\\\"),
        ("#", "\\#"),
        ("$", "\\$"),
        ("*", "\\*"),
        ("_", "\\_"),
        ("@", "\\@"),
        ("<", "\\<"),
        (">", "\\>"),
        ("[", "\\["),
        ("]", "\\]"),
    ):
        s = s.replace(a, b)
    return s


def q(s: str) -> str:
    """Quote as a Typst string literal. Strings are not parsed as markup, so only
    the backslash and the quote need escaping. Escaping markup characters here
    would print the backslashes, which is how an email address ends up reading
    as name\\@example.com on the PDF."""
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + s + '"'


def split_front(md: str):
    """Strip HTML comments, pull the YAML-ish frontmatter, return (meta, body)."""
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)

    meta = {}
    m = re.match(r"\s*---\n(.*?)\n---\n", md, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        md = md[m.end():]

    return meta, md


def parse_letter(md: str):
    """A letter is frontmatter plus blank-line-separated blocks. A single
    newline inside a block is a line break, which is what the greeting and the
    sign-off want."""
    meta, body = split_front(md)
    blocks = []
    for chunk in re.split(r"\n\s*\n", body):
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        if lines:
            blocks.append(lines)
    return meta, blocks


def to_typst_letter(meta, blocks) -> str:
    out = [f'#import "{LETTER_TEMPLATE.name}": letter, para', ""]
    out.append("#show: letter.with(")
    out.append(f"  name: {q(meta.get('name', ''))},")
    out.append(f"  contact: {q(meta.get('contact', ''))},")
    out.append(f"  recipient: {q(meta.get('recipient', ''))},")
    out.append(f"  date: {q(meta.get('date', ''))},")
    out.append(f"  lang: {q(meta.get('lang', 'en'))},")
    out.append(")")
    out.append("")

    for lines in blocks:
        out.append("#para[" + "#linebreak()".join(esc(l) for l in lines) + "]")
        out.append("")

    return "\n".join(out)


def parse(md: str):
    meta, md = split_front(md)

    sections = []
    for chunk in re.split(r"^## ", md, flags=re.M)[1:]:
        lines = chunk.splitlines()
        heading = lines[0].strip()
        body = "\n".join(lines[1:])

        entries = []
        parts = re.split(r"^### ", body, flags=re.M)
        preamble = parts[0].strip()

        for part in parts[1:]:
            plines = [l for l in part.splitlines()]
            head = plines[0].strip()
            role, _, org = head.partition("|")
            entry = {
                "role": role.strip(),
                "org": org.strip(),
                "dates": "",
                "summary": [],
                "bullets": [],
            }
            for line in plines[1:]:
                s = line.strip()
                if not s:
                    continue
                if not entry["dates"] and re.fullmatch(r"\*[^*]+\*", s):
                    entry["dates"] = s.strip("*").strip()
                elif s.startswith("- "):
                    entry["bullets"].append(s[2:].strip())
                else:
                    entry["summary"].append(s)
            entries.append(entry)

        sections.append({"heading": heading, "preamble": preamble, "entries": entries})

    return meta, sections


def to_typst(meta, sections) -> str:
    rel = TEMPLATE.name
    out = [f'#import "{rel}": cv, rule-heading, entry', ""]
    out.append("#show: cv.with(")
    out.append(f"  name: {q(meta.get('name', ''))},")
    out.append(f"  title: {q(meta.get('title', ''))},")
    out.append(f"  contact: {q(meta.get('contact', ''))},")
    out.append(")")
    out.append("")

    for sec in sections:
        out.append(f"#rule-heading({q(sec['heading'])})")
        if sec["preamble"]:
            for para in [p.strip() for p in sec["preamble"].split("\n\n") if p.strip()]:
                para = " ".join(l.strip() for l in para.splitlines())
                out.append(f"#text(size: 9.5pt)[{esc(para)}]")
                out.append("")
        for e in sec["entries"]:
            summary = " ".join(e["summary"])
            bullets = ", ".join(q(b) for b in e["bullets"])
            out.append("#entry(")
            out.append(f"  role: {q(e['role'])},")
            out.append(f"  org: {q(e['org'])},")
            out.append(f"  dates: {q(e['dates'])},")
            out.append(f"  summary: {q(summary)},")
            out.append(f"  bullets: ({bullets}{',' if e['bullets'] else ''}),")
            out.append(")")
        out.append("")

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="path to cv.md or letter.md")
    ap.add_argument("--keep-typ", action="store_true", help="leave the intermediate .typ file")
    ap.add_argument("--letter", action="store_true", help="force the letter template")
    args = ap.parse_args()

    src = Path(args.source).resolve()
    if not src.exists():
        sys.exit(f"no such file: {src}")

    raw = src.read_text(encoding="utf-8")

    # A CV is defined by its level 2 sections. Anything without them is a letter.
    is_letter = args.letter or not re.search(r"^## ", split_front(raw)[1], flags=re.M)

    if is_letter:
        template = LETTER_TEMPLATE
        meta, blocks = parse_letter(raw)
        if not meta.get("name"):
            sys.exit(f"{src.name} has no `name:` in its frontmatter")
        if not blocks:
            sys.exit(f"{src.name} has no body")
        typst_source = to_typst_letter(meta, blocks)
    else:
        template = TEMPLATE
        meta, sections = parse(raw)
        if not meta.get("name"):
            sys.exit(f"{src.name} has no `name:` in its frontmatter")
        typst_source = to_typst(meta, sections)

    typ_path = src.with_suffix(".typ")
    pdf_path = src.with_suffix(".pdf")

    # The template must sit next to the .typ for the relative import to resolve.
    local_template = src.parent / template.name
    local_template.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    typ_path.write_text(typst_source, encoding="utf-8")

    try:
        subprocess.run(
            ["typst", "compile", str(typ_path), str(pdf_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        try:
            import typst  # typst-py fallback
            typst.compile(str(typ_path), output=str(pdf_path))
        except Exception as exc:
            sys.exit(f"typst not found and the python fallback failed: {exc}\nInstall with: brew install typst")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"typst compile failed:\n{exc.stderr}")

    if not args.keep_typ:
        typ_path.unlink(missing_ok=True)
        local_template.unlink(missing_ok=True)

    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
