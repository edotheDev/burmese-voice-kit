#!/usr/bin/env python3
"""Check each paragraph's audio against its prepared text (optional).

Sends work/pNN.mp3 to ElevenLabs Speech to Text (Scribe) with language
Burmese, then compares the transcript to work/pNN.txt with difflib.
Paragraphs under the similarity threshold are flagged with missing and
extra spans. Transcripts are saved in work/transcripts/.

Docs checked (Nov 2026):
  Model ids (scribe_v2; scribe_v1 is deprecated): https://elevenlabs.io/docs/overview/models
  Endpoint POST /v1/speech-to-text, fields model_id, language_code, file:
    https://elevenlabs.io/docs/api-reference/speech-to-text/convert
  Burmese is listed as "mya" (Good tier, 10 to 20 percent WER):
    https://elevenlabs.io/docs/overview/capabilities/speech-to-text
So expect some noise: treat the flags as pointers, then listen.

Do NOT use Whisper for Burmese, it is useless for it.
Manual alternative: upload ONE clip per fresh Gemini chat and ask for a
word-for-word transcript. Several clips in one message get mixed up, and
long files get truncated around 3 minutes.
"""
import argparse
import difflib
import os
import re
import sys
from pathlib import Path

MODEL_ID = "scribe_v2"
API = "https://api.elevenlabs.io/v1/speech-to-text"
TAG_RE = re.compile(r"\[[^\]]*\]")
PUNCT_RE = re.compile(r"[\s၊။,.!?;:\"'“”‘’()\-–—…]+")


def norm(s):
    s = TAG_RE.sub("", s)
    s = PUNCT_RE.sub("", s)
    return s.lower()


def compare(expected, heard):
    a, b = norm(expected), norm(heard)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    missing, extra = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace") and i2 > i1:
            missing.append((i1, a[i1:i2]))
        if tag in ("insert", "replace") and j2 > j1:
            extra.append((j1, b[j1:j2]))
    return sm.ratio(), missing, extra


def transcribe(session, key, path, args):
    import time
    delay = 4.0
    for attempt in range(args.retries + 1):
        with open(path, "rb") as fh:
            r = session.post(API, headers={"xi-api-key": key},
                             data={"model_id": args.model, "language_code": args.language_code,
                                   "tag_audio_events": "false"},
                             files={"file": (Path(path).name, fh, "audio/mpeg")}, timeout=600)
        if r.status_code == 200:
            return r.json().get("text", "")
        if r.status_code in (429, 500, 502, 503, 504) and attempt < args.retries:
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--work", default="work")
    ap.add_argument("--only", help="comma list of paragraph ids, e.g. p03,p07")
    ap.add_argument("--threshold", type=float, default=0.85,
                    help="flag paragraphs with character similarity below this (default 0.85)")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--language-code", default="mya", help='Burmese code (default "mya")')
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--reuse", action="store_true", help="use saved transcripts in work/transcripts/pNN.txt (e.g. made with an ElevenLabs connection) instead of calling the API")
    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    work = Path(args.work)
    tdir = work / "transcripts"
    tdir.mkdir(parents=True, exist_ok=True)
    only = {x.strip() for x in args.only.split(",")} if args.only else None
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key and not args.reuse:
        sys.exit("Set ELEVENLABS_API_KEY first.")
    import requests
    session = requests.Session()

    flagged = 0
    for txt in sorted(work.glob("p[0-9][0-9].txt")):
        pid = txt.stem
        if only and pid not in only:
            continue
        mp3 = work / f"{pid}.mp3"
        if not mp3.exists():
            print(f"{pid}  no mp3, skipped")
            continue
        tfile = tdir / f"{pid}.txt"
        if args.reuse and tfile.exists():
            heard = tfile.read_text(encoding="utf-8")
        elif not key:
            print(f"{pid}  no saved transcript at {tfile}, skipped")
            continue
        else:
            try:
                heard = transcribe(session, key, mp3, args)
            except Exception as e:
                print(f"{pid}  ERROR {str(e).replace(key, '***')}")
                flagged += 1
                continue
            tfile.write_text(heard + "\n", encoding="utf-8")
        ratio, missing, extra = compare(txt.read_text(encoding="utf-8"), heard)
        ok = ratio >= args.threshold
        print(f"{pid}  similarity {ratio:.2f}  {'ok' if ok else 'CHECK'}")
        if not ok:
            flagged += 1
            for pos, s in missing[:12]:
                print(f"   missing (at char {pos}): {s}")
            for pos, s in extra[:12]:
                print(f"   extra   (at char {pos}): {s}")
    print(f"\n{flagged} paragraph(s) to check. A pass is not proof: Scribe is only 'Good' on Burmese, so still listen to anything doubtful.")
    sys.exit(1 if flagged else 0)


if __name__ == "__main__":
    main()
