import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ChatWorkspace } from "../components/chat-workspace";
import { WorkspaceProvider } from "../components/workspace-provider";
import { DocumentsPanel } from "../components/documents-panel";
import { askQuestion, type ChatResponse } from "../lib/chat";
import { deleteDocument, listDocuments, type Document } from "../lib/documents";

vi.mock("../lib/chat", () => ({ askQuestion: vi.fn() }));
vi.mock("../lib/documents", async (original) => ({
  ...(await original<typeof import("../lib/documents")>()),
  listDocuments: vi.fn(),
  deleteDocument: vi.fn(),
}));
const doc: Document = {
  id: "doc-1",
  filename: "Policy.pdf",
  size_bytes: 100,
  page_count: 2,
  chunk_count: 2,
  empty_page_count: 0,
  status: "ready",
  error_message: null,
  embedding_status: "ready",
  embedding_error: null,
  created_at: "2026-11-02T12:00:00Z",
};
const answer: ChatResponse = {
  answer: "The allowance is 25 days.",
  sources_found: true,
  provider: "fake",
  demo: true,
  citations: [
    {
      document_id: doc.id,
      filename: doc.filename,
      page: 2,
      excerpt: "Annual leave allowance is 25 days.",
    },
  ],
};

beforeEach(() => {
  vi.mocked(deleteDocument).mockReset().mockResolvedValue();
  vi.mocked(listDocuments)
    .mockReset()
    .mockResolvedValue({
      mode: "local-demo",
      provider: "fake",
      max_upload_bytes: 1024,
      documents: [doc],
    });
  vi.mocked(askQuestion).mockReset().mockResolvedValue(answer);
});
function open() {
  render(
    <WorkspaceProvider>
      <ChatWorkspace />
    </WorkspaceProvider>,
  );
}
async function submit(question = "Annual leave allowance?") {
  const button = screen.getByRole("button", { name: /Ask question/ });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Your question"), {
    target: { value: question },
  });
  fireEvent.click(button);
}

it("shows an honest empty state and fake-provider limitations", async () => {
  vi.mocked(listDocuments).mockResolvedValue({
    mode: "local-demo",
    provider: "fake",
    max_upload_bytes: 1024,
    documents: [],
  });
  open();
  expect(await screen.findByText("Fake provider · local demo")).toBeVisible();
  expect(screen.getByText(/broad questions like/)).toBeVisible();
  expect(screen.getByRole("button", { name: /Ask question/ })).toBeDisabled();
  expect(screen.getByText(/Upload a text-based PDF to ask/)).toBeVisible();
});

it("sends a scoped question and exposes the real citation page and excerpt", async () => {
  open();
  await submit();
  expect(await screen.findByText(answer.answer)).toBeVisible();
  expect(askQuestion).toHaveBeenCalledWith(
    "Annual leave allowance?",
    [doc.id],
    expect.any(AbortSignal),
  );
  fireEvent.click(screen.getByRole("button", { name: /View 1 source/ }));
  const panel = screen.getByRole("complementary", { name: "Sources" });
  expect(within(panel).getByText("Policy.pdf")).toBeVisible();
  expect(within(panel).getByText("Page 2")).toBeVisible();
  expect(within(panel).getByText(answer.citations[0].excerpt)).toBeVisible();
  expect(screen.getByText(/Each question searches/)).toBeVisible();
});

it("prevents a request with no selected documents", async () => {
  open();
  fireEvent.click(await screen.findByRole("checkbox", { name: /Policy.pdf/ }));
  expect(screen.getByRole("button", { name: /Ask question/ })).toBeDisabled();
  expect(askQuestion).not.toHaveBeenCalled();
});

it("shows no-evidence feedback with an empty sources panel", async () => {
  vi.mocked(askQuestion).mockResolvedValue({
    ...answer,
    sources_found: false,
    citations: [],
    answer: "No supporting evidence was found.",
  });
  open();
  await submit("Quantum zebra?");
  expect(await screen.findByText("No supporting evidence")).toBeVisible();
  expect(screen.getByText("No supporting sources")).toBeVisible();
  expect(screen.queryByText("Page 2")).not.toBeInTheDocument();
});

it("retries a failed request without duplicating the question", async () => {
  vi.mocked(askQuestion).mockRejectedValueOnce(
    new Error("Provider unavailable"),
  );
  open();
  await submit();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Provider unavailable",
  );
  fireEvent.click(screen.getByRole("button", { name: "Retry question" }));
  expect(await screen.findByText(answer.answer)).toBeVisible();
  expect(screen.getAllByRole("article", { name: /Question/ })).toHaveLength(1);
});

it("cancels a request and ignores a response that arrives afterward", async () => {
  let resolve!: (value: ChatResponse) => void;
  vi.mocked(askQuestion).mockReturnValue(
    new Promise((complete) => {
      resolve = complete;
    }),
  );
  open();
  await submit();
  fireEvent.click(
    await screen.findByRole("button", { name: "Cancel request" }),
  );
  expect(screen.getByText(/Request cancelled. The backend/)).toBeVisible();
  resolve(answer);
  await waitFor(() =>
    expect(screen.queryByText(answer.answer)).not.toBeInTheDocument(),
  );
  expect(screen.getByLabelText("Your question")).toBeEnabled();
});

it("clears local answers and sources", async () => {
  open();
  await submit();
  await screen.findByText(answer.answer);
  fireEvent.click(screen.getByRole("button", { name: "Clear chat" }));
  expect(screen.queryByText(answer.answer)).not.toBeInTheDocument();
  expect(screen.getByText("Answers you can trace")).toBeVisible();
});

it("clears related answers when a document is deleted", async () => {
  render(
    <WorkspaceProvider>
      <ChatWorkspace />
      <DocumentsPanel />
    </WorkspaceProvider>,
  );
  await submit();
  await screen.findByText(answer.answer);
  fireEvent.click(screen.getByRole("button", { name: "Delete Policy.pdf" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
  await waitFor(() =>
    expect(screen.queryByText(answer.answer)).not.toBeInTheDocument(),
  );
  expect(screen.queryByText("Page 2")).not.toBeInTheDocument();
});

it("uses Enter to send and Shift+Enter to preserve a multiline draft", async () => {
  open();
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Ask question/ })).toBeEnabled(),
  );
  const input = screen.getByLabelText("Your question");
  fireEvent.change(input, { target: { value: "Annual leave allowance?" } });
  fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
  expect(askQuestion).not.toHaveBeenCalled();
  fireEvent.keyDown(input, { key: "Enter" });
  expect(await screen.findByText(answer.answer)).toBeVisible();
});

it("rejects blank questions and renders provider text as text", async () => {
  vi.mocked(askQuestion).mockResolvedValue({
    ...answer,
    answer: '<img src=x onerror="alert(1)">',
  });
  open();
  await submit("   ");
  expect(screen.getByRole("alert")).toHaveTextContent("Enter a question");
  expect(askQuestion).not.toHaveBeenCalled();
  await submit();
  expect(
    await screen.findByText('<img src=x onerror="alert(1)">'),
  ).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});
