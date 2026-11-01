# AI Knowledge Hub — milestones

## M1 — Repository and foundation
- Inspect repository state; create Next.js TypeScript frontend and FastAPI backend; create PostgreSQL + pgvector Docker Compose.
- Add `.gitignore`, `.env.example`, README with local startup commands, API `/health` and a dashboard shell.
- Configure Python tooling, lint/tests and frontend lint/typecheck. Verify them.
- Use a local-only demo workspace for initial development. Do not expose user data publicly.

## M2 — PDF documents
- PDF upload validation, database migrations, file metadata and delete endpoints.
- Extract page text and store normalized chunks; show processing/error status.
- Unit tests for unsupported files, oversized files, empty/scanned PDFs, and page mapping.

## M3 — RAG pipeline
- Provider interface with fake test implementation and OpenAI implementation.
- Embedding generation and pgvector similarity search.
- Chat route, grounded answer prompt, explicit citations, no-evidence answer.
- Tests for document filtering, retrieval and source correctness.

## M4 — Full UI
- Drag-and-drop upload, documents page, chat area, references panel, responsive styling.
- Friendly states, accessible controls, streaming only if straightforward.

## M5 — Authentication and deployment readiness
- Real authentication, server-enforced per-user document isolation, deletion and storage cleanup.
- Rate limits, quotas, observability without leaking content, privacy notices, secure CORS.
- Deployment options: Vercel frontend + external Python API + managed pgvector Postgres.
- Perform public-launch readiness review before deploy.

## M6 — Portfolio polish (optional)
- Seed with a publicly licensed example PDF and synthetic sample questions.
- Architecture diagram, annotated screenshots, 2-minute demo script, GitHub README summary.
- Highlight RAG, Next.js, Python, FastAPI, PostgreSQL/pgvector, tests, and security design.

## Definition of done for each milestone
Code committed only after user approval; local setup documented; test commands recorded; failures reported; next tasks updated.
