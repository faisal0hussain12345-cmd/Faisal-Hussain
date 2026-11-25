from __future__ import annotations

import re
from pathlib import Path
import requests
from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "BANNA-DocumentaryStudio/1.0 (personal documentary project)"}


def _plain(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("value", "")).strip()
    return str(value or "").strip()


def _allowed_license(ext: dict) -> tuple[bool, str]:
    license_name = _plain(ext.get("LicenseShortName"))
    terms = _plain(ext.get("UsageTerms"))
    normalized = (license_name + " " + terms).lower()
    if "public domain" in normalized or "cc0" in normalized or "cc zero" in normalized:
        return True, license_name or terms or "Public domain"
    if ("cc by" in normalized or "creative commons attribution" in normalized) and not any(
        marker in normalized for marker in ("nc", "noncommercial", "nd", "no derivatives")
    ):
        return True, license_name or terms
    return False, license_name or terms or "Unknown license"


def _query_for_scene(scene: dict) -> str:
    explicit = str(scene.get("photo_search") or "").strip()
    if explicit:
        return explicit[:180]
    parts = [str(scene.get("title") or ""), str(scene.get("narration_cue") or "")]
    query = " ".join(part for part in parts if part).strip()
    query = re.sub(r"[^\w\s'-]", " ", query)
    query = re.sub(r"\s+", " ", query).strip()
    return query[:180] or "historical documentary photograph"


def download_commons_photo(scene: dict, destination: Path) -> dict:
    """Find a reusable Wikimedia Commons still and preserve attribution metadata."""
    query = _query_for_scene(scene)
    prompt_hint = str(scene.get("image_prompt") or "").strip()
    prompt_hint = re.sub(r"[^\w\s'-]", " ", prompt_hint)
    prompt_hint = re.sub(r"\s+", " ", prompt_hint).strip()[:100]
    queries = [query]
    if not scene.get("photo_search") and prompt_hint and prompt_hint.lower() not in query.lower():
        queries.append(prompt_hint)

    for active_query in queries:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {active_query}",
            "gsrnamespace": 6,
            "gsrlimit": 12,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 1920,
            "format": "json",
            "formatversion": 2,
        }
        response = requests.get(API, params=params, headers=HEADERS, timeout=45)
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", [])
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            ext = info.get("extmetadata") or {}
            allowed, license_name = _allowed_license(ext)
            image_url = info.get("thumburl") or info.get("url")
            if not allowed or not image_url:
                continue
            image_response = requests.get(image_url, headers=HEADERS, timeout=60, stream=True)
            image_response.raise_for_status()
            content_type = image_response.headers.get("Content-Type", "").lower()
            if not content_type.startswith("image/"):
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            total = 0
            with destination.open("wb") as output:
                for chunk in image_response.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > 25 * 1024 * 1024:
                        break
                    output.write(chunk)
            if total > 25 * 1024 * 1024 or not destination.is_file() or destination.stat().st_size == 0:
                destination.unlink(missing_ok=True)
                continue
            try:
                with Image.open(destination) as im:
                    im.verify()
                with Image.open(destination) as im:
                    im.convert("RGB").save(destination, format="JPEG", quality=92, optimize=True)
            except Exception:
                destination.unlink(missing_ok=True)
                continue
            page_title = str(page.get("title") or "")
            source_page = "https://commons.wikimedia.org/wiki/" + page_title.replace(" ", "_")
            return {
                "query": active_query,
                "file_title": page_title,
                "source_page": source_page,
                "image_url": image_url,
                "license": license_name,
                "artist": _plain(ext.get("Artist")),
                "credit": _plain(ext.get("Credit")),
                "attribution": _plain(ext.get("Attribution")),
                "destination": str(destination),
            }
    raise RuntimeError(
        f"No reusable Wikimedia Commons photo found for '{query}'. "
        "Set photo_search to a more specific subject or provide a licensed image file."
    )
