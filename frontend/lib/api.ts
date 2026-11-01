export const apiUrl = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

export async function checkHealth(signal: AbortSignal): Promise<void> {
  const response = await fetch(`${apiUrl}/health`, {
    signal,
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Health request failed");
  const data: unknown = await response.json();
  if (
    typeof data !== "object" ||
    data === null ||
    !("status" in data) ||
    data.status !== "ok" ||
    !("mode" in data) ||
    data.mode !== "local-demo"
  ) {
    throw new Error("Unexpected health response");
  }
}
