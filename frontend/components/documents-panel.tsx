"use client";

import { useState } from "react";
import { formatBytes } from "../lib/documents";
import { useWorkspace } from "./workspace-provider";
import { UploadZone } from "./upload-zone";

export function DocumentsPanel() {
  const {
    documents,
    loading,
    loadError,
    actionError,
    notice,
    operation,
    pending,
    refresh,
    remove,
    provider,
  } = useWorkspace();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [deleting, setDeleting] = useState<string | null>(null);
  const visible = documents.filter(
    (doc) =>
      doc.filename.toLowerCase().includes(query.toLowerCase()) &&
      (filter === "all" ||
        (filter === "ready" &&
          doc.status === "ready" &&
          doc.embedding_status === "ready") ||
        (filter === "attention" &&
          (doc.status === "failed" || doc.embedding_status === "failed")) ||
        (filter === "processing" &&
          (doc.status === "processing" ||
            (doc.status === "ready" && doc.embedding_status === "pending")))),
  );
  const busy = Boolean(operation);
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">YOUR KNOWLEDGE, ORGANIZED</p>
          <h1>Document library</h1>
          <p className="muted">
            Add PDFs, follow their processing status, and keep your sources in
            one place.
          </p>
        </div>
        <span className="page-count">{documents.length} documents</span>
      </div>
      <UploadZone />
      {notice && (
        <p role="status" className="document-message">
          {notice}
        </p>
      )}
      {actionError && (
        <p role="alert" className="document-error">
          {actionError}
        </p>
      )}
      <section
        className="panel library-panel"
        aria-labelledby="documents-title"
      >
        <div className="section-heading">
          <h2 id="documents-title">Documents</h2>
          <button
            className="text-button"
            disabled={busy}
            onClick={() => void refresh()}
          >
            Refresh documents
          </button>
        </div>
        <div className="library-tools">
          <label className="search-label">
            Search filenames
            <input
              type="search"
              placeholder="Find a document…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label>
            Status
            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value="all">All statuses</option>
              <option value="ready">Ready for questions</option>
              <option value="processing">Processing / index pending</option>
              <option value="attention">Needs attention</option>
            </select>
          </label>
        </div>
        {loadError && (
          <div role="alert" className="document-error">
            <p>{loadError}</p>
            <p className="fine-print">
              {documents.length
                ? "Showing the last loaded library."
                : "Check your API and database connection, then refresh."}
            </p>
          </div>
        )}
        {loading ? (
          <p role="status" className="empty-state">
            Loading documents…
          </p>
        ) : !documents.length ? (
          <div className="empty-state">
            <span className="empty-symbol" aria-hidden="true">
              ▤
            </span>
            <h3>
              {loadError ? "Library unavailable" : "Your library starts here"}
            </h3>
            <p>Upload a text-based PDF above. Its status will appear here.</p>
          </div>
        ) : !visible.length ? (
          <div className="empty-state">
            <h3>No matching documents</h3>
            <p>Try a different filename or status.</p>
            <button
              className="text-button"
              onClick={() => {
                setQuery("");
                setFilter("all");
              }}
            >
              Clear filters
            </button>
          </div>
        ) : (
          <ul className="document-list">
            {visible.map((doc) => (
              <li className="document-row" key={doc.id}>
                <span className="file-mark" aria-hidden="true">
                  PDF
                </span>
                <div className="document-details">
                  <h3>{doc.filename}</h3>
                  <p className="muted small">
                    {formatBytes(doc.size_bytes)} · {doc.page_count} pages ·{" "}
                    {doc.chunk_count} text chunks
                  </p>
                  <div className="document-labels">
                    <span className={`document-state state-${doc.status}`}>
                      {doc.status === "ready"
                        ? "Text extracted"
                        : doc.status === "failed"
                          ? "Extraction failed"
                          : "Processing"}
                    </span>
                    {doc.status === "ready" && (
                      <span
                        className={`document-state ${doc.embedding_status === "failed" ? "state-failed" : doc.embedding_status === "ready" ? "state-ready" : "state-processing"}`}
                      >
                        Search index: {doc.embedding_status}
                      </span>
                    )}
                  </div>
                  {doc.empty_page_count > 0 && (
                    <p className="fine-print">
                      {doc.empty_page_count} page(s) without extractable text
                      were skipped. OCR is not supported.
                    </p>
                  )}
                  {doc.error_message && (
                    <p className="document-error">{doc.error_message}</p>
                  )}
                  {doc.embedding_error && (
                    <p className="document-error">{doc.embedding_error}</p>
                  )}
                  {doc.status === "ready" &&
                    doc.embedding_status === "pending" && (
                      <p className="fine-print">
                        This document is not searchable yet. Refresh after
                        indexing completes.
                      </p>
                    )}
                </div>
                <div className="document-actions">
                  {deleting === doc.id ? (
                    <div className="delete-confirmation">
                      <p>Delete this document and its extracted text?</p>
                      <div>
                        <button
                          className="action-button danger"
                          disabled={busy || pending}
                          onClick={() =>
                            void remove(doc.id).then((success) => {
                              if (success) setDeleting(null);
                            })
                          }
                        >
                          Confirm delete
                        </button>
                        <button
                          className="text-button"
                          disabled={busy}
                          onClick={() => setDeleting(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      className="text-button"
                      disabled={busy || pending}
                      onClick={() => setDeleting(doc.id)}
                      aria-label={`Delete ${doc.filename}`}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
        <p className="fine-print">
          {provider === "fake"
            ? "Fake provider · deterministic local excerpts, not a language model."
            : provider === "openai"
              ? "OpenAI provider · text is processed by the configured external API."
              : "Connecting to your configured provider…"}{" "}
          Original PDFs are not retained for download.
        </p>
      </section>
    </>
  );
}
