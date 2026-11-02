# Milestone 1 verification

Historical M1 results are below. See [M2 verification](verification-m2.md), [M3 verification](verification-m3.md) including its data-loss incident report, [M4 verification](verification-m4.md), [M5 verification](verification-m5.md), and current [M6 verification](verification-m6.md).

The existing staged handoff and IDE files were preserved. No commit, deployment, or publication was performed.

## Frontend

Node.js 24.19.0 and npm 11.17.0 were available outside the restricted command environment. Dependency installation generated `frontend/package-lock.json` (Next.js 16.4.3).

- `npm run format:check`: passed.
- `npm run lint`: passed with zero warnings.
- `npm run typecheck`: passed.
- `npm test`: passed, 2 files / 6 tests. Covers honest shell labels, disabled uploads, health response validation, and failure/retry behavior.
- `npm run build`: passed; dashboard and not-found routes prerendered.
- `git diff --check`: passed.

Initial lint findings were corrected before the final checks. npm reported an ESLint 9 deprecation during installation; the compatible Next.js lint configuration passes. Backend/database checks below remain outstanding.

## Backend and database

Initially, Python resolved to the Windows Store placeholder and Docker was unavailable. With the user's authorization, CLI installation supplied Python 3.14.10, WSL 2.7.14, and Docker Desktop 4.97.0 (Docker Engine 29.9.2, Compose v5.6.1). No system reboot was performed or needed for the verified startup.

Backend dependencies were installed into ignored `backend/.venv`. Final results:

- `python -m ruff format --check .`: passed, 9 files already formatted.
- `python -m ruff check .`: passed.
- `python -m mypy app tests`: passed, 9 source files.
- `python -m pytest`: passed, 5 tests. One dependency deprecation warning recommends `httpx2` for future Starlette TestClient compatibility; current tests pass with httpx.

Tests cover the health contract, OpenAPI scope, allowed/disallowed CORS origins, and rejection of non-demo mode. An unused type-ignore comment detected by mypy was removed.

Docker Desktop was started and the engine confirmed reachable. Compose config validation passed. The database started with a healthy status, and a live SQL query confirmed `vector` extension version 0.8.7.

Ignored `infra/.env` was created from the example with `POSTGRES_PORT=5433`, because an existing PostgreSQL process occupies port 5432. That existing process was left untouched. The project database remains running on `127.0.0.1:5433`; the example retains its portable default of 5432. Fresh terminals (or an IDE restart) may be needed to pick up installed executable paths.

Browser visual QA is still outstanding; screenshot instructions are in the README.

## Scope

No PDF, retrieval, citation, deletion, or isolation tests are claimed; those capabilities belong to later milestones. Review M1 before beginning M2.
