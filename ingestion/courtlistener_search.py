"""
ingestion/courtlistener_search.py

Purpose: query CourtListener's public REST API for court opinions/filings
matching a search term, and save each result's text as a raw document
with full provenance -- using the SAME download_file()/provenance pattern
from downloader.py, just fed by an API instead of a scraped page.

This replaces scrape_listing.py for now: APIs return structured JSON,
so there's no HTML-parsing guesswork and no bot-detection wall.
"""

import json
import time
from pathlib import Path

import requests

# If you have a CourtListener account, put your token here.
# Leave as None to use the lower, unauthenticated rate limit -- fine for
# learning/testing with a handful of requests.
API_TOKEN = None  # e.g. "abc123yourtokenhere"

BASE_URL = "https://www.courtlistener.com/api/rest/v4/search/"

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROVENANCE_DIR = RAW_DIR / "provenance"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)


def _headers() -> dict:
    """Builds the request headers, adding an auth token only if we have one."""
    headers = {"User-Agent": "learning-project (contact: youremail@example.com)"}
    if API_TOKEN:
        headers["Authorization"] = f"Token {API_TOKEN}"
    return headers


def search_opinions(query: str, max_results: int = 5) -> list[dict]:
    """
    Calls CourtListener's search API for case-law opinions (type=o) matching
    `query`, and returns up to max_results result dicts.

    type=o -> opinions (judicial rulings). Other values exist (r = RECAP
    filings, d = dockets) -- we start with opinions since their full text
    is usually included directly in the API response, no extra fetch needed.
    """
    params = {"q": query, "type": "o"}
    response = requests.get(BASE_URL, params=params, headers=_headers(), timeout=30)
    response.raise_for_status()
    data = response.json()

    results = data.get("results", [])
    print(f"API reports {data.get('count', '?')} total matches; returning first {min(max_results, len(results))}.")
    return results[:max_results]


def save_result_as_document(result: dict, query: str) -> None:
    """
    Takes one search-result dict from the API and saves it as a raw
    document (JSON, since that's the API's native format) plus a
    provenance record -- mirroring exactly what download_file() does
    for plain file downloads.
    """
    # Every CourtListener result has a unique numeric "cluster" id --
    # perfect as a stable, collision-free filename.
    result_id = result.get("cluster_id") or result.get("id") or int(time.time())
    filename = f"courtlistener_{result_id}.json"
    dest_path = RAW_DIR / filename

    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    provenance = {
        "source_url": f"https://www.courtlistener.com{result.get('absolute_url', '')}",
        "source_label": "CourtListener API search result",
        "query_used": query,
        "local_filename": filename,
        "downloaded_at_unix": time.time(),
        "case_name": result.get("caseName"),
        "court": result.get("court"),
        "date_filed": result.get("dateFiled"),
    }

    with open(PROVENANCE_DIR / f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    print(f"Saved: {filename}  ({provenance['case_name']})")


if __name__ == "__main__":
    query = "Epstein"  # try any term relevant to your investigation
    results = search_opinions(query, max_results=5)

    for result in results:
        save_result_as_document(result, query)