from __future__ import annotations
import base64, os, re
from pathlib import Path
import requests

def generate_gemini_image(prompt: str, destination: Path, model: str) -> Path:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it under GitHub Settings > Secrets and variables > Actions.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt + " Create one documentary still photograph, landscape 16:9, no captions, no watermark."}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
    }
    response = requests.post(url, params={"key": api_key}, json=payload, timeout=180)
    if response.status_code >= 400:
        raise RuntimeError(f"Gemini image request failed ({response.status_code}): {response.text[:1500]}")
    data = response.json()
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime = inline.get("mimeType", inline.get("mime_type", "image/png"))
                ext = ".jpg" if "jpeg" in mime else ".png"
                destination = destination.with_suffix(ext)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(base64.b64decode(inline["data"]))
                return destination
    raise RuntimeError("Gemini returned no image bytes. Check the configured image model and API access.")

def resolve_scene_images(storyboard: dict, photos_dir: Path, generated_dir: Path, model: str) -> list[Path]:
    photos_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, scene in enumerate(storyboard["scenes"], 1):
        supplied = scene.get("image")
        if supplied:
            p = Path(supplied)
            if not p.is_absolute():
                p = Path.cwd() / p
            if not p.is_file():
                raise FileNotFoundError(f"Scene {index}: image not found: {p}")
            paths.append(p)
            continue
        prompt = scene.get("image_prompt", "").strip()
        if not prompt:
            raise ValueError(f"Scene {index} needs either image or image_prompt.")
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", scene.get("id", f"scene-{index}")).strip("-")
        paths.append(generate_gemini_image(prompt, generated_dir / f"{safe}.png", model))
    return paths
