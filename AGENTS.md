# AGENTS.md

Instructions for coding agents working in this repository.

## Context

- Product requirements: `_docs/specification.md`. It is the source of truth; ask before deviating from it.
- Working process: `_docs/process.md`.
- Tasks are GitHub issues in `TOmelchenko/AcupuncturePoints`. Work on one issue at a time; read its goal and acceptance criteria before starting and again before closing.

## Stack

- `frontend/` — React + TypeScript + Vite, npm, shadcn/ui + Tailwind, TanStack Query, React Hook Form + Zod, Vitest + React Testing Library, Playwright.
- `backend/` — Python + FastAPI, `pyproject.toml`, pytest.
- `ingestion/` — Python knowledge ingestion pipeline.
- Supabase (Auth, PostgreSQL, `pgvector`, Storage) and Amazon Bedrock.
- Docker Compose for local development; common commands in the `Makefile`.

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
