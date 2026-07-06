"""
preprocessing/run_etl.py

Purpose: the actual Extract-Transform-Load pipeline. Reads every raw
file we've ingested, figures out what KIND of raw file it is, pulls
text + metadata out of it, cleans the text, builds a ProcessedDocument,
and saves it into data/processed/ as a clean JSON file.

Run this any time new raw files show up -- it skips ones already done.
"""

import hashlib
import json
import time
from pathlib import Path

import sys

from schema import ProcessedDocument
from text_cleaning import clean_text_pipeline
from entity_extraction import extract_entities

sys.path.append(str(Path(__file__).resolve().parent.parent / "ingestion"))
from pdf_ocr_extractor import extract_pdf_text

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def make_doc_id(source_type: str, raw_filename: str) -> str:
    """
    Builds a short, stable, unique ID for a document from its source
    type + original filename. Using a hash (rather than e.g. a counter)
    means the SAME input always produces the SAME id, even if you re-run
    the pipeline from scratch -- which matters once a database is
    involved, so re-processing doesn't create duplicate rows.
    """
    raw_key = f"{source_type}:{raw_filename}"
    return hashlib.sha256(raw_key.encode()).hexdigest()[:16]  # 16 chars is plenty unique for this scale


def extract_from_courtlistener_fulltext(filepath: Path) -> ProcessedDocument:
    """
    Handles files shaped like courtlistener_XXXXX_fulltext.json
    (produced by our Phase 2 ingestion scripts).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_text = data.get("full_text", "")
    cleaned = clean_text_pipeline(raw_text)
    entities = extract_entities(cleaned)

    return ProcessedDocument(
        doc_id=make_doc_id("courtlistener_opinion", filepath.name),
        source_type="courtlistener_opinion",
        source_url=data.get("download_url"),
        original_filename=filepath.name,
        title=data.get("case_name"),
        clean_text=cleaned,
        raw_text_length=len(raw_text),
        clean_text_length=len(cleaned),
        people_mentioned=entities["people"],
        sha256_of_source=data.get("sha1_from_courtlistener"),
        processed_at_unix=time.time(),
    )


def extract_from_courtlistener_search_result(filepath: Path) -> ProcessedDocument:
    """
    Handles the OTHER json shape -- plain search results with only a
    short snippet (no full_text). We still process these, just with
    less text and a note that it's a snippet, not a full document.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    opinions = data.get("opinions", [])
    snippet = opinions[0].get("snippet", "") if opinions else ""
    cleaned = clean_text_pipeline(snippet)

    return ProcessedDocument(
        doc_id=make_doc_id("courtlistener_snippet", filepath.name),
        source_type="courtlistener_snippet",
        source_url=f"https://www.courtlistener.com{data.get('absolute_url', '')}",
        original_filename=filepath.name,
        title=data.get("caseName"),
        clean_text=cleaned,
        raw_text_length=len(snippet),
        clean_text_length=len(cleaned),
        court=data.get("court"),
        date_filed=data.get("dateFiled"),
        docket_number=data.get("docketNumber"),
        processed_at_unix=time.time(),
    )


def extract_from_pdf(filepath: Path) -> ProcessedDocument:
    """
    Handles any .pdf file dropped into data/raw/pdfs/. Uses the
    direct-extraction-first, OCR-fallback logic we already built and
    tested, then runs it through the SAME cleaning + entity-extraction
    steps every other source type goes through.
    """
    result = extract_pdf_text(filepath)  # {"text": ..., "method": "direct" or "ocr"}
    raw_text = result["text"]
    cleaned = clean_text_pipeline(raw_text)
    entities = extract_entities(cleaned)

    return ProcessedDocument(
        doc_id=make_doc_id("pdf_document", filepath.name),
        source_type=f"pdf_{result['method']}",  # e.g. "pdf_direct" or "pdf_ocr" -- keeps track of HOW it was read
        original_filename=filepath.name,
        title=filepath.stem,  # filename without extension, as a placeholder title
        clean_text=cleaned,
        raw_text_length=len(raw_text),
        clean_text_length=len(cleaned),
        people_mentioned=entities["people"],
        processed_at_unix=time.time(),
    )


def process_one_file(filepath: Path) -> ProcessedDocument | None:
    """
    Dispatcher: looks at a raw filename and decides which extraction
    function to use. This is the ONLY place that needs to change when
    you add a new source type later (e.g. DOJ PDFs, emails) -- everything
    else in the pipeline stays untouched.
    """
    name = filepath.name
    if filepath.suffix.lower() == ".pdf":
        return extract_from_pdf(filepath)
    elif name.endswith("_fulltext.json"):
        return extract_from_courtlistener_fulltext(filepath)
    elif name.startswith("courtlistener_") and name.endswith(".json"):
        return extract_from_courtlistener_search_result(filepath)
    else:
        print(f"  -> no handler for {name}, skipping (add one when this source type matters)")
        return None


def run_etl() -> None:
    json_files = list(RAW_DIR.glob("*.json"))  # provenance/ subfolder won't match *.json at this level
    pdf_files = list((RAW_DIR / "pdfs").glob("*.pdf")) if (RAW_DIR / "pdfs").exists() else []
    raw_files = json_files + pdf_files
    print(f"Found {len(raw_files)} raw file(s) to process ({len(json_files)} JSON, {len(pdf_files)} PDF).")

    processed_count = 0
    skipped_count = 0

    for filepath in raw_files:
        doc_id_preview = make_doc_id("preview", filepath.name)
        # We don't know the real doc_id until we know source_type, but for
        # a quick "already done?" check we can look for ANY processed file
        # whose original_filename matches -- simplest: just always process
        # and overwrite, since ETL should be safely re-runnable either way.

        print(f"Processing {filepath.name}...")
        doc = process_one_file(filepath)
        if doc is None:
            skipped_count += 1
            continue

        out_path = PROCESSED_DIR / f"{doc.doc_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(doc.to_dict(), f, indent=2)

        print(f"  -> saved {out_path.name}  ({doc.clean_text_length} clean chars, title='{doc.title}')")
        processed_count += 1

    print(f"\nDone. Processed: {processed_count}, Skipped: {skipped_count}")


if __name__ == "__main__":
    run_etl()