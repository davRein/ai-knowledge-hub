"use client";

import { forwardRef } from "react";
import type { ChatTurn } from "../lib/chat";

export const SourcesPanel = forwardRef<HTMLElement, { turn?: ChatTurn }>(
  function SourcesPanel({ turn }, ref) {
    return (
      <aside
        className="panel sources-panel"
        aria-labelledby="sources-title"
        ref={ref}
        tabIndex={-1}
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">FOLLOW THE EVIDENCE</p>
            <h2 id="sources-title">Sources</h2>
          </div>
          <span className="source-count">
            {turn?.result?.citations.length ?? 0}
          </span>
        </div>
        {!turn ? (
          <div className="sources-empty">
            <span aria-hidden="true">⌕</span>
            <h3>Answers you can trace</h3>
            <p>
              Ask a question. Supporting passages will appear here with their
              document and page.
            </p>
          </div>
        ) : turn.status === "pending" ? (
          <p role="status" className="sources-empty">
            Looking for supporting passages…
          </p>
        ) : !turn.result ? (
          <p className="sources-empty">
            {turn.status === "cancelled"
              ? "Request cancelled. No answer was published."
              : "No sources were published for this request. Retry the question when the connection is available."}
          </p>
        ) : !turn.result.sources_found ? (
          <div className="sources-empty">
            <h3>No supporting sources</h3>
            <p>
              No citations were returned for this question. Try a specific
              phrase from an indexed PDF.
            </p>
          </div>
        ) : (
          <>
            <p className="source-question">For: {turn.question}</p>
            <ol className="source-list">
              {turn.result.citations.map((citation, index) => (
                <li key={`${citation.document_id}-${citation.page}-${index}`}>
                  <div className="source-heading">
                    <span className="citation-number">{index + 1}</span>
                    <h3>{citation.filename}</h3>
                    <span className="page-tag">Page {citation.page}</span>
                  </div>
                  <blockquote>{citation.excerpt}</blockquote>
                  <p className="fine-print">
                    Extracted text · Original PDF preview is unavailable
                  </p>
                </li>
              ))}
            </ol>
          </>
        )}
      </aside>
    );
  },
);
