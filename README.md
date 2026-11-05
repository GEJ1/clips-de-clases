# clips-de-clases — skill de Claude Code

Convierte videos de clases, charlas o webinars (slides + cámara) en clips cortos para redes:
vertical 9:16 (Reels, Shorts, TikTok, LinkedIn) y/o horizontal 16:9 con subtítulos.

## Instalación
1. Clonar el repo en la carpeta de skills de Claude Code:
   ```bash
   git clone https://github.com/GEJ1/clips-de-clases.git ~/.claude/skills/clips-de-clases
   ```
   (o en `.claude/skills/clips-de-clases` dentro de un proyecto, para usarla solo ahí).
2. Requisitos: [Claude Code](https://claude.com/claude-code), `ffmpeg` (con libass; el paquete de apt/brew lo trae),
   Python ≥ 3.9 y ~3 GB libres de disco (modelos de transcripción).
3. Opcional: fuente Lato (`sudo apt install fonts-lato`) para que los subtítulos queden como en el ejemplo.

## Uso
Abrir Claude Code en la carpeta de los videos y pedir, por ejemplo:
> "Sacá clips para redes de los videos de esta carpeta"

Claude va a: instalar lo necesario (la primera vez), transcribir los videos, proponer 10–12 fragmentos con previews,
y — una vez que elijas — preguntarte el formato, corregir los subtítulos y renderizar los finales, con el texto del post.

Todo queda en `clips/` dentro de la carpeta de videos: `previews/`, `vertical/`, `horizontal/` e `indice.txt`.
La transcripción es lenta en computadoras sin GPU (≈ media hora por hora de video).
