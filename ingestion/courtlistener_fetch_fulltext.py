"""
ingestion/courtlistener_fetch_fulltext.py

Purpose: for every raw JSON search-result file already saved in data/raw/
(from courtlistener_search.py), look up its cluster_id, call the
/opinions/ endpoint to get the FULL text of the opinion, and save that
as a new, richer raw document -- without touching or overwriting the
original search-result file (raw data stays immutable).

This is step two of the two-step API pattern:
  search endpoint  -> gives you IDs + short snippets
  opinions endpoint -> gives you full text, keyed by ID
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Reads the .env file in the project root and loads its key=value pairs
# as environment variables for this process only (doesn't touch your
# actual system environment permanently).
load_dotenv()

# Reads the COURTLISTENER_API_TOKEN value we put in .env. If it's missing,
# this will be None -- we check for that below and fail with a clear
# message instead of a confusing 401 error later.
API_TOKEN = os.getenv("COURTLISTENER_API_TOKEN")

CLUSTERS_URL = "https://www.courtlistener.com/api/rest/v4/clusters/"

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROVENANCE_DIR = RAW_DIR / "provenance"


def _headers() -> dict:
    return {
        "User-Agent": "learning-project (contact: youremail@example.com)",
        "Authorization": f"Token {API_TOKEN}",
    }


def fetch_with_retry(url: str, max_attempts: int = 3) -> requests.Response:
    """
    Wraps requests.get() with automatic retries on transient failures
    (timeouts, connection resets). Real networks are unreliable -- a
    request that fails once often succeeds on the second or third try.

    Uses "exponential backoff": wait 2s, then 4s, then 8s between
    attempts, instead of retrying instantly (which can make a struggling
    server's problem worse) or waiting a fixed amount every time.
    """
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, headers=_headers(), timeout=30)
            response.raise_for_status()
            return response
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_exception = e
            wait_seconds = 2 ** attempt  # 2, 4, 8...
            print(f"    (attempt {attempt}/{max_attempts} failed: {e.__class__.__name__} -- retrying in {wait_seconds}s)")
            time.sleep(wait_seconds)
    # If we exhausted all attempts, raise the last error we saw so the
    # caller knows this item genuinely failed (not silently skipped).
    raise last_exception


def fetch_full_opinion(cluster_id: int) -> dict | None:
    """
    Two-step lookup, using the documented path (not a guessed filter param):

    1. GET /clusters/{cluster_id}/  -> gives us "sub_opinions", a list of
       URLs pointing to the individual opinion(s) attached to this case
       (a case can have a majority opinion, dissent, concurrence, etc.)
    2. GET the first sub_opinion URL directly -> gives us the actual
       plain_text/html content.

    Fetching a specific resource BY ITS URL (returned to us by the API
    itself) is more reliable than guessing query-filter parameter names --
    the API is telling us exactly where to go next.
    """
    try:
        cluster_response = fetch_with_retry(f"{CLUSTERS_URL}{cluster_id}/")
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            print("401 Unauthorized -- check that API_TOKEN is set correctly.")
        return None

    cluster_data = cluster_response.json()

    sub_opinions = cluster_data.get("sub_opinions", [])
    if not sub_opinions:
        print(f"  -> cluster {cluster_id} has no sub_opinions listed.")
        return None

    # sub_opinions is a list of full URLs -- take the first (usually the
    # lead/majority opinion) and fetch it directly.
    opinion_url = sub_opinions[0]
    opinion_response = fetch_with_retry(opinion_url)
    return opinion_response.json()


def process_all_search_results() -> None:
    """
    Walks every courtlistener_*.json file already in data/raw/, pulls its
    cluster_id, fetches the full opinion, and saves it as a companion
    "_fulltext.json" file with its own provenance record.
    """
    search_result_files = list(RAW_DIR.glob("courtlistener_*.json"))
    print(f"Found {len(search_result_files)} existing search-result file(s) to expand.")

    for filepath in search_result_files:
        with open(filepath, "r", encoding="utf-8") as f:
            search_result = json.load(f)

        cluster_id = search_result.get("cluster_id")
        if not cluster_id:
            print(f"Skipping {filepath.name}: no cluster_id found.")
            continue

        fulltext_filename = f"courtlistener_{cluster_id}_fulltext.json"
        dest_path = RAW_DIR / fulltext_filename

        # Idempotency check: if we already successfully saved this one
        # (e.g. on a previous run that crashed partway through), don't
        # waste an API call redoing it. This lets you just re-run the
        # whole script after any failure instead of tracking progress
        # by hand.
        if dest_path.exists():
            print(f"Already have {fulltext_filename}, skipping.")
            continue

        print(f"Fetching full text for cluster_id={cluster_id} ({search_result.get('caseName')})...")

        try:
            opinion = fetch_full_opinion(cluster_id)
        except requests.exceptions.RequestException as e:
            # Catch-all for anything fetch_with_retry couldn't recover
            # from after all attempts. Log it and move on to the next
            # document rather than crashing the whole batch.
            print(f"  -> FAILED after retries: {e.__class__.__name__}: {e}")
            continue

        if opinion is None:
            print("  -> no opinion data returned, skipping.")
            continue

        # Prefer plain_text; some older/OCR'd opinions only have html fields.
        full_text = opinion.get("plain_text") or opinion.get("html_with_citations") or ""

        output = {
            "cluster_id": cluster_id,
            "case_name": search_result.get("caseName"),
            "full_text": full_text,
            "download_url": opinion.get("download_url"),
            "sha1_from_courtlistener": opinion.get("sha1"),
        }
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        provenance = {
            "source_url": f"{CLUSTERS_URL}{cluster_id}/",
            "source_label": "CourtListener API full opinion text",
            "derived_from": filepath.name,
            "local_filename": fulltext_filename,
            "downloaded_at_unix": time.time(),
            "text_length_chars": len(full_text),
        }
        with open(PROVENANCE_DIR / f"{fulltext_filename}.json", "w", encoding="utf-8") as f:
            json.dump(provenance, f, indent=2)

        print(f"  -> saved {fulltext_filename} ({len(full_text)} characters of text)")

        # Be a polite API citizen -- small pause between requests.
        time.sleep(1)


if __name__ == "__main__":
    if not API_TOKEN:
        raise SystemExit(
            "COURTLISTENER_API_TOKEN not found. Make sure you have a .env file "
            "in the project root containing:\n  COURTLISTENER_API_TOKEN=your_token_here"
        )
    process_all_search_results()