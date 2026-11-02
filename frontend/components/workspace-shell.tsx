"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useState } from "react";
import { AuthProvider, useAuth } from "./auth-provider";
import { apiUrl } from "../lib/api";
import { ApiStatus } from "./api-status";
import { useWorkspace, WorkspaceProvider } from "./workspace-provider";

function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { provider, documents } = useWorkspace();
  const auth = useAuth();
  const [error, setError] = useState("");
  const privateWorkspace = auth?.session?.mode === "authenticated";
  return (
    <div className="workspace app-workspace">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar" aria-label="Workspace navigation">
        <Link className="brand" href="/" aria-label="AI Knowledge Hub home">
          <span className="brand-mark" aria-hidden="true">
            K
          </span>
          <span>
            Knowledge Hub
            <span className="brand-caption">ANSWERS WITH EVIDENCE</span>
          </span>
        </Link>
        <p className="section-label">
          {privateWorkspace ? "PRIVATE WORKSPACE" : "LOCAL WORKSPACE"}
        </p>
        <nav aria-label="Main navigation">
          <Link
            className={pathname === "/" ? "nav-active" : ""}
            href="/"
            aria-current={pathname === "/" ? "page" : undefined}
          >
            <span aria-hidden="true">◈</span> Chat
          </Link>
          <Link
            className={pathname === "/documents" ? "nav-active" : ""}
            href="/documents"
            aria-current={pathname === "/documents" ? "page" : undefined}
          >
            <span aria-hidden="true">▤</span> Documents{" "}
            <span className="nav-count">{documents.length}</span>
          </Link>
          {privateWorkspace && (
            <Link
              href="/account"
              className={pathname === "/account" ? "nav-active" : ""}
            >
              Account & privacy
            </Link>
          )}
        </nav>
        {privateWorkspace && (
          <div className="account-summary">
            <p>{auth?.session?.user?.email}</p>
            <button
              className="text-button"
              onClick={() => {
                setError("");
                void auth
                  ?.logout()
                  .catch(() => setError("Sign out failed. Please retry."));
              }}
            >
              Sign out
            </button>
            {error && <p role="alert">{error}</p>}
          </div>
        )}
        <div className="sidebar-note">
          <p className="eyebrow">TRACE EVERY ANSWER</p>
          <p>
            Your documents.
            <br />
            Your questions.
            <br />
            The evidence behind them.
          </p>
          <p className="muted small">Milestone 6 / 6</p>
          <a
            className="text-button"
            href={`${apiUrl}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            Explore API docs ↗
          </a>
        </div>
      </aside>
      <div className="workspace-body">
        <header className="topbar">
          <span>
            Workspace /{" "}
            <strong>
              {pathname === "/documents"
                ? "Documents"
                : pathname === "/account"
                  ? "Account"
                  : "Chat"}
            </strong>
          </span>
          <div className="topbar-badges">
            <span className="badge neutral">
              {provider === "fake"
                ? "FAKE PROVIDER"
                : provider === "openai"
                  ? "OPENAI"
                  : "CONNECTING"}
            </span>
            <span className="badge">
              {privateWorkspace ? "PRIVATE" : "LOCAL DEMO"}
            </span>
          </div>
        </header>
        <main id="main" className="workspace-content">
          <div className="notice">
            {privateWorkspace ? (
              <>
                <strong>Private workspace.</strong> Server-side ownership checks
                are active. Public deployment still requires the documented
                launch review.{" "}
                {provider === "openai" &&
                  !auth?.session?.user?.external_ai_consent && (
                    <>
                      Enable external AI processing in{" "}
                      <Link href="/account">Account</Link> before uploading or
                      asking questions.
                    </>
                  )}
              </>
            ) : (
              <>
                <strong>Local demo only.</strong> Authentication is disabled in
                this mode. This workspace is not production-secure and must not
                be exposed publicly.
              </>
            )}
          </div>
          {children}
          <footer>
            <span>
              AI Knowledge Hub · M6 · <Link href="/privacy">Privacy</Link>
            </span>
            <details>
              <summary>Service connection</summary>
              <ApiStatus />
            </details>
          </footer>
        </main>
      </div>
    </div>
  );
}

export function WorkspaceShell({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <ScopedWorkspace>{children}</ScopedWorkspace>
    </AuthProvider>
  );
}

function ScopedWorkspace({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const pathname = usePathname();
  if (pathname === "/privacy") return children;
  return (
    <WorkspaceProvider key={auth?.session?.user?.id ?? "local-demo"}>
      <Shell>{children}</Shell>
    </WorkspaceProvider>
  );
}
