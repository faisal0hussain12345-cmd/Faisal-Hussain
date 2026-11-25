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
    url = "https://www.loc.gov/pictures/"
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


STATIC_TITANIC_ARCHIVE = {
    "opening": ("https://cdn.loc.gov/service/pnp/cph/3b00000/3b04000/3b04400/3b04419r.jpg", "https://www.loc.gov/pictures/item/2001704335/", "The TITANIC, 1911", "Library of Congress — no known restrictions on reproduction"),
    "shipyard": ("https://cdn.loc.gov/service/pnp/cph/3b10000/3b14000/3b14800/3b14835r.jpg", "https://www.loc.gov/item/2002721382/", "OLYMPIC and TITANIC — shipyard construction, 1909–1911", "Library of Congress — no known restrictions on reproduction"),
    "launch": ("https://cdn.loc.gov/service/pnp/cph/3a40000/3a40000/3a40700/3a40727r.jpg", "https://www.loc.gov/pictures/item/2001704333/", "TITANIC stern and rudder in drydock, circa 1912", "Library of Congress — no known restrictions on reproduction"),
    "luxury": ("https://cdn.loc.gov/service/pnp/ds/11000/11022v.jpg", "https://www.loc.gov/pictures/item/96503948/", "The veranda cafe and palm court of the Titanic, 1912", "Library of Congress — no known restrictions on publication"),
    "maiden": ("https://cdn.loc.gov/service/pnp/cph/3b00000/3b04000/3b04400/3b04419r.jpg", "https://www.loc.gov/pictures/item/2001704335/", "The TITANIC, 1911", "Library of Congress — no known restrictions on reproduction"),
    "passengers": ("https://cdn.loc.gov/service/pnp/cph/3b30000/3b39000/3b39700/3b39746r.jpg", "https://www.loc.gov/pictures/item/93510852/", "Titanic survivors on way to rescue ship Carpathia, 1912", "Library of Congress — no known restrictions on publication"),
    "warnings": ("https://cdn.loc.gov/service/pnp/cph/3b30000/3b37000/3b37100/3b37182r.jpg", "https://www.loc.gov/pictures/item/96514444/", "The great Titanic disaster — wireless operator and rescue montage, 1912", "Library of Congress — no known restrictions on publication"),
    "lookout": ("https://tile.loc.gov/storage-services/service/pnp/cph/3b30000/3b31000/3b31900/3b31920r.jpg", "https://www.loc.gov/pictures/item/2002714434/", "Harold Bride, surviving Titanic wireless operator, 1912", "Library of Congress — no known restrictions on publication"),
    "lifeboats": ("https://cdn.loc.gov/service/pnp/cph/3a30000/3a33000/3a33900/3a33939r.jpg", "https://www.loc.gov/pictures/item/2001704327/", "Titanic lifeboats on way to Carpathia, April 15, 1912", "Library of Congress — no known restrictions on reproduction"),
    "evacuation": ("https://cdn.loc.gov/service/pnp/cph/3b30000/3b39000/3b39700/3b39746r.jpg", "https://www.loc.gov/pictures/item/93510852/", "Titanic survivors in a lifeboat, 1912", "Library of Congress — no known restrictions on publication"),
    "distress": ("https://cdn.loc.gov/service/pnp/cph/3b30000/3b37000/3b37100/3b37182r.jpg", "https://www.loc.gov/pictures/item/96514444/", "The great Titanic disaster — wireless operator and rescue montage, 1912", "Library of Congress — no known restrictions on publication"),
    "rescue": ("https://cdn.loc.gov/service/pnp/cph/3c10000/3c16000/3c16000/3c16095v.jpg", "https://www.loc.gov/pictures/item/96503948/", "Carpathia and Titanic-related archival photograph, 1912", "Library of Congress — no known restrictions on publication"),
    "aftermath": ("https://cdn.loc.gov/service/pnp/cph/3a20000/3a27000/3a27400/3a27433r.jpg", "https://www.loc.gov/pictures/item/2001704324/", "Crowd awaiting survivors from the Titanic, April 18, 1912", "Library of Congress — no known restrictions on reproduction"),
    "wreck": ("https://oceanexplorer.noaa.gov/wp-content/uploads/2021/04/20210415-hires.jpg", "https://oceanexplorer.noaa.gov/multimedia/daily-image-media-20210415/", "Titanic bow wreck photograph, NOAA Expedition 2003", "NOAA image; credit NOAA and Russian Academy of Sciences"),
    "legacy": ("https://oceanexplorer.noaa.gov/wp-content/uploads/2021/04/20210415-hires.jpg", "https://oceanexplorer.noaa.gov/multimedia/daily-image-media-20210415/", "Titanic bow wreck photograph, NOAA Expedition 2003", "NOAA image; credit NOAA and Russian Academy of Sciences"),
}


def _download_curated_titanic(scene: dict, destination: Path) -> dict | None:
    item = STATIC_TITANIC_ARCHIVE.get(str(scene.get("id") or ""))
    if not item:
        return None
    image_url, source_page, title, license_label = item
    if not _download_verified_image(image_url, destination):
        return None
    return {
        "query": "curated Titanic archival collection",
        "file_title": title,
        "source_page": source_page,
        "image_url": image_url,
        "license": license_label,
        "artist": "",
        "credit": "Library of Congress" if "loc.gov" in image_url else "NOAA / Russian Academy of Sciences",
        "attribution": license_label,
        "destination": str(destination),
    }


def _download_loc_photo(scene: dict, destination: Path) -> dict | None:
    queries = []
    title = _clean_query(scene.get("title"))
    caption = _clean_query(scene.get("caption"))
    explicit = _clean_query(scene.get("photo_search"))
    for query in (f"Titanic {title}" if title else "", f"Titanic {caption}" if caption else "", "Titanic ship 1912"):
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
    # Curated, verified Titanic-specific LOC/NOAA records first; avoids search API
    # rate limits and keeps each scene tied to a relevant primary-source image.
    curated = _download_curated_titanic(scene, destination)
    if curated:
        return curated

    # Then search the Library of Congress public photo catalog.
    loc_result = _download_loc_photo(scene, destination)
    if loc_result:
        return loc_result

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

    detail = (" Search errors: " + " | ".join(errors[:3])) if errors else ""
    raise RuntimeError(
        f"No reusable archival still found for scene '{scene.get('title', 'untitled')}'. "
        "Wikimedia Commons and the Library of Congress fallback returned no image with "
        "a usable rights statement." + detail
    )
