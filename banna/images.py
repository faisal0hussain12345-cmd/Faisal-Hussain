from __future__ import annotations
import base64, os, re, time
from pathlib import Path
import requests
from PIL import Image
from .map_board import render_map_panel, annotate_map_image, draw_coordinate_grid

def generate_gemini_image(prompt: str, destination: Path, model: str) -> Path:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it under GitHub Settings > Secrets and variables > Actions.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt + " Create one documentary still photograph, landscape 16:9, no captions, no watermark."}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
    }
    response = None
    for attempt in range(3):
        try:
            response = requests.post(url, params={"key": api_key}, json=payload, timeout=180)
            if response.status_code < 500 and response.status_code != 429:
                break
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
    if response is None or response.status_code >= 400:
        detail = response.text[:1500] if response is not None else "No response from image service"
        code = response.status_code if response is not None else "network error"
        raise RuntimeError(f"Gemini image request failed ({code}): {detail}")
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
        if scene.get("map_image") or scene.get("map_locations"):
            map_title=str(scene.get("map_title") or scene.get("title") or "LOCATION EVIDENCE")
            locations=scene.get("map_locations",[])
            if scene.get("map_image"):
                base_path=Path(scene["map_image"])
                if not base_path.is_absolute(): base_path=Path.cwd()/base_path
                if not base_path.is_file(): raise FileNotFoundError(f"Scene {index}: map image not found: {base_path}")
                panel=annotate_map_image(Image.open(base_path),map_title,locations)
            else:
                panel=render_map_panel(map_title,locations)
            safe_map=re.sub(r"[^a-zA-Z0-9_-]+","-",scene.get("id",f"map-{index}")).strip("-")
            map_path=generated_dir/f"{safe_map}_map.png"
            panel.save(map_path)
            draw_coordinate_grid(panel).save(generated_dir/f"{safe_map}_map_grid.jpg",quality=92)
            paths.append(map_path)
            continue
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
        cached = next((p for p in (generated_dir / f"{safe}.png", generated_dir / f"{safe}.jpg", generated_dir / f"{safe}.jpeg") if p.is_file()), None)
        paths.append(cached or generate_gemini_image(prompt, generated_dir / f"{safe}.png", model))
    return paths
