"use client";

import { useId, useRef, useState, type DragEvent } from "react";
import { formatBytes } from "../lib/documents";
import { useWorkspace } from "./workspace-provider";
import { useAuth } from "./auth-provider";

export function UploadZone({ compact = false }: { compact?: boolean }) {
  const auth = useAuth();
  const { maxUploadBytes, operation, loading, upload, provider } =
    useWorkspace();
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const depth = useRef(0);
  const input = useRef<HTMLInputElement>(null);
  const helpId = useId();
  const disabled =
    Boolean(operation) ||
    loading ||
    (provider === "openai" &&
      auth?.session?.mode === "authenticated" &&
      !auth.session.user?.external_ai_consent);

  function choose(files: File[]) {
    setError("");
    if (disabled) return;
    if (files.length !== 1) {
      setError("Choose one PDF at a time.");
      return;
    }
    const file = files[0];
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a PDF file.");
      return;
    }
    if (!file.size) {
      setError("This file is empty. Choose a PDF with text.");
      return;
    }
    if (file.size > maxUploadBytes) {
      setError(`PDF exceeds the ${formatBytes(maxUploadBytes)} upload limit.`);
      return;
    }
    void upload(file);
  }
  function drop(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    depth.current = 0;
    setDragging(false);
    choose(Array.from(event.dataTransfer.files));
  }

  return (
    <div
      className={`upload-zone ${compact ? "compact" : ""} ${dragging ? "is-dragging" : ""}`}
      data-testid="upload-zone"
      onDragEnter={(event) => {
        event.preventDefault();
        depth.current++;
        if (!disabled) setDragging(true);
      }}
      onDragOver={(event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = disabled ? "none" : "copy";
      }}
      onDragLeave={(event) => {
        event.preventDefault();
        depth.current--;
        if (depth.current <= 0) setDragging(false);
      }}
      onDrop={drop}
    >
      <span className="upload-glyph" aria-hidden="true">
        ↥
      </span>
      <div>
        <h3>
          {operation === "upload"
            ? "Extracting and indexing your PDF…"
            : "Drop a PDF to get started"}
        </h3>
        <p id={helpId}>
          One text-based PDF · up to {formatBytes(maxUploadBytes)} · No OCR
        </p>
      </div>
      <button
        className="action-button"
        disabled={disabled}
        aria-describedby={helpId}
        onClick={() => input.current?.click()}
      >
        {operation === "upload" ? "Processing PDF…" : "Upload PDF"}
      </button>
      <input
        ref={input}
        className="file-input"
        type="file"
        accept="application/pdf,.pdf"
        tabIndex={-1}
        aria-label="Choose PDF"
        disabled={disabled}
        onChange={(event) => {
          choose(Array.from(event.target.files ?? []));
          event.target.value = "";
        }}
      />
      {!compact && (
        <p className="upload-disclosure">
          Original PDFs are discarded after processing.{" "}
          {provider === "openai"
            ? "Extracted text is sent to the configured OpenAI API."
            : "Extracted text and the search index stay in your configured project database."}
        </p>
      )}
      {error && (
        <p role="alert" className="document-error">
          {error}
        </p>
      )}
    </div>
  );
}
