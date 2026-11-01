import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiStatus } from "../components/api-status";
import { checkHealth } from "../lib/api";

afterEach(() => vi.unstubAllGlobals());

describe("API connection", () => {
  it("reports a confirmed local demo response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok", mode: "local-demo" }),
      }),
    );
    render(<ApiStatus />);
    expect(screen.getByRole("status")).toHaveTextContent("Checking API");
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("API reachable"),
    );
  });

  it("shows an error and allows a retry after a failed connection", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error("Offline"))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", mode: "local-demo" }),
      });
    vi.stubGlobal("fetch", fetchMock);
    render(<ApiStatus />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Retry connection" }),
    );
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("API reachable"),
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it.each([
    { ok: false, json: async () => ({ status: "ok", mode: "local-demo" }) },
    { ok: true, json: async () => ({ status: "ok" }) },
    { ok: true, json: async () => null },
  ])("rejects unhealthy or unexpected responses %#", async (response) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
    await expect(checkHealth(new AbortController().signal)).rejects.toThrow();
  });
});
