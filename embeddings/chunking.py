"""
embeddings/chunking.py

Purpose: split a long clean_text string into smaller overlapping
"chunks" -- the pieces we'll actually generate embeddings for and
search over later, instead of whole documents.
"""

from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_index: int      # position of this chunk within its parent document (0, 1, 2...)
    text: str
    char_start: int        # where this chunk starts in the ORIGINAL text (useful for citations later)
    char_end: int


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[Chunk]:
    """
    Splits text into chunks of roughly `chunk_size` characters, with
    `overlap` characters shared between consecutive chunks.

    WHY OVERLAP? Imagine a sentence gets cut right at a chunk boundary --
    "The defendant was found" | "guilty on all counts." Split cleanly in
    half, NEITHER chunk contains the full, useful statement. Overlap
    means the end of one chunk is repeated at the start of the next, so
    important sentences near a boundary usually survive intact in at
    least one chunk.

    We're using a simple character-based sliding window here (not
    sentence-aware splitting) because it's easy to understand and
    reason about first. A more advanced version could split on sentence
    boundaries -- worth revisiting once the basic pipeline works end to end.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap, or chunks would never advance.")

    chunks: list[Chunk] = []
    start = 0
    index = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_text_slice = text[start:end]

        chunks.append(Chunk(
            chunk_index=index,
            text=chunk_text_slice,
            char_start=start,
            char_end=end,
        ))

        if end == text_length:
            # We've reached the end of the text -- stop, don't create a
            # tiny trailing chunk from the overlap logic below.
            break

        # Move the window forward by (chunk_size - overlap), NOT by the
        # full chunk_size -- this is what creates the overlapping region
        # between this chunk and the next one.
        start += (chunk_size - overlap)
        index += 1

    return chunks


if __name__ == "__main__":
    # Self-test: a short fake document, using tiny chunk_size/overlap
    # values so we can actually see the overlap happening in the printout.
    sample_text = (
        "This is sentence one. This is sentence two. This is sentence three. "
        "This is sentence four. This is sentence five. This is sentence six."
    )
    result = chunk_text(sample_text, chunk_size=40, overlap=10)
    for c in result:
        print(f"[chunk {c.chunk_index}] ({c.char_start}-{c.char_end}): {c.text!r}")