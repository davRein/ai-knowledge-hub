import { apiUrl } from "./api";
import { authenticatedFetch } from "./auth";
import { errorMessage } from "./documents";

export type Citation = {
  document_id: string;
  filename: string;
  page: number;
  excerpt: string;
};
export type ChatResponse = {
  answer: string;
  citations: Citation[];
  sources_found: boolean;
  provider: "fake" | "openai";
  demo: boolean;
};
export type ChatTurn = {
  id: string;
  question: string;
  documentIds: string[];
  scope: string;
  status: "pending" | "complete" | "failed" | "cancelled";
  result?: ChatResponse;
  error?: string;
};

function isCitation(value: unknown): value is Citation {
  return (
    typeof value === "object" &&
    value !== null &&
    "document_id" in value &&
    typeof value.document_id === "string" &&
    "filename" in value &&
    typeof value.filename === "string" &&
    "page" in value &&
    typeof value.page === "number" &&
    Number.isInteger(value.page) &&
    value.page > 0 &&
    "excerpt" in value &&
    typeof value.excerpt === "string"
  );
}

export async function askQuestion(
  question: string,
  documentIds: string[],
  signal: AbortSignal,
): Promise<ChatResponse> {
  const response = await authenticatedFetch(`${apiUrl}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, document_ids: documentIds }),
    signal,
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  const data: unknown = await response.json();
  if (
    typeof data !== "object" ||
    data === null ||
    !("answer" in data) ||
    typeof data.answer !== "string" ||
    !("citations" in data) ||
    !Array.isArray(data.citations) ||
    !data.citations.every(isCitation) ||
    !("sources_found" in data) ||
    typeof data.sources_found !== "boolean" ||
    !("provider" in data) ||
    !["fake", "openai"].includes(String(data.provider)) ||
    !("demo" in data) ||
    typeof data.demo !== "boolean" ||
    (!data.sources_found && data.citations.length > 0) ||
    (data.sources_found && data.citations.length === 0) ||
    data.citations.some(
      (citation) => !documentIds.includes(citation.document_id),
    )
  ) {
    throw new Error(
      "The API returned an unexpected answer or source. Please refresh and try again.",
    );
  }
  return data as ChatResponse;
}
