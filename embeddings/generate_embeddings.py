"""
embeddings/generate_embeddings.py

Purpose: load a local embedding model (downloaded once, then cached),
and provide a simple function to turn a piece of text into a vector
(a list of floating-point numbers).
"""

from sentence_transformers import SentenceTransformer

# "all-MiniLM-L6-v2" is a small, fast, well-regarded general-purpose
# embedding model -- about 80MB, runs fine on CPU (no GPU required),
# and produces 384-dimensional vectors. Good default for learning and
# for most real small-to-medium projects.
#
# Loading the model is SLOW (a few seconds) -- we do it ONCE at module
# level (not inside a function), so it only happens once no matter how
# many times embed_text() gets called afterward.
print("Loading embedding model (first run will download it, ~80MB)...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("Model loaded.")


def embed_text(text: str) -> list[float]:
    """
    Converts a string into an embedding vector.

    model.encode() can actually take a LIST of strings and embed them
    all at once (much faster than one at a time, since it batches the
    computation) -- we wrap it here to keep the single-text case simple,
    but see embed_many() below for the efficient batch version.
    """
    vector = model.encode(text)
    return vector.tolist()  # numpy array -> plain Python list, so it's JSON-serializable


def embed_many(texts: list[str]) -> list[list[float]]:
    """
    Embeds many texts in one batched call -- significantly faster than
    calling embed_text() in a loop, because the underlying model can
    process multiple inputs in parallel instead of one at a time.
    """
    vectors = model.encode(texts, show_progress_bar=True)
    return [v.tolist() for v in vectors]


if __name__ == "__main__":
    # Quick sanity check: embed two similar sentences and one unrelated
    # one, then confirm the similar pair is actually "closer" numerically.
    import numpy as np

    a = embed_text("The defendant pleaded guilty to all charges.")
    b = embed_text("He admitted to the crimes in court.")
    c = embed_text("The weather in Tokyo is sunny today.")

    def cosine_similarity(v1, v2):
        v1, v2 = np.array(v1), np.array(v2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    print(f"Similarity (related sentences a vs b):   {cosine_similarity(a, b):.3f}")
    print(f"Similarity (unrelated sentences a vs c):  {cosine_similarity(a, c):.3f}")
    print("\n(Expect the first number noticeably higher than the second --")
    print(" that's semantic similarity working as intended.)")