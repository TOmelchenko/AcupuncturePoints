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

## AI provider

The backend and ingestion call Amazon Bedrock: Claude (via the Anthropic SDK's `AnthropicBedrockMantle` client, model `BEDROCK_TEXT_MODEL_ID`, default `anthropic.claude-opus-5-5`) for structured generation and translation, and Titan Text Embeddings V2 for 1,024-dimension embeddings. AWS credentials come from the standard AWS environment variables or `~/.aws`, and stay on the backend.

Automated tests never call AWS: they use a programmable `FakeAI`. Set `AI_PROVIDER=fake` to run the app offline. To check the real integration once credentials and model access are set up, run the opt-in smoke test (it makes two small billable calls):

```sh
cd backend && RUN_LIVE_AI=1 uv run pytest tests/test_ai.py -k live
```

## Errors and logging

Every API error uses one shape: `{"error": {"code": "...", "message": "...", "retryable": true|false}}`. Messages are generic and safe to show; responses never include stack traces, provider errors, prompts or request ids. AI or technical failures during a recommendation return `502 recommendation_failed` with `retryable: true`, and the attempt is stored with outcome `failed`.

Logs (level from `LOG_LEVEL`, default `INFO`) record attempt ids, outcomes and error classes. Symptom text is never logged, and unexpected exceptions are logged with their class and stack frames but not their message, since messages can echo stored values.

## Integration tests

`tests/integration/` starts the real backend as a separate process against local Supabase (with the development seed data) and the offline demo AI, then exercises the API over HTTP with real Supabase Auth tokens: recommendation outcomes, an unknown point id from the model, feedback storage, user data isolation (also directly through Supabase's REST API, where RLS applies) and account deletion.

```sh
make supabase-start
make test-integration   # applies db/ scripts and seed data first
```

The demo AI (`AI_PROVIDER=fake`, never for production) understands two markers for testing failure paths: a symptom containing `[demo:fail]` makes the AI call fail, and `[demo:invalid-id]` makes it return a point id that does not exist.

## Browser tests

A small Playwright suite (`frontend/e2e/`) runs key flows in Chromium at desktop and mobile sizes: registering with a real confirmation email (read from local Mailpit), signing in and out, protected pages, submitting a symptom, answering a clarifying question, seeing three recommendations, rating a point, and the generic error with retry. Playwright starts the backend with the demo AI and the Vite dev server itself.

```sh
make supabase-start
cd frontend && npx playwright install chromium   # once
make e2e
```
