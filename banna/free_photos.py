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


def _query_for_scene(scene: dict) -> str:
    """Backward-compatible primary query selector used by tests and callers."""
    explicit = _clean_query(scene.get("photo_search"))
    if explicit:
        return explicit
    title = _clean_query(scene.get("title"))
    caption = _clean_query(scene.get("caption"))
    return title or caption or "RMS Titanic 1912"


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


def _download_verified_image(image_url: str, destination: Path) -> bool:
    try:
        response = requests.get(image_url, headers=HEADERS, timeout=60, stream=True)
        response.raise_for_status()
        if not response.headers.get("Content-Type", "").lower().startswith("image/"):
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        with destination.open("wb") as output:
            for chunk in response.iter_content(chunk_size=256 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > 25 * 1024 * 1024:
                    destination.unlink(missing_ok=True)
                    return False
                output.write(chunk)
        if not destination.is_file() or destination.stat().st_size == 0:
            return False
        with Image.open(destination) as im:
            im.verify()
        with Image.open(destination) as im:
            im.convert("RGB").save(destination, format="JPEG", quality=92, optimize=True)
        return True
    except Exception:
        destination.unlink(missing_ok=True)
        return False


def _loc_search(query: str) -> list[dict]:
    url = "https://www.loc.gov/photos/"
    response = requests.get(
        url,
        params={"fo": "json", "q": query, "c": 40},
        headers=HEADERS,
        timeout=45,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def _loc_rights_ok(item: dict) -> tuple[bool, str]:
    rights = " ".join(str(item.get(key) or "") for key in ("rights", "rights_information", "rights_advisory"))
    clean = re.sub(r"<[^>]+>", " ", rights).lower()
    if "no known restrictions" in clean or "public domain" in clean or "no restrictions" in clean:
        return True, "Library of Congress — no known restrictions noted"
    return False, rights[:300] or "Rights status not stated"


def _loc_image_urls(item: dict) -> list[str]:
    urls = item.get("image_url") or item.get("image") or []
    if isinstance(urls, str):
        urls = [urls]
    if isinstance(urls, dict):
        urls = list(urls.values())
    result = [str(url) for url in urls if isinstance(url, str) and url.startswith("http")]
    # Prefer the largest common image derivative when the API returns multiple sizes.
    result.sort(key=lambda u: (("full" in u.lower()) or ("large" in u.lower()), len(u)), reverse=True)
    return result


def _download_loc_photo(scene: dict, destination: Path) -> dict | None:
    queries = []
    title = _clean_query(scene.get("title"))
    caption = _clean_query(scene.get("caption"))
    explicit = _clean_query(scene.get("photo_search"))
    for query in (f"Titanic {title}" if title else "", f"Titanic {caption}" if caption else "", "RMS Titanic 1912"):
        if query and query not in queries:
            queries.append(query)
    for query in queries:
        try:
            results = _loc_search(query)
        except requests.RequestException:
            continue
        for item in results:
            ok, rights_label = _loc_rights_ok(item)
            if not ok:
                continue
            for image_url in _loc_image_urls(item):
                if not _download_verified_image(image_url, destination):
                    continue
                title_text = str(item.get("title") or scene.get("title") or "Library of Congress photograph")
                return {
                    "query": query,
                    "file_title": title_text,
                    "source_page": str(item.get("url") or item.get("id") or "https://www.loc.gov/"),
                    "image_url": image_url,
                    "license": rights_label,
                    "artist": "",
                    "credit": "Library of Congress",
                    "attribution": "Library of Congress",
                    "destination": str(destination),
                }
    return None


def download_commons_photo(scene: dict, destination: Path) -> dict:
    """Find a reusable Wikimedia Commons still and preserve attribution metadata."""
    errors: list[str] = []
    for active_query in _query_candidates(scene):
        try:
            pages = _commons_search(active_query)
        except requests.RequestException as exc:
            errors.append(f"{active_query}: {exc}")
            # Wikimedia Commons can temporarily rate-limit GitHub-hosted runners.
            # Stop querying it on HTTP errors and use the Library of Congress fallback.
            if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code in (429, 403):
                break
            continue

        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            ext = info.get("extmetadata") or {}
            allowed, license_name = _allowed_license(ext)
            image_url = info.get("thumburl") or info.get("url")
            if not allowed or not image_url:
                continue
            if not _download_verified_image(image_url, destination):
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

    # Secondary public archive fallback: Library of Congress JSON photo API.
    loc_result = _download_loc_photo(scene, destination)
    if loc_result:
        return loc_result

    detail = (" Search errors: " + " | ".join(errors[:3])) if errors else ""
    raise RuntimeError(
        f"No reusable archival still found for scene '{scene.get('title', 'untitled')}'. "
        "Wikimedia Commons and the Library of Congress fallback returned no image with "
        "a usable rights statement." + detail
    )
