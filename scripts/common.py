import json, os, subprocess

VENV = os.environ.get("CLIPS_VENV", os.path.expanduser("~/.cache/clips-de-clases/venv"))
HERE = os.path.dirname(os.path.abspath(__file__))


def secs(x):
    if isinstance(x, (int, float)): return float(x)
    r = 0.0
    for v in str(x).split(":"): r = r * 60 + float(v)
    return r


def load_project(pdir):
    p = os.path.join(pdir, "project.json")
    cfg = json.load(open(p))
    cfg["_dir"] = os.path.abspath(pdir)
    cfg["_videos"] = os.path.abspath(os.path.join(pdir, cfg.get("videos_dir", "..")))
    return cfg


def probe(path, entries, stream=None):
    cmd = ["ffprobe", "-v", "error"]
    if stream: cmd += ["-select_streams", stream]
    cmd += ["-show_entries", entries, "-of", "csv=p=0", path]
    return subprocess.check_output(cmd, text=True).strip()


def duration(path):
    return float(probe(path, "format=duration"))


def decoded_audio_seconds(path):
    """Real decoded audio length (catches broken timestamps that metadata hides)."""
    out = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-vn", "-f", "null", "-"], capture_output=True, text=True).stderr
    t = [l for l in out.replace("\r", "\n").split("\n") if "time=" in l]
    if not t: return 0.0
    v = t[-1].split("time=")[1].split()[0]
    return secs(v)


def words_of(transcript_json):
    d = json.load(open(transcript_json))
    return [{"s": w["s"], "e": w["e"], "w": w["w"].strip()} for seg in d for w in seg["words"] if w["w"].strip()]


def apply_fixes(words, fixes):
    """fixes: [["from words", "to words"], ...] — exact token match (punctuation included)."""
    for src, dst in fixes or []:
        src, dst = src.split(), dst.split()
        i = 0
        while i <= len(words) - len(src):
            if [w["w"] for w in words[i:i + len(src)]] == src:
                a, b = words[i]["s"], words[i + len(src) - 1]["e"]
                step = (b - a) / max(len(dst), 1)
                words[i:i + len(src)] = [{"s": a + k * step, "e": a + (k + 1) * step, "w": d} for k, d in enumerate(dst)]
                i += len(dst)
            else:
                i += 1
    return words


def run_transcribe(files, out, model, lang):
    py = os.path.join(VENV, "bin", "python")
    if not os.path.exists(py):
        raise SystemExit(f"No existe el venv {VENV}: correr scripts/setup.sh primero")
    subprocess.run([py, "-I", os.path.join(HERE, "transcribe.py"), "--out", out, "--model", model, "--lang", lang, *files], check=True)
