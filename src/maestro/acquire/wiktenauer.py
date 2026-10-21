"""
Wiktenauer downloader, built on the MediaWiki API, which:
- returns only the page content (no menus, scripts or CSS);
- reports the revision number, so every download can be traced back to the
  exact version of the page it came from.

The endpoint is action=parse, which returns the already rendered HTML.
Documentation: https://www.mediawiki.org/wiki/API:Parsing_wikitext
"""
from datetime import datetime, timezone
import time
import json
import re
from pathlib import Path
import requests

BASE = "https://wiktenauer.com"
API = "https://wiktenauer.com/api.php"
USER_AGENT = "MaestroDArme/0.1 (HEMA treatises project)"
SECONDS_BETWEEN_REQUESTS = 1.0

_last_request_time = 0.0   # when the last request was sent (0 = never)


def call_api(params: dict, attempts: int = 3) -> dict:
    """Send a request to the Wiktenauer API and return the response as a dictionary.

    Respects the rate limit and retries on network or server errors.
    """
    params = {**params, "format": "json", "formatversion": "2"}  # fixed parameters
    for attempt in range(1, attempts + 1):   # 1, 2, 3
        _throttle()
        try:
            r = requests.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
            if r.status_code == 200:
                data = r.json()
                if "error" in data:
                    # "logical" error (e.g. the page does not exist): retrying would not help
                    raise RuntimeError(f"API error: {data['error'].get('info')}")
                return data     # success: return also exits the loop
            print(f"    HTTP {r.status_code}, attempt {attempt}/{attempts}")
        except requests.RequestException as e:
            print(f"    network error ({e}), attempt {attempt}/{attempts}")
        if attempt < attempts:
            time.sleep(2 ** attempt)  # 2, then 4 seconds; no point waiting after the last attempt

    # if we get here, every attempt failed
    raise RuntimeError(f"Could not complete the request after {attempts} attempts.")


def safe_filename(title: str) -> str:
    """"Fiore de'i Liberi" -> "fiore_de_i_liberi": anything that is not a letter or a digit becomes _"""
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def download_page(title: str, folder: Path) -> Path:
    """
    Download a page and save it as .html, next to a .meta.json file.

    The .meta.json file records the provenance: title, URL, revision
    and download date.
    """
    folder.mkdir(parents=True, exist_ok=True)
    print(f"Downloading '{title}'...")
    page = call_api({"action": "parse", "page": title, "prop": "text|revid"})["parse"]

    base = folder / safe_filename(title)            # e.g. corpus/raw/fiore/fiore_de_i_liberi
    html_path = base.with_suffix(".html")
    html_path.write_text(page["text"], encoding="utf-8")

    meta = {
        "title": page["title"],
        "revid": page["revid"],
        "url": f"{BASE}/wiki/{page['title'].replace(' ', '_')}",
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    base.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return html_path


def _throttle():
    """Wait just long enough for at least SECONDS_BETWEEN_REQUESTS to pass between two requests."""
    global _last_request_time                     # we want to MODIFY the module-level variable
    elapsed = time.time() - _last_request_time    # seconds since the last request
    if elapsed < SECONDS_BETWEEN_REQUESTS:
        time.sleep(SECONDS_BETWEEN_REQUESTS - elapsed)  # wait only for the difference
    _last_request_time = time.time()              # record the time of this request
