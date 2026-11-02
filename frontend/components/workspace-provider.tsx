"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  deleteDocument,
  listDocuments,
  uploadDocument,
  type Document,
} from "../lib/documents";
import { askQuestion, type ChatTurn } from "../lib/chat";

function describeError(error: unknown): string {
  if (error instanceof TypeError)
    return "Could not reach the API. Check that the backend is running, then retry.";
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please retry.";
}

function useWorkspaceState() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [provider, setProvider] = useState<"fake" | "openai" | null>(null);
  const [maxUploadBytes, setMaxUploadBytes] = useState(10 * 1024 * 1024);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [operation, setOperation] = useState<"upload" | "delete" | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[] | null>(null);
  const [pending, setPending] = useState(false);
  const request = useRef<AbortController | null>(null);
  const operationLock = useRef(false);
  const generation = useRef(0);
  const loadController = useRef<AbortController | null>(null);
  const readyDocuments = documents.filter(
    (doc) => doc.status === "ready" && doc.embedding_status === "ready",
  );
  const effectiveIds = readyDocuments
    .filter((doc) => selectedIds === null || selectedIds.includes(doc.id))
    .map((doc) => doc.id);

  const refresh = useCallback(async () => {
    const version = ++generation.current;
    loadController.current?.abort();
    const controller = new AbortController();
    loadController.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 10_000);
    try {
      const result = await listDocuments(controller.signal);
      if (version !== generation.current) return;
      setDocuments(result.documents);
      setProvider(result.provider);
      setMaxUploadBytes(result.max_upload_bytes);
      setLoadError(null);
    } catch (error) {
      if (version === generation.current)
        setLoadError(
          controller.signal.aborted
            ? "Loading documents timed out. Check your connection and refresh."
            : describeError(error),
        );
    } finally {
      window.clearTimeout(timeout);
      if (version === generation.current) setLoading(false);
    }
  }, []);

  const invalidateLoads = useCallback(() => {
    generation.current++;
  }, []);
  useEffect(() => {
    void refresh();
    return () => {
      invalidateLoads();
      loadController.current?.abort();
      request.current?.abort();
    };
  }, [refresh, invalidateLoads]);

  const hasProcessing = documents.some(
    (doc) =>
      doc.status === "processing" ||
      (doc.status === "ready" && doc.embedding_status === "pending"),
  );
  useEffect(() => {
    if (!hasProcessing || operation) return;
    const interval = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(interval);
  }, [hasProcessing, operation, refresh]);

  async function upload(file: File): Promise<void> {
    if (operationLock.current) return;
    operationLock.current = true;
    generation.current++;
    loadController.current?.abort();
    setOperation("upload");
    setActionError(null);
    setNotice("");
    try {
      const doc = await uploadDocument(file);
      setDocuments((current) => [
        doc,
        ...current.filter((item) => item.id !== doc.id),
      ]);
      setNotice(
        doc.status === "failed"
          ? "PDF saved with an extraction error. Review its status below."
          : doc.embedding_status === "failed"
            ? "Text extracted, but the search index failed. Review the indexing error."
            : "PDF processed and ready for questions.",
      );
    } catch (error) {
      setActionError(describeError(error));
    } finally {
      operationLock.current = false;
      setOperation(null);
      await refresh();
    }
  }

  async function remove(id: string): Promise<boolean> {
    if (operationLock.current || request.current) return false;
    operationLock.current = true;
    generation.current++;
    loadController.current?.abort();
    setOperation("delete");
    setActionError(null);
    setNotice("");
    try {
      await deleteDocument(id);
      setDocuments((current) => current.filter((doc) => doc.id !== id));
      setSelectedIds(
        (current) => current?.filter((item) => item !== id) ?? null,
      );
      setTurns((current) =>
        current.filter((turn) => !turn.documentIds.includes(id)),
      );
      setNotice(
        "Document and its extracted text deleted. Related answers were cleared from this tab.",
      );
      return true;
    } catch (error) {
      setActionError(describeError(error));
      return false;
    } finally {
      operationLock.current = false;
      setOperation(null);
    }
  }

  async function send(
    question: string,
    ids: string[],
    retryId?: string,
  ): Promise<void> {
    const trimmed = question.trim();
    if (
      request.current ||
      (!retryId && turns.length >= 20) ||
      operationLock.current ||
      !trimmed ||
      trimmed.length > 2000 ||
      !ids.length ||
      ids.some((id) => !readyDocuments.some((doc) => doc.id === id))
    )
      return;
    const controller = new AbortController();
    request.current = controller;
    setPending(true);
    const id = retryId ?? crypto.randomUUID();
    const names = readyDocuments
      .filter((doc) => ids.includes(doc.id))
      .map((doc) => doc.filename);
    const turn: ChatTurn = {
      id,
      question: trimmed,
      documentIds: [...ids],
      scope: names.join(", "),
      status: "pending",
    };
    setTurns((current) =>
      retryId
        ? current.map((item) => (item.id === retryId ? turn : item))
        : [...current, turn],
    );
    setActiveTurnId(id);
    let timedOut = false;
    const timeout = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 45_000);
    try {
      const result = await askQuestion(trimmed, ids, controller.signal);
      if (request.current !== controller) return;
      setTurns((current) =>
        current.map((item) =>
          item.id === id ? { ...item, status: "complete", result } : item,
        ),
      );
    } catch (error) {
      if (request.current !== controller) return;
      setTurns((current) =>
        current.map((item) =>
          item.id === id
            ? {
                ...item,
                status: "failed",
                error: timedOut
                  ? "The answer took too long. Please retry."
                  : describeError(error),
              }
            : item,
        ),
      );
    } finally {
      window.clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        setPending(false);
      }
    }
  }

  function cancel() {
    request.current?.abort();
    request.current = null;
    setPending(false);
    setTurns((current) =>
      current.map((turn) =>
        turn.status === "pending" ? { ...turn, status: "cancelled" } : turn,
      ),
    );
  }
  function clearChat() {
    cancel();
    setTurns([]);
    setActiveTurnId(null);
  }

  return {
    documents,
    readyDocuments,
    effectiveIds,
    selectedIds,
    setSelectedIds,
    provider,
    maxUploadBytes,
    loading,
    loadError,
    actionError,
    notice,
    operation,
    refresh,
    upload,
    remove,
    turns,
    activeTurnId,
    setActiveTurnId,
    pending,
    send,
    cancel,
    clearChat,
  };
}

type WorkspaceState = ReturnType<typeof useWorkspaceState>;
const WorkspaceContext = createContext<WorkspaceState | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const state = useWorkspaceState();
  return (
    <WorkspaceContext.Provider value={state}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceState {
  const state = useContext(WorkspaceContext);
  if (!state) throw new Error("WorkspaceProvider is required");
  return state;
}
