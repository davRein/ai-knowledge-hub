import { apiUrl } from "./api";

export type User = { id: string; email: string; external_ai_consent: boolean };
export type SessionInfo = {
  mode: "local-demo" | "authenticated";
  user: User | null;
  csrf_token: string | null;
  registration_enabled: boolean;
};
let csrf: string | null = null;
export function setSession(session: SessionInfo | null) {
  csrf = session?.csrf_token ?? null;
}
export async function authenticatedFetch(url: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (csrf && !["GET", "HEAD", "OPTIONS"].includes(init.method ?? "GET"))
    headers.set("X-CSRF-Token", csrf);
  const response = await fetch(url, {
    ...init,
    headers,
    credentials: "include",
  });
  if (response.status === 401 && !url.endsWith("/auth/login")) {
    setSession(null);
    window.dispatchEvent(new Event("aihub-session-expired"));
  }
  return response;
}
export async function authRequest<T>(
  path: string,
  method = "GET",
  body?: object,
  signal?: AbortSignal,
): Promise<T> {
  const response = await authenticatedFetch(`${apiUrl}${path}`, {
    method,
    cache: "no-store",
    signal: signal ?? AbortSignal.timeout(15_000),
    ...(body
      ? {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : {}),
  });
  if (!response.ok) {
    const error: unknown = await response.json().catch(() => null);
    throw new Error(
      typeof error === "object" &&
        error &&
        "detail" in error &&
        typeof error.detail === "string"
        ? error.detail
        : `Request failed (${response.status}). Check your input and try again.`,
    );
  }
  return response.status === 204
    ? (undefined as T)
    : (response.json() as Promise<T>);
}
export async function getSession(signal?: AbortSignal): Promise<SessionInfo> {
  const session = await authRequest<SessionInfo>(
    "/api/auth/session",
    "GET",
    undefined,
    signal,
  );
  if (
    !["local-demo", "authenticated"].includes(session.mode) ||
    (session.mode === "authenticated" &&
      session.user &&
      (!session.user.id || !session.csrf_token))
  )
    throw new Error("Unexpected session response.");
  setSession(session);
  return session;
}
