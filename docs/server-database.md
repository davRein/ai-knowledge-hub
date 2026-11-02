# Existing PostgreSQL on the Linux server

M2 accepts a PostgreSQL URL through `backend/.env`; Docker is not required when using an existing PostgreSQL installation. The app still runs as a local demo: no public frontend/API deployment or authentication is included.

## Information needed

- Existing SSH alias, or SSH username, server address and SSH port.
- PostgreSQL host/port as reachable from that server (often `127.0.0.1:5432`).
- A dedicated project database and role, or authorization for an administrator to create them.
- PostgreSQL version and whether pgvector is installed. M2 stores plain text and does not require vector columns; M3 will need pgvector.

No remote connection, role, database, extension or migration has been created by this implementation. The actual server address is not yet known. Do not paste passwords/private keys into chat, commit them, or put them into frontend environment variables.

## Dedicated database

Use an isolated database such as `ai_knowledge_hub` and a role such as `ai_knowledge_hub_app`. An administrator can create the role/database after choosing the target server:

```sql
CREATE ROLE ai_knowledge_hub_app LOGIN;
-- In interactive psql, set its password without putting it into SQL history:
\password ai_knowledge_hub_app
CREATE DATABASE ai_knowledge_hub OWNER ai_knowledge_hub_app;
```

These are instructions for a reviewed target, not commands to run against an unspecified existing application database. Do not reuse unrelated application tables. A role owning this dedicated database can run the project's Alembic migrations. Granting production privileges and deployment hardening belong to M5.

## Connect through SSH

In a separate local PowerShell/bash terminal, substitute your existing SSH alias:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:15432:127.0.0.1:5432 YOUR_SSH_ALIAS
```

The right-hand `127.0.0.1:5432` refers to PostgreSQL as seen from the Linux server. Adjust it to the actual server-side host/port; keep local port 15432 free. The forward is loopback-only. Keep this terminal open. Normal SSH host-key verification applies; do not disable it. No public PostgreSQL firewall port is needed for this approach.

Set the following only in ignored `backend/.env`, replacing the placeholders and URL-encoding special password characters:

```dotenv
DATABASE_URL=postgresql+psycopg://ai_knowledge_hub_app:REPLACE_WITH_URL_ENCODED_PASSWORD@127.0.0.1:15432/ai_knowledge_hub
```

The SSH tunnel encrypts the connection to the server. If connecting directly instead, explicitly configure TLS with certificate verification according to the server setup. Do not expose PostgreSQL publicly just to connect this local demo.

## Migrate and verify

After verifying the chosen database is dedicated to this project, from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On Linux/macOS use `.venv/bin/python`. Migration `0001_documents` creates only `documents`, `chunks`, their constraints/indexes and Alembic's version table in the target schema. It does not create users, embeddings, or pgvector. Migrations are explicit, never automatic on API startup.

Check `/api/documents` (empty list initially), upload a non-sensitive text-based PDF via `/docs` or the dashboard, verify its status/counts, and delete it. `/health` alone does not test the database connection. Keep database backups according to your server policy; do not downgrade populated migrations casually, as downgrade removes the document/chunk tables.
