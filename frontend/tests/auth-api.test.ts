import { afterEach, expect, it, vi } from "vitest";
import { authenticatedFetch, setSession } from "../lib/auth";

afterEach(() => {
  setSession(null);
  vi.unstubAllGlobals();
});
it("sends cookies and a memory-only CSRF token for writes", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetcher);
  setSession({
    mode: "authenticated",
    user: null,
    csrf_token: "csrf-test",
    registration_enabled: false,
  });
  await authenticatedFetch("http://example.com/api/documents/id", {
    method: "DELETE",
  });
  const options = fetcher.mock.calls[0][1];
  expect(options.credentials).toBe("include");
  expect(options.headers.get("X-CSRF-Token")).toBe("csrf-test");
});
it("clears the token and notifies the UI when a session expires", async () => {
  const listener = vi.fn();
  window.addEventListener("aihub-session-expired", listener);
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(new Response(null, { status: 401 }))
    .mockResolvedValueOnce(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetcher);
  setSession({
    mode: "authenticated",
    user: null,
    csrf_token: "old",
    registration_enabled: false,
  });
  await authenticatedFetch("http://example.com/api/documents");
  await authenticatedFetch("http://example.com/api/documents/id", {
    method: "DELETE",
  });
  expect(listener).toHaveBeenCalledOnce();
  expect(fetcher.mock.calls[1][1].headers.has("X-CSRF-Token")).toBe(false);
  window.removeEventListener("aihub-session-expired", listener);
});
