# BANNA — AI Photo Documentary Production Studio

BANNA is a Python documentary production system based on the supplied Priyanshu Web Documentary skill. Its delivery target is a 1920×1080, 30 fps MP4 whose duration follows the uploaded narration. It uses still photographs and generated still illustrations only; it does not use stock video clips.

## Production workflow

1. Select an audience profile: Indian/Hindi or USA/US English. Both profiles support Recent News, Historical Documentaries and UFO Documentaries.
2. Research and verify the selected story, then prepare the clean narration script and a scene-by-scene visual plan.
3. Record or generate the narration and provide the MP3/WAV plus the approved `storyboard.json`.
4. Add the Gemini API key as a GitHub Actions secret named `GEMINI_API_KEY`.
5. Run **Actions → BANNA Documentary Render**. GitHub-hosted runners perform the rendering; a local GPU is not required.
6. Download the MP4 and the QC contact sheet/report from the workflow artifact.

## Skill-aligned visual direction

- Midnight Navy background, ice-paper cards and Signal Orange (#ff6b00) evidence annotations.
- Five selectable surfaces: Map Board, Paper Press, Scrapbook Dossier, Chalk Case Board and Digital Coda.
- A single large evidence-board world with continuous camera pans, pushes, gentle drift, two-worker parallel rendering and a closing network pullback.
- Archival-grade still photographs, pinned cards, paper labels, connected evidence strings, typed tags and hand-drawn highlight marks.
- Schematic map panels with normalized, validated coordinates and a coordinate-grid inspection helper.
- Cyanotype-blue vintage 2D illustration frames with route graphics, moving silhouettes, film grain and intertitle treatment.
- Synthetic suspense bed, transition whooshes, typing clicks and thuds; voice-over is kept as the timing master and mixed to the final MP4.
- Non-graphic treatment of violent historical events.

The bundled skill's exact-geometry helpers are available in `banna/annotations.py`: `card_anchor`, `make_paper_tracked`, `text_underline_world`, and `text_circle_world`. Map inspection helpers are in `banna/map_board.py`.

## Architecture

- `main.py` — command-line entry point.
- `banna/config.py` — environment-driven configuration and voice-over discovery.
- `banna/audio.py`, `banna/timing.py`, `banna/transcription.py` — media probing, silence detection, optional CPU Whisper word timestamps and spoken-cue alignment. The renderer falls back to silence-based timing if Whisper is unavailable. Scene cues can be aligned to transcribed trigger phrases.
- `banna/images.py` — user-provided stills and Gemini still-image generation.
- `banna/documentary_engine.py` — continuous evidence-board world and camera renderer.
- `banna/annotations.py` — exact paper-line geometry, underlines, circles and orange wobble marks.
- `banna/map_board.py` — coordinate grid and schematic map panels.
- `banna/vintage.py` — cyanotype silent-film-style animated still illustrations and optional storyboard-triggered inserts.
- `banna/sound.py` — synthesized music bed and synchronized editorial SFX.
- `banna/board.py` — audio ducking, loudness normalization and H.264/AAC mux.
- `banna/qc.py` — final resolution/duration validation and contact-sheet extraction.
- `banna/pipeline.py` — production orchestration.
- `tests/` — unit and FFmpeg smoke tests.

## Requirements and local development

Python 3.11+, FFmpeg/FFprobe, Pillow, NumPy, Requests and Faster-Whisper (CPU word alignment; optional at runtime with a silence-based fallback).

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Local rendering:

```bash
copy storyboard.example.json storyboard.json
python main.py render
```

Use `cp` instead of `copy` on macOS/Linux. Put optional user-supplied photos in `media/photos/` and reference their paths in the storyboard.

## Secrets, cost and limits

Never commit API keys. Set `GEMINI_API_KEY` in GitHub → Settings → Secrets and variables → Actions. Image-generation availability, model access, free quota, rate limits and billing are controlled by the provider. GitHub Actions runtime and artifact retention are subject to GitHub plan limits; BANNA does not promise unlimited free usage.

## Verification status

The CI suite runs on GitHub Actions and checks core timing, sound-bed output, storyboard validation, exact annotation geometry, map image generation, vintage insert encoding, parallel chunk assembly and FFmpeg rendering smoke tests. The render artifact also contains the contact sheet, QC report, word timing JSON and map coordinate-grid inspection images. A real documentary render still requires a valid story-specific storyboard and configured image-generation credentials. Final acceptance also requires inspecting the generated QC contact sheet; a green unit-test run alone is not proof that every annotation is pixel-perfect for every future story.
