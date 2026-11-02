import { expect, test } from "@playwright/test";

test("account consent, password rotation and confirmed deletion", async ({
  page,
}, testInfo) => {
  let consent = false;
  const session = {
    mode: "authenticated",
    user: {
      id: "account-fixture",
      email: "account@example.com",
      external_ai_consent: consent,
    },
    csrf_token: "before-rotation",
    registration_enabled: false,
  };
  await page.route("**/api/auth/session", (route) =>
    route.fulfill({ json: session }),
  );
  await page.route("**/api/documents", (route) =>
    route.fulfill({
      json: {
        mode: "authenticated",
        provider: "openai",
        max_upload_bytes: 10485760,
        documents: [],
      },
    }),
  );
  await page.route("**/health", (route) =>
    route.fulfill({ json: { status: "ok", mode: "authenticated" } }),
  );
  await page.route("**/api/account", (route) => {
    if (route.request().method() === "DELETE") {
      expect(route.request().headers()["x-csrf-token"]).toBe("after-rotation");
      expect(route.request().postDataJSON().password).toBe(
        "a new synthetic password",
      );
      return route.fulfill({ status: 204 });
    }
    return route.fulfill({
      json: {
        user: session.user,
        usage: { documents: 2, bytes: 1024 },
        limits: { documents: 50, bytes: 209715200 },
      },
    });
  });
  await page.route("**/api/account/consent", (route) => {
    consent = route.request().postDataJSON().accepted;
    return route.fulfill({
      json: { ...session.user, external_ai_consent: consent },
    });
  });
  await page.route("**/api/account/password", (route) => {
    expect(route.request().headers()["x-csrf-token"]).toBe("before-rotation");
    expect(route.request().postDataJSON().new_password).toBe(
      "a new synthetic password",
    );
    return route.fulfill({
      json: {
        ...session,
        csrf_token: "after-rotation",
        user: { ...session.user, external_ai_consent: consent },
      },
    });
  });
  await page.goto("/account");
  await expect(
    page.getByRole("heading", { name: "Account & privacy" }),
  ).toBeVisible();
  await expect(page.getByText(/Storage: 2 \/ 50/)).toBeVisible();
  await page.getByRole("checkbox", { name: /Allow my text/ }).click();
  await expect(
    page.getByRole("checkbox", { name: /Allow my text/ }),
  ).toBeChecked();
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "External AI preference saved." }),
  ).toBeVisible();
  await page
    .getByLabel("Current password", { exact: true })
    .fill("an old synthetic password");
  await page
    .getByLabel("New password", { exact: true })
    .fill("a new synthetic password");
  await page
    .getByRole("button", { name: "Change password", exact: true })
    .click();
  await expect(
    page.getByText("Password changed. Other sessions were revoked."),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("account.png"),
    fullPage: true,
  });
  await page
    .getByLabel("Confirm current password")
    .fill("a new synthetic password");
  await page
    .getByRole("checkbox", { name: /I want to permanently delete/ })
    .check();
  await page
    .getByRole("button", { name: "Delete my account permanently" })
    .click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(
    page.getByText("account@example.com", { exact: true }),
  ).toHaveCount(0);
});
