import { expect, test, type Page } from "@playwright/test";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";

const root = path.resolve(process.cwd(), "..");
const assets = path.join(root, "docs", "assets");

async function annotate(page: Page, selectors: string[]) {
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  await page.evaluate((targets) => {
    document
      .querySelectorAll(".portfolio-pin,.portfolio-banner")
      .forEach((el) => el.remove());
    document
      .querySelectorAll<HTMLElement>("[data-portfolio-outline]")
      .forEach((el) => {
        el.style.outline = "";
        el.style.outlineOffset = "";
      });
    const banner = document.createElement("div");
    banner.className = "portfolio-banner";
    banner.textContent =
      "SYNTHETIC DEMO · Real local API + PostgreSQL · Fake provider";
    banner.style.cssText =
      "padding:10px 18px;background:#282147;color:#eee6ff;font:600 11px/1.6 Arial;letter-spacing:.04em;";
    document.body.prepend(banner);
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    targets.forEach((selector, index) => {
      const element = document.querySelector<HTMLElement>(selector);
      if (!element) throw new Error(`Missing screenshot target: ${selector}`);
      element.style.outline = "2px solid #f5bd74";
      element.style.outlineOffset = "3px";
      element.dataset.portfolioOutline = "true";
      const box = element.getBoundingClientRect();
      const pin = document.createElement("span");
      pin.className = "portfolio-pin";
      pin.textContent = String(index + 1);
      pin.style.cssText = `position:absolute;left:${box.x + window.scrollX + 8}px;top:${Math.max(0, box.y + window.scrollY - 15)}px;z-index:9999;display:grid;place-items:center;width:26px;height:26px;border-radius:50%;background:#f5bd74;color:#17121b;font:bold 13px Arial;box-shadow:0 0 0 3px #101620;`;
      document.body.append(pin);
    });
  }, selectors);
}

test("capture verified synthetic portfolio with a real isolated API", async ({
  page,
  context,
}, info) => {
  const api = process.env.PORTFOLIO_API_URL;
  if (api !== "http://127.0.0.1:8810")
    throw new Error(
      "Run the disposable-cluster capture helper; do not target a user database.",
    );
  // Transport redirect only: no fulfilled or fabricated API responses.
  await context.route(
    (url) => url.pathname.startsWith("/api/") || url.pathname === "/health",
    (route) => {
      const original = new URL(route.request().url());
      return route.continue({
        url: `${api}${original.pathname}${original.search}`,
      });
    },
  );
  const source = JSON.parse(
    await readFile(path.join(root, "examples/atlas-handbook.json"), "utf8"),
  ) as {
    questions: {
      question: string;
      answer_contains: string | null;
      page: number | null;
    }[];
  };
  await mkdir(assets, { recursive: true });
  await page.goto("/");
  await page.getByRole("button", { name: "Create an account" }).click();
  await page
    .getByLabel("Email", { exact: true })
    .fill(`demo-${info.project.name}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Synthetic-only portfolio password 2026");
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Ask your knowledge." }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: /Documents/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "Document library" }),
  ).toBeVisible();
  await expect(page.getByLabel("Choose PDF")).toBeEnabled();
  const uploaded = page.waitForResponse(
    (response) =>
      response.url().includes("/api/documents") &&
      response.request().method() === "POST",
  );
  await page
    .getByLabel("Choose PDF")
    .setInputFiles(path.join(root, "examples/atlas-handbook.pdf"));
  const uploadedDocument = (await (await uploaded).json()) as {
    id: string;
    page_count: number;
    chunk_count: number;
    embedding_status: string;
  };
  expect(uploadedDocument.page_count).toBe(3);
  expect(uploadedDocument.chunk_count).toBe(3);
  expect(uploadedDocument.embedding_status).toBe("ready");
  await expect(page.getByText("Search index: ready")).toBeVisible();
  await annotate(page, [".upload-zone", ".library-panel"]);
  await page.screenshot({
    path: path.join(assets, `documents-${info.project.name}.png`),
    fullPage: true,
  });
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Chat", exact: true })
    .click();
  await expect(
    page.getByRole("checkbox", { name: /atlas-handbook.pdf/ }),
  ).toBeChecked();
  for (const [index, question] of source.questions.entries()) {
    if (question.page === null) {
      await page
        .getByRole("button", { name: "Clear chat", exact: true })
        .click();
    }
    const answered = page.waitForResponse(
      (response) =>
        response.url().includes("/api/chat") &&
        response.request().method() === "POST",
    );
    await page.getByLabel("Your question").fill(question.question);
    await page.getByRole("button", { name: /Ask question/ }).click();
    const result = (await (await answered).json()) as {
      answer: string;
      sources_found: boolean;
      citations: { page: number; document_id: string }[];
    };
    expect(result.sources_found).toBe(question.page !== null);
    if (question.page !== null) {
      expect(result.answer).toContain(question.answer_contains);
      expect(result.citations.map((citation) => citation.page)).toEqual([
        question.page,
      ]);
      expect(
        result.citations.every(
          (citation) => citation.document_id === uploadedDocument.id,
        ),
      ).toBe(true);
    } else expect(result.citations).toEqual([]);
    await expect(
      page.getByRole("button", { name: /Ask question/ }),
    ).toBeEnabled();
    if (index === 0) {
      await page.getByRole("button", { name: /View 1 source/ }).click();
      await expect(page.getByText("Page 1", { exact: true })).toBeVisible();
      await expect(page.locator("blockquote")).toContainText("48,000 euros");
      await annotate(page, [".scope-panel", ".chat-panel", ".sources-panel"]);
      await page.screenshot({
        path: path.join(assets, `chat-${info.project.name}.png`),
        fullPage: true,
      });
    }
  }
  await expect(
    page.getByText("No supporting evidence", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Why are there no sources/ }).click();
  await annotate(page, [".chat-panel", ".sources-panel"]);
  await page.screenshot({
    path: path.join(assets, `no-evidence-${info.project.name}.png`),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  // Verify actual tenant isolation with a second synthetic browser account.
  const other = await context.browser()!.newContext();
  try {
    const registered = await other.request.post(`${api}/api/auth/register`, {
      headers: { Origin: "http://127.0.0.1:3200" },
      data: {
        email: `other-${info.project.name}@example.com`,
        password: "Synthetic-only second account password",
        accepted_privacy: true,
      },
    });
    expect(registered.status()).toBe(201);
    const listing = await other.request.get(`${api}/api/documents`);
    expect((await listing.json()).documents).toEqual([]);
    expect(
      (
        await other.request.get(`${api}/api/documents/${uploadedDocument.id}`)
      ).status(),
    ).toBe(404);
  } finally {
    await other.close();
  }
});
