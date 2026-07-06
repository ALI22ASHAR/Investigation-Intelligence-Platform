"""
embeddings/index_documents.py

Purpose: the pipeline that actually makes semantic search possible.

For every document in Postgres:
  1. Split its clean_text into overlapping chunks (Phase 5 logic)
  2. Generate an embedding vector for each chunk (Phase 5 model)
  3. Store each chunk's vector + text + metadata in Chroma (this phase)

Run this after loading new documents into Postgres (Phase 4), any time
you want the vector index to catch up with what's in the database.
"""

import sys
from pathlib import Path

# Add sibling folders to the import path so this script (living in
# embeddings/) can import modules from database/ and preprocessing/.
# This is a common pattern in small multi-folder Python projects that
# don't (yet) use a formal installable package structure.
sys.path.append(str(Path(__file__).resolve().parent.parent / "database"))

from chunking import chunk_text
from generate_embeddings import embed_many
from vector_store import collection
from connection import get_session
from models import Document


def index_all_documents(chunk_size: int = 1000, overlap: int = 150) -> None:
    session = get_session()
    documents = session.query(Document).all()
    print(f"Found {len(documents)} document(s) in the database to index.")

    for doc in documents:
        if not doc.clean_text or len(doc.clean_text.strip()) == 0:
            print(f"  Skipping {doc.doc_id} ({doc.title}): no text to index.")
            continue

        chunks = chunk_text(doc.clean_text, chunk_size=chunk_size, overlap=overlap)
        print(f"  {doc.doc_id} ({doc.title}): {len(chunks)} chunk(s)")

        # Batch-embed ALL chunks for this document in one call --
        # far faster than embedding one at a time (Phase 5 note).
        chunk_texts = [c.text for c in chunks]
        vectors = embed_many(chunk_texts)

        # Chroma's add() wants PARALLEL lists: one entry per chunk across
        # ids, embeddings, documents (the raw text), and metadatas.
        # Building these as separate lists (rather than one big object
        # per chunk) is just what Chroma's API expects.
        ids = [f"{doc.doc_id}_chunk{c.chunk_index}" for c in chunks]
        metadatas = [
            {
                "doc_id": doc.doc_id,
                "title": doc.title or "",
                "source_type": doc.source_type or "",
                "source_url": doc.source_url or "",
                "chunk_index": c.chunk_index,
                "char_start": c.char_start,
                "char_end": c.char_end,
            }
            for c in chunks
        ]

        # upsert() (not add()) means: insert new ones, or overwrite if an
        # id already exists -- safe to re-run this whole script without
        # creating duplicate chunks every time.
        collection.upsert(
            ids=ids,
            embeddings=vectors,
            documents=chunk_texts,
            metadatas=metadatas,
        )

    session.close()
    print(f"\nDone indexing. Total chunks in collection now: {collection.count()}")


if __name__ == "__main__":
    index_all_documents()