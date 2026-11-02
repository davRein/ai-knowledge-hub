# Milestone 6 verification - 2026-11-02

## Delivered scope

M6 packages the working local application for portfolio review. It does not add a public deployment or change account/provider settings in the personal development stack. The repository was clean at the beginning (`6d39884`); existing source and the earlier German test PDF under `output/pdf/` were preserved. No commit was made.

- `examples/atlas-handbook.pdf`: original, synthetic three-page CC0 handbook, with `atlas-handbook.json` as source and the executable question/answer/page manifest. `examples/LICENSE.txt` scopes CC0 to those sample-content files only; application licensing is unchanged. `examples/README.md` explains upload, seed and rebuild workflows.
- `backend/app/seed_demo.py`: read-only preview and explicit import using the ordinary document service, selected owner/workspace, quotas and fake embeddings. Sequential repeat imports return the existing ID; incompatible filenames are rejected without overwrite. Production/external-provider operation is rejected. It never registers users or claims old documents.
- `backend/scripts/build_demo_pdf.py` plus optional `portfolio` dependencies: deterministic PDF rebuild with standard PDF fonts. Viewing/uploading/seeding the bundled PDF needs no authoring dependencies.
- `docs/assets/architecture.svg`, six annotated synthetic-data PNGs, `docs/demo.md` two-minute walkthrough and recording instructions, plus updated README/architecture/roadmap.
- A separate Playwright portfolio configuration and real-stack capture harness. The existing disposable PostgreSQL helper gains `--portfolio`; regular test behavior is preserved. The UI milestone label is updated to M6.

## Automated results

| Check | Result |
| --- | --- |
| Backend Ruff format and lint | Passed |
| Backend mypy `app tests` | Passed, 53 source files |
| pytest / temporary SQLite | 62 passed, 1 pgvector-specific skip |
| pytest / disposable PostgreSQL 18.6 + pgvector | 63 passed |
| Frontend Prettier, ESLint, TypeScript | Passed |
| Vitest | 34 passed / 6 files |
| Next.js production build | Passed |
| Regular Edge UI tests using simulated APIs | 12 passed, desktop + mobile |
| Portfolio capture using actual API/PostgreSQL | 2 passed, desktop + mobile |
| Compose config and Git whitespace check | Passed |

The five new backend cases exercise the actual bundled PDF and all expected answers/page citations, the unsupported-question case, preview/repeat import, selected account, unchanged foreign/legacy records, production/OpenAI rejection, and filename conflict protection. Existing M5 authentication/isolation tests remain passing.

The PDF has three readable, unencrypted text pages and three page-preserving chunks. License notices/page numbering are extracted successfully. All pages were rendered through PDFium and visually inspected for clipping, spacing, glyphs and page transitions. The invariant builder was checked for reproducible bytes. The SVG diagram was browser-rendered and inspected; no generated bitmap artwork or external image assets are used.

The known Starlette TestClient/httpx deprecation and Playwright color-environment warnings remain. No live OpenAI request, independent security audit, performance benchmark or recorded video is claimed.

## Live portfolio capture boundary

The Windows helper creates a fresh native PostgreSQL cluster on 127.0.0.1:55432, checks `SHOW data_directory` against its own temporary directory, enables pgvector there and runs migrations exclusively against that cluster. It then starts an authenticated development FastAPI process on port 8810 with a random temporary key, fake provider, empty external-provider key, and exact frontend origin for port 3200. No credentials, account selection or provider/database URL are copied from the personal project's `.env` into the demo's effective settings.

The production Next.js server on 3200 is exercised by a fresh Edge context for each viewport. Browser API traffic is forwarded to the disposable API as a transport redirect; responses are not mocked or supplied by the capture script. Each flow registers a synthetic account, uploads the actual sample PDF, checks ready embeddings and three chunks, asks all four manifest questions, and validates returned document IDs/pages/evidence. A second synthetic account sees an empty library and gets 404 for the first account's document. Desktop viewport is 1440x1100; mobile is 390x844. Horizontal overflow is checked.

Documentation outlines/numbers and a clearly labelled synthetic/fake-provider strip are added before taking PNGs. They annotate real UI regions without rewriting questions, answers, citations or metadata. The no-evidence scene starts with the ordinary Clear chat action so the relevant result is visible. Screenshots and the architecture diagram were visually reviewed. No personal account/email, document content, credential, prompt log or session token is included.

Initial capture attempts exposed a TypeScript variable shadow and a missing build after that type-check failure. A mobile upload attempt raced the route/loading state; the capture now waits for the Document library heading and enabled file input. The fixes were followed by successful build/capture runs. A visual check also caught a no-evidence desktop crop showing earlier history; clearing chat before that scene resolves it. Temporary processes/clusters from all attempts were stopped and removed; the personal database was never targeted by tests, capture migrations or seed commands.

## Operational status

README links to the synthetic sample, demo script, annotated captures and architecture. The underlying legal terms are linked to Creative Commons' official CC0 pages; no downloaded third-party PDF or private material is redistributed. Only the sample content is dedicated under CC0. Source text/manifest is bundled for traceability and regeneration.

All six roadmap milestones have local implementations and verification records. There is no defined M7. Public launch remains subject to [the M5 operator/security/privacy gates](security.md). The Linux server, personal `.env` files and persistent account/document data were unchanged. No deployment, publication, remote messaging or Git commit occurred.
