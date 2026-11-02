import { afterEach, expect, it, vi } from "vitest";
import { askQuestion } from "../lib/chat";

afterEach(() => vi.unstubAllGlobals());
const result = {
  answer: "A grounded answer",
  citations: [
    {
      document_id: "doc-1",
      filename: "Policy.pdf",
      page: 2,
      excerpt: "Source text.",
    },
  ],
  sources_found: true,
  provider: "fake",
  demo: true,
};

it("serializes the scope and validates successful responses", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => result });
  vi.stubGlobal("fetch", fetchMock);
  expect(
    await askQuestion("Question?", ["doc-1"], new AbortController().signal),
  ).toEqual(result);
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
    question: "Question?",
    document_ids: ["doc-1"],
  });
});

it.each([
  { ...result, citations: [{ ...result.citations[0], page: 0 }] },
  {
    ...result,
    citations: [{ ...result.citations[0], document_id: "outside-scope" }],
  },
  { ...result, sources_found: false },
  { ...result, citations: [] },
  { ...result, provider: "unknown" },
])("rejects inconsistent citations and provider metadata %#", async (data) => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => data }),
  );
  await expect(
    askQuestion("Question?", ["doc-1"], new AbortController().signal),
  ).rejects.toThrow("unexpected");
});

it("shows safe API failure messages", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Provider unavailable" }),
    }),
  );
  await expect(
    askQuestion("Question?", ["doc-1"], new AbortController().signal),
  ).rejects.toThrow("Provider unavailable");
});
