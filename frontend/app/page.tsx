import Link from "next/link";
import { ApiStatus } from "../components/api-status";
import { apiUrl } from "../lib/api";

const steps = [
  {
    number: "01",
    title: "Bring your documents",
    description: "PDF upload and page-aware text extraction.",
    milestone: "Milestone 2",
  },
  {
    number: "02",
    title: "Ask with context",
    description: "Answers grounded in retrieved document excerpts.",
    milestone: "Milestone 3",
  },
  {
    number: "03",
    title: "Follow the evidence",
    description: "Inspect source documents and page references.",
    milestone: "Milestones 3–4",
  },
];

export default function Home() {
  return (
    <div className="workspace">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar" aria-label="Workspace overview">
        <Link className="brand" href="/" aria-label="AI Knowledge Hub home">
          <span className="brand-mark" aria-hidden="true">
            K
          </span>
          <span>
            Knowledge Hub
            <span className="brand-caption">YOUR DOCUMENT WORKSPACE</span>
          </span>
        </Link>
        <p className="section-label">WORKSPACE</p>
        <nav aria-label="Main navigation">
          <Link className="nav-active" href="/" aria-current="page">
            <span aria-hidden="true">◈</span> Overview
          </Link>
        </nav>
        <div className="sidebar-note">
          <span className="eyebrow">BUILT IN THE OPEN</span>
          <p>A foundation for answers you can trace.</p>
          <span className="muted">Milestone 1 / 6</span>
        </div>
      </aside>

      <main id="main">
        <header className="topbar">
          <span>
            Workspace / <strong>Overview</strong>
          </span>
          <span className="badge">LOCAL DEMO</span>
        </header>
        <div className="content">
          <div className="notice">
            <strong>Local development only.</strong> Authentication is not
            implemented. This workspace is not production-secure and must not be
            exposed publicly.
          </div>
          <section className="hero" aria-labelledby="welcome-title">
            <p className="eyebrow">LESS SEARCHING. MORE UNDERSTANDING.</p>
            <h1 id="welcome-title">
              Your knowledge,
              <br />
              <span>connected.</span>
            </h1>
            <p className="hero-copy">
              A home for your documents and the questions they inspire. The
              foundation is here; document tools and AI answers are coming in
              later milestones.
            </p>
            <a
              className="primary-link"
              href={`${apiUrl}/docs`}
              target="_blank"
              rel="noreferrer"
            >
              Explore API docs <span aria-hidden="true">↗</span>
            </a>
          </section>

          <section className="summary-grid" aria-label="Foundation status">
            <article className="panel">
              <p className="section-label">WORKSPACE MODE</p>
              <h2>Local demo</h2>
              <p className="muted">No accounts or document storage yet.</p>
            </article>
            <article className="panel">
              <p className="section-label">BACKEND CONNECTION</p>
              <h2>FastAPI</h2>
              <ApiStatus />
            </article>
            <article className="panel">
              <p className="section-label">CURRENT MILESTONE</p>
              <h2>
                01 <span className="muted small">/ Foundation</span>
              </h2>
              <p className="muted">Dashboard shell &amp; service setup.</p>
            </article>
          </section>

          <section
            className="panel documents"
            aria-labelledby="documents-title"
          >
            <div className="section-heading">
              <div>
                <p className="eyebrow">YOUR LIBRARY</p>
                <h2 id="documents-title">Documents</h2>
              </div>
              <span className="badge neutral">PLANNED · M2</span>
            </div>
            <div className="empty-state">
              <span className="document-icon" aria-hidden="true">
                ▤
              </span>
              <h3>Your library starts here</h3>
              <p>
                PDF upload, ingestion status, and document management
                <br className="desktop-break" /> will be added in Milestone 2.
              </p>
              <button disabled>PDF upload coming in M2</button>
              <p className="fine-print">
                No documents are stored in this foundation.
              </p>
            </div>
          </section>

          <section aria-labelledby="next-title">
            <div className="section-heading">
              <h2 id="next-title">What comes next</h2>
              <span className="muted small">Planned capabilities</span>
            </div>
            <div className="steps-grid">
              {steps.map((step) => (
                <article className="step" key={step.number}>
                  <span className="step-number">{step.number}</span>
                  <p className="eyebrow">{step.milestone}</p>
                  <h3>{step.title}</h3>
                  <p className="muted">{step.description}</p>
                </article>
              ))}
            </div>
          </section>
          <footer>
            AI Knowledge Hub{" "}
            <span>Next.js · FastAPI · PostgreSQL + pgvector</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
