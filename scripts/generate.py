#!/usr/bin/env python3
"""Generate one mp3 per paragraph with ElevenLabs Eleven v4.

One request per paragraph. Reads work/paragraphs.json (from prepare.py).
Writes work/pNN.mp3 and keeps an untouched copy in work/raw/pNN.mp3.
The API key is read from ELEVENLABS_API_KEY and never printed.

Docs checked (Nov 2026):
  Models list (model_id "eleven_v4", Burmese code "my"): https://elevenlabs.io/docs/overview/models
  Endpoint, voice_settings, language_code, output_format:
    https://elevenlabs.io/docs/api-reference/text-to-speech/convert
  POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
"""
import argparse
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

MODEL_ID = "eleven_v4"
API = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def synth(session, key, voice_id, text, args):
    import requests  # noqa: F401  (session is a requests.Session)
    body = {"text": text, "model_id": args.model}
    if args.language_code:
        body["language_code"] = args.language_code
    vs = {}
    if args.stability is not None:
        vs["stability"] = args.stability
    if args.speed is not None:
        vs["speed"] = args.speed
    if vs:
        body["voice_settings"] = vs
    delay = 4.0
    for attempt in range(1, args.retries + 2):
        r = session.post(API.format(voice_id=voice_id),
                         params={"output_format": args.output_format},
                         headers={"xi-api-key": key, "Content-Type": "application/json"},
                         json=body, timeout=300)
        if r.status_code == 200:
            return r.content
        if r.status_code in (429, 500, 502, 503, 504) and attempt <= args.retries:
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    raise RuntimeError("retries exhausted")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", default="work")
    ap.add_argument("--voice-id", default=os.environ.get("ELEVENLABS_VOICE_ID"),
                    help="voice id (or set ELEVENLABS_VOICE_ID)")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--language-code", default="my",
                    help='ISO 639-1 code to force the language (default "my"); pass "" to omit')
    ap.add_argument("--only", help="comma list of paragraph ids, e.g. p03,p07")
    ap.add_argument("--force", action="store_true", help="regenerate even if the mp3 exists")
    ap.add_argument("--takes", type=int, default=1,
                    help="takes per paragraph (default 1; credits are expensive). "
                         "Extra takes are saved as pNN_t2.mp3, pNN_t3.mp3")
    ap.add_argument("--concurrency", type=int, default=4, help="max parallel requests (max 4)")
    ap.add_argument("--retries", type=int, default=5, help="retries on 429/5xx with backoff")
    ap.add_argument("--stability", type=float, default=None, help="optional voice_settings.stability")
    ap.add_argument("--speed", type=float, default=None, help="optional voice_settings.speed")
    ap.add_argument("--output-format", default="mp3_44100_128")
    ap.add_argument("--dry-run", action="store_true", help="show what would be generated, no requests")
    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    work = Path(args.work)
    paras = json.loads((work / "paragraphs.json").read_text(encoding="utf-8"))
    only = {x.strip() for x in args.only.split(",")} if args.only else None
    jobs = []
    for p in paras:
        if only and p["id"] not in only:
            continue
        for t in range(1, max(1, args.takes) + 1):
            name = f"{p['id']}.mp3" if t == 1 else f"{p['id']}_t{t}.mp3"
            if (work / name).exists() and not args.force and not only:
                print(f"skip {name} (exists)")
                continue
            if (work / name).exists() and not args.force and only:
                print(f"skip {name} (exists, use --force to redo)")
                continue
            jobs.append((p, name))

    chars = sum(len(p["text"]) for p, _ in jobs)
    print(f"{len(jobs)} request(s), {chars} characters")
    if args.dry_run or not jobs:
        return

    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("Set ELEVENLABS_API_KEY first.")
    if not args.voice_id:
        sys.exit("Give --voice-id or set ELEVENLABS_VOICE_ID.")
    import requests
    session = requests.Session()
    (work / "raw").mkdir(parents=True, exist_ok=True)
    failed = 0
    with ThreadPoolExecutor(max_workers=max(1, min(4, args.concurrency))) as ex:
        futs = {ex.submit(synth, session, key, args.voice_id, p["text"], args): (p, name) for p, name in jobs}
        for f in as_completed(futs):
            p, name = futs[f]
            try:
                audio = f.result()
                (work / name).write_bytes(audio)
                shutil.copyfile(work / name, work / "raw" / name)
                print(f"ok   {name}")
            except Exception as e:  # never print the key
                failed += 1
                print(f"FAIL {name}: {str(e).replace(key, '***')}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
