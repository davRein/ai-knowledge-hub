import { apiUrl } from "./api";
import { authenticatedFetch } from "./auth";

export type Document = {
  id: string;
  filename: string;
  size_bytes: number;
  status: "processing" | "ready" | "failed";
  error_message: string | null;
  page_count: number;
  empty_page_count: number;
  chunk_count: number;
  embedding_status: "pending" | "ready" | "failed";
  embedding_error: string | null;
  created_at: string;
};

export type DocumentList = {
  mode: "local-demo" | "authenticated";
  provider: "fake" | "openai";
  max_upload_bytes: number;
  documents: Document[];
};

export async function errorMessage(response: Response): Promise<string> {
  try {
    const data: unknown = await response.json();
    if (
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      typeof data.detail === "string"
    )
      return data.detail;
  } catch {
    /* Fall back for unavailable proxies/non-JSON responses. */
  }
  return `Request failed (${response.status}). Please try again.`;
}

export async function listDocuments(
  signal?: AbortSignal,
): Promise<DocumentList> {
  const response = await authenticatedFetch(`${apiUrl}/api/documents`, {
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<DocumentList>;
}

export async function uploadDocument(file: File): Promise<Document> {
  const body = new FormData();
  body.append("file", file);
  const response = await authenticatedFetch(`${apiUrl}/api/documents`, {
    method: "POST",
    body,
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<Document>;
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await authenticatedFetch(
    `${apiUrl}/api/documents/${encodeURIComponent(id)}`,
    { method: "DELETE" },
  );
  if (!response.ok) throw new Error(await errorMessage(response));
}

export function formatBytes(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.ceil(bytes / 1024))} KB`;
}
