import Link from "next/link";
export default function PrivacyPage() {
  return (
    <main className="auth-page">
      <article className="auth-card privacy-card">
        <p className="eyebrow">AI KNOWLEDGE HUB · 2026-11-02</p>
        <h1>Privacy notice</h1>
        <p>
          This development project stores your email, an Argon2id password hash,
          session records, PDF metadata, extracted page text and embeddings in
          PostgreSQL. Uploaded PDF bytes are processed in memory; original PDF
          files are not retained by the application. Questions and answers stay
          in browser memory until you reload or sign out.
        </p>
        <h2>AI providers</h2>
        <p>
          The fake provider processes data locally and is clearly labelled. When
          OpenAI is configured, external processing requires your separate
          opt-in in Account. Extracted text is sent for embeddings; questions
          and relevant excerpts are sent for answers. Your text may be processed
          outside your country. Review{" "}
          <a
            href="https://openai.com/enterprise-privacy/"
            target="_blank"
            rel="noreferrer"
          >
            OpenAI’s API data policies
          </a>{" "}
          and the operator’s provider agreement before using private documents.
          Revoking consent stops new external requests; it does not recall
          previous transfers or delete existing embeddings.
        </p>
        <h2>Retention and deletion</h2>
        <p>
          Documents remain until you delete them or delete your account.
          Deletion removes their text and embeddings from the active database.
          Database backups and provider retention are separate: the operator
          must define retention and restore procedures before public use.
          Expired sessions and anonymous rate-limit buckets are removed by the
          operator’s cleanup command.
        </p>
        <h2>Cookies and logs</h2>
        <p>
          One essential HttpOnly session cookie is used for sign-in (8 hours by
          default). CSRF tokens stay in memory. There are no analytics,
          marketing trackers or browser storage of document content. Application
          request logs contain only a generated request ID, route category,
          status and duration. The hosting operator must also configure proxy
          and infrastructure logs to avoid sensitive URLs and content.
        </p>
        <h2>Development status</h2>
        <p>
          No public deployment is approved. Before serving real users, the
          operator must supply its identity, contact details, legal basis,
          processor contracts, retention periods and rights request procedure.
          For account recovery, contact your local operator; automated email
          recovery is not implemented.
        </p>
        <Link href="/">Back to workspace / sign in</Link>
      </article>
    </main>
  );
}
