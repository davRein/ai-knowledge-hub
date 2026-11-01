# AI Knowledge Hub

A portfolio project for document-grounded answers with traceable sources. **M1 implements the local development foundation only.** This project is independent of ForgeFlow. The original handoff instructions remain in [AGENTS.md](AGENTS.md), [ROADMAP.md](ROADMAP.md), and [CODEX_START.md](CODEX_START.md).

## Implemented in M1

- Next.js App Router, React, strict TypeScript, Tailwind CSS, and a dark responsive dashboard shell.
- Explicit local-demo labels, disabled upload control, and a real API health indicator with loading/error/retry states.
- FastAPI `GET /health`, typed settings, explicit local frontend CORS origins, and generated OpenAPI docs.
- PostgreSQL 17 + pgvector Compose configuration, persistent volume, healthcheck, and first-start extension SQL.
- Frontend lint, formatting, typecheck and Vitest; backend Ruff, mypy and pytest configuration and tests.

**Planned, not implemented:** PDF upload/storage/extraction and database models/migrations (M2), embeddings/retrieval/AI/citations (M3), full documents/chat UI (M4), authentication and user isolation (M5). The API does not connect to PostgreSQL yet. No API key is required or used.

**Local demo only; not production-secure.** No accounts or authentication exist. Keep the loopback bindings and do not expose these services publicly. CORS is not authentication. No deployment is part of M1.

## Repository layout

```text
frontend/              Next.js app, components, API helper, tests, npm lockfile
backend/               FastAPI app, settings, response schemas, pytest tests
infra/compose.yaml     Database only; application services run separately
infra/init/            First-start pgvector extension SQL
docs/architecture.md   Boundaries, current data flow, security and future layers
docs/verification.md   Observed checks and missing prerequisites
ROADMAP.md             Authoritative milestone scope
```

## Prerequisites

- Node.js 22.13+ or Node.js 24 LTS, with npm.
- Python 3.12+ with pip and venv.
- Running Docker Desktop with Linux containers on Windows/macOS, or Docker Engine + Compose v2 on Linux.
- Free local ports: frontend `3000`, API `8000`, PostgreSQL `5432`.

Run from the repository root unless indicated. Use separate terminals for frontend and backend.

## Windows PowerShell

### Database

```powershell
Copy-Item infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/compose.yaml up -d --wait
docker compose --env-file infra/.env -f infra/compose.yaml ps
docker compose --env-file infra/.env -f infra/compose.yaml exec db psql -U knowledge_hub -d knowledge_hub -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

The example credentials are local development defaults. If you change the username/database, adjust the `psql` command. Change `POSTGRES_PORT` in `infra/.env` if 5432 is occupied. On the current development machine, the local file is already configured for **5433** to avoid an existing PostgreSQL instance; skip the copy command when keeping that file. The database is bound to `127.0.0.1` only. The API can run without the database in M1.

### Backend (terminal A)

```powershell
Set-Location backend
Copy-Item .env.example .env
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If the Python launcher is unavailable, use `python -m venv .venv` after confirming `python --version` is 3.12+. Direct virtual environment paths avoid PowerShell activation-policy changes.

- Health: <http://127.0.0.1:8000/health> → `{"status":"ok","mode":"local-demo"}`
- Swagger: <http://127.0.0.1:8000/docs>
- OpenAPI: <http://127.0.0.1:8000/openapi.json>

`/health` reports API process liveness only, not database or AI readiness.

### Frontend (terminal B)

```powershell
Set-Location frontend
Copy-Item .env.example .env.local
npm.cmd ci
npm.cmd run dev
```

Open <http://127.0.0.1:3000>. `npm.cmd` avoids PowerShell script-policy issues. `NEXT_PUBLIC_API_URL` defaults to `http://127.0.0.1:8000`. Restart after changing `.env.local`; production builds embed the public URL. Never put secrets in `NEXT_PUBLIC_*` variables. The example disables Next.js telemetry.

## Linux / macOS

Database, from the root:

```bash
cp infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/compose.yaml up -d --wait
docker compose --env-file infra/.env -f infra/compose.yaml exec db psql -U knowledge_hub -d knowledge_hub -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

Backend, in its own terminal:

```bash
cd backend
cp .env.example .env
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, in another terminal:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

## Checks

From `frontend/` (PowerShell: use `npm.cmd`):

```bash
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

Apply formatting with `npm run format`. Use `npm run start` to serve a production build locally after building.

From `backend/`, after installing the dev extra:

```powershell
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy app tests
.\.venv\Scripts\python.exe -m pytest
```

Linux/macOS: substitute `.venv/bin/python` for `.\.venv\Scripts\python.exe`. Apply Python formatting with that interpreter and `-m ruff format .`.

Compose validation, from root after creating `infra/.env`:

```bash
docker compose --env-file infra/.env -f infra/compose.yaml config --quiet
```

See [verification results](docs/verification.md) for observed outcomes. Configured tests are not proof of unexecuted functionality.

## Shutdown and troubleshooting

- Stop frontend/backend with `Ctrl+C`.
- Stop the database while retaining data: `docker compose --env-file infra/.env -f infra/compose.yaml down`.
- Inspect startup: `docker compose --env-file infra/.env -f infra/compose.yaml logs db`.
- Initialization SQL runs only on an empty volume. An existing database missing the extension needs `CREATE EXTENSION IF NOT EXISTS vector;` via `psql`. Changing `.env` credentials does not update credentials in an existing database volume.
- If the API is unavailable, start the backend, open `/health` directly, then click **Retry connection**. If the frontend origin changes, update the JSON `CORS_ORIGINS` array in `backend/.env` explicitly.
- If Python opens the Microsoft Store, install Python 3.12+ and reopen the terminal. If Docker is unavailable, install/start Docker Desktop with Linux containers.
- Environment files, caches, screenshots, and local uploads are ignored. Existing staged IDE files were preserved; ignore rules do not unstage files.

## Screenshots

Start frontend and backend, open the dashboard, and capture desktop (1440×1000) and mobile (390×844) views using browser developer tools. Check horizontal overflow, keyboard focus, readable local-demo labels, and the actual API health state. Save optional local captures under ignored `screenshots/`. No screenshots or example documents are bundled in M1.

## Next step

Review M1 and resolve outstanding environment checks, then explicitly begin **M2: PDF documents**. No later milestone has been started.
