#!/usr/bin/env python3
"""Convert numbers to spoken Burmese words.

Integers 0 to 9,999,999 are converted. Anything bigger, or with decimals,
is NOT converted: it is flagged so you can write it by hand.

Use as a module (to_words, replace_numbers) or from the command line.
"""
import argparse
import re
import sys

DIGITS = ["သုည", "တစ်", "နှစ်", "သုံး", "လေး", "ငါး", "ခြောက်", "ခုနစ်", "ရှစ်", "ကိုး"]
PCT_WORD = "ရာခိုင်နှုန်း"
MAX_N = 9_999_999

MY_TO_LATIN = {ord(c): str(i) for i, c in enumerate("၀၁၂၃၄၅၆၇၈၉")}


def to_words(n: int) -> str:
    """Integer 0..9,999,999 to Burmese words (spoken form)."""
    if not isinstance(n, int) or n < 0 or n > MAX_N:
        raise ValueError("only integers 0 to 9,999,999 are supported")
    if n == 0:
        return DIGITS[0]
    # (divisor, plain place word, creaky place word, lower-part modulus)
    places = [
        (1_000_000, "သန်း", "သန်း", None),
        (100_000, "သိန်း", "သိန်း", None),
        (10_000, "သောင်း", "သောင်း", None),
        (1_000, "ထောင်", "ထောင့်", 1_000),
        (100, "ရာ", "ရာ့", 100),
        (10, "ဆယ်", "ဆယ့်", 10),
    ]
    out = []
    rest = n
    for div, plain, creaky, mod in places:
        d = rest // div
        rest %= div
        if d == 0:
            continue
        # creaky tone when a non-zero lower part follows
        word = creaky if (mod is not None and n % mod != 0) else plain
        if div == 10 and d == 1 and 11 <= n <= 19:
            out.append(word)  # 15 -> ဆယ့်ငါး (no leading တစ်)
        else:
            out.append(DIGITS[d] + word)
    if rest:
        out.append(DIGITS[rest])
    return "".join(out)


# A number: Latin or Myanmar digits, optional thousands commas, optional decimal part.
_NUM_RE = re.compile(
    r"(?<![A-Za-z0-9၀-၉])"
    r"(?P<num>[0-9၀-၉]+(?:,[0-9၀-၉]{3})*(?:\.[0-9၀-၉]+)?)"
    r"(?P<pct>\s*%)?"
    r"(?![A-Za-z0-9၀-၉])"
)
_GLUED_RE = re.compile(r"[A-Za-z][0-9၀-၉]+|[0-9၀-၉]+[A-Za-z]")


def replace_numbers(text: str):
    """Replace digits in text. Returns (new_text, flags).

    flags is a list of strings describing numbers left untouched
    (decimals, >= 10,000,000, leading zeros, digits glued to letters).
    """
    flags = []

    def repl(m):
        raw = m.group("num")
        pct = m.group("pct")
        latin = raw.translate(MY_TO_LATIN)
        if "." in latin:
            flags.append(f"decimal left as is: {raw}")
            return m.group(0)
        digits = latin.replace(",", "")
        if len(digits) > 1 and digits.startswith("0"):
            flags.append(f"leading zero left as is: {raw}")
            return m.group(0)
        n = int(digits)
        if n > MAX_N:
            flags.append(f"too big, write by hand: {raw}")
            return m.group(0)
        words = to_words(n)
        return words + (" " + PCT_WORD if pct else "")

    new = _NUM_RE.sub(repl, text)
    for g in _GLUED_RE.findall(new):
        flags.append(f"digits glued to letters left as is: {g}")
    return new, flags


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("text", nargs="*", help="text or numbers to convert (default: read stdin)")
    args = ap.parse_args()
    for s in (sys.stdout, sys.stdin):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    text = " ".join(args.text) if args.text else sys.stdin.read()
    new, flags = replace_numbers(text)
    print(new)
    for f in flags:
        print("FLAG:", f, file=sys.stderr)


if __name__ == "__main__":
    main()
