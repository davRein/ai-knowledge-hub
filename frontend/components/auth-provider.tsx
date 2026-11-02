"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  type ReactNode,
  type FormEvent,
} from "react";
import {
  authRequest,
  getSession,
  setSession,
  type SessionInfo,
} from "../lib/auth";

type AuthState = {
  session: SessionInfo | null;
  update: (value: SessionInfo) => void;
  logout: () => Promise<void>;
};
const AuthContext = createContext<AuthState | null>(null);
export function useAuth() {
  return useContext(AuthContext);
}

function SignIn({
  registration,
  update,
}: {
  registration: boolean;
  update: AuthState["update"];
}) {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true);
    setError("");
    try {
      const session = await authRequest<SessionInfo>(
        `/api/auth/${register ? "register" : "login"}`,
        "POST",
        {
          email: String(data.get("email")),
          password: String(data.get("password")),
          ...(register
            ? { accepted_privacy: data.get("privacy") === "on" }
            : {}),
        },
      );
      form.reset();
      update(session);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Sign in failed.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">AI KNOWLEDGE HUB</p>
        <h1>{register ? "Create your account" : "Sign in"}</h1>
        <p className="muted">
          Your PDFs and answers stay in your private workspace.
        </p>
        <form onSubmit={submit}>
          <label>
            Email
            <input
              name="email"
              type="email"
              autoComplete="username"
              maxLength={320}
              required
              disabled={busy}
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              minLength={register ? 12 : 1}
              maxLength={128}
              required
              disabled={busy}
            />
          </label>
          {register && (
            <>
              <p className="muted small">
                Use at least 12 characters. External AI processing is off until
                you choose it in Account.
              </p>
              <label className="checkbox-label">
                <input
                  name="privacy"
                  type="checkbox"
                  required
                  disabled={busy}
                />
                I have read the <Link href="/privacy">privacy notice</Link>.
              </label>
            </>
          )}
          {error && (
            <p role="alert" className="error-text">
              {error}
            </p>
          )}
          <button className="action-button" disabled={busy}>
            {busy ? "Please wait…" : register ? "Create account" : "Sign in"}
          </button>
        </form>
        {registration && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() => {
              setRegister(!register);
              setError("");
            }}
          >
            {register
              ? "Already have an account? Sign in"
              : "Create an account"}
          </button>
        )}
        {!registration && (
          <p className="muted small">
            Registration is closed. Contact the operator for access or password
            recovery.
          </p>
        )}
        <Link href="/privacy">Privacy notice</Link>
      </section>
    </main>
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [session, updateState] = useState<SessionInfo | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const authChannel = useRef<BroadcastChannel | null>(null);
  function update(value: SessionInfo) {
    setSession(value);
    updateState(value);
    authChannel.current?.postMessage("session-changed");
  }
  useEffect(() => {
    const controller = new AbortController();
    let timedOut = false;
    const timeout = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 10000);
    void getSession(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) updateState(value);
      })
      .catch(() => {
        if (controller.signal.aborted && !timedOut) return;
        setError(
          "Could not check your session. Start the backend, then retry.",
        );
      })
      .finally(() => window.clearTimeout(timeout));
    const expired = () => {
      setSession(null);
      updateState((current) =>
        current ? { ...current, user: null, csrf_token: null } : null,
      );
    };
    window.addEventListener("aihub-session-expired", expired);
    const channel =
      typeof BroadcastChannel !== "undefined"
        ? new BroadcastChannel("aihub-auth")
        : null;
    if (channel) channel.onmessage = expired;
    authChannel.current = channel;
    return () => {
      controller.abort();
      window.clearTimeout(timeout);
      window.removeEventListener("aihub-session-expired", expired);
      channel?.close();
      authChannel.current = null;
    };
  }, [attempt]);
  async function logout() {
    await authRequest("/api/auth/logout", "POST");
    setSession(null);
    updateState((current) =>
      current ? { ...current, user: null, csrf_token: null } : null,
    );
    authChannel.current?.postMessage("logout");
  }
  const value = { session, update, logout };
  if (pathname === "/privacy")
    return (
      <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    );
  return (
    <AuthContext.Provider value={value}>
      {error ? (
        <main className="auth-page">
          <section className="auth-card">
            <p role="alert">{error}</p>
            <button
              onClick={() => {
                setError("");
                setAttempt(attempt + 1);
              }}
            >
              Retry connection
            </button>
          </section>
        </main>
      ) : !session ? (
        <main className="auth-page">
          <p role="status">Checking session…</p>
        </main>
      ) : session.mode === "authenticated" && !session.user ? (
        <SignIn registration={session.registration_enabled} update={update} />
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
}
