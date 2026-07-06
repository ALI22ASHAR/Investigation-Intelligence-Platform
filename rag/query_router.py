"""
rag/query_router.py

Purpose: look at a question BEFORE doing any semantic search, and
decide whether it's really asking for something structural (a count,
a list of distinct values across the whole dataset) versus a specific
factual lookup that semantic search + an LLM can actually answer.

This is a simple, explainable, pattern-based router -- not an LLM call
itself. Keeping it simple and fast means every question gets checked
here for free before the (much slower) RAG pipeline ever runs.
"""

import re


def classify_question(question: str) -> str:
    """
    Returns one of: "count_documents", "list_courts", "list_people",
    or "semantic" (the default -- handled by the normal RAG pipeline).

    Uses simple regex pattern matching on common phrasings. This is
    deliberately NOT trying to be a full NLP intent classifier --
    it's a fast, transparent first pass that catches the most common
    aggregate-question patterns. Anything it doesn't recognize falls
    through to semantic search, which is always a safe default.
    """
    q = question.lower()

    # "how many cases/documents/verdicts/opinions are there/indexed"
    if re.search(r"how many (cases|documents|verdicts|opinions|records|files)", q):
        return "count_documents"

    # "which/what courts" or "list (all) courts"
    if re.search(r"(which|what) courts?\b", q) or re.search(r"list (all )?courts?\b", q):
        return "list_courts"

    # "who are the people/parties" or "list people/parties mentioned"
    if re.search(r"(who are|list) (the )?(people|parties|persons)", q):
        return "list_people"

    return "semantic"


if __name__ == "__main__":
    # Quick self-test with a handful of real and near-miss phrasings.
    test_questions = [
        "How many cases are indexed?",
        "how many verdicts are in the documents",
        "Which courts are represented here?",
        "list all courts",
        "Who are the people involved?",
        "What was the court's ruling in Hansraj v Epstein?",  # should stay "semantic"
        "Tell me about the weather",  # should stay "semantic"
    ]
    for tq in test_questions:
        print(f"{classify_question(tq):18s} <- {tq!r}")