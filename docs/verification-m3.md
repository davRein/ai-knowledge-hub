# Milestone 3 verification

## Data-loss incident and correction

An initial PostgreSQL M3 test run added `public` to the isolated schema's search path so the pgvector type/operators were visible. Alembic's unqualified version table then resolved to `public.alembic_version`, causing fixture upgrades to skip the isolated tables. Tests accidentally operated on public project tables, and the downgrade test removed them. One document existed before the run; its stored text/metadata was lost. Original PDFs are not retained by the application, so recovery requires the original PDF or an earlier external database backup. No restored document content is claimed.

The user was informed during implementation. A dump of the remaining database state was taken before repair at the local temporary path `ai-knowledge-hub-before-repair-20261101-235254.dump`. This is an after-incident state capture, not a backup containing the lost document. The empty project schema was recreated at `0002_embeddings`. No other database was targeted or modified by these tests.

Corrections:

- Alembic explicitly schema-qualifies its version table using `current_schema()` and wraps migrations in a committed engine transaction.
- Test ORM engines translate table names to the generated schema explicitly.
- Before API tests run, fixtures verify the schema, the existence of all three local tables and actual PostgreSQL table resolution.
- After each PostgreSQL test, fixtures verify public table identities are unchanged.
- Migration reflection checks name the test schema, avoiding public-table fallback.

Use a dedicated test database and keep backups for persistent development data. The incident is not hidden by the later passing tests.

## Implemented scope

Provider interface, deterministic fake adapter, optional OpenAI adapter, `vector(1536)` migration/provenance, upload indexing, explicit reindex, scoped cosine retrieval, Chat API, no-evidence behavior and validated source mapping. No chat UI, authentication, streaming, deployment, or commit was added.

pgvector 0.8.7 was built from official source tag v0.8.7 (commit f37c13f68b57d2c3472b2214fbcff699d6d34876) with installed MSVC x64 tools. Files were installed for native PostgreSQL 18; the extension was enabled only in `ai_knowledge_hub` through the existing pgAdmin administrator session. The application role received no elevated privileges. PostgreSQL 18.6 / pgvector 0.8.7 and migration `0002_embeddings` are the local target.

## Checks

The final repaired suite passed **46 backend tests against PostgreSQL 18**, including actual pgvector distance queries, schema-checked migration rollback/upgrade, preservation of source text across the embedding migration, retrieval, real source pages, workspace/document filters, deleted evidence, model provenance, malformed vectors, database dimension mismatch, second-batch failure without partial indexing, indexing failure/reindex and rejection of invented source IDs. SQLite passed **45 tests with 1 PostgreSQL-only dimension test skipped**. OpenAI adapter tests use simulated HTTP responses only. No live OpenAI request or API charge was made. One existing Starlette TestClient deprecation warning remains.

Frontend lint/typecheck, 13 Vitest tests and production build passed. Dashboard changes show M3 status, active provider and embedding status; they do not implement the M4 chat interface. Browser visual QA and real OpenAI retrieval/answer quality remain unverified.

The live application smoke test against the repaired public project schema passed PDF ingestion, embedding generation, document-filtered chat, exact page mapping, unsupported-question abstention and deletion of its generated PDF. The generated smoke document was deleted. Public document/chunk counts were both zero afterward; this does not restore the lost pre-incident document. `python -m app.reindex` ran in fake mode and reported indexed=0, failed=0 on that empty schema.
