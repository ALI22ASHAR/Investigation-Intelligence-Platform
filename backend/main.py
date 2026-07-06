"""
backend/main.py

Purpose: expose the RAG pipeline (rag/rag_pipeline.py) as a real HTTP
API, so a frontend (or any other client) can send a question over the
network and get back an answer + sources as JSON.
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent / "rag"))
sys.path.append(str(Path(__file__).resolve().parent.parent / "database"))
from rag_pipeline import answer_question
from connection import get_session
from models import Document

app = FastAPI(title="Investigation Intelligence Platform API")

# CORS (Cross-Origin Resource Sharing): by default, browsers BLOCK a
# webpage on one origin (e.g. http://localhost:5173, your future React
# app) from calling an API on a different origin (http://localhost:8000,
# this backend) -- a security default. This middleware explicitly says
# "it's fine, allow requests from anywhere" -- appropriate for local
# development; you'd restrict allow_origins to your real domain in
# production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    """
    Pydantic model describing the expected shape of an incoming request
    body. FastAPI uses this to automatically: validate incoming JSON
    (reject requests missing "question", or with the wrong type),
    generate API documentation, and give you a typed Python object
    instead of a raw untyped dict.
    """
    question: str
    n_results: int = 5  # default value -- caller doesn't have to specify this


class SourceItem(BaseModel):
    doc_id: str
    title: str
    source_url: str | None
    distance: float
    chunk_preview: str
    people_mentioned: list[str]


class AnswerResponse(BaseModel):
    """Describes the shape of what we send BACK -- FastAPI validates this too."""
    answer: str
    sources: list[SourceItem]


@app.get("/")
def health_check():
    """
    A minimal endpoint just to confirm the server is alive. Hitting
    http://localhost:8000/ in a browser should return this JSON.
    """
    return {"status": "ok", "service": "Investigation Intelligence Platform"}


@app.get("/stats")
def get_stats():
    """
    Returns real counts from the database -- used by the frontend
    sidebar footer ("N sources indexed") instead of a hardcoded/fake
    number. A tiny endpoint, but it's the difference between a UI
    element that LOOKS real and one that actually IS real.
    """
    session = get_session()
    document_count = session.query(Document).count()
    session.close()
    return {"document_count": document_count}


@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    """
    The main endpoint. FastAPI automatically:
      - parses the incoming JSON body into a QuestionRequest object
      - validates it (e.g. rejects a request with no "question" field)
      - calls this function with that validated object
      - serializes whatever we return into a JSON response

    request.question and request.n_results are typed, auto-completed
    attributes -- not raw dict lookups like request["question"].
    """
    result = answer_question(request.question, n_results=request.n_results)
    return result


if __name__ == "__main__":
    import uvicorn
    # reload=True auto-restarts the server whenever you save a code
    # change -- extremely useful during development, should be turned
    # off in a real production deployment.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
