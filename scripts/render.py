"""Render final clips from previews, in vertical 9:16 and/or horizontal 16:9.

Usage:
  python3 render.py [--project clips] --text ID ...    transcribe previews with the precise model (if needed) and
                                                        print the caption text (with fixes applied) for review
  python3 render.py [--project clips] [--format vertical|horizontal|both] ID ...
      vertical   -> <project>/vertical/<id>_vertical.mp4   hook on top, slide, word-highlighted captions, enlarged cam
      horizontal -> <project>/horizontal/<id>_horizontal.mp4  original frame + captions at the bottom
                    (set "subtitles": false in the clip to skip captions)
  --format overrides; otherwise each clip's "formats" list in project.json is used (default ["vertical"]).
Per-clip config: hook [line1, line2], fixes [[from, to]], formats, subtitles, optional cam override.
"""
import argparse, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_project, words_of, apply_fixes, duration, decoded_audio_seconds, run_transcribe, probe

ap = argparse.ArgumentParser()
ap.add_argument("--project", default="clips")
ap.add_argument("--text", action="store_true")
ap.add_argument("--format", choices=["vertical", "horizontal", "both"])
ap.add_argument("ids", nargs="+")
a = ap.parse_args()
P = load_project(a.project)
PREV = os.path.join(P["_dir"], "previews")
HQ = os.path.join(P["_dir"], "work", "transcripts_hq")
WORK = os.path.join(P["_dir"], "work"); os.makedirs(WORK, exist_ok=True)
CLIPS = {c["id"]: c for c in P["clips"]}

missing = [i for i in a.ids if i not in CLIPS]
if missing: raise SystemExit(f"IDs no encontrados en project.json: {missing}")
need = [os.path.join(PREV, i + ".mp4") for i in a.ids if not os.path.exists(os.path.join(HQ, i + ".json"))]
if need:
    run_transcribe(need, HQ, P.get("hq_model", "medium"), P.get("language", "es"))

fams = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
HAS_LATO = any(l.startswith("Lato") for l in fams.splitlines())
F_BOLD, F_MED, BOLDFLAG = ("Lato Black", "Lato Semibold", 0) if HAS_LATO else ("DejaVu Sans", "DejaVu Sans", -1)


def ass_color(hexrgb):
    h = hexrgb.lstrip("#").upper(); return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}&"


ACC = ass_color(P.get("accent", "B8F000"))
WHITE = "&H00FFFFFF&"


def ts(x):
    x = max(x, 0); h, r = divmod(x, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def esc(t):
    return t.replace("{", "(").replace("}", ")").replace("\\", "/")


def chunks(words):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 4 or len(" ".join(x["w"] for x in cur)) >= 18 or re.search(r"[.,;:?!…]$", w["w"]):
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out


def layout(src_w, src_h, cam):
    sh = int(round(1080 * src_h / src_w / 2) * 2)
    top = 330
    sb = top + sh
    L = {"slide_h": sh, "slide_y": top, "cap_y": sb + 100}
    if cam:
        cam_y = sb + 352
        size = int(min(460, 1920 - 150 - cam_y))
        L.update(cam_y=cam_y, cam_size=size - size % 2, name_y=cam_y + size + 50)
    else:
        L.update(cap_y=sb + 170, name_y=1920 - 160)
    return L


STYLE_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""


def caption_events(words, dur, y, x=540):
    ev = []
    ch = chunks(words)
    for i, cc in enumerate(ch):
        endc = min(ch[i + 1][0]["s"] if i + 1 < len(ch) else dur, cc[-1]["e"] + 0.8)
        for j, w in enumerate(cc):
            en = cc[j + 1]["s"] if j + 1 < len(cc) else endc
            txt = " ".join((f"{{\\c{ACC}}}{esc(x_['w'])}{{\\c{WHITE}}}" if k == j else esc(x_["w"])) for k, x_ in enumerate(cc))
            ev.append(f"Dialogue: 1,{ts(w['s'])},{ts(en)},Cap,,0,0,0,,{{\\pos({x},{y})}}{txt}")
    return ev


def finish(inputs, fc, dur, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-t", f"{dur:.3f}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "copy", "-movflags", "+faststart", os.path.abspath(dst)], check=True, cwd=WORK)
    vd, ad = duration(dst), decoded_audio_seconds(dst)
    print(f"{dst}  video {vd:.1f}s audio {ad:.1f}s  {'OK' if abs(vd-ad) < 0.3 else 'ERROR: audio y video no coinciden'}")


def horizontal(cid, c, words):
    src = os.path.join(PREV, cid + ".mp4")
    dur = duration(src)
    sw, sh_ = [int(v) for v in probe(src, "stream=width,height", "v:0").split(",")[:2]]
    out = os.path.join(P["_dir"], "horizontal"); os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, cid + "_horizontal.mp4")
    if not c.get("subtitles", True):
        finish(["-i", os.path.abspath(src)], "[0:v]null[v]", dur, dst); return
    fs = int(sh_ * 0.065)
    ass = os.path.join(WORK, cid + "_h.ass")
    open(ass, "w").write(STYLE_HEAD.format(W=sw, H=sh_) +
        f"Style: Cap,{F_BOLD},{fs},&H00FFFFFF,&H00FFFFFF,&H00141414,&H00141414,{BOLDFLAG},0,0,0,100,100,0,0,3,{max(6, fs//4)},0,5,40,40,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" +
        "\n".join(caption_events(words, dur, int(sh_ * 0.88), sw // 2)) + "\n")
    finish(["-i", os.path.abspath(src)], f"[0:v]ass={os.path.basename(ass)}[v]", dur, dst)


def vertical(cid, c, words):
    out = os.path.join(P["_dir"], "vertical"); os.makedirs(out, exist_ok=True)
    src = os.path.join(PREV, cid + ".mp4")
    dur = duration(src)
    sw, sh_ = [int(v) for v in probe(src, "stream=width,height", "v:0").split(",")[:2]]
    cam = c.get("cam", P.get("cam"))
    L = layout(sw, sh_, cam)

    hook = c.get("hook") or [c.get("title", ""), ""]
    hsize = lambda t: int(min(70, 70 * 26 / max(len(t), 1)))
    ev = [f"Dialogue: 0,{ts(0)},{ts(dur)},Hook,,0,0,0,,{{\\pos(540,120)\\fs{hsize(hook[0])}}}{esc(hook[0])}"]
    if len(hook) > 1 and hook[1]:
        ev.append(f"Dialogue: 0,{ts(0)},{ts(dur)},Hook,,0,0,0,,{{\\pos(540,215)\\fs{hsize(hook[1])}\\c{ACC}}}{esc(hook[1])}")
    if P.get("name"):
        ev.append(f"Dialogue: 0,{ts(0)},{ts(dur)},Name,,0,0,0,,{{\\pos(540,{L['name_y']})}}{esc(P['name'])}")
    ev += caption_events(words, dur, L["cap_y"])
    ass = os.path.join(WORK, cid + ".ass")
    open(ass, "w").write(STYLE_HEAD.format(W=1080, H=1920) + f"""Style: Cap,{F_BOLD},74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,{BOLDFLAG},0,0,0,100,100,0,0,1,5,2,5,60,60,0,1
Style: Hook,{F_BOLD},70,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,{BOLDFLAG},0,0,0,100,100,0,0,1,0,0,5,30,30,0,1
Style: Name,{F_MED},40,&H00BBBBBB,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")

    inputs = ["-i", os.path.abspath(src)]
    fc = f"color=c=0x111111:s=1080x1920:r=30:d={dur:.3f}[bg];"
    if cam:
        x, y, s = int(cam["x"]), int(cam["y"]), int(cam["size"])
        C = L["cam_size"]
        bx, by = max(x - 8, 0), max(y - 8, 0)
        bw, bh = min(sw - 5, x + s + 8) - bx, min(sh_ - 4, y + s + 8) - by
        mask = os.path.join(WORK, f"mask{C}.png")
        if not os.path.exists(mask):
            r = C / 2
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=black:s={C}x{C}", "-vf",
                            f"format=gray,geq=lum='255*clip(({r-1}-hypot(X-{r},Y-{r}))*1.5,0,1)'", "-frames:v", "1", mask], check=True)
        inputs += ["-loop", "1", "-i", mask, "-loop", "1", "-i", mask]
        R = C + 12
        fc += (f"[0:v]split[a][b];"
               f"[a]drawbox=x={bx}:y={by}:w={bw}:h={bh}:color=white:t=fill,scale=1080:{L['slide_h']}[slide];"
               f"[b]crop={s}:{s}:{x}:{y},scale={C}:{C}:flags=lanczos,unsharp=5:5:0.6,format=rgba[c0];"
               f"[1:v]format=gray[m];[c0][m]alphamerge[cam];"
               f"color=c=0x{P.get('accent','B8F000').lstrip('#')}:s={R}x{R}:r=30:d={dur:.3f},format=rgba[r0];"
               f"[2:v]scale={R}:{R},format=gray[m2];[r0][m2]alphamerge[ring];"
               f"[bg][slide]overlay=0:{L['slide_y']}[t1];[t1][ring]overlay={540-R//2}:{L['cam_y']-6}[t2];"
               f"[t2][cam]overlay={540-C//2}:{L['cam_y']}:shortest=1[t3];[t3]ass={os.path.basename(ass)}[v]")
    else:
        fc += f"[0:v]scale=1080:{L['slide_h']}[slide];[bg][slide]overlay=0:{L['slide_y']}:shortest=1[t3];[t3]ass={os.path.basename(ass)}[v]"
    finish(inputs, fc, dur, os.path.join(out, cid + "_vertical.mp4"))


for cid in a.ids:
    c = CLIPS[cid]
    words = apply_fixes(words_of(os.path.join(HQ, cid + ".json")), c.get("fixes"))
    if a.text:
        print(f"== {cid}\n" + " ".join(w["w"] for w in words) + "\n"); continue
    fmts = {"both": ["vertical", "horizontal"]}.get(a.format, [a.format] if a.format else c.get("formats", ["vertical"]))
    for f in fmts:
        (vertical if f == "vertical" else horizontal)(cid, c, words)
