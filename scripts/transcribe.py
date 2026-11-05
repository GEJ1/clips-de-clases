"""Transcribe videos with faster-whisper, word-level timestamps.

Usage: <venv>/bin/python transcribe.py --out DIR [--model small|medium] [--lang es] [--force] FILE...
Writes DIR/<stem>.json (segments with words) and DIR/<stem>.txt ([mm:ss] lines).
Prints progress every minute of audio and one 'DONE <stem>' line per file (flushed).
"""
import argparse, json, os, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--model", default="small")
ap.add_argument("--lang", default="es")
ap.add_argument("--prompt", default="Clase sobre inteligencia artificial y machine learning.")
ap.add_argument("--force", action="store_true")
ap.add_argument("files", nargs="+")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

from faster_whisper import WhisperModel
model = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)

for f in a.files:
    stem = os.path.splitext(os.path.basename(f))[0]
    jp = os.path.join(a.out, stem + ".json")
    if os.path.exists(jp) and not a.force:
        print(f"SKIP {stem} (ya existe)", flush=True); continue
    t0, nxt = time.time(), 60
    segs, info = model.transcribe(f, language=a.lang, word_timestamps=True, vad_filter=True, initial_prompt=a.prompt)
    data = []
    with open(os.path.join(a.out, stem + ".txt"), "w") as txt:
        for s in segs:
            data.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                         "words": [{"s": w.start, "e": w.end, "w": w.word} for w in s.words]})
            m, sec = divmod(int(s.start), 60)
            txt.write(f"[{m:02d}:{sec:02d}] {s.text.strip()}\n"); txt.flush()
            if s.start >= nxt:
                print(f"  {stem}: {int(s.start)//60}/{int(info.duration)//60} min", flush=True); nxt += 60
    json.dump(data, open(jp, "w"), ensure_ascii=False)
    print(f"DONE {stem} ({time.time()-t0:.0f}s)", flush=True)
print("ALL DONE", flush=True)
