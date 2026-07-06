# Investigation Intelligence Platform

Investigation Intelligence Platform is a local RAG application for searching and questioning indexed legal and investigative source documents. It combines a FastAPI backend, a React/Vite frontend, a PostgreSQL database, and a Chroma vector store to answer questions with source-backed citations.

## What it does

- Ask questions about indexed case records and source documents.
- Get answers with cited source chunks and document metadata.
- Browse multi-turn conversation threads in the UI.
- See how many documents are currently indexed.
- Run the full stack locally with Docker or run the backend and frontend separately during development.

## Architecture

- `backend/` exposes the HTTP API used by the frontend.
- `frontend/` contains the React/Vite chat interface.
- `database/` manages the SQLAlchemy connection and document models.
- `rag/` contains the retrieval and answer-generation pipeline.
- `embeddings/` contains the chunking and vector-store indexing utilities.
- `ingestion/` contains scripts for collecting source material.
- `preprocessing/` contains text cleanup and entity extraction helpers.
- `data/` stores local working data such as raw inputs, processed outputs, and the Chroma database.

## Requirements

- Python 3.11 or newer
- Node.js 18 or newer
- PostgreSQL
- Ollama, if you want local model inference
- Docker and Docker Compose, if you want the containerized setup

## Quick Start

### Option 1: Docker

1. Create a `.env` file in the project root based on `.env.example`.
2. Make sure PostgreSQL and Ollama are available at the hosts configured in `.env`.
3. Start the stack:

```bash
docker compose up --build
```

4. Open the frontend in your browser at the Vite port exposed by the compose setup.

### Option 2: Local development

1. Create and activate a Python virtual environment.
2. Install backend dependencies:

```bash
pip install -r requirements.txt
```

3. Install frontend dependencies:

```bash
cd frontend
npm install
```

4. Start the backend:

```bash
python backend/main.py
```

5. In another terminal, start the frontend:

```bash
cd frontend
npm run dev
```

## Environment Variables

The backend reads these values from the project root `.env` file:

- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `COURTLISTENER_API_TOKEN`
- `OLLAMA_URL`

Copy `.env.example` to `.env` and fill in the real values before running the app.

## Repository Notes

- Generated local data under `data/chroma_db/`, `data/raw/`, `data/processed/`, `data/emails/`, and `data/images/` is ignored so the repo stays lightweight.
- The frontend chat history now persists in the browser with localStorage.
- The backend API exposes `/`, `/stats`, and `/ask`.

## Useful Commands

```bash
# Start the backend locally
python backend/main.py

# Build the frontend
npm --prefix frontend run build

# Run Docker Compose
docker compose up --build
```