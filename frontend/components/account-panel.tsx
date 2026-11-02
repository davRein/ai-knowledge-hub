"use client";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { authRequest, type SessionInfo, type User } from "../lib/auth";
import { useAuth } from "./auth-provider";

export function AccountPanel() {
  const auth = useAuth();
  const [usage, setUsage] = useState<{
    usage: { documents: number; bytes: number };
    limits: { documents: number; bytes: number };
  } | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const user = auth?.session?.user;
  useEffect(() => {
    if (user)
      void authRequest<NonNullable<typeof usage>>("/api/account")
        .then(setUsage)
        .catch(() => setError("Could not load account usage."));
  }, [user]);
  if (!auth || !user)
    return (
      <section className="panel">
        <h1>Account</h1>
        <p>Account controls are available in authenticated mode.</p>
      </section>
    );
  async function consent(accepted: boolean) {
    if (!auth?.session) return;
    setBusy(true);
    setError("");
    try {
      const updated = await authRequest<User>("/api/account/consent", "PATCH", {
        accepted,
      });
      auth.update({ ...auth.session, user: updated });
      setMessage("External AI preference saved.");
    } catch (error) {
      setError(error instanceof Error ? error.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }
  async function submit(event: FormEvent<HTMLFormElement>, deleting = false) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true);
    setMessage("");
    setError("");
    try {
      if (deleting) {
        await authRequest("/api/account", "DELETE", {
          password: String(data.get("password")),
        });
        window.dispatchEvent(new Event("aihub-session-expired"));
        const channel =
          typeof BroadcastChannel !== "undefined"
            ? new BroadcastChannel("aihub-auth")
            : null;
        channel?.postMessage("deleted");
        channel?.close();
      } else {
        const updated = await authRequest<SessionInfo>(
          "/api/account/password",
          "POST",
          {
            password: String(data.get("password")),
            new_password: String(data.get("new_password")),
          },
        );
        auth?.update(updated);
        form.reset();
        setMessage("Password changed. Other sessions were revoked.");
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel account-panel">
      <p className="eyebrow">PRIVATE WORKSPACE</p>
      <h1>Account & privacy</h1>
      <p>{user.email}</p>
      {usage && (
        <p>
          Storage: {usage.usage.documents} / {usage.limits.documents} documents
          · {(usage.usage.bytes / 1048576).toFixed(1)} /{" "}
          {(usage.limits.bytes / 1048576).toFixed(0)} MB
        </p>
      )}
      <h2>External AI processing</h2>
      <p>
        With OpenAI configured, extracted PDF text is sent for embeddings.
        Questions and retrieved excerpts are sent for answers. The fake provider
        runs locally. <Link href="/privacy">Read the privacy notice</Link>{" "}
        before enabling this.
      </p>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={user.external_ai_consent}
          disabled={busy}
          onChange={(event) => void consent(event.target.checked)}
        />
        Allow my text and questions to be processed by the configured external
        AI provider.
      </label>
      <h2>Change password</h2>
      <form onSubmit={(event) => void submit(event)}>
        <label>
          Current password
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            required
            maxLength={128}
            disabled={busy}
          />
        </label>
        <label>
          New password
          <input
            type="password"
            name="new_password"
            autoComplete="new-password"
            required
            minLength={12}
            maxLength={128}
            disabled={busy}
          />
        </label>
        <button className="action-button" disabled={busy}>
          Change password
        </button>
      </form>
      <h2>Delete account</h2>
      <p>
        This permanently deletes your account, sessions, documents, chunks and
        embeddings from the active database. Backups follow the operator’s
        retention policy.
      </p>
      <form onSubmit={(event) => void submit(event, true)}>
        <label>
          Confirm current password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            maxLength={128}
            disabled={busy}
          />
        </label>
        <label className="checkbox-label">
          <input type="checkbox" required disabled={busy} />I want to
          permanently delete my account and documents.
        </label>
        <button className="action-button danger" disabled={busy}>
          Delete my account permanently
        </button>
      </form>
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="error-text">
          {error}
        </p>
      )}
    </section>
  );
}
