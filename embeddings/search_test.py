"""
embeddings/search_test.py

Purpose: prove the whole pipeline works by running a real semantic
search query against the indexed chunks and inspecting the results.
"""

from generate_embeddings import embed_text
from vector_store import collection


def search(query: str, n_results: int = 3):
    query_vector = embed_text(query)

    # collection.query() finds the n_results chunks whose stored vectors
    # are closest (by cosine similarity, per our earlier config) to the
    # query vector -- this is the actual "semantic search" operation.
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
    )

    print(f"\nQuery: {query!r}\n")
    # Chroma returns parallel lists again, nested one level for
    # multi-query support -- we only sent one query, so we index [0].
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for i, (text, meta, distance) in enumerate(zip(documents, metadatas, distances)):
        print(f"--- Result {i+1} (distance={distance:.4f}) ---")
        print(f"From: {meta['title']}  (chunk {meta['chunk_index']})")
        print(text[:300] + ("..." if len(text) > 300 else ""))
        print()


if __name__ == "__main__":
    # Try a couple of different queries -- including one phrased very
    # differently from the source text, to demonstrate semantic (not
    # just keyword) matching.
    search("What was the court's ruling?")
    search("custody dispute between family members")