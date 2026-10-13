#!/usr/bin/env python3
"""Countable checks for a cover-letter draft, letter.md.

Standard library only. It calls no model and writes no files.

A rule that can be counted is followed more reliably when it is checked on its own after the
draft exists than when it sits inside a long writing instruction, so those rules live here.

    python3 ../../tools/lettercheck.py letter.md --title "Product Engineer"

Every number in this file is an illustrative threshold chosen for this demo. None of them is
derived from a set of letters, and all of them are meant to be changed by whoever uses the tool.

Exit status is 1 if any HARD check fails. SOFT checks print a note and never fail the run: they
are measurements with a direction and no correct value, and a person reads them next to the draft.

Swedish ("sv") and English ("en") have their own phrase lists, pronouns and length band. Any
other value of `lang` in the front matter is measured with the English ones.
"""

import argparse
import re
import statistics
import sys

HARD, SOFT = "HARD", "soft"

# Stock cover-letter phrases, matched as lower-case substrings of the whole letter. These are
# invented examples of the kind any style guide warns about. Replace them with your own.
BANNED_EN = [
    "i am writing to express my interest", "to whom it may concern",
    "i am a highly motivated", "team player", "passionate about",
    "fast-paced environment", "hit the ground running", "think outside the box",
    "proven track record", "i would be a great asset", "perfect fit",
    "dynamic company", "go the extra mile", "results-oriented", "detail-oriented",
    "wear many hats", "unique opportunity",
]
BANNED_SV = [
    "härmed söker jag", "jag heter", "positiv och glad", "har lätt för att lära",
    "har lätt för att samarbeta", "trivs i högt tempo", "tänka utanför boxen",
    "både självständigt och i grupp", "spindeln i nätet", "passion för",
    "gedigen erfarenhet", "ser fram emot nya utmaningar", "rätt person för",
    "prestigelös", "resultatinriktad", "noggrann och strukturerad",
    "ett spännande företag", "jag tror att jag skulle passa",
]
BANNED = {"en": BANNED_EN, "sv": BANNED_SV}

# Word lists, matched as whole words or whole phrases. English and Swedish share one list each,
# because no entry in one language is a word in the other.
INTENSIFIERS = ["highly", "incredibly", "truly", "deeply", "hugely", "immensely", "exceptionally",
                "extremt", "enormt", "oerhört", "verkligen"]
HEDGES = ["somewhat", "quite", "a bit", "to some extent", "arguably",
          "ganska", "någorlunda", "till viss del", "i viss mån"]
SINCERITY = ["frankly", "truthfully", "in all honesty", "to be frank", "i truly believe",
             "from the bottom of my heart",
             "uppriktigt sagt", "ärligt talat", "helt ärligt", "i ärlighetens namn",
             "av hela mitt hjärta"]
FILLER = ["of course", "needless to say", "it goes without saying", "as you know",
          "givetvis", "det säger sig självt", "som ni säkert vet"]

# First-person words per language. They are kept apart because "i" is a pronoun in English and
# a common preposition in Swedish.
FIRST_PERSON = {
    "en": r"\b(?:i|me|my|mine|myself)\b",
    "sv": r"\b(?:jag|mig|min|mitt|mina)\b",
}

# Target word band per language. Swedish letters are conventionally shorter.
WORD_BAND = {"en": (300, 450), "sv": (180, 300)}

# A sentence that denies one thing in order to assert another ("not X but Y").
CONTRAST = {
    "en": r"\bnot\b[^.]{0,60}\bbut\b",
    "sv": r"\binte\b[^.]{0,60}\butan\b",
}

# A clause hung on the end of a sentence after a comma: ", making it ..." or ", vilket ...".
TRAILING_CLAUSE = {
    "en": r",\s+\w+ing\b",
    "sv": r",\s+vilket\b",
}


def load(path):
    """Return the letter text and its front matter, with HTML comments removed."""
    raw = open(path, encoding="utf-8").read()
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)          # comments never reach the PDF
    fm = {}
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            for line in raw[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            raw = raw[end + 4:]
    return raw.strip(), fm


def body_paragraphs(text):
    """Return the paragraphs between the greeting and the sign-off."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if paras and re.match(r"^(hej|hi|hello|dear)\b", paras[0], re.I) and len(paras[0].split()) <= 6:
        paras = paras[1:]                                       # greeting
    while paras and len(paras[-1].split()) <= 6:
        paras = paras[:-1]                                      # sign-off and name
    return paras


def sentences(text):
    """Split on sentence-ending punctuation followed by a capital letter."""
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÅÄÖ])", text)
    return [s.strip() for s in parts if s.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--title", default=None, help="the job title exactly as brief.md gives it")
    a = ap.parse_args()

    text, fm = load(a.path)
    declared = (fm.get("lang") or "en").lower()
    lang = declared if declared in BANNED else "en"            # other languages use English
    paras = body_paragraphs(text)
    words = text.split()
    sents = sentences(" ".join(p for p in paras))
    lower = text.lower()
    results = []

    def check(level, name, ok, detail):
        results.append((level, name, ok, detail))

    # The reader should learn which job this is about almost at once.
    if a.title:
        m = re.search(re.escape(a.title), text, re.I)
        before = len(text[:m.start()].split()) if m else None
        check(HARD, "words before the job title",
              before is not None and before < 25,
              f"{before} (illustrative threshold: under 25)" if before is not None
              else f"TITLE NOT PRESENT: {a.title!r}")
    else:
        check(SOFT, "words before the job title", True, "skipped, pass --title")

    # A letter that seldom says "I" tends to describe a field or an employer, not an applicant.
    fp = len(re.findall(FIRST_PERSON[lang], lower))
    rate = 100 * fp / max(len(words), 1)
    check(SOFT, "first person per 100 words", rate >= 4,
          f"{rate:.1f} (illustrative threshold: at least 4)")

    # A complete sentence inside parentheses is an aside the letter has no room for.
    whole = len(re.findall(r"(?:^|(?<=[.!?])\s)\([^)]*[.!?]\)", text))
    check(HARD, "whole-sentence parentheses", whole == 0,
          f"{whole} (illustrative threshold: none)")

    # Em and en dashes. Built with chr() so that this file contains neither character.
    dashes = sum(text.count(c) for c in (chr(0x2014), chr(0x2013)))
    check(HARD, "em and en dashes", dashes == 0,
          f"{dashes} (illustrative threshold: none; use a comma, a colon or a full stop)")

    hits = [b for b in BANNED[lang] if b in lower]
    check(HARD, "banned phrases", not hits, ", ".join(hits) or "none")

    for label, lst, cap, lvl in [
        ("intensifiers", INTENSIFIERS, 1, SOFT),
        ("hedges", HEDGES, 1, SOFT),
        ("sincerity markers", SINCERITY, 0, HARD),
        ("filler asides", FILLER, 0, HARD),
    ]:
        found = [w for w in lst for _ in re.findall(r"\b" + re.escape(w) + r"\b", lower)]
        detail = f"{len(found)} (illustrative threshold: at most {cap})"
        if found:
            detail += ": " + ", ".join(found)
        check(lvl, label, len(found) <= cap, detail)

    if sents:
        lens = [len(s.split()) for s in sents]
        over = sum(1 for n in lens if n > 45)
        check(SOFT, "sentences over 45 words", over <= 1,
              f"{over} (illustrative threshold: at most 1)")
        check(SOFT, "median sentence length", statistics.median(lens) < 25,
              f"{statistics.median(lens):.0f} words (illustrative threshold: under 25)")

    # Length. The band is a soft target. Only the ceiling, 20 percent above the band, is hard.
    n = len(words)
    band = WORD_BAND[lang]
    ceiling = int(band[1] * 1.2)
    check(HARD, "word count", n <= ceiling,
          f"{n} (illustrative thresholds for {lang}: band {band[0]} to {band[1]}, "
          f"hard ceiling {ceiling})")
    if band[0] <= n <= band[1]:
        check(SOFT, "word count in band", True, "yes")
    else:
        check(SOFT, "word count in band", False,
              f"outside {band[0]} to {band[1]}, inside the ceiling" if n <= ceiling
              else f"outside {band[0]} to {band[1]} and over the ceiling")
    check(SOFT, "paragraphs", 4 <= len(paras) <= 6,
          f"{len(paras)} (illustrative threshold: 4 to 6)")

    # Paragraphs of near-equal length read as a filled-in template. The measure is the standard
    # deviation of paragraph length divided by its mean.
    if len(paras) > 1:
        pl = [len(p.split()) for p in paras]
        cv = statistics.pstdev(pl) / (sum(pl) / len(pl))
        check(SOFT, "paragraph-length variation", cv >= 0.3,
              f"{cv:.2f} (illustrative threshold: at least 0.3; near zero means "
              "paragraphs of equal length)")

    neg = len(re.findall(CONTRAST[lang], lower))
    check(SOFT, "manufactured contrast", neg <= 2,
          f"{neg} (illustrative threshold: at most 2)")

    part = len(re.findall(TRAILING_CLAUSE[lang], lower))
    check(SOFT, "trailing clauses after a comma", part <= 1,
          f"{part} (illustrative threshold: at most 1)")

    # English only. A letter with no contractions at all reads stiffer than people write.
    if lang == "en":
        c = len(re.findall(r"\b\w+n't\b|\b\w+'(?:re|ve|ll|m|d)\b"
                           r"|\b(?:it|that|there|here|what|who|he|she|let)'s\b", text, re.I))
        check(SOFT, "contractions", c > 0, f"{c} (illustrative threshold: at least 1)")

    # The renderer decides between its CV and letter templates by looking for these headings.
    check(HARD, "no level 2 headings", "\n## " not in "\n" + text,
          "a file with them renders as a CV")

    # Report.
    print("lettercheck: countable checks with illustrative thresholds, to be read by a person")
    print("alongside the draft. FAIL means rewrite. A note means read the passage and decide.")
    if declared != lang:
        print(f"Language {declared!r} has no lists of its own here, so the English lists, pronouns")
        print("and length band were used. Read the word-based lines with that in mind.")
    print()
    width = max(len(nm) for _, nm, _, _ in results)
    failed = 0
    for level, name, ok, detail in results:
        mark = "ok  " if ok else ("FAIL" if level == HARD else "note")
        if not ok and level == HARD:
            failed += 1
        print(f"{mark}  {name.ljust(width)}  {detail}")
    print()
    if failed:
        print(f"{failed} hard check(s) failed. Rewrite, do not soften.")
        return 1

    # Whether a paragraph asks for something cannot be settled by matching words, so the closing
    # text is printed for the reader to judge.
    closing_text = "\n        ".join(paras[-2:])
    print("Hard checks pass. Read the notes above.")
    print("Read these last two paragraphs and answer four questions the script cannot:")
    print()
    print("        " + closing_text)
    print()
    print("  1. Does the final paragraph ASK for a conversation? An offer to show something")
    print("     if invited is not an ask.")
    print("  2. Does the letter end once? If an earlier paragraph already closed and this one")
    print("     opens a new topic, cut one of them.")
    print("  3. Is every specific attached, in its own paragraph, to the claim it proves?")
    print("  4. Could another applicant have sent this letter, and would it still read true")
    print("     with a competitor's name in place of this employer's?")
    return 0


if __name__ == "__main__":
    sys.exit(main())
