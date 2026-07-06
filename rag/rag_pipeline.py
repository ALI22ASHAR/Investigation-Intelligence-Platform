"""
rag/rag_pipeline.py

Purpose: the actual "ask a question, get a grounded answer with
citations" pipeline. Combines:
  - Phase 6's semantic search (retrieval)
  - A local LLM via Ollama (generation)

This is the point where your platform stops being "a database with
search" and becomes something you can actually converse with about
your documents.
"""

import os
import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parent.parent / "embeddings"))
sys.path.append(str(Path(__file__).resolve().parent.parent / "database"))
from generate_embeddings import embed_text
from vector_store import collection
from connection import get_session
from models import Document
from query_router import classify_question

# Ollama runs as a local background service after installation -- this
# is its default local API address. No API key needed since nothing
# leaves your machine.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL_NAME = "llama3.2"  # must match a model you've pulled with `ollama pull`


def answer_count_documents() -> dict:
    """
    Answers "how many cases/documents/verdicts" with a REAL count from
    Postgres -- a single, fast, always-correct query, instead of
    guessing from a handful of semantically-retrieved text chunks.
    """
    session = get_session()
    count = session.query(Document).count()
    session.close()
    return {
        "answer": f"There are {count} documents currently indexed in the system.",
        "sources": [],
    }


def answer_list_courts() -> dict:
    """
    Answers "which courts" with the actual DISTINCT set of courts in
    the database -- a proper aggregate query, not a text-similarity
    guess.
    """
    session = get_session()
    # .distinct() at the SQL level means Postgres itself removes
    # duplicates before sending results back -- more efficient than
    # fetching everything and de-duplicating in Python.
    rows = session.query(Document.court).distinct().all()
    session.close()

    # Each row is a one-element tuple like ("Supreme Court of NY",) --
    # unpack and filter out None/empty values (some sources don't have
    # court metadata, per Phase 3's schema design).
    courts = sorted({r[0] for r in rows if r[0]})

    if not courts:
        return {"answer": "No court information is recorded in the indexed documents.", "sources": []}

    answer = "The indexed documents come from the following court(s):\n" + "\n".join(
        f"- {c}" for c in courts
    )
    return {"answer": answer, "sources": []}


def answer_list_people() -> dict:
    """
    Answers "who are the people/parties" by aggregating the
    people_mentioned field (populated back in Phase 10's entity
    extraction) across EVERY document -- a real cross-document
    aggregate, which semantic search over individual chunks could
    never assemble correctly on its own.
    """
    session = get_session()
    rows = session.query(Document.people_mentioned).all()
    session.close()

    # Each row's people_mentioned is a JSON list (possibly empty/None).
    # Flatten every document's list into one combined set, deduplicating
    # as we go -- the same set() pattern from Phase 10.
    all_people = set()
    for (people,) in rows:
        if people:
            all_people.update(people)

    if not all_people:
        return {"answer": "No named people were extracted from the indexed documents.", "sources": []}

    sorted_people = sorted(all_people)
    answer = f"{len(sorted_people)} distinct people are mentioned across the indexed documents:\n" + "\n".join(
        f"- {p}" for p in sorted_people
    )
    return {"answer": answer, "sources": []}


def retrieve_chunks(question: str, n_results: int = 5) -> list[dict]:
    """
    Runs the same semantic search from Phase 6, but returns the results
    as a list of clean dicts (rather than Chroma's raw nested-list
    format) -- easier for the rest of this pipeline to work with.
    """
    query_vector = embed_text(question)
    results = collection.query(query_embeddings=[query_vector], n_results=n_results)

    chunks = []
    for text, meta, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        chunks.append({"text": text, "meta": meta, "distance": distance})
    return chunks


def build_context_block(chunks: list[dict]) -> str:
    """
    Formats retrieved chunks into a labeled block of text to hand the
    LLM. Each chunk is tagged with a [Source N] label so we can later
    ask the model to cite sources by that same label -- and so a human
    reading the raw prompt (great for debugging) can see exactly what
    the model was given.
    """
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        title = chunk["meta"].get("title", "Unknown document")
        parts.append(f"[Source {i}: {title}]\n{chunk['text']}")
    return "\n\n".join(parts)


def get_people_by_doc_id(doc_ids: list[str]) -> dict[str, list[str]]:
    """
    Fetches people_mentioned for a batch of documents in ONE database
    query (using .in_(doc_ids)) rather than one query per document --
    avoiding the classic "N+1 query" performance problem, where you'd
    otherwise hit the database once per source instead of once total.
    """
    session = get_session()
    rows = session.query(Document.doc_id, Document.people_mentioned).filter(
        Document.doc_id.in_(doc_ids)
    ).all()
    session.close()
    return {doc_id: (people or []) for doc_id, people in rows}


def answer_question(question: str, n_results: int = 5) -> dict:
    """
    The full pipeline. NEW: routes aggregate/count/list questions to
    real SQL queries FIRST, since semantic search over a handful of
    chunks can never correctly answer "how many" or "which distinct X"
    questions -- those require looking at every row, not the most
    similar few.

    Only questions that don't match a known aggregate pattern fall
    through to the normal retrieve-then-generate RAG pipeline below.
    """
    question_type = classify_question(question)

    if question_type == "count_documents":
        return answer_count_documents()
    elif question_type == "list_courts":
        return answer_list_courts()
    elif question_type == "list_people":
        return answer_list_people()
    # else: question_type == "semantic" -- fall through to RAG as normal

    chunks = retrieve_chunks(question, n_results=n_results)

    if not chunks:
        return {"answer": "No relevant documents found in the index.", "sources": []}

    context_block = build_context_block(chunks)

    # Fetch people_mentioned for every source document in one batched
    # lookup, keyed by doc_id, so we can attach it to each source below.
    doc_ids = [c["meta"]["doc_id"] for c in chunks]
    people_by_doc = get_people_by_doc_id(doc_ids)

    # This system prompt is the most important part of the whole RAG
    # pipeline to get right: it explicitly instructs the model to stick
    # to the provided context and cite sources, rather than freely
    # generating from its own general knowledge.
    system_prompt = (
        "You are an investigative research assistant. Answer the user's "
        "question using ONLY the information in the provided sources below. "
        "If the sources don't contain enough information to answer, say so "
        "clearly instead of guessing. When you state a fact, cite it using "
        "the matching [Source N] label.\n\n"
        f"SOURCES:\n{context_block}"
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                "stream": False,  # get the whole answer back at once, not word-by-word
            },
            timeout=120,  # local models on CPU can be slow -- give it real time
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return {
            "answer": (
                "Could not reach Ollama at localhost:11434. Make sure Ollama "
                "is installed and running (it should start automatically after "
                "installation, or run `ollama serve` manually)."
            ),
            "sources": [],
        }

    data = response.json()

    # Ollama's chat response shape: {"message": {"role": "assistant", "content": "..."}}
    answer_text = data["message"]["content"]

    return {
        "answer": answer_text,
        "sources": [
            {
                "doc_id": c["meta"]["doc_id"],
                "title": c["meta"]["title"],
                "source_url": c["meta"]["source_url"],
                "distance": c["distance"],
                "chunk_preview": c["text"][:400],  # enough to show context, not the whole chunk
                "people_mentioned": people_by_doc.get(c["meta"]["doc_id"], []),
            }
            for c in chunks
        ],
    }


if __name__ == "__main__":
    result = answer_question("What was the court's ruling in these cases?")
    print("ANSWER:\n")
    print(result["answer"])
    print("\nSOURCES USED:")
    for s in result["sources"]:
        print(f"  - {s['title']}  ({s['source_url']})")