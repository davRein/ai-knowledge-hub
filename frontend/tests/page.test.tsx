import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { WorkspaceShell } from "../components/workspace-shell";
vi.mock("next/navigation", () => ({ usePathname: () => "/" }));
vi.mock("../lib/auth", () => ({
  getSession: vi.fn().mockResolvedValue({ mode: "local-demo", user: null }),
  setSession: vi.fn(),
}));
vi.mock("../lib/documents", () => ({
  listDocuments: vi.fn().mockResolvedValue({
    documents: [],
    provider: "fake",
    max_upload_bytes: 1024,
  }),
}));

vi.mock("../components/api-status", () => ({
  ApiStatus: () => <p>API status</p>,
}));

it("clearly labels the local workspace and implemented milestone", async () => {
  render(
    <WorkspaceShell>
      <p>Workspace content</p>
    </WorkspaceShell>,
  );
  expect(await screen.findByText(/not production-secure/)).toBeVisible();
  expect(screen.getByText("Milestone 6 / 6")).toBeVisible();
  expect(screen.getByRole("link", { name: "Chat" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(
    screen.getByRole("link", { name: /Explore API docs/ }),
  ).toHaveAttribute("href", "http://127.0.0.1:8000/docs");
});
