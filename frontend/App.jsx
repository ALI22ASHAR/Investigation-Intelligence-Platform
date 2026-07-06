// frontend/src/App.jsx
//
// v2: adds conversation history (multiple Q&A pairs stacked, not just
// one), expandable source cards showing the actual retrieved chunk
// text, and entity chips showing people mentioned in each source.

import { useState } from "react";
import "./App.css";

function App() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]); // array of {question, answer, sources} objects
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSource, setExpandedSource] = useState(null); // "turnIndex-sourceIndex" or null

  const BACKEND_URL = "http://localhost:8000";

  async function handleAsk() {
    if (!question.trim()) return;

    const currentQuestion = question;
    setQuestion(""); // clear the input immediately, like a normal chat UI
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: currentQuestion, n_results: 5 }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`);
      }

      const data = await response.json();

      // Append this turn to the running history, rather than replacing
      // a single answer/sources state -- this is what makes it a
      // conversation instead of a one-shot lookup.
      setHistory((prev) => [
        ...prev,
        { question: currentQuestion, answer: data.answer, sources: data.sources },
      ]);
    } catch (err) {
      setError(`Couldn't reach the backend. Is it running at ${BACKEND_URL}? (${err.message})`);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") handleAsk();
  }

  function toggleSource(turnIndex, sourceIndex) {
    const key = `${turnIndex}-${sourceIndex}`;
    // Clicking an already-open card closes it; clicking a different one
    // switches to it. Simple toggle logic using a single shared piece
    // of state rather than per-card state.
    setExpandedSource(expandedSource === key ? null : key);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-eyebrow">Investigation Intelligence Platform</span>
        <h1>Ask the record.</h1>
        <p className="app-subtitle">
          Answers are generated only from indexed source documents, with citations attached.
        </p>
      </header>

      <div className="query-bar">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. What was the court's ruling in this case?"
          className="query-input"
        />
        <button onClick={handleAsk} disabled={loading} className="query-button">
          {loading ? "Searching…" : "Ask"}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {/* Render the whole conversation, most recent turn last -- like a
          normal chat log. .map() over the history array builds one
          block of JSX per past question. */}
      <div className="conversation">
        {history.map((turn, turnIndex) => (
          <div key={turnIndex} className="turn">
            <div className="turn-question">{turn.question}</div>

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
                        <span className="source-tag">[{sourceIndex + 1}]</span>
                        <span className="source-title">{s.title}</span>
                        <span className="source-toggle">{isOpen ? "−" : "+"}</span>
                      </button>

                      {/* Only render the expanded content when open --
                          keeps the DOM small and avoids showing chunk
                          text for every source all the time. */}
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
        ))}
      </div>
    </div>
  );
}

export default App;