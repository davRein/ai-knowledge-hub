import { expect, test } from "@playwright/test";

test("private workspace requires login and clears content on logout and expiry", async ({
  page,
}, testInfo) => {
  let privateCalls = 0;
  let expired = false;
  const session = {
    mode: "authenticated",
    user: {
      id: "user-a",
      email: "alice@example.com",
      external_ai_consent: false,
    },
    csrf_token: "fixture-csrf",
    registration_enabled: true,
  };
  await page.route("**/api/auth/session", (route) =>
    route.fulfill({ json: { ...session, user: null, csrf_token: null } }),
  );
  await page.route("**/api/auth/login", async (route) => {
    expect(route.request().postDataJSON().email).toBe("alice@example.com");
    await route.fulfill({ json: session });
  });
  await page.route("**/api/auth/logout", async (route) => {
    expect(route.request().headers()["x-csrf-token"]).toBe("fixture-csrf");
    await route.fulfill({ status: 204 });
  });
  await page.route("**/api/documents", async (route) => {
    privateCalls++;
    await route.fulfill({
      status: expired ? 401 : 200,
      json: expired
        ? { detail: "Session expired" }
        : {
            mode: "authenticated",
            provider: "fake",
            max_upload_bytes: 10485760,
            documents: [
              {
                id: "00000000-0000-4000-8000-000000000004",
                filename: "Private.pdf",
                size_bytes: 100,
                page_count: 1,
                chunk_count: 1,
                empty_page_count: 0,
                status: "ready",
                embedding_status: "ready",
                embedding_error: null,
                error_message: null,
                created_at: "2026-11-02T12:00:00Z",
              },
            ],
          },
    });
  });
  await page.route("**/health", (route) =>
    route.fulfill({ json: { status: "ok", mode: "authenticated" } }),
  );
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  expect(privateCalls).toBe(0);
  await page.screenshot({
    path: testInfo.outputPath("sign-in.png"),
    fullPage: true,
  });
  await page.getByLabel("Email", { exact: true }).fill("alice@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill("a synthetic password 123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("checkbox", { name: /Private.pdf/ }),
  ).toBeVisible();
  await expect(page.getByText("PRIVATE", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByText("Private.pdf", { exact: true })).toHaveCount(0);
  expired = true;
  await page.getByLabel("Email", { exact: true }).fill("alice@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill("a synthetic password 123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect.poll(() => privateCalls).toBeGreaterThanOrEqual(2);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("registration requires privacy acceptance and privacy page is public", async ({
  page,
}) => {
  await page.route("**/api/auth/session", (route) =>
    route.fulfill({
      json: {
        mode: "authenticated",
        user: null,
        csrf_token: null,
        registration_enabled: true,
      },
    }),
  );
  let registered = false;
  await page.route("**/api/auth/register", (route) => {
    const payload = route.request().postDataJSON();
    expect(payload.accepted_privacy).toBe(true);
    registered = true;
    return route.fulfill({
      status: 409,
      json: { detail: "Fixture registration result" },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Create an account" }).click();
  await page.getByLabel("Email", { exact: true }).fill("new@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill("a synthetic password 123");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  expect(registered).toBe(false);
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Fixture registration result" }),
  ).toHaveText("Fixture registration result");
  await page.goto("/privacy");
  await expect(
    page.getByRole("heading", { name: "Privacy notice" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
