#!/usr/bin/env python3
"""Prepare a Burmese script for Eleven v4.

Input: a .txt file, paragraphs separated by blank lines.
Does: lexicon replacements, number conversion.
Flags (never auto-fixes): paragraphs that are probably too long, leftover
digits, homophone entries, ALL CAPS Latin words, tags with hyphens, risky tags.
Output: work/paragraphs.json, work/pNN.txt, work/report.txt
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from numbers_my import replace_numbers  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RISKY_TAGS = {"softly", "whispers", "pointed", "frustrated", "angry"}
TAG_RE = re.compile(r"\[([^\]]*)\]")
CAPS_RE = re.compile(r"\b[A-Z]{2,}\b")
DIGIT_RE = re.compile(r"[0-9၀-၉]")
# Rough guess: 1,000 Myanmar characters is about 60 s of speech (Burmese reads slow).
DEFAULT_SEC_PER_CHAR = 0.06


def read_tsv(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        rows.append(line.split("\t"))
    return rows


def spoken_chars(text):
    """Characters that get spoken: drop tags and whitespace."""
    return len(re.sub(r"\s+", "", TAG_RE.sub("", text)))


def split_suggestions(text, limit_s, sec_per_char):
    parts = [p for p in re.split(r"(?<=။)\s*", text) if p.strip()]
    chunks, cur = [], ""
    for p in parts:
        if cur and (spoken_chars(cur + p) * sec_per_char) > limit_s:
            chunks.append(cur.strip())
            cur = p
        else:
            cur = (cur + " " + p) if cur else p
    if cur:
        chunks.append(cur.strip())
    return chunks


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("script", help="script .txt, paragraphs separated by blank lines")
    ap.add_argument("--work", default="work", help="output folder (default: work)")
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon.tsv"))
    ap.add_argument("--homophones", default=str(ROOT / "homophones.tsv"))
    ap.add_argument("--max-seconds", type=float, default=40.0,
                    help="flag paragraphs estimated longer than this (default 40)")
    ap.add_argument("--sec-per-char", type=float, default=DEFAULT_SEC_PER_CHAR,
                    help="seconds per spoken character; rough guess, calibrate on your voice "
                         "(default 0.06 = 1,000 chars in 60 s)")
    ap.add_argument("--allow-caps", default="AI",
                    help="comma list of ALL CAPS words not to flag (default AI)")
    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    raw = Path(args.script).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    paras = [re.sub(r"\s*\n\s*", " ", p) for p in paras]

    lexicon = [r for r in read_tsv(Path(args.lexicon)) if len(r) >= 2]
    homophones = [r for r in read_tsv(Path(args.homophones)) if len(r) >= 2]
    allow = {w.strip() for w in args.allow_caps.split(",") if w.strip()}

    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    out, report = [], []
    for i, text in enumerate(paras, 1):
        pid = f"p{i:02d}"
        flags = []
        lex_hits = 0
        for written, spoken in lexicon:
            c = text.count(written)
            if c:
                text = text.replace(written, spoken)
                lex_hits += c
        text, num_flags = replace_numbers(text)
        flags += [("number", f) for f in num_flags]

        est = spoken_chars(text) * args.sec_per_char
        if est > args.max_seconds:
            chunks = split_suggestions(text, args.max_seconds, args.sec_per_char)
            flags.append(("long", f"estimated {est:.0f} s (limit {args.max_seconds:.0f}); "
                                  f"suggest splitting at sentence ends into {len(chunks)} parts: "
                                  + " | ".join(f"{spoken_chars(c) * args.sec_per_char:.0f}s" for c in chunks)))
        if DIGIT_RE.search(text):
            flags.append(("digits", "digits remain; write them as words"))
        for row in homophones:
            if row[0] in text:
                note = row[2] if len(row) > 2 else ""
                flags.append(("homophone", f"'{row[0]}' may be heard as '{row[1]}'. {note}"))
        for w in sorted(set(CAPS_RE.findall(re.sub(TAG_RE, "", text)))):
            if w not in allow:
                flags.append(("caps", f"ALL CAPS word: {w}"))
        for t in TAG_RE.findall(text):
            if "-" in t:
                flags.append(("tag", f"hyphen in tag: [{t}]"))
            if t.strip().lower() in RISKY_TAGS:
                flags.append(("tag", f"risky tag: [{t}]"))

        (work / f"{pid}.txt").write_text(text + "\n", encoding="utf-8")
        out.append({"id": pid, "text": text, "est_seconds": round(est, 1),
                    "lexicon_hits": lex_hits,
                    "flags": [{"type": a, "detail": b} for a, b in flags]})
        report.append(f"{pid}  ~{est:.0f}s (rough guess)  lexicon replacements: {lex_hits}  flags: {len(flags)}")
        for a, b in flags:
            report.append(f"    [{a}] {b}")

    (work / "paragraphs.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(p["est_seconds"] for p in out)
    report.append(f"\n{len(out)} paragraphs, ~{total:.0f}s total. Duration is a rough guess from character count.")
    (work / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
