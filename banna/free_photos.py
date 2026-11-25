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
    return title or caption or "historical archival photograph"


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
        candidates.append(title)
    if caption:
        candidates.append(caption)
    if cue:
        candidates.append(cue)
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



STATIC_MANHATTAN_ARCHIVE = {
    "opening": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/photo_gallery_515_x_325_/public/2024-02/1.jpg?itok=KKJRGZ2C",
        "source_page": "https://www.energy.gov/em/photos/manhattan-project-photo-gallery",
        "file_title": "Hanford construction camp, 1944",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "fission": {
        "pdf_url": "https://www.energy.gov/sites/prod/files/DOENevadaTestSite.pdf",
        "pdf_match": "Lise Meitner and Otto Hahn in their laboratory",
        "pdf_image_index": 1,
        "image_url": "https://www.energy.gov/sites/prod/files/DOENevadaTestSite.pdf#page=23&image=2",
        "source_page": "https://www.energy.gov/management/articles/fehner-and-gosling-origins-nevada-test-site",
        "file_title": "Lise Meitner and Otto Hahn in their laboratory",
        "credit": "Argonne National Laboratory / U.S. Department of Energy",
        "license": "U.S. Department of Energy historical publication; attribution retained",
    },
    "chain-reaction": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/full_article_width/public/Metallurgical-Laboratory_0.jpg?itok=UaQt7IIW",
        "source_page": "https://www.energy.gov/lm/metallurgical-laboratory-university-chicago",
        "file_title": "Metallurgical Laboratory and Stagg Field bleachers",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "german-threat": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/full_article_width/public/TE-EinsteinSzilard.jpg?itok=jQhlXAJs",
        "source_page": "https://www.energy.gov/management/august-2-1939-einsteins-letter",
        "file_title": "Albert Einstein and Leo Szilard",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "einstein-letter": {
        "image_url": "https://i0.wp.com/prologue.blogs.archives.gov/wp-content/uploads/sites/9/2019/08/document007_Page_1-813x1024.jpg?resize=685%2C863&ssl=1",
        "source_page": "https://prologue.blogs.archives.gov/2019/11/01/facial-hair-friday-mmustache/",
        "file_title": "First page of Einstein's August 2, 1939 letter to President Roosevelt",
        "credit": "Franklin D. Roosevelt Library and Museum / U.S. National Archives",
        "license": "U.S. National Archives primary-source document; attribution retained",
    },
    "pearl-harbor": {
        "image_url": "https://www.archives.gov/files/research/still-pictures/080-g-0032420-28-1274m.jpg",
        "source_page": "https://www.archives.gov/research/still-pictures/highlights/uss-arizona-burning",
        "file_title": "USS Arizona burning after the attack on Pearl Harbor, December 7, 1941",
        "credit": "U.S. Navy / National Archives",
        "license": "U.S. Government photograph held by the National Archives",
    },
    "district": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/photo_gallery_515_x_325_/public/2023-11/k25%20construction.jpg?itok=NCe1jUu2",
        "source_page": "https://www.energy.gov/em/photos/manhattan-project-photo-gallery",
        "file_title": "K-25 construction at Oak Ridge",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "groves": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/full_article_width/public/2025-06/Photo-Groves.jpg?itok=stQzUg1C",
        "source_page": "https://www.energy.gov/nnsa/articles/army-and-origins-nuclear-security-enterprise",
        "file_title": "General Leslie R. Groves portrait",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "oppenheimer": {
        "image_url": "https://www.nps.gov/articles/000/images/Opp-new.jpg?autorotate=false&maxwidth=650",
        "source_page": "https://www.nps.gov/mapr/learn/historyculture/oppenheimer.htm",
        "file_title": "J. Robert Oppenheimer",
        "credit": "Manhattan Project National Historical Park / National Park Service",
        "license": "U.S. National Park Service image; retain individual image credit",
    },
    "oak-ridge": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/photo_gallery_515_x_325_/public/2023-11/Oak-Ridge-looking-east-from-Jefferson-Square-c.jpg?itok=ecgs5apK",
        "source_page": "https://www.energy.gov/em/photos/manhattan-project-photo-gallery",
        "file_title": "Oak Ridge looking east from Jefferson Square",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "calutron-workers": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/photo_gallery_515_x_325_/public/34786721743_1e6e7aec26_o.jpg?itok=porNBZYZ",
        "source_page": "https://www.energy.gov/photos/women-manhattan-project",
        "file_title": "A Calutron Girl at her station",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "hanford": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/photo_gallery_515_x_325_/public/2024-02/4.jpg?itok=IAWAAKx3",
        "source_page": "https://www.energy.gov/em/photos/manhattan-project-photo-gallery",
        "file_title": "Hanford B Reactor complex",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "los-alamos": {
        "image_url": "https://www.nps.gov/articles/000/images/Main-Gate-new.jpg?autorotate=false&maxwidth=650",
        "source_page": "https://www.nps.gov/mapr/learn/historyculture/los-alamos.htm",
        "file_title": "Los Alamos Main Gate",
        "credit": "Manhattan Project National Historical Park / National Park Service",
        "license": "U.S. National Park Service image; retain individual image credit",
    },
    "chicago-pile": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/photo_gallery_515_x_325_/public/10556202784_c601291401_o.jpg?itok=Wfz1Ayv3",
        "source_page": "https://www.energy.gov/photos/women-manhattan-project",
        "file_title": "Leona Woods Marshall, member of Enrico Fermi's Chicago Pile-1 team",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "workforce": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/full_article_width/public/2025-06/Photo%20-%20WACs.jpg?itok=FNaeiseq",
        "source_page": "https://www.energy.gov/nnsa/articles/army-and-origins-nuclear-security-enterprise",
        "file_title": "Women Army Corps members associated with the Manhattan Project",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "secrecy": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/photo_gallery_515_x_325_/public/2023-11/OR%20sign.jpg?itok=9DuH7-Y0",
        "source_page": "https://www.energy.gov/em/photos/manhattan-project-photo-gallery",
        "file_title": "Oak Ridge secrecy sign",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
    "bomb-designs": {
        "image_url": "https://www.nps.gov/articles/000/images/19278887165_11b63aa668_k.jpg?autorotate=false&maxwidth=650",
        "source_page": "https://www.nps.gov/mapr/learn/historyculture/trinity-test.htm",
        "file_title": "Trinity device being prepared",
        "credit": "Manhattan Project National Historical Park / National Park Service",
        "license": "U.S. National Park Service image; retain individual image credit",
    },
    "truman": {
        "image_url": "https://catalog.archives.gov/medialz/presidential-libraries/truman/photographs/58/58-1.jpg",
        "source_page": "https://www.trumanlibrary.gov/photograph-records/58-1",
        "file_title": "Churchill, Truman, and Stalin at Potsdam",
        "credit": "U.S. Army Signal Corps / Harry S. Truman Library and Museum",
        "license": "Public Domain, as identified by the Harry S. Truman Library",
    },
    "trinity-tower": {
        "pdf_url": "https://www.energy.gov/sites/default/files/Manhattan_Project_2010.pdf",
        "pdf_match": "Tower For Trinity Test",
        "pdf_image_index": 0,
        "image_url": "https://www.energy.gov/sites/default/files/Manhattan_Project_2010.pdf#page=90&image=1",
        "source_page": "https://www.energy.gov/sites/default/files/Manhattan_Project_2010.pdf",
        "file_title": "Tower for the Trinity test",
        "credit": "U.S. Department of Energy",
        "license": "U.S. Department of Energy historical publication; attribution retained",
    },
    "trinity-fireball": {
        "image_url": "https://npgallery.nps.gov/GetAsset/c212b977-b0e2-4736-9759-8ed40caf0405/original.jpg",
        "source_page": "https://npgallery.nps.gov/AssetDetail/c212b977-b0e2-4736-9759-8ed40caf0405",
        "file_title": "Trinity test explosion",
        "credit": "Manhattan Project National Historical Park / National Park Service",
        "license": "U.S. National Park Service image; retain individual image credit",
    },
    "potsdam": {
        "image_url": "https://catalog.archives.gov/medialz/presidential-libraries/truman/photographs/62/62-770.jpg",
        "source_page": "https://www.trumanlibrary.gov/photograph-records/62-770",
        "file_title": "Stalin, Truman, and Churchill at Potsdam",
        "credit": "U.S. Army Signal Corps / Harry S. Truman Library and Museum",
        "license": "Public Domain, as identified by the Harry S. Truman Library",
    },
    "hiroshima": {
        "image_url": "https://www.archives.gov/files/news/images/hiroshima-after-atomic-bomb-crop-243-hp-i-31-2.jpg",
        "source_page": "https://www.archives.gov/research/japanese-war-crimes/atomic-bombing",
        "file_title": "Hiroshima after the atomic bombing",
        "credit": "U.S. National Archives",
        "license": "U.S. Government archival photograph; attribution retained",
    },
    "nagasaki": {
        "image_url": "https://www.archives.gov/files/news/images/atomic-cloud-nagasaki-535795-crop-b.png",
        "source_page": "https://www.archives.gov/research/japanese-war-crimes/atomic-bombing",
        "file_title": "Atomic cloud over Nagasaki",
        "credit": "U.S. National Archives",
        "license": "U.S. Government archival photograph; attribution retained",
    },
    "surrender": {
        "image_url": "https://docsteach.org/wp-content/uploads/documents/265416113580/primary_12655_20211029090129.jpg",
        "source_page": "https://docsteach.org/document/surrender-ceremony-uss-missouri/",
        "file_title": "Surrender ceremony aboard USS Missouri, September 2, 1945",
        "credit": "General Records of the Department of the Navy / National Archives",
        "license": "Public Domain, Free of Known Copyright Restrictions",
    },
    "legacy": {
        "image_url": "https://www.energy.gov/sites/default/files/styles/photo_gallery_515_x_325_/public/2024-02/6_0.jpg?itok=yK22vzIu",
        "source_page": "https://www.energy.gov/em/photos/manhattan-project-photo-gallery",
        "file_title": "Los Alamos laboratory scientists",
        "credit": "U.S. Department of Energy",
        "license": "Official U.S. Department of Energy archival photograph; retain source credit",
    },
}


def _extract_pdf_photo(pdf_url: str, match_text: str, image_index: int, destination: Path) -> bool:
    """Extract one embedded archival photograph from an official DOE PDF page."""
    try:
        import fitz
        response = requests.get(pdf_url, timeout=60, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        document = fitz.open(stream=response.content, filetype="pdf")
        target = match_text.casefold()
        for page in document:
            if target not in page.get_text("text").casefold():
                continue
            images = page.get_images(full=True)
            if image_index >= len(images):
                continue
            xref = images[image_index][0]
            extracted = document.extract_image(xref)
            payload = extracted.get("image", b"")
            if not payload:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            try:
                with Image.open(destination) as check:
                    check.verify()
            except Exception:
                destination.unlink(missing_ok=True)
                continue
            return True
    except Exception:
        return False
    return False


def _download_static_manhattan_photo(scene: dict, destination: Path) -> dict | None:
    entry = STATIC_MANHATTAN_ARCHIVE.get(str(scene.get("id") or ""))
    if not entry:
        return None
    if entry.get("pdf_url"):
        ok = _extract_pdf_photo(
            entry["pdf_url"], entry["pdf_match"], int(entry.get("pdf_image_index", 0)), destination
        )
    else:
        ok = _download_verified_image(entry["image_url"], destination)
    if not ok:
        return None
    return {
        "query": scene.get("photo_search") or scene.get("title") or "Manhattan Project archival photograph",
        "file_title": entry["file_title"],
        "source_page": entry["source_page"],
        "image_url": entry["image_url"],
        "license": entry["license"],
        "artist": "",
        "credit": entry["credit"],
        "attribution": f"{entry['credit']} — {entry['file_title']}",
        "destination": str(destination),
    }


STATIC_TITANIC_ARCHIVE = {
    "opening": ("https://cdn.loc.gov/service/pnp/cph/3b00000/3b04000/3b04400/3b04419r.jpg", "https://www.loc.gov/pictures/item/2001704335/", "The TITANIC, 1911", "Library of Congress — no known restrictions on reproduction"),
    "shipyard": ("https://cdn.loc.gov/service/pnp/cph/3b10000/3b14000/3b14800/3b14835r.jpg", "https://www.loc.gov/item/2002721382/", "OLYMPIC and TITANIC — shipyard construction, 1909–1911", "Library of Congress — no known restrictions on reproduction"),
    "launch": ("https://cdn.loc.gov/service/pnp/cph/3a40000/3a40000/3a40700/3a40727r.jpg", "https://www.loc.gov/pictures/item/2001704333/", "TITANIC stern and rudder in drydock, circa 1912", "Library of Congress — no known restrictions on reproduction"),
    "luxury": ("https://cdn.loc.gov/service/pnp/ds/11000/11022v.jpg", "https://www.loc.gov/pictures/item/96503948/", "The veranda cafe and palm court of the Titanic, 1912", "Library of Congress — no known restrictions on publication"),
    "maiden": ("https://cdn.loc.gov/service/pnp/cph/3b00000/3b04000/3b04400/3b04419r.jpg", "https://www.loc.gov/pictures/item/2001704335/", "The TITANIC, 1911", "Library of Congress — no known restrictions on reproduction"),
    "passengers": ("https://cdn.loc.gov/service/pnp/cph/3b30000/3b39000/3b39700/3b39746r.jpg", "https://www.loc.gov/pictures/item/93510852/", "Titanic survivors on way to rescue ship Carpathia, 1912", "Library of Congress — no known restrictions on publication"),
    "warnings": ("https://cdn.loc.gov/service/pnp/cph/3b30000/3b37000/3b37100/3b37182r.jpg", "https://www.loc.gov/pictures/item/96514444/", "The great Titanic disaster — wireless operator and rescue montage, 1912", "Library of Congress — no known restrictions on publication"),
    "lookout": ("https://cdn.loc.gov/service/pnp/cph/3b00000/3b04000/3b04400/3b04419r.jpg", "https://www.loc.gov/pictures/item/2001704335/", "The TITANIC at sea, 1911", "Library of Congress — no known restrictions on reproduction"),
    "lifeboats": ("https://cdn.loc.gov/service/pnp/cph/3a30000/3a33000/3a33900/3a33939r.jpg", "https://www.loc.gov/pictures/item/2001704327/", "Titanic lifeboats on way to Carpathia, April 15, 1912", "Library of Congress — no known restrictions on reproduction"),
    "evacuation": ("https://cdn.loc.gov/service/pnp/cph/3b30000/3b39000/3b39700/3b39746r.jpg", "https://www.loc.gov/pictures/item/93510852/", "Titanic survivors in a lifeboat, 1912", "Library of Congress — no known restrictions on publication"),
    "distress": ("https://cdn.loc.gov/service/pnp/cph/3b30000/3b37000/3b37100/3b37182r.jpg", "https://www.loc.gov/pictures/item/96514444/", "The great Titanic disaster — wireless operator and rescue montage, 1912", "Library of Congress — no known restrictions on publication"),
    "rescue": ("https://cdn.loc.gov/service/pnp/cph/3c20000/3c21000/3c21000/3c21012r.jpg", "https://www.loc.gov/pictures/item/98509237/", "Carpathia with Titanic lifeboats, circa 1912", "Library of Congress — no known restrictions on publication"),
    "aftermath": ("https://cdn.loc.gov/service/pnp/cph/3a20000/3a27000/3a27400/3a27433r.jpg", "https://www.loc.gov/pictures/item/2001704324/", "Crowd awaiting survivors from the Titanic, April 18, 1912", "Library of Congress — no known restrictions on reproduction"),
    "wreck": ("https://upload.wikimedia.org/wikipedia/commons/9/9c/Titanic_wreck_bow.jpg", "https://commons.wikimedia.org/wiki/File:Titanic_wreck_bow.jpg", "Titanic bow wreck photograph, NOAA Expedition 2003", "Public domain in the United States — NOAA/IFE/URI photograph"),
    "legacy": ("https://oceanexplorer.noaa.gov/wp-content/uploads/2021/04/20210415-hires.jpg", "https://oceanexplorer.noaa.gov/multimedia/daily-image-media-20210415/", "Titanic bow wreck photograph, NOAA Expedition 2003", "NOAA image; credit NOAA and Russian Academy of Sciences"),
}


def _is_titanic_scene(scene: dict) -> bool:
    project_name = str(scene.get("project_name") or "").casefold()
    scene_query = str(scene.get("photo_search") or "").casefold()
    return "titanic" in project_name or "titanic" in scene_query


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
        "credit": "Library of Congress" if "loc.gov" in image_url else "NOAA / Institute for Exploration / University of Rhode Island",
        "attribution": license_label,
        "destination": str(destination),
    }


def _download_loc_photo(scene: dict, destination: Path, used_sources: set[str] | None = None) -> dict | None:
    used_sources = used_sources or set()
    for query in _query_candidates(scene):
        try:
            results = _loc_search(query)
        except requests.RequestException:
            continue
        for item in results:
            source_page = str(item.get("url") or item.get("id") or "https://www.loc.gov/")
            if source_page in used_sources:
                continue
            ok, rights_label = _loc_rights_ok(item)
            if not ok:
                continue
            for image_url in _loc_image_urls(item):
                if image_url in used_sources:
                    continue
                if not _download_verified_image(image_url, destination):
                    continue
                title_text = str(item.get("title") or scene.get("title") or "Library of Congress photograph")
                return {
                    "query": query,
                    "file_title": title_text,
                    "source_page": source_page,
                    "image_url": image_url,
                    "license": rights_label,
                    "artist": "",
                    "credit": "Library of Congress",
                    "attribution": "Library of Congress",
                    "destination": str(destination),
                }
    return None


def download_commons_photo(scene: dict, destination: Path, used_sources: set[str] | None = None) -> dict:
    """Find a reusable Wikimedia Commons still and preserve attribution metadata."""
    errors: list[str] = []
    used_sources = used_sources or set()
    curated = _download_curated_titanic(scene, destination) if _is_titanic_scene(scene) and str(scene.get("id", "")) in STATIC_TITANIC_ARCHIVE else None
    if curated and curated.get("source_page") not in used_sources:
        return curated

    # Search the Library of Congress catalog with this scene's own subject.
    loc_result = _download_loc_photo(scene, destination, used_sources)
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
            page_title = str(page.get("title") or "")
            source_page = "https://commons.wikimedia.org/wiki/" + page_title.replace(" ", "_")
            if source_page in used_sources or image_url in used_sources:
                continue
            if not _download_verified_image(image_url, destination):
                continue

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
        "Wikimedia Commons and the Library of Congress returned no distinct image with "
        "a usable rights statement." + detail
    )
