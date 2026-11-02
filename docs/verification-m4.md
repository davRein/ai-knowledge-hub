# Milestone 4 verification

## Scope

Frontend workspace only: Chat and Documents routes, file-picker/drop upload, selection/filtering, pending/error/empty states, cancellation/retry, in-tab history and a per-answer source panel. No backend route, migration, provider configuration, authentication, streaming, deployment or commit was added by M4. Existing earlier milestone changes were preserved.

The frontend's generated `AGENTS.md` was read, along with the installed Next.js 16.4.3 guides on layouts/pages and server/client components before implementation. The existing English UI language, dark styling and explicit local-demo limitations were retained.

## Automated results

- ESLint: passed with zero warnings.
- Strict TypeScript: passed.
- Prettier formatting: applied and checked.
- Vitest: **32 passed** across 5 files.
- Next.js production build: passed, with `/`, `/documents` and not-found routes.
- Playwright / installed Microsoft Edge: **6 passed**, 3 workflows each at desktop 1440×1000 and mobile 390×844.
- Existing backend regression suite, forced to temporary SQLite databases: **45 passed, 1 PostgreSQL-only test skipped**. Backend Ruff format/lint and mypy also passed. The pre-existing Starlette TestClient deprecation warning remains; no PostgreSQL migration test ran for M4.
- `git diff --check`: passed. Local environment files and browser artifacts remain Git-ignored.

Unit tests cover library loading/failure/refresh, file validation, dropped/multiple PDFs, filename/status filters, successful/failed deletion, scope selection, request serialization, citation metadata validation, no evidence, provider failure/retry, cancellation ignoring late responses, history clearing, removal of related answers on deletion, keyboard submission, and rendering provider text as plain text.

Browser workflows cover chat/source viewing, exact page/excerpt display, history preservation across navigation, document upload/filter/confirmed deletion, provider failure/retry, and no horizontal overflow in the two tested viewports. Browser API responses are simulated and clearly separated from the production app; no demonstration documents or answers are preloaded for real users. Initial retry-test selection also matched Next.js's empty route announcer; the test was corrected to select the actual provider error, then all six passed.

Full-page screenshots of Chat and Documents at desktop and mobile sizes were captured and inspected. Sources stack below chat on smaller screens, navigation remains available, document names wrap/truncate within their controls, and status/error labels remain visible. Screenshots are local ignored artifacts under `frontend/test-results/`.

## Live integration smoke test

A separate headless Edge context exercised the running frontend on port 3000 and backend on 8000 with no mocked API. Before starting, the document API confirmed provider=fake and the existing document ID set was captured in memory. A uniquely named synthetic two-page PDF was generated, uploaded through the UI, and confirmed index-ready. The test selected only this generated document, asked about its annual-leave sentence, and verified its document ID, exact excerpt and page 1 citation.

Only the newly returned generated document ID was deleted afterward. All **1 pre-existing document ID** remained present. No migration or destructive database test ran against the real project database for M4. No OpenAI request was made.

## Behavior and limits

Chat history is browser memory only and survives internal navigation, not page reload. Each question searches a snapshot of the selected indexed documents independently. Cancellation stops waiting in the browser; the backend may finish work already received. Requests time out after 45 seconds. Deleted documents clear related answers from the current tab; other tabs are not synchronized. Source content and answer text are rendered as plain React text, not trusted HTML. There is no original-PDF preview/download.

Authentication, public deployment readiness, real OpenAI quality and other browser engines are outside the verified M4 scope. Fake mode is still keyword matching, not a language model. Historical M3 data loss and its repair remain documented in [verification-m3.md](verification-m3.md); this milestone does not claim that document was recovered.
