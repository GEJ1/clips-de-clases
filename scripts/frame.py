"""Grab frames to locate the facecam.

  python3 frame.py grid VIDEO TIME OUT.png        full frame with a labelled 50 px grid (read it to find the cam)
  python3 frame.py crop VIDEO TIME X Y SIZE OUT.png   crop of the square X,Y,SIZE (to verify the cam box)
  python3 frame.py sheet VIDEO X Y SIZE OUT.png    3 crops at 10%/50%/90% of the video (cam moves?)
"""
import subprocess, sys

FONT = ""
try:
    FONT = subprocess.check_output(["fc-match", "-f", "%{file}", "DejaVu Sans"], text=True)
except Exception:
    pass


def dur(v):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v]))


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


mode = sys.argv[1]
if mode == "grid":
    v, t, out = sys.argv[2], sys.argv[3], sys.argv[4]
    labels = ""
    if FONT:
        parts = []
        for x in range(0, 4000, 100):
            parts.append(f"drawtext=fontfile={FONT}:text='{x}':x={x}+2:y=2:fontsize=14:fontcolor=red:box=1:boxcolor=white@0.7")
            parts.append(f"drawtext=fontfile={FONT}:text='{x}':x=2:y={x}+2:fontsize=14:fontcolor=blue:box=1:boxcolor=white@0.7")
        labels = "," + ",".join(parts)
    ff("-ss", t, "-i", v, "-frames:v", "1", "-vf", "drawgrid=w=50:h=50:t=1:c=red@0.35" + labels, out)
elif mode == "crop":
    v, t, x, y, s, out = sys.argv[2:8]
    ff("-ss", t, "-i", v, "-frames:v", "1", "-vf", f"crop={s}:{s}:{x}:{y},scale=300:300", out)
elif mode == "sheet":
    v, x, y, s, out = sys.argv[2:7]
    d = dur(v)
    ins = []
    for p in (0.1, 0.5, 0.9):
        ins += ["-ss", f"{d*p:.1f}", "-i", v]
    fc = ";".join(f"[{i}:v]crop={s}:{s}:{x}:{y},scale=240:240[c{i}]" for i in range(3)) + ";[c0][c1][c2]hstack=3"
    ff(*ins, "-frames:v", "1", "-filter_complex", fc, out)
print("ok", sys.argv[-1])
