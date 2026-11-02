# Milestone 2 verification

## Scope and environment

PDF documents only: no RAG, provider, chat, authentication, deployment, or commit was added. The user's existing Linux PostgreSQL server was not contacted or modified because its connection details are not yet supplied. It remains configurable through `DATABASE_URL`; [server connection instructions](server-database.md) are included.

Checks ran with Python 3.14.10 and Node 24.19.0. The local PostgreSQL 17 / pgvector container on 127.0.0.1:5433 was used solely for integration tests with disposable `test_m2_<uuid>` schemas. Existing databases/tables outside those schemas were not migrated or deleted. A second run used temporary SQLite databases, also built through Alembic rather than `create_all`.

Subsequently, the user selected the existing local PostgreSQL 18 instance and explicitly authorized creating `ai_knowledge_hub_app` and `ai_knowledge_hub`. Creation used the already authenticated pgAdmin session. The new role owns the new project database and its superuser, create-role and create-database flags were verified false. A generated project password is stored only in ignored `backend/.env`; the SQL editor received a SCRAM verifier rather than a plaintext password.

PostgreSQL 18.6 on 127.0.0.1:5432 is now the configured backend database. Alembic upgrade completed at `0001_documents`; the persistent public tables are `documents`, `chunks`, and `alembic_version`. Existing ForgeFlow databases were not modified. The Linux server was not accessed.

## Observed results

- Ruff formatting and lint: passed.
- mypy on `app tests`: passed.
- pytest with SQLite: 24 passed.
- pytest with local PostgreSQL: 24 passed.
- pytest repeated with PostgreSQL 18.6 and the restricted project role: 24 passed, using isolated temporary schemas.
- Backend API smoke test against the migrated native project database: list returned 200; generated two-page PDF ingested with ready status and two chunks; deletion returned 204. The generated test document was removed afterward.
- Frontend formatting, ESLint and strict TypeScript: passed.
- Vitest: 13 passed in 3 files.
- Next.js production build: passed.

Backend tests cover valid/mixed-page ingestion, exact source pages, deterministic chunk indices, metadata, filename sanitation, list/detail/delete, FK chunk cascade, unrelated workspace queries, unsupported filenames/MIME/signatures, zero-byte and oversized uploads, multipart body limiting without Content-Length, damaged/encrypted/empty/image-only/zero-page PDFs, page/text extraction limits, visible processing state, and migration upgrade/downgrade/upgrade.

Frontend tests cover API health/retry/response validation, demo labels, loading and real empty library, connection-error refresh, client file validation, upload status/page counts, extraction failure display, successful confirmed deletion, and retention of rows after deletion failure.

One pre-existing dependency warning remains: Starlette's TestClient recommends httpx2 in future; tests pass with the configured httpx. No warnings are suppressed.

## Remaining manual checks

- Linux server connection is deferred by the user's choice to use local PostgreSQL 18 for testing. No remote configuration is claimed.
- Browser visual QA on desktop/mobile remains outstanding; follow README screenshot instructions.
- Full UI and drag-and-drop remain M4. OCR remains outside MVP. M3 has not started.
