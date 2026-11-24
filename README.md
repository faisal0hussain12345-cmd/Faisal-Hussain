# BANNA — AI Photo Documentary Production Studio

BANNA is a Python-based, photo-only documentary renderer. It follows the supplied Priyanshu Web Documentary skill's visual direction: midnight-navy evidence board, ice-paper photo cards, Signal Orange annotations, camera movement, vintage-inspired inserts, and narration-led sound design.

## Audience and story workflow

- **Hindi / Indian audience** — Hindi narration and India-relevant story selection.
- **USA audience** — US English narration and US-relevant story selection.

Each profile supports **Recent News**, **Historical Documentaries**, and **UFO Documentaries**. Research and script preparation happen before rendering; the renderer starts when the voice-over and a story-specific `storyboard.json` are ready.

## Rendering architecture

Python 3.11+, FFmpeg/FFprobe, Pillow, NumPy and Requests. Gemini image generation is accessed through `GEMINI_API_KEY`. GitHub Actions performs cloud rendering so the user's 8 GB laptop is not required to render 1080p.

The final MP4 runtime follows the voice-over duration. Scene boundaries are distributed across narration and nudged toward detected silence boundaries. Visuals are still photographs only; movement comes from Ken Burns zoom/pan and evidence-board composition. No stock video clips are used.

## Repository layout

- `main.py` — command-line entry point
- `banna/config.py` — runtime configuration and voice-over discovery
- `banna/audio.py` — duration probing, silence detection and scene timing
- `banna/images.py` — supplied-photo handling and Gemini still-image generation
- `banna/board.py` — evidence-board cards, camera movement, FFmpeg rendering and audio mux
- `banna/pipeline.py` — end-to-end orchestration
- `storyboard.example.json` — starter storyboard
- `media/photos/` — optional user-supplied still photographs
- `output/` — final MP4 artifact

## Prepare a documentary

1. Copy `storyboard.example.json` to `storyboard.json`.
2. Set audience, language, category, title and source notes in project metadata.
3. Add scenes. Each scene needs either an `image` path to a supplied still or a detailed `image_prompt` for Gemini.
4. Keep image prompts factual, period-aware and non-graphic.
5. Add `GEMINI_API_KEY` under GitHub → Settings → Secrets and variables → Actions. Never commit API keys.
6. Run Actions → BANNA Documentary Render → Run workflow, then download the MP4 artifact.

A root-level MP3/WAV voice-over is discovered automatically. Set `BANNA_VOICEOVER` to select another file.

## Local run

Install FFmpeg and Python 3.11+, then:

```bash
python -m pip install -r requirements.txt
copy storyboard.example.json storyboard.json
python main.py render
```

Use `cp` instead of `copy` on macOS/Linux.

## API cost and limits

The Python renderer does not need a paid local GPU. Gemini image generation is a separate API service: availability, free quota, rate limits and billing depend on the Google AI account and model access. GitHub Actions minutes and artifact retention are subject to GitHub plan limits. BANNA does not promise unlimited free generation or cloud rendering.

## Implementation status

This is the first working application core: still-photo scene cards, motion, narration-length timing and MP4 muxing. Advanced skill features—precision map pins/strings, word-level annotation timing, custom vintage 2D action inserts, layered SFX cue authoring and automated contact-sheet QC—remain further engineering work and are not claimed as complete.