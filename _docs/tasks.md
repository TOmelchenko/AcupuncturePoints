# Backlog — Acupressure Recommendation App MVP

Tasks are derived from `_docs/specification.md`. Each task is sized for one session and written to be understandable on its own; section numbers refer to the specification.

## 1. Empty project skeleton with a passing test
Goal: Create the monorepo layout with a minimal backend and frontend that each have one passing test.
Description: Set up `backend/` (Python + FastAPI, `pyproject.toml`, pytest) with a `GET /api/health` endpoint and a test for it, and `frontend/` (React + TypeScript + Vite, npm, Vitest + React Testing Library) with one trivial component test. Add a root `Makefile` with `make test` running both suites, plus `.gitignore` (ignoring real `.env` files) and an `.env.example` with placeholders only.

## 2. Local Docker Compose environment
Goal: Run the backend and frontend locally with one command.
Description: Add Dockerfiles for `backend/` and `frontend/` and a root `docker-compose.yml` that starts both, reading configuration from `.env`. Extend the `Makefile` with `make up`, `make down` and `make logs`, and verify the frontend can reach the backend health endpoint.

## 3. Linting and type checks
Goal: Add lightweight code-quality checks for both apps behind `make lint`.
Description: Configure ESLint for the frontend and a simple Python linter/type checker (for example ruff and mypy) for the backend, and later for `ingestion/`. Wire them into a `make lint` target and fix any initial findings; Prettier is not required.

## 4. GitHub Actions CI pipeline
Goal: Run install, lint, tests, builds and Docker build checks on every PR and push to `main`.
Description: Create a GitHub Actions workflow with jobs for the frontend (install, lint, test, production build), the backend (dependency setup, lint/type check, tests) and building both Docker images. Credentials, when needed later, must come from GitHub Actions Secrets.

## 5. Dependency vulnerability scanning and secret detection
Goal: Catch vulnerable packages and committed credentials automatically in CI.
Description: Add CI steps that scan Python dependencies (for example pip-audit) and npm dependencies (for example npm audit) and fail on significant vulnerabilities. Add secret detection (for example gitleaks) over the repository, and document how to run the same checks locally.

## 6. Database schema SQL scripts
Goal: Provide initial SQL setup scripts for all MVP tables in Supabase PostgreSQL with `pgvector`.
Description: Write plain SQL scripts (no migration framework) that enable `pgvector` and create tables for curated points (optional image reference, location text, image attribution/permission, instructions, optional duration and pressure), symptom categories and mappings, source documents, knowledge chunks with embeddings, recommendation attempts and outcomes, recommendation sets and per-point ratings. Keep the design simple and document how to apply the scripts to a local or hosted Supabase project.

## 7. Row Level Security policies and isolation tests
Goal: Ensure users can only read and write their own private records.
Description: Add RLS policies so attempts, recommendation results and ratings are visible only to the owning user, while curated content stays readable by authenticated users and writable only by privileged backend processes. Write tests showing that one user cannot read or modify another user's records.

## 8. Development seed data
Goal: Load a small, fake but realistic curated dataset for local development and tests.
Description: Create a seed script with a handful of symptom categories and acupressure point records, covering points with and without an image and with and without duration/pressure guidance. Use invented, non-personal symptom examples only; this dataset is for development and is not the final curated knowledge base.

## 9. Ingestion: document reading and text extraction
Goal: Extract clean text and page references from curated source documents, including PDFs.
Description: In `ingestion/`, build a Python step that reads source documents (local files and/or URLs, whichever is simpler), extracts and cleans text per page, and falls back to OCR for scanned pages. Output should keep source metadata (title, language, page numbers) so later steps can preserve attribution.

## 10. Ingestion: translation, chunking, embeddings and storage
Goal: Turn extracted text into embedded chunks stored in Supabase `pgvector`.
Description: Take extracted page text with metadata, translate non-English content selected for the knowledge base into English (or document a multilingual choice), split it into chunks and create embeddings with an Amazon Bedrock embedding model. Store chunks, embeddings, source language and page references in the database, with the Bedrock client mockable for tests.

## 11. Ingestion: point images catalogue
Goal: Attach permitted location images to curated point records.
Description: Provide a simple way (script plus a manifest file) to catalogue point-location images or diagrams from sources, upload permitted files to Supabase Storage and link them to point records with attribution and usage permission. Points without a permitted image must keep a text location description as fallback.

## 12. Backend: Supabase authentication dependency
Goal: Require a valid Supabase Auth user on protected API endpoints.
Description: Add a FastAPI dependency that verifies the Supabase JWT sent by the frontend and exposes the current user ID to route handlers. Do not build a separate auth system; return a consistent 401 error shape for missing or invalid tokens and cover it with tests.

## 13. Backend: API contract and error schemas
Goal: Define explicit request/response models so the OpenAPI document describes the full contract.
Description: Create Pydantic models for submitting a symptom (with optional clarification answer), the four recommendation outcomes (recommendation set, clarification needed, no match, error), point details with optional image URL and text location fallback, and the per-point feedback request. Define a common error shape and status codes, and check the generated OpenAPI docs reflect them.

## 14. Backend: Amazon Bedrock client wrapper
Goal: Provide one small, mockable module for calling Bedrock models.
Description: Implement a thin wrapper for text generation and embeddings using AWS credentials from environment variables, with timeouts and clear exceptions on failure. Provide a fake implementation used by tests so CI never calls the live provider, and a separate, opt-in live smoke test.

## 15. Backend: symptom interpretation
Goal: Map free-text symptoms to predefined categories and search terms, or flag ambiguity.
Description: Implement a function that sends the symptom (and any clarification answer) with the list of predefined categories to Bedrock and parses a structured result: matched categories, search terms, and whether clarification is needed with a suggested question. Interpretation failure must raise an error rather than guess; unit-test with the mocked Bedrock client.

## 16. Backend: knowledge retrieval
Goal: Retrieve relevant knowledge chunks and candidate curated points for a symptom.
Description: Embed the interpreted search terms and query `pgvector` for the most similar chunks, then collect candidate point records linked to the matched categories or chunks. Return a relevance score and apply a threshold so weak matches are reported as insufficient rather than padded out.

## 17. Backend: ranking with historical ratings
Goal: Rank candidate points by symptom relevance, using past ratings only as a secondary signal.
Description: Implement a ranking function that orders candidates mainly by retrieval relevance and adjusts lightly using average ratings for the same point in the same symptom category. Unit tests must show that ratings cannot push a clearly less relevant point above a more relevant one, and that sparse or missing ratings have no effect.

## 18. Backend: model output validation
Goal: Reject any AI recommendation output that is malformed or not grounded in curated data.
Description: Validate the Bedrock structured response against the expected schema, require exactly three distinct point IDs that exist in the curated database, and reject incomplete output. Build the final point details (name, image or location text, duration, pressure) from database records so missing values are omitted, never invented.

## 19. Backend: recommendation endpoint orchestration
Goal: Implement `POST /api/recommendations` end to end with every outcome persisted.
Description: Wire authentication, attempt storage (original text), interpretation, retrieval, ranking, the grounded Bedrock call and validation into one endpoint returning a recommendation set, clarification request, no-match result or generic error. Persist every outcome including failures and clarifications, and test each path with the mocked Bedrock client.

## 20. Backend: per-point feedback endpoint
Goal: Let a user rate each recommended point from 1 to 5 stars.
Description: Implement `POST /api/recommendations/{id}/points/{point_id}/feedback` storing the rating against the user, attempt and point. Reject ratings outside 1–5, points not in that recommendation set, and attempts owned by another user, and define whether re-rating updates the existing rating.

## 21. Backend: account deletion endpoint
Goal: Delete a user's account and all of their personal data.
Description: Add an authenticated endpoint that removes the user's attempts, symptom text, recommendation results and ratings, then deletes the Supabase Auth user using the service-role key kept only on the backend. Test that no personal data remains and that other users' data is untouched.

## 22. Backend: error handling and privacy-safe logging
Goal: Log useful diagnostics without leaking details to users or symptom text to logs.
Description: Add global exception handlers that return the common generic error shape with no stack traces, provider details, prompts or request IDs. Configure logging so failures record useful context (outcome type, error class) but not raw symptom text or secrets, and add tests for both.

## 23. Frontend: app shell, styling and API client
Goal: Set up the frontend foundation used by all pages.
Description: Add Tailwind CSS and shadcn/ui, client-side routing with protected routes, a Supabase client configured from public environment variables, and a small `fetch`-based API client that attaches the user's token. Set up TanStack Query and a responsive layout with a light theme.

## 24. Frontend: authentication pages
Goal: Let users register, sign in, sign out, verify email and reset their password.
Description: Build registration, login and password-reset-request pages plus the reset-link landing page, using Supabase Auth with React Hook Form and Zod validation. Show clear, accessible error messages and cover the key form states with component tests.

## 25. Frontend: account settings page
Goal: Let users change their password and delete their account.
Description: Build an account settings page with a change-password form (via Supabase Auth) and a delete-account action that requires explicit confirmation and calls the backend deletion endpoint. There is no email change or history view; add component tests for validation and confirmation.

## 26. Frontend: home page and symptom submission flow
Goal: Let an authenticated user submit a symptom and see each possible outcome state.
Description: Build the home page with a short introduction, the general wellness disclaimer, a free-text symptom form and submit action. Handle loading, clarification (answer and resubmit), no-match and generic error with retry states using TanStack Query, with component tests for each state.

## 27. Frontend: recommendation cards
Goal: Display three recommended points clearly and safely.
Description: Render each point with its name, location image when available or text location fallback otherwise, step-by-step instructions, and duration/pressure only when present. Repeat the disclaimer next to results and add component tests for image vs. fallback and omitted optional fields.

## 28. Frontend: per-point star ratings
Goal: Let users rate each recommended point independently.
Description: Add an accessible, keyboard-operable 1–5 star control to each recommendation card that submits to the feedback endpoint. Show saved and error states per point and cover them with component tests.

## 29. Integration tests
Goal: Verify the backend, API and database work together correctly.
Description: Write integration tests in `tests/integration/` that run the backend against a local Supabase/Postgres with seed data and a mocked Bedrock client. Cover the recommendation outcomes, unknown point IDs, feedback storage, user data isolation and account deletion, and run them in CI where practical.

## 30. Playwright end-to-end tests
Goal: Check the key browser flows work in a running local app.
Description: Add a small Playwright suite covering registration/login, submitting a symptom and seeing three recommendations, and rating a point, using a mocked or stubbed AI provider. Add a `make e2e` target and document how to run it.

## 31. Project documentation
Goal: Document setup, architecture, testing, AI workflow and limitations.
Description: Write the README (setup, configuration, commands, architecture, tests, troubleshooting, medical disclaimer and known limitations), `AGENTS.md` with repository-wide instructions for coding agents, and `docs/ai-workflow.md` describing prompts, task delegation, context files, review and verification. Avoid unsupported efficacy claims.

## 32. Choose hosting and deploy to a development environment
Goal: Get the full app running at a public URL against hosted Supabase.
Description: After all local tests pass, compare simple, low-cost hosting options for the frontend and FastAPI backend, record the decision, and deploy a development environment using hosted Supabase and Bedrock. Verify the complete user flow end to end and add the URL to the README.

## 33. Continuous deployment to development
Goal: Deploy automatically to the development environment after a successful merge to `main`.
Description: Extend GitHub Actions so that, once CI passes on `main`, the frontend and backend are deployed to the development environment using GitHub Actions Secrets. Add a post-deploy smoke check against the health endpoint.

## 34. Manual production deployment with rollback
Goal: Promote a verified build to production with approval and a clear rollback path.
Description: Add a production environment and a manually triggered or approval-gated GitHub Actions job that deploys the already-verified build. Ensure a failed deployment does not replace the working version, and document how to return to the last known good release.

## 35. Optional dark mode
Goal: Offer a simple dark theme without affecting core functionality.
Description: If it can be done simply with Tailwind and shadcn/ui, add a dark theme toggle that respects the system preference, keeping light as the default. This is not a release blocker and should be skipped if it adds complexity.
