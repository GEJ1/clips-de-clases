---
name: clips-de-clases
description: Turn recorded classes, talks or webinars (slides + facecam videos) into short clips for social media — LinkedIn, Instagram Reels, YouTube Shorts, TikTok. Transcribes the videos, proposes self-contained fragments with a hook, renders previews, and produces final clips in vertical 9:16 (hook, slide, word-by-word captions, enlarged facecam) and/or horizontal 16:9 with captions, plus a post text adapted to the chosen network. Use when the user asks for clips, highlights, recortes, reels, shorts or fragments of their class/course/talk videos.
---

# Clips de clases para redes

Pipeline: **setup → transcribe → choose candidates → previews → user picks → precise captions → render → post text**.
The mechanical work lives in `scripts/` (tested; do not rewrite ffmpeg commands ad hoc). Your job is the judgment:
choosing fragments, cut points, hooks, caption fixes, and checking in with the user at the checkpoints.

Talk to the user in their language. `SKILL_DIR` below = the directory of this file.

## 0. Setup (once per machine)

```bash
bash SKILL_DIR/scripts/setup.sh
```
Checks ffmpeg (with libass), Python ≥ 3.9, free disk, and creates a venv with faster-whisper in
`~/.cache/clips-de-clases/venv` (override with `CLIPS_VENV`). Whisper models download to `~/.cache/huggingface`
(small ≈ 0.5 GB, medium ≈ 1.5 GB). **If free disk < 3 GB, tell the user before continuing.**

## 1. Project folder

Work inside the folder with the videos. Create `clips/project.json` (see `references/project.example.json`):

```json
{ "videos_dir": "..", "name": "Nombre Apellido", "accent": "B8F000", "language": "es",
  "cam": {"x": 1123, "y": 572, "size": 148}, "clips": [] }
```
- `name`: shown under the facecam in vertical clips (ask the user how they want to appear; omit to hide).
- `accent`: hex colour for highlighted word / hook line / cam ring. Suggest the brand colour you see in the slides.
- `cam`: facecam square in source pixels, or `null` if there is no facecam (see step 4). Per-clip override allowed.
- Displayed cam size (vertical) is **relative to the recorded cam**: `size × cam_zoom` (default 2.7, capped at 460 px).
  A 148 px cam → 400 px. Override with `"cam_zoom": 3.0` or a fixed `"cam_display": 420` (project or per clip).

Layout: `clips/work/` (transcripts, temp), `clips/previews/`, `clips/vertical/`, `clips/horizontal/`.

## 2. Transcribe everything (long: run in background)

```bash
VENV=${CLIPS_VENV:-~/.cache/clips-de-clases/venv}
$VENV/bin/python -I SKILL_DIR/scripts/transcribe.py --out clips/work/transcripts --model small --lang es *.mp4
```
- Use `run_in_background`. Speed on CPU with `small`: roughly 2× real time on 8 cores, slower if the machine is busy.
  Tell the user the total video duration and a realistic estimate.
- It prints `ALL DONE` at the end. To wait, use a background command that waits **on the PID** or greps the log for
  `ALL DONE`; never `pgrep -f transcribe.py` inside a loop whose own command line contains that string (it matches itself
  and never exits).
- Files finished early (`DONE <stem>`) can be read while the rest runs — start reading them to save time.

## 3. Choose 10–12 candidates

Read the `.txt` transcripts fully. Criteria in `references/criterios.md` — short version: **self-contained, hook in the
first 3 s, one idea, 30–90 s, clear ending, valuable to someone who never took the course.** Prefer real cases,
myths/counterintuitive claims, analogies, practical advice, and what is unique to the speaker (their research, field).

For exact cut points use the word timestamps:
```bash
python3 SKILL_DIR/scripts/words.py clips/work/transcripts/<stem>.json 09:15 09:30
```
Start on the first word of the idea (drop leading "Bueno,", "Entonces,"); end right after the closing sentence.
Avoid moments that reference the course ("como vimos antes", "en la próxima unidad", "pausen el video") or on-screen
actions ("me corro para que vean"). A clip may join 2 parts of the same video (`parts` list) if each part is clean.

Add each candidate to `clips` in project.json:
```json
{"id": "08_hospital", "source": "modulo3.mp4", "parts": [["11:17.6", "12:28.0"]],
 "title": "El modelo aprendió a reconocer el hospital"}
```

## 4. Locate the facecam (if any)

```bash
python3 SKILL_DIR/scripts/frame.py grid  <video> 300 clips/work/grid.png        # labelled 50px grid → read the image
python3 SKILL_DIR/scripts/frame.py crop  <video> 300 X Y SIZE clips/work/cam.png  # check the square is centred on the cam
python3 SKILL_DIR/scripts/frame.py sheet <video> X Y SIZE clips/work/sheet.png    # 10/50/90 % — does it move?
```
Check **every source video used** — the cam can differ between recordings (or move mid-video). Use a per-clip `cam`
override when it does. The cam is upscaled ~2.7× by default, so it will look a bit soft; mention it once.
If the recorded cam is small (< ~110 px, displayed < 300 px), `render.py` prints an AVISO: ask the user whether they
prefer it smaller and sharper, or bigger (`cam_zoom` 3–3.2) and softer.

## 5. Previews → user picks

```bash
python3 SKILL_DIR/scripts/cut.py --project clips            # all clips (also writes clips/indice.txt)
python3 SKILL_DIR/scripts/cut.py --project clips 08_hospital  # just one
```
Previews keep the original aspect ratio, cuts snap to word boundaries, audio is cleaned and normalised.
**Check the printed first/last words** of every clip and that every line ends in `OK` (audio length == video length);
fix `parts` and re-run if a clip starts/ends mid-sentence.

Present a table (id, duration, hook, why it works), mark your 2–3 favourites, and share the previews
(send the files if the user is remote). **Checkpoint: the user picks the clips.** Then ask which **format** they want
for each: vertical 9:16 (Reels/Shorts/TikTok, also fine on LinkedIn), horizontal 16:9 with captions
(LinkedIn/YouTube/web), or both — set `"formats": ["vertical", "horizontal"]` per clip. Ask where they will post.

## 6. Precise captions

```bash
python3 SKILL_DIR/scripts/render.py --project clips --text 08_hospital 10_accuracy
```
Re-transcribes the chosen previews with `medium` (≈ 1× real time) and prints the caption text. Read it and fix
mis-heard words — especially technical terms, English terms in Spanish speech, names and paper authors (check them
against what the slide shows). Add fixes to the clip; tokens must match exactly, including punctuation:
```json
"fixes": [["cure así", "accuracy"], ["escuria.", "espuria."], ["Jay", "Ye"]]
```
Re-run `--text` to confirm. Show the user any non-obvious correction.

## 7. Render

Write a hook for each vertical clip: 2 lines, ≤ 26 characters each; line 2 is highlighted with the accent colour.
A question or a counterintuitive claim works best (`["La IA que detectaba cáncer…", "reconocía el hospital"]`).
```bash
python3 SKILL_DIR/scripts/render.py --project clips 08_hospital 10_accuracy          # formats from project.json
python3 SKILL_DIR/scripts/render.py --project clips --format both 08_hospital        # override
```
Horizontal: `"subtitles": false` in a clip renders it without captions.
**Verify**: every line ends in `OK`; extract one frame per clip and look at it
(`ffmpeg -ss 20 -i clips/vertical/X_vertical.mp4 -frames:v 1 -vf scale=540:-1 frame.png`): hook fits, captions don't
overlap the slide or cam, the small original cam is hidden, nothing is cut off.
**After the first vertical clip, send it (or a frame) and ask the user if the cam size looks right**; adjust
`cam_zoom`/`cam_display` for the project before rendering the rest. You cannot hear audio — ask the user to
confirm it sounds right.

## 8. Post text

For each clip write a post adapted to the network the user chose (LinkedIn: 1st line = hook, short paragraphs,
one takeaway, a question to invite comments, 3–5 hashtags; Instagram/TikTok: shorter caption). Same language and tone
as the speaker; first person; no invented facts beyond what the clip says.

## Gotchas learned the hard way
- **Audio**: never use single-pass `loudnorm` on a quiet recording (it pumps and outputs 96/192 kHz). `cut.py` measures
  loudness and applies a fixed gain + limiter, resamples to 48 kHz and regenerates audio timestamps
  (`asetpts=N/SR/TB`). Without that, concatenated audio had broken timestamps → choppy playback. Don't change it.
- Metadata durations can lie; the scripts verify the *decoded* audio length. Trust their `OK/ERROR` line.
- Whisper `small` is fine for choosing clips but makes many caption errors; always use `medium` (step 6) for captions.
- Low disk: models + venv need ~2.5 GB. Offer to delete `~/.cache/huggingface` models when done.
- Files with accents/spaces in names are fine (scripts pass paths as arguments; ffmpeg runs `ass` from the work dir).
