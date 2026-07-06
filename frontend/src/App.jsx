// frontend/src/App.jsx
//
// v4: adds a sidebar with multiple conversation "threads" (like the
// mockup), suggested-question starter pills on the empty state, and a
// real document-count footer pulled from the backend's /stats endpoint.
//
// Data model change from v3: instead of one flat `history` array, we
// now have `threads` -- an array of {id, title, history} objects -- and
// `activeThreadId` tracking which one is currently shown. This is the
// standard shape for any "multiple conversations" UI (Slack channels,
// ChatGPT's chat list, email threads, etc.).

import { useState, useRef, useEffect } from "react";
import "./App.css";

const LIVE_STORAGE_KEY = "ask-the-record.threads.v1";

const SUGGESTED_QUESTIONS = [
  "How many cases are indexed?",
  "Which court, city and country?",
  "Who are the parties involved?",
  "What was the court's ruling?",
  "Who won?",
];

function makeThread() {
  return { id: crypto.randomUUID(), title: null, history: [] };
}

function loadThreadState(storageKey, createFallbackThread) {
  if (typeof window === "undefined") {
    const thread = createFallbackThread();
    return { threads: [thread], activeThreadId: thread.id };
  }

  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      const thread = createFallbackThread();
      return { threads: [thread], activeThreadId: thread.id };
    }

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed.threads) || parsed.threads.length === 0) {
      const thread = createFallbackThread();
      return { threads: [thread], activeThreadId: thread.id };
    }

    const activeThreadId =
      parsed.activeThreadId && parsed.threads.some((thread) => thread.id === parsed.activeThreadId)
        ? parsed.activeThreadId
        : parsed.threads[0].id;

    return { threads: parsed.threads, activeThreadId };
  } catch {
    const thread = createFallbackThread();
    return { threads: [thread], activeThreadId: thread.id };
  }
}

function loadSavedState() {
  return loadThreadState(LIVE_STORAGE_KEY, makeThread);
}

function App() {
  const [{ threads: initialThreads, activeThreadId: initialActiveThreadId }] = useState(() =>
    loadSavedState()
  );
  const [threads, setThreads] = useState(initialThreads);
  const [activeThreadId, setActiveThreadId] = useState(initialActiveThreadId);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSource, setExpandedSource] = useState(null);
  const [documentCount, setDocumentCount] = useState(null);
  const [backendReady, setBackendReady] = useState(false);

  const messagesEndRef = useRef(null);
  const BACKEND_URL = "http://localhost:8000";

  const activeThread = threads.find((t) => t.id === activeThreadId);

  // Poll the backend's health endpoint every 1.5s until it actually
  // responds, instead of assuming it's ready the instant the page
  // loads. This is what fixes the "first request fails, second one
  // works" pattern -- we now WAIT for real readiness instead of
  // guessing.
  useEffect(() => {
    let cancelled = false;

    async function pollUntilReady() {
      while (!cancelled) {
        try {
          const res = await fetch(`${BACKEND_URL}/`);
          if (res.ok) {
            if (!cancelled) setBackendReady(true);
            return; // stop polling once we get a real success
          }
        } catch {
          // Backend not reachable yet -- completely expected during
          // startup, so we deliberately do NOT show this as an error.
          // Just wait and try again.
        }
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
    }

    pollUntilReady();
    return () => {
      cancelled = true; // stop polling if the component unmounts
    };
  }, []);

  // Fetch the real indexed-document count once the backend is ready,
  // for the sidebar footer -- a genuine number from Postgres, not a
  // placeholder.
  useEffect(() => {
    if (!backendReady) return;
    fetch(`${BACKEND_URL}/stats`)
      .then((r) => r.json())
      .then((data) => setDocumentCount(data.document_count))
      .catch(() => setDocumentCount(null));
  }, [backendReady]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeThread?.history, loading]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(LIVE_STORAGE_KEY, JSON.stringify({ threads, activeThreadId }));
  }, [threads, activeThreadId]);

  async function sendQuestion(text) {
    if (!text.trim() || !backendReady) return;

    setQuestion("");
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, n_results: 5 }),
      });

      if (!response.ok) throw new Error(`Server responded with status ${response.status}`);
      const data = await response.json();

      setThreads((prev) =>
        prev.map((t) =>
          t.id === activeThreadId
            ? {
                ...t,
                // First question in a thread becomes its sidebar title,
                // truncated -- same convention ChatGPT/Slack use.
                title: t.title ?? (text.length > 40 ? text.slice(0, 40) + "…" : text),
                history: [...t.history, { question: text, answer: data.answer, sources: data.sources }],
              }
            : t
        )
      );
    } catch (err) {
      setError(`Couldn't reach the backend. Is it running at ${BACKEND_URL}? (${err.message})`);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion(question);
    }
  }

  function startNewThread() {
    const fresh = makeThread();
    setThreads((prev) => [fresh, ...prev]);
    setActiveThreadId(fresh.id);
    setError(null);
  }

  function toggleSource(turnIndex, sourceIndex) {
    const key = `${turnIndex}-${sourceIndex}`;
    setExpandedSource(expandedSource === key ? null : key);
  }

  return (
    <div className="app-shell">
      {/* --- Sidebar --- */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-badge">IIP</div>
          <div>
            <div className="brand-title">Ask the Record</div>
            <div className="brand-subtitle">Investigation Intelligence</div>
          </div>
        </div>

        <button className="new-thread-button" onClick={startNewThread}>
          + New investigation
        </button>

        <div className="thread-list-label">Recent threads</div>
        <div className="thread-list">
          {threads.map((t) => (
            <button
              key={t.id}
              className={`thread-item ${t.id === activeThreadId ? "thread-item-active" : ""}`}
              onClick={() => setActiveThreadId(t.id)}
            >
              {t.title ?? "New investigation"}
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <span>{documentCount !== null ? `${documentCount} sources indexed` : ""}</span>
          <span>v0.4</span>
        </div>
      </aside>

      {/* --- Main chat panel --- */}
      <main className="main-panel">
        <header className="app-header">
          <div>
            <div className="app-title">Case Record Assistant</div>
          </div>
          <span className="header-pill">answers cite source documents</span>
        </header>

        <div className="message-list">
          {activeThread.history.length === 0 && !loading && (
            <div className="empty-state">
              <span className="empty-eyebrow">Investigation Intelligence Platform</span>
              <h1>Ask the record.</h1>
              <p>
                Answers are generated only from indexed source documents, with citations
                attached. Ask a follow-up any time — this is a running conversation, not a
                single query.
              </p>

              <div className="suggested-questions">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button key={q} className="suggested-pill" onClick={() => sendQuestion(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeThread.history.map((turn, turnIndex) => (
            <div key={turnIndex} className="turn">
              <div className="message message-user">
                <div className="bubble bubble-user">{turn.question}</div>
              </div>

              <div className="message message-assistant">
                <div className="avatar">◈</div>
                <div className="bubble bubble-assistant">
                  <p className="answer-text">{turn.answer}</p>

                  {turn.sources.length > 0 && (
                    <div className="source-list">
                      {turn.sources.map((s, sourceIndex) => {
                        const key = `${turnIndex}-${sourceIndex}`;
                        const isOpen = expandedSource === key;
                        return (
                          <div key={sourceIndex} className="source-card">
                            <button
                              className="source-card-header"
                              onClick={() => toggleSource(turnIndex, sourceIndex)}
                            >
                              <span className="source-tag">{sourceIndex + 1}</span>
                              <span className="source-title">{s.title}</span>
                              <span className="source-toggle">{isOpen ? "−" : "+"}</span>
                            </button>

                            {isOpen && (
                              <div className="source-card-body">
                                <p className="source-chunk-preview">{s.chunk_preview}…</p>

                                {s.people_mentioned.length > 0 && (
                                  <div className="entity-chips">
                                    {s.people_mentioned.map((person, i) => (
                                      <span key={i} className="entity-chip">
                                        {person}
                                      </span>
                                    ))}
                                  </div>
                                )}

                                {s.source_url && (
                                  <a
                                    href={s.source_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="source-link"
                                  >
                                    view full record ↗
                                  </a>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="message message-assistant">
              <div className="avatar">◈</div>
              <div className="bubble bubble-assistant bubble-loading">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          )}

          {error && <div className="error-box">{error}</div>}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          {!backendReady && (
            <div className="connecting-banner">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span>Connecting to backend…</span>
            </div>
          )}
          <div className="input-bar">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                backendReady
                  ? "Ask about a case, party, court, or verdict…"
                  : "Waiting for backend to finish starting up…"
              }
              className="query-input"
              rows={1}
              disabled={!backendReady}
            />
            <button
              onClick={() => sendQuestion(question)}
              disabled={loading || !backendReady}
              className="query-button"
            >
              →
            </button>
          </div>
          <p className="input-disclaimer">
            Ask the Record answers only from indexed documents. It will say so when a source
            isn't in the index.
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
