"""Cut preview clips (original aspect ratio) from project.json, snapped to word boundaries.

Usage: python3 cut.py [--project clips] [ID ...]
- Each part [start, end] is snapped: starts just before the first word that begins >= start-0.3,
  ends just after the last word that ends <= end+0.15, never bleeding into the neighbouring words.
- Audio: highpass + light denoise + fixed gain to -16 LUFS (measured) + limiter, 48 kHz, timestamps regenerated.
- Verifies decoded audio length == video length (a mismatch means choppy/cut audio).
Writes <project>/previews/<id>.mp4 and <project>/indice.txt
"""
import argparse, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_project, secs, words_of, duration, decoded_audio_seconds

ap = argparse.ArgumentParser()
ap.add_argument("--project", default="clips")
ap.add_argument("ids", nargs="*")
a = ap.parse_args()
P = load_project(a.project)
OUT = os.path.join(P["_dir"], "previews"); os.makedirs(OUT, exist_ok=True)
TR = os.path.join(P["_dir"], "work", "transcripts")
PRE = "highpass=f=80,afftdn=nf=-30"


def snap(W, a, b):
    i0 = next(i for i, w in enumerate(W) if w["s"] >= a - 0.3)
    i1 = max(i for i, w in enumerate(W) if w["e"] <= b + 0.15)
    s = W[i0]["s"] - 0.25
    if i0 > 0: s = max(s, (W[i0 - 1]["e"] + W[i0]["s"]) / 2)
    e = W[i1]["e"] + 0.4
    if i1 + 1 < len(W): e = min(e, (W[i1]["e"] + W[i1 + 1]["s"]) / 2)
    return max(s, 0), e, W[i0:i1 + 1]


def ffinputs(src, parts):
    inp = []
    for s, e in parts: inp += ["-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", src]
    return inp


def measure_I(src, parts):
    n = len(parts)
    fc = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1,{PRE},loudnorm=print_format=json"
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *ffinputs(src, parts), "-filter_complex", fc, "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.search(r'"input_i"\s*:\s*"(-?[\d.]+|-inf)"', err)
    return float(m.group(1)) if m and m.group(1) != "-inf" else -30.0


index = []
for c in P["clips"]:
    if a.ids and c["id"] not in a.ids: continue
    src = os.path.join(P["_videos"], c["source"])
    W = words_of(os.path.join(TR, os.path.splitext(c["source"])[0] + ".json"))
    parts = []
    for pa, pb in c["parts"]:
        s, e, ws = snap(W, secs(pa), secs(pb))
        parts.append((s, e))
        txt = " ".join(w["w"] for w in ws)
        print(f"{c['id']} [{s:.2f}-{e:.2f}] {e-s:.0f}s  «{' '.join(txt.split()[:8])} … {' '.join(txt.split()[-8:])}»")
    gain = max(-10.0, min(24.0, -16.0 - measure_I(src, parts)))
    n = len(parts)
    fc = ("".join(f"[{i}:v][{i}:a]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a0];"
          f"[a0]{PRE},volume={gain:.1f}dB,alimiter=limit=0.84:attack=5:release=50:level=false,"
          f"aresample=48000,asetpts=N/SR/TB[a]")
    dst = os.path.join(OUT, c["id"] + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ffinputs(src, parts), "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst], check=True)
    vd, ad = duration(dst), decoded_audio_seconds(dst)
    flag = "OK" if abs(vd - ad) < 0.3 else "ERROR: audio y video no coinciden"
    print(f"  -> {dst}  video {vd:.1f}s audio {ad:.1f}s  ganancia {gain:+.1f} dB  {flag}")
    index.append(f"{c['id']}.mp4 | {c.get('title','')} | {c['source']} " +
                 " + ".join(f"{int(s//60):02d}:{s%60:04.1f}-{int(e//60):02d}:{e%60:04.1f}" for s, e in parts))

if index and not a.ids:
    open(os.path.join(P["_dir"], "indice.txt"), "w").write("\n".join(index) + "\n")
