"""
embeddings/vector_store.py

Purpose: create/connect to a persistent Chroma vector database, and
expose a "collection" -- Chroma's term for a named set of vectors,
similar in spirit to a table in a normal database.
"""

from pathlib import Path

import chromadb

# PersistentClient saves data to disk at this path, so your indexed
# vectors survive between script runs (an in-memory-only client would
# lose everything the moment your script ends).
CHROMA_DIR = Path(__file__).resolve().parent.parent / "data" / "chroma_db"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

client = chromadb.PersistentClient(path=str(CHROMA_DIR))

# get_or_create_collection: fetches the collection if it already exists,
# or creates a fresh one if this is the first run. Safe to call every time.
collection = client.get_or_create_collection(
    name="document_chunks",
    metadata={"hnsw:space": "cosine"},
    # "hnsw:space": "cosine" tells Chroma to use cosine similarity
    # (the same metric from our Phase 5 similarity test) when comparing
    # vectors internally -- matching the metric the embedding model
    # itself was designed and evaluated with.
)


if __name__ == "__main__":
    print(f"Chroma collection '{collection.name}' ready.")
    print(f"Current chunk count in collection: {collection.count()}")