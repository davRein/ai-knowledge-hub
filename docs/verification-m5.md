# Milestone 5 verification — 2026-11-02

## Scope and files

M5 adds real accounts/sessions, owner isolation, account/data deletion, quotas/rates, privacy/AI consent, safe request metadata and deployment preparation. M6, publication, remote Linux changes and commits are excluded. Earlier uncommitted work was preserved.

- Backend: `core/access.py`, `passwords.py`, `security_headers.py`; `models/auth.py`; `schemas/auth.py`; `services/auth.py`, `limits.py`; `api/auth.py`; migration `0003_authentication`; operator commands `manage.py`, `setup_local_auth.py`. Existing document/retrieval/provider/configuration/routes now enforce ownership and consent. `reindex.py` selects an explicit authenticated account.
- Frontend: `lib/auth.ts`, `components/auth-provider.tsx`, `account-panel.tsx`, `/account`, `/privacy`; shell/API clients/health display and upload/chat controls updated for authenticated mode. Essential cookie/CSRF state is separated from ephemeral document/chat state.
- Tests: backend authentication/management coverage, frontend cookie/CSRF client tests and auth/account browser workflows. `scripts/test_postgres.py` provides a separate disposable Windows PostgreSQL cluster.
- Documentation: README local account/legacy-transfer/operator instructions, architecture and [security/deployment review](security.md). `infra/.env.example` remains database-only.

## Automated checks

- Backend `ruff format --check .` and `ruff check .`: passed.
- Backend `mypy app tests`: passed (51 source files).
- Backend `pip check`: passed.
- Temporary SQLite tests: **57 passed, 1 skipped**. The one skip needs actual pgvector schema behavior.
- Separate PostgreSQL 18.6/pgvector instance: **58 passed**, including real cosine retrieval, migration upgrade/downgrade/upgrade, authentication and owner boundaries. This cluster used a random credential, loopback port 55432 and its own temporary data directory; data-directory identity was checked. It was stopped and removed afterward. The persistent project database was not a test target.
- Frontend Prettier, ESLint (zero warnings), TypeScript and production Next.js build: passed.
- Frontend Vitest: **34 passed** across 6 files.
- Playwright/Edge: **12 passed**, desktop 1440×1000 and mobile 390×844. Covers sign-in gating, no private fetch before login, CSRF transport, logout/expiry state clearing, privacy acceptance/public notice, consent saving, password rotation, confirmed account deletion and the previous upload/chat/source/navigation/error workflows. Browser API fixtures are synthetic; they do not contact the project document database.
- `git diff --check`: passed.
- Compose `config --quiet`: passed without needing the stopped Docker daemon. The database configuration itself was unchanged.

Backend tests prove cross-account list/detail/delete/retrieval/selected-ID isolation, real citation ownership, anonymous rejection, CSRF/Origin failure, password hashing/rotation/session revocation/expiry, quota release, rate-limit Retry-After, sanitized validation, consent blocking, closed registration, host/security settings, deletion cascades and explicit legacy transfer. They also prove the ownership migration retains document IDs/text/page references with no automatic assignment.

The known Starlette TestClient/httpx deprecation warning remains; tests pass. Playwright emits an environment color-variable warning. No live OpenAI call was made. No dependency/security scanner or independent penetration test is claimed.

## Persistent local upgrade and smoke check

A proposed test run targeting the configured project URL was rejected by automatic safety review because a fixture/isolation regression could damage persistent documents. It was not executed. Docker Desktop was not running, so tests instead used a new disposable native PostgreSQL cluster. An initial Windows stdout-inheritance issue in that helper was corrected, its stopped temporary files removed, and the successful run above completed with cleanup. No approval or safety rejection remains blocking the isolated checks.

Before the actual additive project upgrade, a fresh custom-format `pg_dump` was created and its archive directory validated with `pg_restore --list`:

`C:\Users\info\AppData\Local\Temp\ai-knowledge-hub-before-m5-final-20261102-144325.dump`

Only `alembic upgrade head` ran against local database `ai_knowledge_hub` on port 5432. No test/downgrade ran there. Before/after in-memory row hashes and IDs verified **1 existing document and 5 chunks unchanged** (excluding the newly added null owner field). The head is `0003_authentication`; all legacy documents remain unassigned. No application's data was moved, auto-claimed or deleted.

Ignored `backend/.env` was updated to authenticated development mode with registration enabled and an unprinted random security key. Existing database/provider settings were preserved. No real account or password was created. A backend reload reports `mode=authenticated` and `/api/auth/session` reports no signed-in user with registration enabled. A fresh Edge context opened the actual frontend on port 3000 and actual backend on 8000 and verified the sign-in screen without fixtures or account creation. The screenshot is an ignored local artifact; existing documents were not accessed by that browser check.

Register your own account in the UI. The legacy document stays invisible until the local operator explicitly runs the README `claim-demo` dry run and confirmation for that account. The dump contains private data and must be protected, moved into the operator's backup process if desired, and deleted according to its retention policy; a Temp file is not a durable backup strategy. An archive-list check is not a full restore drill.

## Limits and next action

Read [the launch decision](security.md#public-launch-decision) before public exposure. Hosting/TLS/proxy policy, operational privacy details/contracts, backup restore/deletion handling, abuse/resource isolation, recovery policy and independent review remain operator gates. No deployment took place. M6 portfolio polish is the next optional roadmap milestone and has not started.
