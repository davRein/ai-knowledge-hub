import { test, expect, type Page } from "@playwright/test";

const doc = {
  id: "00000000-0000-4000-8000-000000000004",
  filename: "Policy.pdf",
  size_bytes: 1024,
  page_count: 2,
  chunk_count: 2,
  empty_page_count: 0,
  status: "ready",
  error_message: null,
  embedding_status: "ready",
  embedding_error: null,
  created_at: "2026-11-02T12:00:00Z",
};
type FixtureDocument = typeof doc;

async function fixtureAPI(page: Page, initial: FixtureDocument[] = [doc]) {
  await page.route("**/api/auth/session", (route) =>
    route.fulfill({
      json: {
        mode: "local-demo",
        user: null,
        csrf_token: null,
        registration_enabled: false,
      },
    }),
  );
  let documents = [...initial];
  await page.route("**/health", (route) =>
    route.fulfill({ json: { status: "ok", mode: "local-demo" } }),
  );
  await page.route(/\/api\/documents(?:\/[^/?]+)?$/, async (route) => {
    const method = route.request().method();
    if (method === "POST") {
      documents = [doc];
      await route.fulfill({ status: 201, json: doc });
    } else if (method === "DELETE") {
      documents = [];
      await route.fulfill({ status: 204 });
    } else
      await route.fulfill({
        json: {
          mode: "local-demo",
          provider: "fake",
          max_upload_bytes: 10485760,
          documents,
        },
      });
  });
  await page.route("**/api/chat", async (route) => {
    const body = route.request().postDataJSON();
    expect(body.document_ids).toEqual([doc.id]);
    await route.fulfill({
      json: {
        answer:
          "Fake provider (deterministic excerpts): Annual leave allowance is 25 days.",
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
      },
    });
  });
}

test("chat, source inspection and navigation preserve in-tab history", async ({
  page,
}, testInfo) => {
  await fixtureAPI(page);
  await page.goto("/");
  await expect(
    page.getByRole("checkbox", { name: /Policy.pdf/ }),
  ).toBeChecked();
  await expect(
    page.getByText("Fake provider · local demo", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Your question").fill("Annual leave allowance?");
  await page.getByRole("button", { name: /Ask question/ }).click();
  await expect(
    page.getByText(/Fake provider \(deterministic excerpts\): Annual leave/),
  ).toBeVisible();
  await page.getByRole("button", { name: /View 1 source/ }).click();
  await expect(page.getByText("Page 2", { exact: true })).toBeVisible();
  await expect(page.locator("blockquote")).toHaveText(
    "Annual leave allowance is 25 days.",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("chat.png"),
    fullPage: true,
  });
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: /Documents/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "Document library" }),
  ).toBeVisible();
  await expect(page.getByText("Search index: ready")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("documents.png"),
    fullPage: true,
  });
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Chat", exact: true })
    .click();
  await expect(page.locator("blockquote")).toHaveText(
    "Annual leave allowance is 25 days.",
  );
});

test("file selection, filtering and confirmed deletion use the document workflow", async ({
  page,
}) => {
  await fixtureAPI(page, []);
  await page.goto("/documents");
  await expect(page.getByText("Your library starts here")).toBeVisible();
  await page.getByLabel("Choose PDF").setInputFiles({
    name: "Policy.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-fixture-only"),
  });
  await expect(
    page.getByRole("heading", { name: "Policy.pdf", exact: true }),
  ).toBeVisible();
  await page.getByRole("searchbox").fill("missing");
  await expect(page.getByText("No matching documents")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await page.getByRole("button", { name: "Delete Policy.pdf" }).click();
  await page.getByRole("button", { name: "Confirm delete" }).click();
  await expect(page.getByText("Your library starts here")).toBeVisible();
});

test("failed chat requests show a working retry action", async ({ page }) => {
  await fixtureAPI(page);
  await page.route(
    "**/api/chat",
    (route) =>
      route.fulfill({ status: 503, json: { detail: "Provider unavailable" } }),
    { times: 1 },
  );
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: /Ask question/ }),
  ).toBeEnabled();
  await page.getByLabel("Your question").fill("Annual leave allowance?");
  await page.getByRole("button", { name: /Ask question/ }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Provider unavailable" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retry question" }).click();
  await expect(
    page.getByText(/Fake provider \(deterministic excerpts\): Annual leave/),
  ).toBeVisible();
});
