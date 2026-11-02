# Synthetic portfolio sample

`atlas-handbook.pdf` is an original three-page, English-language example made for this project. All names, budgets, dates, employment policies and service targets are fictional. The PDF and its source/question manifest `atlas-handbook.json` carry **CC0-1.0**; see [the scoped notice](LICENSE.txt) and the [official terms](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en). The sample license does not relicense the application.

| Question (copy exactly in fake mode) | Expected answer | Source |
| --- | --- | --- |
| What is the project budget for Project Atlas in euros? | 48,000 euros | Page 1 |
| How many days of annual leave do full-time employees receive per calendar year? | 30 days | Page 2 |
| What is the response time in hours for critical incidents? | 2 hours | Page 3 |
| What food should an axolotl eat? | No supporting evidence; no citations | None |

Upload the PDF through Documents, wait for the search index to be ready, select only this PDF in Chat, and use the questions above. The fake provider extracts matching sentences and does not paraphrase like an LLM. These questions are tested against the actual chunk text and default retrieval threshold; broad summaries are not a fake-provider capability.

For a local account, import explicitly from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m app.seed_demo --email YOUR_EMAIL
.\.venv\Scripts\python.exe -m app.seed_demo --email YOUR_EMAIL --confirm
```

The first command previews. The second imports through normal PDF extraction/indexing and user quotas. An already imported matching sample returns its existing ID; a conflicting filename fails without overwriting anything. The account must already exist. Only development plus `AI_PROVIDER=fake` is accepted; no provider credentials or network AI calls are used. In explicit local-demo mode omit `--email`. No startup seed, automatic account creation or claim of old demo documents occurs. Delete the sample using the ordinary Documents controls when finished.

On Linux/macOS replace the interpreter path with `.venv/bin/python`. Run from a repository checkout with the editable backend installation; the CLI resolves the sibling `examples/` folder independently of your shell's current directory.

The PDF is already bundled; viewing/uploading/seeding it does not require a PDF authoring library. To rebuild it, install the optional authoring tools from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[portfolio]'
.\.venv\Scripts\python.exe scripts/build_demo_pdf.py
```

The builder uses standard PDF fonts and invariant PDF metadata for deterministic output. It creates text-based pages suitable for pypdf extraction, with visible fiction/license/page notices. No font binary or private data is bundled.
