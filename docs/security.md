# M5 security and deployment review

Status: implemented for local testing; **no deployment or public launch approved**. This is a source-level review plus the automated checks in [verification-m5.md](verification-m5.md), not an independent penetration test.

## Authentication and authorization

Passwords use Argon2id (19 MiB, two iterations, parallelism one), following the [OWASP password-storage baseline](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). Password inputs are 12–128 characters for creation/change. Unknown-user login still verifies a dummy hash. Login failures are generic. Validation responses omit input values; credentials never appear in command arguments or intentional application logs.

A random 256-bit opaque session token is issued on login/registration/password change. Only its SHA-256 hash is stored in PostgreSQL, with absolute expiry (8 hours by default, maximum configuration 24). At most five sessions are kept per account. Logout revokes the current session; password change/reset revokes all sessions, with a fresh session for the password-changing browser. Cookies are HttpOnly, SameSite=Lax, Path=/; production requires Secure and uses the `__Host-` prefix, with no Domain attribute. See [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

Unsafe authenticated requests require an exact allowed Origin and an HMAC-derived CSRF token, compared in constant time. Login/registration require an allowed Origin even before a session exists. The CSRF key must be randomly generated and kept private; rotating it invalidates CSRF tokens, not stored session hashes. To forcibly invalidate sessions, delete/revoke the session rows too. See [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

`PrincipalDependency` derives user/workspace IDs from the database session, never client parameters. Both owner and workspace filter document list/get/delete, selected-document validation and retrieval before top-k. Citation metadata comes exclusively from retrieved owned chunks. Unauthenticated requests fail closed. Local-demo mode is an explicit exception for loopback development; it selects only unassigned records in its fixed demo workspace. No public anonymous demo is provided.

Migration `0003_authentication` preserves existing records with null ownership. Registration never claims them. The local operator can transfer them explicitly using the quota-checked `claim-demo` dry-run/confirmation command. DB administration/management commands are privileged operator tools, not HTTP endpoints. Application users have no administrative role.

## Data lifecycle and resource bounds

Original PDFs are processed in memory and discarded. Active database records contain extracted text, page references, vectors and metadata. Document deletion cascades to chunks/vectors. Account deletion requires password reconfirmation and cascades through documents, chunks and sessions. It does not remove other accounts or unassigned legacy data. Database disk space is reclaimed/reused according to PostgreSQL maintenance, not a promise of physical secure erasure.

Upload bytes, page/text limits and user document/byte/chunk quotas bound normal ingestion. PostgreSQL user-row locks serialize quota checks and writes. Failed documents count against document/byte quotas until deleted. Fixed-window counters use atomic database upserts and HMAC keys rather than storing raw IPs or email addresses. Authentication and protected-user/chat/upload limits are shared across API workers; 429 includes Retry-After. There is no Redis dependency. Password confirmation is separately limited. Default numbers are in README and `.env.example`.

Run `python -m app.manage cleanup` hourly through cron/Task Scheduler to remove expired sessions and rate buckets. Data and accounts otherwise persist until explicitly deleted. Define encrypted backup retention and a restore process that reapplies deletion requests before restoring service; deletion from the active DB does not erase existing dumps, provider retention or infrastructure logs.

No analytics/marketing tracking is installed. `/privacy` lists stored data, essential cookies and the external processing boundary. Authenticated users must separately opt into OpenAI before uploads/questions/reindex send text externally. Revocation prevents new requests, not requests already running or previous transfers. The fake provider needs no credentials and makes no external AI requests. Original files are not sent to AI; extracted text is sent for embeddings and selected excerpts/questions for answers. No live OpenAI quality or provider retention setting was verified.

## Observability and safe configuration

The API adds a generated request ID, no-store, nosniff, frame denial, no-referrer, no-index and a restrictive CSP on JSON API responses. Next.js adds nosniff/frame/referrer/permissions headers. The frontend renders document text and answers as React text, never injected HTML. An enforced frontend script CSP remains a deployment review item because Next.js needs nonce/hash integration.

`aihub.requests` emits only request ID, coarse route category, method, status and duration. It does not emit URL identifiers, IPs, emails, questions, text, SQL parameters or credentials. The request logger emits INFO metadata to stderr by default; configure its collector/retention explicitly when operating the service. Start Uvicorn with `--no-access-log` to avoid its separate URL/IP logs; review proxy, platform and error-reporting logs as well. Do not enable SQL echo or request-body logging. `/health` is liveness only, not database readiness. Database failures produce generic 503 responses. Development API docs are disabled in production.

Production startup fails unless authenticated mode, Secure cookies, closed registration, explicit HTTPS CORS origins, public allowed hosts and a non-example database credential are configured. These checks reduce configuration mistakes; they do not validate TLS, DNS, proxy settings or a weak real database password. The database application role should have only project privileges. Migrations need DDL rights; consider separating migration and runtime roles during deployment review.

## Deployment options and runbook

Keep Next.js on Vercel if desired, run FastAPI on a separate Python host/container, and use separately managed PostgreSQL with pgvector and private/TLS database access. Vercel does not host this application's complete stack. An operator-managed Linux server for API/PostgreSQL is also possible, with backups and maintenance owned by the operator. No hosting plan, account, paid service or remote server was configured here.

Use a common site such as `hub.example.com` and `api.example.com`, or proxy `/api` to the API on the frontend origin. SameSite=Lax cookies do not support an unrelated default Vercel domain calling an unrelated API domain. Prefer controlled subdomains rather than loosening cookie policy. Configure the following on the API host through secret management:

```dotenv
APP_MODE=authenticated
APP_ENV=production
ALLOW_REGISTRATION=false
AUTH_COOKIE_SECURE=true
SECURITY_KEY=<random secret of at least 32 characters>
ALLOWED_HOSTS=["api.example.com"]
CORS_ORIGINS=["https://hub.example.com"]
DATABASE_URL=<private PostgreSQL URL with TLS and unique credential>
AI_PROVIDER=fake
```

Provision operator-approved users with `python -m app.manage create-user --email ...` after presenting the privacy notice. Supply `NEXT_PUBLIC_API_URL=https://api.example.com` at frontend build time; never include secrets in `NEXT_PUBLIC_*`. Backup first, run `alembic upgrade head` once as a release step, then start `uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log` behind the configured TLS proxy. Restrict trusted proxy addresses explicitly; do not trust client-controlled forwarded headers. If binding inside a private container network, restrict ingress through its proxy. Test logout, CSRF, ownership and deletion on staging with synthetic PDFs before any launch. Do not roll back schema destructively on persistent user data; restore/forward-fix using the reviewed backup runbook.

## Public-launch decision

Completed: authenticated sessions, password hashing/rotation/revocation, server ownership boundaries, deletion cascades, basic quotas/rates/body limits, exact CORS/host validation, separate AI consent, privacy screen and safe request metadata. Tests cover these boundaries with synthetic data.

Still required before public exposure:

- Choose hosting/region, TLS, controlled cookie domains, proxy trust, network isolation, database credentials/TLS and secret rotation procedures. Verify actual cross-origin cookies and allowed/disallowed origins in staging.
- Supply operator identity/contact, privacy basis, processor agreements, retention/deletion/restore policy, rights requests and recovery procedure. The development notice is not a finished public privacy policy.
- Review authentication independently, decide whether verified email, automated recovery and MFA are required; they are not implemented. Keep production registration closed. Do not treat an email string as proof of ownership.
- Apply edge limits for anonymous traffic, request timeouts, concurrency and platform spending; database counters do not prevent distributed volumetric attacks. Synchronous PDF parsing is not sandboxed against decompression/CPU attacks; evaluate worker isolation/resource limits before untrusted uploads.
- Review dependencies/images, run staging security/abuse tests, configure frontend CSP and HSTS at the HTTPS edge, monitor errors/rates without private content, schedule cleanup and verify encrypted backup restoration. No independent penetration test or full software-supply-chain audit was performed.
- Obtain explicit user authorization for deployment. M5 work creates no public endpoint and gives no blanket launch approval.

M6 portfolio materials are optional and outside this milestone.
