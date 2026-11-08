# AGENTS.md

Instructions for coding agents working in this repository.

## Context

- Product requirements: `_docs/specification.md`. It is the source of truth; ask before deviating from it.
- Working process: `_docs/process.md`.
- Roles: `_docs/roles/` — `developer.md` implements an issue, `reviewer.md` reviews the change, `qa.md` verifies acceptance criteria before closing. Follow the file for the role you are asked to play.
- Tasks are GitHub issues in `TOmelchenko/AcupuncturePoints`. Work on one issue at a time; read its goal and acceptance criteria before starting and again before closing.

## Stack

- `frontend/` — React + TypeScript + Vite, npm, shadcn/ui + Tailwind, TanStack Query, React Hook Form + Zod, Vitest + React Testing Library, Playwright.
- `backend/` — Python + FastAPI (uv, `pyproject.toml`), pytest, ruff, mypy (strict).
- `ingestion/` — Python knowledge ingestion pipeline (uv).
- `db/` — plain SQL setup scripts (schema, RLS, storage) and development seed data.
- `tests/integration/` — integration tests against a running backend and local Supabase.
- Supabase (Auth, PostgreSQL, `pgvector`, Storage) and Amazon Bedrock.
- Docker Compose for local development; common commands in the `Makefile`.

## Commands

Local Supabase must be running for database, integration and browser tests: `make supabase-start supabase-env db-setup db-seed`.

| Task | Command |
|---|---|
| Install everything | `make install` |
| Run the app | `make up` (or `uv run uvicorn app.main:app --reload` in `backend/`, `npm run dev` in `frontend/`) |
| Unit and component tests | `make test` |
| Integration tests | `make test-integration` |
| Browser tests | `make e2e` |
| Lint and type checks | `make lint` |
| Dependency and secret scans | `make security` |

See `README.md` for configuration, architecture and troubleshooting, and `_docs/ai-workflow.md` for the AI-assisted workflow.

## Rules

- Keep it simple: no frameworks, services, abstractions or features beyond what the current issue needs.
- Commit regularly, in small focused commits.
- Add or update tests with every behavior change, and run them before committing.
- Mock Amazon Bedrock in automated tests; live-provider tests must be opt-in.
- Never commit secrets. Use environment variables; `.env.example` holds placeholders only. AWS and Supabase service-role credentials stay on the backend.
- Treat symptom text as sensitive: do not log it, and use only invented examples in tests and fixtures.
- Never let the model invent point IDs, images, durations or pressure guidance; recommendation details come from curated database records.
- Do not show stack traces, provider errors, prompts or request IDs to users.
- Do not add MCP integration; it is out of scope for the MVP.
- Use `AI_PROVIDER=fake` (the demo AI) for offline runs and tests; never in production.
- Database changes go into the idempotent scripts in `db/` (no migration framework); keep RLS policies in `db/02_rls.sql` and add tests for them.
- The frontend design follows the pressure·point prototype: reuse the tokens in `frontend/src/styles.css` and the shadcn/ui components in `frontend/src/components/ui/`.
