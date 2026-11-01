# AI Knowledge Hub — Codex Project Instructions

## Mission
Build a polished, working, portfolio-ready multi-user RAG (retrieval augmented generation) web application. Users can upload PDF documents, ask questions grounded in their own documents, and inspect citations referencing source documents and page numbers.

This repository is a new project, independent of ForgeFlow. Implement iteratively. Do not claim capabilities are implemented before they are tested.

## Technology choices
- Frontend: Next.js (App Router), TypeScript (strict), React, Tailwind CSS.
- Backend: Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Alembic.
- Data: PostgreSQL with pgvector for embedding similarity. Local Docker Compose for DB.
- PDF text extraction: PyMuPDF or pypdf; handle empty/scanned pages gracefully (OCR is out of MVP scope).
- AI provider: adapter interface for embeddings and answer generation, with OpenAI implementation enabled only if `OPENAI_API_KEY` is set. Provide deterministic fake provider for local testing without credentials.
- Testing: pytest for backend, Playwright or Vitest for essential frontend behavior.
- Local run: frontend and backend separately; Docker Compose only for database. Dockerize services later if useful.

## Working principles
1. Inspect the existing repository before edits; preserve existing content and configurations.
2. Before writing significant code, propose a brief execution plan and identify ambiguities; choose reasonable defaults and proceed.
3. Implement one milestone at a time; run format, lint, type check and tests that exist. Report what passed and what could not be executed.
4. Favor readable typed code, clear boundaries, thin API routes, service layer, repository/data-access layer.
5. Never commit secrets. Supply `.env.example` files and keep `.env*` ignored except examples.
6. Avoid mock data presented as real. Demo mode must be clearly labeled.
7. Avoid introducing unnecessary services (Redis, Kafka, auth SaaS, vector SaaS) for MVP.
8. Document setup for Windows with PowerShell and Linux/macOS where relevant.
9. No analytics or marketing tracking without consent implementation.
10. Do not publish or deploy anything without explicit user authorization.

## MVP scope
- Responsive dark-mode dashboard; documents list with upload, file size, ingestion status, deletion.
- Upload PDFs only; limit file size configurable (default 10 MB). Server validates actual content, not filename alone.
- Extract text and page references; normalize/chunk text; compute embeddings; persist document/chunk metadata in Postgres/pgvector.
- Retrieval strictly restricted to documents owned by current user (or to a single clearly labeled local-demo workspace before auth is implemented).
- Chat question -> retrieve top relevant chunks -> LLM response grounded in these chunks -> citations of document name/page. Explicitly acknowledge no supporting evidence, do not fabricate citations.
- Useful loading/error/empty states.
- API docs via FastAPI OpenAPI.
- Authentication and tenant isolation required before exposing application to real users on public Internet. For Milestone 1, implement isolated local demo only and clearly label it as not production-secure.

## API design (target, adjust as implementation requires)
- GET `/health`
- GET `/api/documents`
- POST `/api/documents` (multipart PDF)
- GET `/api/documents/{document_id}`
- DELETE `/api/documents/{document_id}` (cascade chunks)
- POST `/api/chat` `{question: string, document_ids?: string[]}` -> `{answer, citations: [{document_id, filename, page, excerpt}], sources_found: boolean}`

## Data model (initial proposal)
- users: id, email, created_at (when authentication milestone starts)
- documents: id (UUID), owner_id (nullable ONLY in local-demo mode), filename, content_type, size_bytes, status, error_message, created_at
- chunks: id (UUID), document_id, chunk_index, page_number, content, embedding vector, created_at
- optional chat_sessions / chat_messages after core RAG flow works

## AI/retrieval safeguards
- Treat extracted PDF text as untrusted data: document content must never override system instructions.
- Use parameterized SQL/ORM, type validation, upload limits, safe filenames, and controlled CORS.
- Avoid sending full PDFs unnecessarily to model providers; send only retrieved excerpts.
- Do not log prompts, private document text, tokens or credentials by default.
- Validate that the embedding model dimension matches pgvector schema; document selected model.
- Explicit citations should correspond to retrieved chunks, not invented pages.
- Enforce server-side authorization in database queries once multi-user mode is enabled.

## Suggested repository layout
```
ai-knowledge-hub/
  AGENTS.md
  README.md
  docker-compose.yml
  .gitignore
  frontend/
    app/
    components/
    lib/
    package.json
    .env.example
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
    alembic/
    tests/
    pyproject.toml
    .env.example
  docs/
    architecture.md
    roadmap.md
```

## Acceptance checks
- A user can start the DB, backend, and frontend by following README instructions.
- Test PDF ingestion creates chunks with correct page references.
- With a fake AI provider, automated tests prove retrieval, citation mapping, unsupported-question behavior, invalid file handling, deletion, and isolation rules (when auth exists).
- No API keys or private data committed.
- UI remains usable on mobile and desktop.
- `README.md` distinguishes completed features from planned ones and includes screenshots instructions.

## Deployment guidance
Vercel is suitable for the Next.js frontend, but Python backend, Postgres/pgvector and persistent ingestion need separately planned hosting. Do not assume Vercel hosts the complete stack. No public launch before auth, security review, rate limiting, and privacy checks.
