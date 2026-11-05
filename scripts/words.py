"""Print words with timestamps in a time range, to choose exact cut points.

Usage: python3 words.py TRANSCRIPT.json FROM TO      (FROM/TO as mm:ss, hh:mm:ss or seconds)
Output: one line per word: 'start-end  word', plus a mark '  <pausa X.Xs>' for gaps >= 0.4 s.
"""
import json, sys


def secs(x):
    p = [float(v) for v in str(x).split(":")]
    r = 0.0
    for v in p: r = r * 60 + v
    return r


d = json.load(open(sys.argv[1]))
a, b = secs(sys.argv[2]), secs(sys.argv[3])
prev = None
for seg in d:
    for w in seg["words"]:
        if a <= w["s"] <= b:
            if prev is not None and w["s"] - prev >= 0.4:
                print(f"            <pausa {w['s']-prev:.1f}s>")
            print(f"{w['s']:8.2f}-{w['e']:.2f}  {w['w'].strip()}")
            prev = w["e"]
