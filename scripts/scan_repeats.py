#!/usr/bin/env python3
"""Detect looped / duplicated stretches in generated mp3 files.

Decodes each file with ffmpeg to 16 kHz mono, computes MFCCs, and compares
every 1.2 s window with windows 1.5 to 12 s later (cosine similarity).
  > 0.80            -> REPEAT
  0.70 to 0.80      -> SUSPECT, only at a sentence length offset (2 to 8 s)
Also lists deep silences (below -60 dB, 0.25 s or longer) as cut candidates.

Note: a script's own repeated words score around 0.75, so every SUSPECT
needs your ears. REPEAT hits are almost always real.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SR = 16000
HOP = 160            # 10 ms
WIN_S = 1.2
STEP_S = 0.3
MIN_OFF, MAX_OFF = 1.5, 12.0
SENT_OFF = (2.0, 8.0)


def decode(path):
    import numpy as np
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode(errors="replace")[:300])
    return np.frombuffer(p.stdout, dtype=np.float32)


def windows(y):
    import librosa
    import numpy as np
    mf = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=20, hop_length=HOP, n_fft=512)
    mf = mf[1:]  # drop energy-like c0
    mf = (mf - mf.mean(axis=1, keepdims=True)) / (mf.std(axis=1, keepdims=True) + 1e-8)
    rms = librosa.feature.rms(y=y, hop_length=HOP, frame_length=512)[0]
    wf, step = int(WIN_S * SR / HOP), int(STEP_S * SR / HOP)
    vecs, times, keep = [], [], []
    for s in range(0, mf.shape[1] - wf, step):
        v = mf[:, s:s + wf].flatten()
        vecs.append(v / (np.linalg.norm(v) + 1e-8))
        times.append(s * HOP / SR)
        keep.append(rms[s:s + wf].mean() > 0.01)  # skip near silent windows
    return np.array(vecs), np.array(times), np.array(keep)


def merge(hits, gap=0.35):
    """hits: list of (a_start, b_start, sim). Merge neighbours into ranges."""
    hits.sort()
    out = []
    for a, b, s in hits:
        if out and a - out[-1]["a1"] <= gap + 0.3:
            o = out[-1]
            o["a1"] = max(o["a1"], a)
            o["b0"], o["b1"] = min(o["b0"], b), max(o["b1"], b)
            o["sim"] = max(o["sim"], s)
        else:
            out.append({"a0": a, "a1": a, "b0": b, "b1": b, "sim": s})
    return out


def scan_file(path, rep_thr, sus_thr):
    import numpy as np
    y = decode(path)
    dur = len(y) / SR
    V, T, K = windows(y)
    res = {"duration": dur, "repeat": [], "suspect": []}
    if len(V) < 3:
        return res
    S = V @ V.T
    rep, sus = [], []
    for i in range(len(V)):
        if not K[i]:
            continue
        for j in range(i + 1, len(V)):
            off = T[j] - T[i]
            if off < MIN_OFF:
                continue
            if off > MAX_OFF:
                break
            if not K[j]:
                continue
            s = float(S[i, j])
            if s > rep_thr:
                rep.append((float(T[i]), float(T[j]), s))
            elif s > sus_thr and SENT_OFF[0] <= off <= SENT_OFF[1]:
                sus.append((float(T[i]), float(T[j]), s))
    res["repeat"] = merge(rep)
    res["suspect"] = merge(sus)
    return res


def silences(path, db, min_dur):
    cmd = ["ffmpeg", "-v", "info", "-i", str(path), "-af", f"silencedetect=noise={db}dB:d={min_dur}", "-f", "null", "-"]
    p = subprocess.run(cmd, capture_output=True)
    txt = p.stderr.decode(errors="replace")
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", txt)]
    ends = [(float(a), float(b)) for a, b in re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", txt)]
    out = []
    for k, st in enumerate(starts):
        if k < len(ends):
            out.append((st, ends[k][0], ends[k][1]))
        else:
            out.append((st, None, None))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("inputs", nargs="*", help="mp3 files or a work folder (default: work)")
    ap.add_argument("--repeat", type=float, default=0.80, help="cosine similarity for REPEAT (default 0.80)")
    ap.add_argument("--suspect", type=float, default=0.70, help="lower bound for SUSPECT (default 0.70)")
    ap.add_argument("--silence-db", type=float, default=-60, help="deep silence level in dB (default -60)")
    ap.add_argument("--silence-min", type=float, default=0.25, help="min silence length in s (default 0.25)")
    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    items = args.inputs or ["work"]
    files = []
    for it in items:
        p = Path(it)
        if p.is_dir():
            files += sorted(f for f in p.glob("p*.mp3"))
        else:
            files.append(p)
    if not files:
        sys.exit("no mp3 files found")

    bad = 0
    for f in files:
        r = scan_file(f, args.repeat, args.suspect)
        status = "REPEAT" if r["repeat"] else ("suspect" if r["suspect"] else "clean")
        print(f"{f.name}  {r['duration']:.1f}s  {status}")
        for h in r["repeat"]:
            print(f"   REPEAT   {h['a0']:.1f}-{h['a1'] + WIN_S:.1f}s  again at {h['b0']:.1f}-{h['b1'] + WIN_S:.1f}s  (sim {h['sim']:.2f})")
        for h in r["suspect"]:
            print(f"   suspect  {h['a0']:.1f}-{h['a1'] + WIN_S:.1f}s  vs {h['b0']:.1f}-{h['b1'] + WIN_S:.1f}s  (sim {h['sim']:.2f}) listen to it")
        sil = silences(f, args.silence_db, args.silence_min)
        if sil:
            print("   deep silences (cut candidates): " + ", ".join(
                f"{a:.2f}-{b:.2f}s" if b is not None else f"{a:.2f}s-end" for a, b, _ in sil))
        bad += bool(r["repeat"])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
