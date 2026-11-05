#!/usr/bin/env bash
# Checks requirements and creates the Python venv with faster-whisper.
# Usage: setup.sh            (venv in $CLIPS_VENV or ~/.cache/clips-de-clases/venv)
set -euo pipefail
VENV="${CLIPS_VENV:-$HOME/.cache/clips-de-clases/venv}"

ok=1
for b in ffmpeg ffprobe; do
  command -v "$b" >/dev/null || { echo "FALTA: $b (instalar ffmpeg: sudo apt install ffmpeg / brew install ffmpeg)"; ok=0; }
done
filters=$(ffmpeg -hide_banner -filters 2>/dev/null || true)
if command -v ffmpeg >/dev/null && ! grep -q " ass " <<<"$filters"; then
  echo "FALTA: ffmpeg sin libass (no puede quemar subtítulos)"; ok=0
fi
for f in deblock hqdn3d alimiter afftdn; do
  grep -q " $f " <<<"$filters" || { echo "FALTA: filtro $f de ffmpeg (actualizar ffmpeg a >= 4.2)"; ok=0; }
done

PY=""
for c in python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)' 2>/dev/null; then PY=$(command -v "$c"); break; fi
done
[ -z "$PY" ] && { echo "FALTA: Python >= 3.9"; ok=0; }

free_gb=$(df -Pk "$HOME" | awk 'NR==2{printf "%.1f", $4/1048576}')
echo "Disco libre en \$HOME: ${free_gb} GB (modelo small ~0.5 GB, medium ~1.5 GB, venv ~0.5 GB)"

if [ "$ok" = 1 ] && [ ! -x "$VENV/bin/python" ]; then
  echo "Creando venv en $VENV ..."
  mkdir -p "$(dirname "$VENV")"
  if command -v uv >/dev/null; then
    uv venv -q -p "$PY" "$VENV" && uv pip install -q -p "$VENV/bin/python" faster-whisper
  else
    "$PY" -m venv "$VENV" && "$VENV/bin/pip" install -q faster-whisper
  fi
fi
if [ -x "$VENV/bin/python" ]; then
  "$VENV/bin/python" -c "import faster_whisper; print('faster-whisper', faster_whisper.__version__, 'OK en', '$VENV')"
fi
fams=$(fc-list : family 2>/dev/null || true)
grep -qi "^Lato" <<<"$fams" && echo "Fuente: Lato" || echo "Fuente: Lato no está, se usa DejaVu Sans (opcional: instalar fonts-lato)"
[ "$ok" = 1 ] && echo "SETUP OK" || { echo "SETUP INCOMPLETO"; exit 1; }
