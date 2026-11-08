# Acupressure Recommendation App

A responsive web app that suggests acupressure points for a described symptom, using curated knowledge and AI-assisted retrieval. See `_docs/specification.md` for requirements.

> General wellness information only — not a diagnosis or a substitute for professional medical care.

## Development commands

| Command | What it does |
|---|---|
| `make install` | Install backend (uv) and frontend (npm) dependencies |
| `make up` / `make down` / `make logs` | Start, stop and follow the Docker Compose environment (frontend on http://localhost:5173, backend on http://localhost:8000) |
| `make test` | Run backend and frontend tests |
| `make lint` | Run ruff, mypy and ESLint |
| `make supabase-start` / `make db-setup` | Start local Supabase and apply the SQL scripts in `db/` |
| `make security` | Scan dependencies (pip-audit, npm audit) and detect committed secrets (gitleaks, via Docker) |

The same checks run in GitHub Actions on every pull request and push to `main`.

## Database

The app uses Supabase (PostgreSQL + `pgvector`, Auth, Storage). Schema and policies are plain SQL scripts in `db/`, applied in file-name order — there is no migration framework.

**Local:** `make supabase-start` runs the Supabase stack in Docker via the Supabase CLI (Studio on http://127.0.0.1:54323, test emails in Mailpit on http://127.0.0.1:54324). Then run `make db-setup` to apply the scripts. `make db-reset` recreates the local database and reapplies them. `make db-seed` loads invented development data (`db/seed/`: six symptom categories, seven points, two placeholder diagrams) — local only, never production.

**Hosted:** set `DATABASE_URL` in `.env` to the project's connection string (Supabase dashboard → Connect) and run `make db-setup`. Scripts are idempotent and safe to re-run.

Database tests in `backend/tests/db/` run against `DATABASE_URL` and are skipped if it is unreachable (CI sets `REQUIRE_DB=1` so they fail instead).

## Knowledge ingestion

`ingestion/` is a Python pipeline that turns curated source documents into the knowledge base.

**Step 1 — extract text.** List local source files (PDF, `.txt`, `.md`) in a JSON manifest with their metadata, then run:

```sh
cd ingestion
uv run python -m ingestion.extract sources/manifest.json -o out/pages.jsonl
```

```json
{"sources": [{"file": "guide.pdf", "title": "Guide title", "language": "en",
              "author": "Author", "url": "https://...", "license": "CC BY 4.0"}]}
```

Each output line holds one page's cleaned text, its page number and the source metadata. Pages without extractable text are OCR'd with Tesseract (`brew install tesseract` / `apt-get install tesseract-ocr`, plus language packs for non-English sources). `ingestion/sources/` and `ingestion/out/` are git-ignored.

**Step 2 — translate, chunk, embed and store.**

```sh
uv run python -m ingestion.load out/pages.jsonl
```

Non-English pages are translated into English with Claude on Amazon Bedrock (the source keeps its original language and page references). Text is split into ~1,000-character overlapping chunks, embedded with Amazon Titan Text Embeddings V2 (1,024 dimensions) and stored in `knowledge_chunks`. A chunk that mentions exactly one known point code (e.g. `LI4`) is linked to that point. Re-running a source replaces its chunks. Configuration comes from `DATABASE_URL`, `AWS_REGION`, `BEDROCK_TEXT_MODEL_ID` and `BEDROCK_EMBEDDING_MODEL_ID`; set `AI_PROVIDER=fake` to run offline with deterministic fake embeddings.

**Step 3 — point images.** Location images are catalogued by hand in a JSON manifest, each with an explicit usage decision:

```json
{"images": [{"point_id": "LI4", "file": "images/li4.png", "permitted": true,
             "attribution": "Figure 3, A. Author", "license": "CC BY 4.0",
             "source_title": "Guide title", "page": 12}]}
```

```sh
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... uv run python -m ingestion.images sources/images.json
```

All entries are validated first (known point, attribution and licence present, PNG/JPEG/WebP/SVG file exists). Permitted images are uploaded to the public `point-images` bucket as `points/<point_id>.<ext>` and linked with their attribution, source and page. Only use images whose licence allows it; entries with `"permitted": false` clear any existing image so the app shows the text location instead.
