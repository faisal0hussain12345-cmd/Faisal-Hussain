from __future__ import annotations

import re
import time
from pathlib import Path

import requests
from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "BANNA-DocumentaryStudio/1.1 (personal documentary project)"}


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
    # Match explicit CC BY variants; avoid broad substring tests such as "nd".
    if re.search(r"\bcc\s*by(?:-sa)?(?:\s|$|[-0-9])", normalized) or "creative commons attribution" in normalized:
        if not any(marker in normalized for marker in ("noncommercial", "no derivatives", "cc by-nc", "cc by-nd", "cc-by-nc", "cc-by-nd")):
            return True, license_name or terms
    return False, license_name or terms or "Unknown license"


def _clean_query(value: object) -> str:
    query = str(value or "").replace("_", " ")
    query = re.sub(r"[^\w\s'-]", " ", query)
    query = re.sub(r"\s+", " ", query).strip()
    return query[:100]


def _query_candidates(scene: dict) -> list[str]:
    """Build short Commons-friendly searches instead of sending image-prompt prose."""
    candidates: list[str] = []
    explicit = _clean_query(scene.get("photo_search"))
    title = _clean_query(scene.get("title"))
    caption = _clean_query(scene.get("caption"))
    cue = _clean_query(scene.get("narration_cue"))
    project = _clean_query((scene.get("project") or {}).get("name")) if isinstance(scene.get("project"), dict) else ""

    if explicit:
        candidates.append(explicit)
    if title:
        candidates.extend([f"Titanic {title}", title])
    if caption:
        candidates.extend([caption, f"Titanic {caption}"])
    if cue:
        candidates.append(f"Titanic {cue}")
    # Generic Titanic archive searches are a last resort, not the first query.
    candidates.extend(["RMS Titanic 1912", "Titanic ship 1912"])
    unique: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _commons_search(query: str) -> list[dict]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": 6,
        "gsrlimit": 50,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1920,
        "format": "json",
        "formatversion": 2,
    }
    response = requests.get(API, params=params, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return response.json().get("query", {}).get("pages", [])


def download_commons_photo(scene: dict, destination: Path) -> dict:
    """Find a reusable Wikimedia Commons still and preserve attribution metadata."""
    errors: list[str] = []
    for active_query in _query_candidates(scene):
        try:
            pages = _commons_search(active_query)
        except requests.RequestException as exc:
            errors.append(f"{active_query}: {exc}")
            continue

        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            ext = info.get("extmetadata") or {}
            allowed, license_name = _allowed_license(ext)
            image_url = info.get("thumburl") or info.get("url")
            if not allowed or not image_url:
                continue
            try:
                image_response = requests.get(image_url, headers=HEADERS, timeout=60, stream=True)
                image_response.raise_for_status()
                content_type = image_response.headers.get("Content-Type", "").lower()
                if not content_type.startswith("image/"):
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                total = 0
                too_large = False
                with destination.open("wb") as output:
                    for chunk in image_response.iter_content(chunk_size=1024 * 256):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > 25 * 1024 * 1024:
                            too_large = True
                            break
                        output.write(chunk)
                if too_large or not destination.is_file() or destination.stat().st_size == 0:
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
            except requests.RequestException as exc:
                destination.unlink(missing_ok=True)
                errors.append(f"{active_query}: {exc}")
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

        # Be polite to Commons and avoid hammering its API between fallback searches.
        time.sleep(0.15)

    detail = (" Search errors: " + " | ".join(errors[:3])) if errors else ""
    raise RuntimeError(
        f"No reusable Wikimedia Commons photo found for scene '{scene.get('title', 'untitled')}'. "
        "Tried the scene title, caption, and broader Titanic archive terms. "
        "Provide a licensed image or refine this scene's photo_search." + detail
    )
