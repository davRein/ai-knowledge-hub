"use client";

import Link from "next/link";
import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { useWorkspace } from "./workspace-provider";
import { UploadZone } from "./upload-zone";
import { SourcesPanel } from "./sources-panel";
import { useAuth } from "./auth-provider";

export function ChatWorkspace() {
  const auth = useAuth();
  const workspace = useWorkspace();
  const {
    documents,
    readyDocuments,
    effectiveIds,
    selectedIds,
    setSelectedIds,
    loading,
    loadError,
    provider,
    turns,
    activeTurnId,
    setActiveTurnId,
    pending,
    operation,
    send,
    cancel,
    clearChat,
    refresh,
  } = workspace;
  const [question, setQuestion] = useState("");
  const [validation, setValidation] = useState("");
  const sources = useRef<HTMLElement>(null);
  const questionInput = useRef<HTMLTextAreaElement>(null);
  const history = useRef<HTMLDivElement>(null);
  const wasPending = useRef(false);
  useEffect(() => {
    if (history.current)
      history.current.scrollTop = history.current.scrollHeight;
  }, [turns.length, pending]);
  useEffect(() => {
    if (wasPending.current && !pending) questionInput.current?.focus();
    wasPending.current = pending;
  }, [pending]);
  const activeTurn = turns.find((turn) => turn.id === activeTurnId);
  const canAsk =
    !(
      provider === "openai" &&
      auth?.session?.mode === "authenticated" &&
      !auth.session.user?.external_ai_consent
    ) &&
    !loading &&
    !loadError &&
    Boolean(provider) &&
    effectiveIds.length > 0 &&
    !operation &&
    !pending &&
    turns.length < 20;

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!question.trim()) {
      setValidation("Enter a question about your documents.");
      questionInput.current?.focus();
      return;
    }
    if (question.trim().length > 2000) {
      setValidation("Keep your question under 2,000 characters.");
      return;
    }
    if (!canAsk) return;
    setValidation("");
    void send(question, effectiveIds);
    setQuestion("");
  }
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      submit();
    }
  }
  function viewSources(id: string) {
    setActiveTurnId(id);
    requestAnimationFrame(() => {
      sources.current?.focus();
      sources.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">FROM DOCUMENTS TO UNDERSTANDING</p>
          <h1>Ask your knowledge.</h1>
          <p className="muted">
            Explore your PDFs with answers grounded in their text.
          </p>
        </div>
        <Link className="secondary-button" href="/documents">
          Manage documents ↗
        </Link>
      </div>
      <div
        className={`provider-notice ${provider === "openai" ? "real-provider" : ""}`}
      >
        <span aria-hidden="true">◈</span>
        <div>
          <strong>
            {provider === "fake"
              ? "Fake provider · local demo"
              : provider === "openai"
                ? "OpenAI provider"
                : "Connecting to the provider…"}
          </strong>
          <p>
            {provider === "fake"
              ? "This demo matches keywords and quotes passages. Use specific words from your PDF; broad questions like “What is in it?” may find no evidence. It is not a language model."
              : provider === "openai"
                ? "Your question and retrieved excerpts are sent to the configured OpenAI API. Check the sources behind each answer."
                : "Start the backend to load your document library and provider."}
          </p>
        </div>
      </div>
      {loadError && (
        <div className="document-error" role="alert">
          <p>{loadError}</p>
          <button className="text-button" onClick={() => void refresh()}>
            Refresh documents
          </button>
        </div>
      )}
      <section className="panel scope-panel" aria-labelledby="scope-title">
        <div className="section-heading">
          <div>
            <h2 id="scope-title">Search scope</h2>
            <p className="fine-print">
              {effectiveIds.length} of {readyDocuments.length} indexed documents
              selected
            </p>
          </div>
          <button
            className="text-button"
            disabled={pending || !readyDocuments.length}
            onClick={() => setSelectedIds(null)}
          >
            Use all indexed documents
          </button>
        </div>
        {loading ? (
          <p role="status">Loading documents…</p>
        ) : readyDocuments.length ? (
          <fieldset
            disabled={pending || Boolean(operation)}
            className="document-scope"
          >
            <legend className="visually-hidden">Documents to search</legend>
            {readyDocuments.map((doc) => (
              <label key={doc.id} title={doc.filename}>
                <input
                  type="checkbox"
                  checked={effectiveIds.includes(doc.id)}
                  onChange={(event) => {
                    const current =
                      selectedIds ?? readyDocuments.map((item) => item.id);
                    setSelectedIds(
                      event.target.checked
                        ? [...current, doc.id]
                        : current.filter((id) => id !== doc.id),
                    );
                  }}
                />
                <span>{doc.filename}</span>
                <span className="small muted">{doc.page_count}p</span>
              </label>
            ))}
          </fieldset>
        ) : (
          <p className="muted">
            {documents.length
              ? "Your documents are not indexed yet. Check their status in the document library."
              : "Upload a text-based PDF to ask your first question."}
          </p>
        )}
        {!loading && documents.length > readyDocuments.length && (
          <p className="fine-print">
            {documents.length - readyDocuments.length} document(s) are still
            processing or need attention.{" "}
            <Link href="/documents" className="inline-link">
              Review status
            </Link>
          </p>
        )}
      </section>
      {!loading && !documents.length && <UploadZone compact />}
      <div className="chat-grid">
        <section className="panel chat-panel" aria-labelledby="chat-title">
          <div className="section-heading">
            <h2 id="chat-title">Conversation</h2>
            <button
              className="text-button"
              disabled={!turns.length}
              onClick={clearChat}
            >
              Clear chat
            </button>
          </div>
          <p className="fine-print">
            History stays in this tab until refresh. Each question searches the
            selected documents independently.
          </p>
          <div
            className="chat-history"
            ref={history}
            aria-label="Conversation history"
            aria-busy={pending}
          >
            {!turns.length && (
              <div className="chat-empty">
                <span aria-hidden="true">✧</span>
                <h3>Start with something specific.</h3>
                <p>
                  Ask about a topic, rule, number, or phrase that appears in
                  your PDF. Sources will appear alongside the answer.
                </p>
                <p className="fine-print">
                  No sample answers or documents are preloaded.
                </p>
              </div>
            )}
            {turns.map((turn, index) => (
              <article
                className="chat-turn"
                key={turn.id}
                aria-label={`Question ${index + 1}`}
              >
                <div className="question-bubble">
                  <p className="message-label">YOU</p>
                  <p>{turn.question}</p>
                  <p className="question-scope" title={turn.scope}>
                    Searched: {turn.scope}
                  </p>
                </div>
                <div className="answer-bubble">
                  <p className="message-label">
                    {turn.result?.provider === "fake"
                      ? "FAKE PROVIDER · EXCERPT DEMO"
                      : turn.result?.provider === "openai"
                        ? "OPENAI · DOCUMENT ANSWER"
                        : "KNOWLEDGE HUB"}
                  </p>
                  {turn.status === "pending" ? (
                    <p role="status" className="thinking">
                      <span aria-hidden="true" />
                      Searching your selected documents…
                    </p>
                  ) : turn.status === "failed" ? (
                    <div role="alert">
                      <p className="document-error">{turn.error}</p>
                      <button
                        className="text-button"
                        disabled={
                          pending ||
                          Boolean(operation) ||
                          turn.documentIds.some(
                            (id) =>
                              !readyDocuments.some((doc) => doc.id === id),
                          )
                        }
                        onClick={() =>
                          void send(turn.question, turn.documentIds, turn.id)
                        }
                      >
                        Retry question
                      </button>
                    </div>
                  ) : turn.status === "cancelled" ? (
                    <p className="muted">
                      Request cancelled. The backend may still finish
                      processing.
                    </p>
                  ) : (
                    turn.result && (
                      <>
                        {!turn.result.sources_found && (
                          <p className="no-evidence-label">
                            No supporting evidence
                          </p>
                        )}
                        <p className="answer-text">{turn.result.answer}</p>
                        <button
                          className="source-button"
                          aria-pressed={activeTurnId === turn.id}
                          onClick={() => viewSources(turn.id)}
                        >
                          {turn.result.citations.length
                            ? `View ${turn.result.citations.length} source${turn.result.citations.length === 1 ? "" : "s"}`
                            : "Why are there no sources?"}{" "}
                          <span aria-hidden="true">↗</span>
                        </button>
                      </>
                    )
                  )}
                </div>
              </article>
            ))}
          </div>
          <form className="chat-composer" onSubmit={submit}>
            <label htmlFor="question">Your question</label>
            <textarea
              ref={questionInput}
              id="question"
              rows={3}
              maxLength={2000}
              value={question}
              onChange={(event) => {
                setQuestion(event.target.value);
                setValidation("");
              }}
              onKeyDown={onKeyDown}
              placeholder="Ask about a specific topic in your PDF…"
              aria-describedby="question-help"
              disabled={pending}
            />
            <div className="composer-bottom">
              <p id="question-help">
                Enter to send · Shift+Enter for a new line{" "}
                <span>{question.length}/2000</span>
              </p>
              {pending ? (
                <button
                  type="button"
                  className="secondary-button"
                  onClick={cancel}
                >
                  Cancel request
                </button>
              ) : (
                <button
                  className="action-button"
                  type="submit"
                  disabled={!canAsk}
                >
                  Ask question <span aria-hidden="true">↑</span>
                </button>
              )}
            </div>
            {validation && (
              <p role="alert" className="document-error">
                {validation}
              </p>
            )}
            {!pending && !effectiveIds.length && !loading && (
              <p className="fine-print">
                Select at least one indexed document to ask a question.
              </p>
            )}
            {turns.length >= 20 && (
              <p className="fine-print">
                This tab has reached 20 questions. Clear the chat to start
                fresh.
              </p>
            )}
          </form>
        </section>
        <SourcesPanel turn={activeTurn} ref={sources} />
      </div>
    </>
  );
}
