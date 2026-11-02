#!/usr/bin/env python3
"""Join paragraph mp3s into one file, or cut a range out of one paragraph.

  join.py join   trim silence at both ends of each work/pNN.mp3, concat in
                 order with a gap, export final mp3 + wav
  join.py cut    remove time ranges from one paragraph, 10 ms crossfades,
                 always reading the untouched raw file in work/raw/

Needs ffmpeg on PATH.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        sys.exit("ffmpeg failed: " + p.stderr.decode(errors="replace")[-600:])


def duration(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True)
    return float(p.stdout.decode().strip())


def cmd_join(a):
    work = Path(a.work)
    files = sorted(f for f in work.glob("p[0-9][0-9].mp3"))
    if a.only:
        keep = {x.strip() for x in a.only.split(",")}
        files = [f for f in files if f.stem in keep]
    if not files:
        sys.exit("no pNN.mp3 files in " + str(work))
    tdir = work / "trimmed"
    tdir.mkdir(exist_ok=True)
    th = f"{a.trim_db}dB"
    sr = "44100"
    trimmed = []
    for f in files:
        out = tdir / (f.stem + ".wav")
        sil = f"silenceremove=start_periods=1:start_threshold={th}:start_silence=0.03"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(f), "-af", f"{sil},areverse,{sil},areverse",
             "-ac", "1", "-ar", sr, "-c:a", "pcm_s16le", str(out)])
        trimmed.append(out)
    gap = tdir / "gap.wav"
    run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=mono",
         "-t", str(a.gap), "-c:a", "pcm_s16le", str(gap)])
    lst = tdir / "list.txt"
    lines = []
    for i, t in enumerate(trimmed):
        if i:
            lines.append(f"file '{gap.resolve().as_posix()}'")
        lines.append(f"file '{t.resolve().as_posix()}'")
    lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    base = Path(a.out)
    base.parent.mkdir(parents=True, exist_ok=True)
    wav, mp3 = base.with_suffix(".wav"), base.with_suffix(".mp3")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c:a", "pcm_s16le", str(wav)])
    run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-c:a", "libmp3lame", "-q:a", "2", str(mp3)])
    print(f"joined {len(files)} paragraph(s), gap {a.gap}s, {duration(wav):.1f}s total")
    print(f"wrote {mp3} and {wav}")
    print("Now listen to the last 3 seconds of the final file.")


def cmd_cut(a):
    work = Path(a.work)
    raw_dir = work / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw = raw_dir / f"{a.para}.mp3"
    cur = work / f"{a.para}.mp3"
    if not raw.exists():
        if not cur.exists():
            sys.exit(f"{cur} not found")
        shutil.copyfile(cur, raw)  # first cut: keep the untouched file as raw
        print(f"saved raw copy {raw}")
    cuts = sorted((float(s), float(e)) for s, e in a.cut)
    for s, e in cuts:
        if e <= s:
            sys.exit("each cut needs END greater than START")
    total = duration(raw)
    segs, pos = [], 0.0
    for s, e in cuts:
        segs.append((pos, s))
        pos = e
    segs.append((pos, None))
    cf = a.crossfade
    parts = []
    for i, (s, e) in enumerate(segs):
        trim = f"atrim=start={s}" + (f":end={e}" if e is not None else "")
        parts.append(f"[0:a]{trim},asetpts=PTS-STARTPTS[s{i}]")
    chain, last = [], "s0"
    for i in range(1, len(segs)):
        nxt = f"x{i}"
        chain.append(f"[{last}][s{i}]acrossfade=d={cf}:c1=tri:c2=tri[{nxt}]")
        last = nxt
    fc = ";".join(parts + chain)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-filter_complex", fc,
         "-map", f"[{last}]", "-c:a", "libmp3lame", "-q:a", "2", str(cur)])
    print(f"{a.para}: {total:.2f}s -> {duration(cur):.2f}s, removed {len(cuts)} range(s); raw untouched")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd")
    j = sub.add_parser("join", help="trim, concat with gaps, export mp3 + wav")
    j.add_argument("--work", default="work")
    j.add_argument("--out", default="work/final", help="output base path, .mp3 and .wav are added (default work/final)")
    j.add_argument("--gap", type=float, default=0.45, help="seconds of silence between paragraphs (default 0.45)")
    j.add_argument("--trim-db", type=float, default=-45, help="silence threshold for trimming ends (default -45)")
    j.add_argument("--only", help="comma list of paragraph ids to include")
    j.set_defaults(fn=cmd_join)
    c = sub.add_parser("cut", help="remove time ranges from one paragraph")
    c.add_argument("para", help="paragraph id, e.g. p03")
    c.add_argument("--cut", nargs=2, action="append", required=True, metavar=("START", "END"),
                   help="range to remove in seconds, repeat for several")
    c.add_argument("--crossfade", type=float, default=0.010, help="crossfade seconds (default 0.010)")
    c.add_argument("--work", default="work")
    c.set_defaults(fn=cmd_cut)
    a = ap.parse_args()
    if not a.cmd:
        ap.print_help()
        sys.exit(2)
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a.fn(a)


if __name__ == "__main__":
    main()
