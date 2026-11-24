# The Secret Project That Changed the World

A GitHub Actions-based rendering project for the Manhattan Project documentary.

## Current setup

- Target audience: United States
- Narration language: US English
- Visual direction: 1080p evidence-board documentary, archival-paper palette, orange highlights, maps, labels, and restrained camera movement
- The final runtime follows the voice-over duration.

## Add the narration

Upload the final voice-over audio to this repository at:

`assets/voiceover.mp3`

On GitHub, open the repository, choose **Add file → Upload files**, and upload the narration as `assets/voiceover.mp3`. GitHub's regular web uploader has a 25 MB limit; for larger files, use Git LFS or Git from your computer. Do not put private API keys or passwords in the repository.

## Render

The workflow runs when you push changes to `assets/`, `render.py`, or the workflow file. It can also be started from **Actions → Render Documentary → Run workflow**.

The current renderer creates an evidence-board visual draft synchronized to the narration. This is a draft pipeline, not yet the final archival-footage edit: verified archival photographs/film, citations, and any licensed music/SFX still need to be integrated.

When the workflow succeeds, download the MP4 from the run's **Artifacts** section.

## Local development

Python 3.11+ and FFmpeg are required.

```bash
python -m pip install -r requirements.txt
python render.py
```

## Project structure

- `render.py` — creates the 1080p draft and synchronizes narration
- `assets/voiceover.mp3` — narration file to be supplied
- `.github/workflows/render.yml` — cloud render workflow
- `output/` — rendered MP4 (created during rendering)
