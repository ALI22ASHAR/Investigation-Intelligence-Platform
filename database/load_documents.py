"""
database/load_documents.py

Purpose: read every processed JSON file from data/processed/ and load it
into the "documents" table -- inserting new rows, or updating existing
ones if a document with the same doc_id already exists (an "upsert").

This is meant to be safely re-runnable: run it after every ETL pass,
and it'll just sync whatever's new/changed.
"""

import json
from pathlib import Path

from connection import get_session
from models import Document

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def load_one_document(session, filepath: Path) -> str:
    """
    Loads a single processed JSON file into the database.
    Returns "inserted", "updated", or "error" for simple reporting.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc_id = data.get("doc_id")
    if not doc_id:
        return "error"

    # session.get(Model, primary_key) is SQLAlchemy's way of asking
    # "does a row with this primary key already exist?" -- returns the
    # matching object, or None if there isn't one yet.
    existing = session.get(Document, doc_id)

    if existing:
        # UPDATE path: modify the fields on the existing Python object.
        # SQLAlchemy tracks these changes automatically -- we don't write
        # any SQL "UPDATE ... SET ..." ourselves.
        for field in [
            "source_type", "source_url", "original_filename", "title",
            "clean_text", "raw_text_length", "clean_text_length",
            "court", "date_filed", "docket_number", "people_mentioned",
            "processed_at_unix", "sha256_of_source",
        ]:
            setattr(existing, field, data.get(field))
        return "updated"
    else:
        # INSERT path: build a brand-new Document object from the dict
        # using **data (unpacks the dict's key-value pairs as keyword
        # arguments -- e.g. {"doc_id": "abc"} becomes doc_id="abc").
        # Only pass fields that actually exist as columns to avoid errors
        # if the JSON has extra keys we don't store.
        valid_fields = {c.name for c in Document.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        new_doc = Document(**filtered_data)
        session.add(new_doc)
        return "inserted"


def load_all_documents():
    session = get_session()
    processed_files = list(PROCESSED_DIR.glob("*.json"))
    print(f"Found {len(processed_files)} processed file(s) to load.")

    counts = {"inserted": 0, "updated": 0, "error": 0}

    for filepath in processed_files:
        result = load_one_document(session, filepath)
        counts[result] += 1
        print(f"  {filepath.name}: {result}")

    # Nothing is actually saved to Postgres until commit() is called --
    # everything above happens in an in-memory "pending" state first.
    # This means if something goes wrong partway through, you can
    # session.rollback() instead of leaving a half-written mess.
    session.commit()
    session.close()

    print(f"\nDone. Inserted: {counts['inserted']}, Updated: {counts['updated']}, Errors: {counts['error']}")


if __name__ == "__main__":
    load_all_documents()