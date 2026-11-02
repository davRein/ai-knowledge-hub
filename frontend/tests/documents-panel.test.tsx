import {
  fireEvent,
  render as renderView,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { WorkspaceProvider } from "../components/workspace-provider";
import { beforeEach, expect, it, vi } from "vitest";
import { DocumentsPanel } from "../components/documents-panel";
import {
  deleteDocument,
  listDocuments,
  uploadDocument,
  type Document,
} from "../lib/documents";

vi.mock("../lib/documents", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/documents")>()),
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
}));

function render(view: ReactNode) {
  return renderView(<WorkspaceProvider>{view}</WorkspaceProvider>);
}

const doc: Document = {
  id: "example-id",
  filename: "report.pdf",
  size_bytes: 1024,
  status: "ready",
  error_message: null,
  page_count: 3,
  empty_page_count: 1,
  chunk_count: 4,
  embedding_status: "ready",
  embedding_error: null,
  created_at: "2026-11-01T12:00:00Z",
};
const listing = (documents: Document[] = []) => ({
  mode: "local-demo" as const,
  provider: "fake" as const,
  max_upload_bytes: 1024,
  documents,
});

beforeEach(() => {
  vi.mocked(listDocuments).mockReset().mockResolvedValue(listing());
  vi.mocked(uploadDocument).mockReset();
  vi.mocked(deleteDocument).mockReset().mockResolvedValue();
});

it("loads a real empty library without sample records", async () => {
  render(<DocumentsPanel />);
  expect(screen.getByText("Loading documents…")).toBeVisible();
  expect(await screen.findByText("Your library starts here")).toBeVisible();
  expect(screen.queryByText("report.pdf")).not.toBeInTheDocument();
  expect(
    screen.getByText(/Fake provider · deterministic local excerpts/),
  ).toBeVisible();
});

it("shows connection errors instead of claiming the library is empty", async () => {
  vi.mocked(listDocuments).mockRejectedValueOnce(
    new Error("Database unavailable"),
  );
  render(<DocumentsPanel />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Database unavailable",
  );
  expect(screen.getByText("Library unavailable")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Refresh documents" }));
  expect(await screen.findByText("Your library starts here")).toBeVisible();
});

it("rejects unsupported and oversized files before upload", async () => {
  render(<DocumentsPanel />);
  await screen.findByText("Your library starts here");
  const input = screen.getByLabelText("Choose PDF");
  fireEvent.change(input, {
    target: { files: [new File(["notes"], "notes.txt")] },
  });
  expect(screen.getByRole("alert")).toHaveTextContent("Please select a PDF");
  fireEvent.change(input, {
    target: { files: [new File(["x".repeat(1025)], "large.pdf")] },
  });
  expect(screen.getByRole("alert")).toHaveTextContent("upload limit");
  expect(uploadDocument).not.toHaveBeenCalled();
});

it("uploads and displays the returned extraction status and page counts", async () => {
  vi.mocked(uploadDocument).mockImplementation(async () => {
    vi.mocked(listDocuments).mockResolvedValue(listing([doc]));
    return doc;
  });
  render(<DocumentsPanel />);
  await screen.findByText("Your library starts here");
  fireEvent.change(screen.getByLabelText("Choose PDF"), {
    target: {
      files: [
        new File(["%PDF-test"], "report.pdf", { type: "application/pdf" }),
      ],
    },
  });
  expect(await screen.findByText("report.pdf")).toBeVisible();
  expect(screen.getByText("Text extracted")).toBeVisible();
  expect(screen.getByText("Search index: ready")).toBeVisible();
  expect(screen.getByText(/3 pages · 4 text chunks/)).toBeVisible();
  expect(
    screen.getByText(/1 page\(s\) without extractable text/),
  ).toBeVisible();
});

it("shows failed ingestion returned by the API", async () => {
  vi.mocked(listDocuments).mockResolvedValue(
    listing([
      {
        ...doc,
        status: "failed",
        error_message: "No extractable text. OCR is not supported.",
      },
    ]),
  );
  render(<DocumentsPanel />);
  expect(await screen.findByText("Extraction failed")).toBeVisible();
  expect(
    screen.getByText("No extractable text. OCR is not supported."),
  ).toBeVisible();
});

it("confirms deletion and removes the row only after a successful response", async () => {
  vi.mocked(listDocuments).mockResolvedValue(listing([doc]));
  render(<DocumentsPanel />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Delete report.pdf" }),
  );
  expect(deleteDocument).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
  await waitFor(() =>
    expect(screen.queryByText("report.pdf")).not.toBeInTheDocument(),
  );
  expect(deleteDocument).toHaveBeenCalledWith("example-id");
});

it("retains documents when deletion fails", async () => {
  vi.mocked(listDocuments).mockResolvedValue(listing([doc]));
  vi.mocked(deleteDocument).mockRejectedValue(new Error("Deletion failed"));
  render(<DocumentsPanel />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Delete report.pdf" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Deletion failed");
  expect(screen.getByText("report.pdf")).toBeVisible();
});

it("accepts a dropped PDF and rejects multiple dropped files", async () => {
  vi.mocked(uploadDocument).mockImplementation(async () => {
    vi.mocked(listDocuments).mockResolvedValue(listing([doc]));
    return doc;
  });
  render(<DocumentsPanel />);
  await screen.findByText("Your library starts here");
  const file = new File(["%PDF-test"], "report.pdf", {
    type: "application/pdf",
  });
  fireEvent.drop(screen.getByTestId("upload-zone"), {
    dataTransfer: { files: [file, file] },
  });
  expect(screen.getByRole("alert")).toHaveTextContent("one PDF at a time");
  expect(uploadDocument).not.toHaveBeenCalled();
  fireEvent.drop(screen.getByTestId("upload-zone"), {
    dataTransfer: { files: [file] },
  });
  expect(
    await screen.findByRole("heading", { name: "report.pdf" }),
  ).toBeVisible();
  expect(uploadDocument).toHaveBeenCalledWith(file);
});

it("filters filenames and status without losing stored rows", async () => {
  vi.mocked(listDocuments).mockResolvedValue(
    listing([
      doc,
      {
        ...doc,
        id: "failed-id",
        filename: "broken.pdf",
        status: "failed",
        error_message: "Damaged PDF",
      },
    ]),
  );
  render(<DocumentsPanel />);
  await screen.findByRole("heading", { name: "report.pdf" });
  fireEvent.change(screen.getByLabelText("Status"), {
    target: { value: "attention" },
  });
  expect(
    screen.queryByRole("heading", { name: "report.pdf" }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "broken.pdf" })).toBeVisible();
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "missing" },
  });
  expect(screen.getByText("No matching documents")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(screen.getByRole("heading", { name: "report.pdf" })).toBeVisible();
});
