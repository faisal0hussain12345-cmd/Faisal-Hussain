from __future__ import annotations
import base64, hashlib, os, re, time
from pathlib import Path
import requests
from PIL import Image
from .map_board import render_map_panel, annotate_map_image, draw_coordinate_grid
from .free_photos import download_commons_photo
from .titanic_graphics import render_titanic_graphic
from .manhattan_graphics import render_manhattan_graphic

def generate_gemini_image(prompt: str, destination: Path, model: str) -> Path:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it under GitHub Settings > Secrets and variables > Actions.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt + " Create one highly realistic archival documentary still photograph in landscape 16:9. Preserve period-accurate objects, architecture, clothing and lighting. Editorial silver-gelatin archival finish where historically appropriate; natural documentary realism, fine film grain, clear subject separation. No captions, no typography, no watermark, no collage, no video frames."}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}
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

def resolve_scene_images(storyboard: dict, photos_dir: Path, generated_dir: Path, model: str, image_generation_enabled: bool = False) -> list[Path]:
    photos_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    source_records = []
    project_name = str((storyboard.get("project") or {}).get("name") or "")
    for scene in storyboard["scenes"]:
        scene["project_name"] = project_name
    used_sources: set[str] = set()
    used_image_hashes: set[str] = set()
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
        graphic_type = scene.get("graphic_type")
        if graphic_type and not scene.get("photo_search"):
            raise ValueError(
                f"Scene {scene.get('id', index)} uses graphic_type without photo_search. "
                "For this photographic documentary, each beat must resolve to a distinct archival still."
            )
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
        if cached:
            paths.append(cached)
        elif image_generation_enabled:
            paths.append(generate_gemini_image(prompt, generated_dir / f"{safe}.png", model))
        else:
            # Zero-cost default: search topic-specific LOC/Wikimedia archival records and preserve attribution.
            commons_path = generated_dir / f"{safe}_commons.jpg"
            source = download_commons_photo(scene, commons_path, used_sources)
            source_page = str(source.get("source_page") or "")
            image_url = str(source.get("image_url") or "")
            image_hash = hashlib.sha256(commons_path.read_bytes()).hexdigest()
            if (not source_page or source_page in used_sources or
                    (image_url and image_url in used_sources) or image_hash in used_image_hashes):
                raise RuntimeError(f"Duplicate or untraceable archival image for scene {scene.get('id', safe)}.")
            used_sources.add(source_page)
            used_image_hashes.add(image_hash)
            if image_url:
                used_sources.add(image_url)
            paths.append(commons_path)
            source_records.append({"scene_id": scene.get("id", safe), **source})
    if source_records:
        import json
        (generated_dir / 'BANNA_photo_sources.json').write_text(
            json.dumps(source_records, ensure_ascii=False, indent=2), encoding='utf-8'
        )
    return paths
