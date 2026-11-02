#!/usr/bin/env python3
"""Detect looped / duplicated stretches in generated mp3 files.

Decodes each file with ffmpeg to 16 kHz mono, computes a MFCC vector per
10 ms frame, and looks for diagonal stripes: stretches of at least 1.2 s that
come back 1.5 to 12 s later.
  >= 0.72           -> REPEAT  (known real loops scored 0.80 to 0.83)
  0.64 to 0.72      -> SUSPECT (clean takes scored up to 0.62)
Also lists deep silences (below -60 dB, 0.25 s or longer) as cut candidates.

Every SUSPECT needs your ears. A script that really says the same phrase
twice will also show up, so check hits against the text.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SR = 16000
HOP = 160            # 10 ms frames
WIN_S = 1.2          # a match must hold for this long along the diagonal
MIN_OFF, MAX_OFF = 1.5, 12.0


def decode(path):
    import numpy as np
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode(errors="replace")[:300])
    return np.frombuffer(p.stdout, dtype=np.float32)


def frames(y):
    """Unit-norm MFCC vector per 10 ms frame, plus a voiced mask."""
    import librosa
    import numpy as np
    mf = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=20, hop_length=HOP, n_fft=512)[1:]  # drop c0
    mf = (mf - mf.mean(axis=1, keepdims=True)) / (mf.std(axis=1, keepdims=True) + 1e-8)
    F = mf / (np.linalg.norm(mf, axis=0, keepdims=True) + 1e-8)
    rms = librosa.feature.rms(y=y, hop_length=HOP, frame_length=512)[0][:F.shape[1]]
    return F, rms > 0.01


def merge(hits, t_gap=0.6, lag_gap=0.3):
    """hits: (t, lag, sim). Group hits that sit on the same stripe."""
    hits.sort()
    out = []
    for t, lag, s in hits:
        for o in out:
            if t - o["t1"] <= t_gap and abs(lag - o["lag"]) <= lag_gap:
                o["t1"] = t
                if s > o["sim"]:
                    o["sim"], o["lag"] = s, lag
                break
        else:
            out.append({"t0": t, "t1": t, "lag": lag, "sim": s})
    return sorted(out, key=lambda o: o["t0"])


def scan_file(path, rep_thr, sus_thr, max_off=None):
    """Diagonal-stripe search on a frame-level self-similarity matrix.

    A loop is the same audio again L seconds later, so frame t matches frame
    t+L for a whole stretch. For every lag L (1.5 to 12 s) we average the
    frame similarity over a sliding 1.2 s run. Frame level (not window
    vectors) keeps re-spoken copies with small timing drift from slipping
    through. Calibrated on real Eleven v4 Burmese takes: three known loops
    scored 0.80 to 0.83, clean takes 0.37 to 0.62.
    """
    import numpy as np
    y = decode(path)
    dur = len(y) / SR
    res = {"duration": dur, "repeat": [], "suspect": []}
    F, act = frames(y)
    n, W = F.shape[1], int(WIN_S * SR / HOP)
    lo, hi = int(MIN_OFF * SR / HOP), int((max_off or MAX_OFF) * SR / HOP)
    k = np.ones(W)
    rep, sus = [], []
    for L in range(lo, min(hi, n - W) + 1):
        d = np.einsum("ij,ij->j", F[:, :n - L], F[:, L:])
        a = (act[:n - L] & act[L:]).astype(float)
        den = np.convolve(a, k, "valid")
        m = np.where(den > W * 0.6, np.convolve(d * a, k, "valid") / np.maximum(den, 1), 0.0)
        for i in np.flatnonzero(m > sus_thr)[::5]:  # every 50 ms is enough
            hit = (i * HOP / SR, L * HOP / SR, float(m[i]))
            (rep if m[i] > rep_thr else sus).append(hit)
    res["repeat"] = merge(rep)
    rep_spans = [(o["t0"], o["t1"] + o["lag"] + WIN_S) for o in res["repeat"]]
    res["suspect"] = [o for o in merge(sus)
                      if not any(a <= o["t0"] <= b for a, b in rep_spans)]
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
    ap.add_argument("--repeat", type=float, default=0.72, help="stripe similarity for REPEAT (default 0.72)")
    ap.add_argument("--suspect", type=float, default=0.64, help="lower bound for SUSPECT (default 0.64)")
    ap.add_argument("--max-offset", type=float, default=MAX_OFF,
                    help="look this many seconds back for a repeat (default 12; use 60+ on a long single take, it is slower)")
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
        r = scan_file(f, args.repeat, args.suspect, args.max_offset)
        status = "REPEAT" if r["repeat"] else ("suspect" if r["suspect"] else "clean")
        print(f"{f.name}  {r['duration']:.1f}s  {status}")
        for h in r["repeat"]:
            a0, a1 = h["t0"], h["t1"] + WIN_S
            print(f"   REPEAT   {a0:.1f}-{a1:.1f}s  said again at {a0 + h['lag']:.1f}-{a1 + h['lag']:.1f}s  (sim {h['sim']:.2f})")
        for h in r["suspect"]:
            a0, a1 = h["t0"], h["t1"] + WIN_S
            print(f"   suspect  {a0:.1f}-{a1:.1f}s  vs {a0 + h['lag']:.1f}-{a1 + h['lag']:.1f}s  (sim {h['sim']:.2f}) listen to it")
        sil = silences(f, args.silence_db, args.silence_min)
        if sil:
            print("   deep silences (cut candidates): " + ", ".join(
                f"{a:.2f}-{b:.2f}s" if b is not None else f"{a:.2f}s-end" for a, b, _ in sil))
        bad += bool(r["repeat"])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
