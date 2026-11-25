# BANNA — AI Photo Documentary Production Studio

BANNA is a Python documentary production system based on the supplied Priyanshu Web Documentary skill. Its delivery target is a 1920×1080, 30 fps MP4 whose duration follows the uploaded narration. It uses still photographs and generated still illustrations only; it does not use stock video clips.

## Current production: The Manhattan Project

The default workflow uses the existing root MP3 and `storyboard.manhattan.json`. The recording is approximately 11 minutes 15 seconds and narrates the Manhattan Project. Original programmatic diagrams cover fission, the Einstein–Szilard letter, Chicago Pile-1, Oak Ridge, Hanford, Los Alamos, Trinity, Hiroshima, Nagasaki and the project's legacy. These are explicitly treated as illustrations, not fabricated archival photographs.

## Production workflow

1. Select an audience profile: Indian/Hindi or USA/US English. Both profiles support Recent News, Historical Documentaries and UFO Documentaries.
2. Research and verify the selected story, then prepare the clean narration script and a scene-by-scene visual plan.
3. Record or generate the narration and provide the MP3/WAV plus the approved `storyboard.json`.
4. Add `GEMINI_API_KEY` and `OPENROUTER_API_KEY` under GitHub Actions secrets. Run **Actions → BANNA API Connection Test** to verify both without printing the keys.
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
- `banna/images.py` — user-provided stills, Wikimedia Commons still-photo fallback and local map panels. Paid Gemini image generation is disabled in free mode.
- `banna/free_photos.py` — searches Wikimedia Commons for public-domain/CC BY/CC BY-SA photographs, filters restrictive licenses and records attribution in `BANNA_photo_sources.json`.
- `banna/gemini_text.py` — Gemini free-tier text drafting.
- `banna/openrouter_review.py` — OpenRouter free-only script review.
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

## Zero-cost API setup

Add these GitHub Actions repository secrets:
- `GEMINI_API_KEY`: Gemini 2.5 Flash free-tier text drafting.
- `OPENROUTER_API_KEY`: OpenRouter free-model routing for script review.

No OpenAI API key is needed. BANNA's OpenRouter adapter accepts only `openrouter/free` or a model ID ending in `:free`, and rejects paid model IDs. Free model availability and quotas can change; OpenRouter's free plan currently lists 50 requests per day and 20 requests per minute for free models. If the free endpoint is unavailable or quota is exhausted, the workflow fails rather than switching to a paid model.

Paid Gemini image generation is disabled. If a scene has no supplied image, BANNA searches Wikimedia Commons for a reusable public-domain or permissively licensed still and saves its license/artist/source attribution. If no suitable photo is found, provide a more specific `photo_search` field or a licensed image. Maps, evidence boards, annotations and transitions are rendered locally. Gemini free text is not the same as free image generation. GitHub Actions also has plan-dependent usage limits, so no hosted service can guarantee unlimited free rendering.

Actions workflows:
- **BANNA API Connection Test** — safely test both API secrets.
- **BANNA Gemini Free Script Draft** — generate a narration draft.
- **BANNA Free Script Review** — review a script using OpenRouter free models only.
- **BANNA Documentary Render** — render a supplied storyboard and voice-over.
- Add only `GEMINI_API_KEY` and `OPENROUTER_API_KEY`; never put keys in source files.

CLI:
```bash
python main.py draft-script --topic "Your topic" --audience "USA audience" --language English --duration 10
python main.py review-script --input script.txt --output output/review.md
python main.py render --storyboard storyboard.json
```

## Verification status

The CI suite runs on GitHub Actions and checks core timing, sound-bed output, storyboard validation, Gemini response parsing (mocked), exact annotation geometry, map image generation, vintage insert encoding, parallel chunk assembly and FFmpeg rendering smoke tests. It also runs a 60-second audio-to-MP4 pipeline integration test using fixture audio and mocked visual-render providers, then verifies 1080p resolution, duration and QC outputs. The render artifact contains the final contact sheet, QC report, word timing JSON and map coordinate-grid inspection images. A real documentary render still requires a story-specific storyboard with supplied/licensed still-photo files or local map panels. The zero-cost renderer does not require image-generation credentials. Final acceptance also requires inspecting the generated QC contact sheet; automated tests do not prove pixel-perfect results for every future story.


## One-minute visual acceptance test

The **BANNA 60-Second Documentary Preview** workflow is a short acceptance render. It uses only the first 60 seconds of the selected narration and the first seven storyboard beats, with one large, individually framed archival photograph per beat. The evidence-board camera crop preserves the 16:9 frame so each selected photo is presented as a distinct full-screen documentary shot rather than a distant thumbnail in a multi-photo collage. The workflow uploads a 1080p MP4 and QC contact sheets. This preview cap is separate from the normal full-length documentary render.
