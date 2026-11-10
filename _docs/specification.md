# Acupressure Recommendation App — MVP Specification

**Status:** MVP requirements consolidated; some implementation details deferred  
**Language:** English  
**Repository:** Public GitHub monorepo  
**Product type:** Responsive web application  

## 1. Purpose and Overview

Build a simple web app that helps a user explore acupressure points related to a physical or mental/emotional symptom. The user describes the symptom in free text. An AI-assisted workflow interprets the description, retrieves relevant material from a curated knowledge base, and returns a shortlist of three acupressure points. Each point should have a location picture when one is available; if there is no picture, show a text description of the location instead. Application instructions are text-based.

Users must have an account. The app stores symptom attempts, recommendation outcomes, and ratings so that past feedback can be used as a secondary signal when ranking later recommendations. Users can browse their own past recommendations on a history page. There is no admin interface in the MVP.

The app is an informational wellness tool. It must not claim to diagnose or replace professional medical care.

## 2. MVP Principles

- Keep the implementation as simple as possible while meeting the requirements below.
- Prefer a small number of well-understood services over additional infrastructure.
- Use curated knowledge as the source of truth for point recommendations; do not let the model invent point IDs or unsupported point details.
- Use symptom relevance as the primary ranking factor. Historical ratings can only be a secondary factor.
- Do not fabricate recommendations when matching is uncertain or the AI workflow fails.
- Make the application responsive on mobile and desktop.
- Defer optional features and tooling unless they are needed to meet a requirement.

## 3. In Scope

- English-language free-text symptom input for physical and mental/emotional symptoms.
- Required user accounts and authentication.
- Password reset by secure email link.
- Password change and account deletion.
- AI-assisted symptom interpretation and category mapping.
- Retrieval-augmented generation (RAG) over curated content stored in Supabase PostgreSQL with `pgvector`.
- Exactly three curated acupressure point recommendations when a suitable match is available.
- A location picture for each point when available; show a text location description when no picture is available.
- Text application instructions for each point; include duration and pressure guidance only when supported by curated source information.
- Clarification flow when a symptom is ambiguous or cannot initially be matched.
- Clear no-recommendation result if there is still no suitable match after clarification.
- A separate 1–5-star rating for each recommended point, submitted manually after the user has had time to try it.
- Optional dark mode if it can be implemented simply without delaying core MVP functionality.
- Storage of every attempt and outcome, including failed attempts.
- Lightweight validation of AI output before it is shown to a user.
- Local development with Docker Compose and common commands in a Makefile.
- Automated tests, GitHub Actions CI, dependency vulnerability checks, and secret detection.
- AI-assisted development workflow documentation.
- Cloud deployment only after the complete app passes local tests.
- Public cloud deployment with a working end-to-end application URL.
- Automatic deployment to a development environment after a successful merge to `main`.
- Manual production deployment/approval after the development deployment is verified.

## 4. Out of Scope

- Native mobile application.
- Admin interface or in-app knowledge-base editor.
- Analytics dashboard.
- Email address change workflow.
- Automatic reminders to submit a rating.
- Session-by-session deletion.
- Request limits for the MVP.
- MCP server/tool integration (TBD for a later phase; not part of the MVP).
- Advanced security/DevOps audit artifacts (TBD for a later phase; not part of the MVP).
- Formal database migration framework for the MVP.
- Automated symptom safety screening or medical triage beyond a general disclaimer.

## 5. User Accounts and Authentication

Use **Supabase Auth**. The recommendation workflow requires an authenticated user.

Users can:
- Register and sign in.
- Verify email according to the configured Supabase Auth behavior.
- Request a password reset using a secure email link.
- Change their password in account settings.
- Delete their account.

Email changes are not supported in the MVP. No separate authentication system should be built in FastAPI if Supabase Auth already provides the required behavior.

### Account deletion and access control

Deleting an account must remove the user's personal data, including original symptom text, attempts, recommendation results, and ratings tied to that user. Only properly anonymized analytics may remain, if any are retained. Authorization must prevent one user from reading another user's private records. Apply suitable Supabase Row Level Security (RLS) rules and handle any privileged backend credentials securely.

## 6. Main User Experience

1. The user registers or signs in.
2. The user lands on a simple home page with a short introduction, a general disclaimer, and a symptom input field.
3. The user submits an English description of a physical or mental/emotional symptom.
4. The backend records the attempt and starts the interpretation and retrieval workflow.
5. If the description is ambiguous or cannot be matched sufficiently, the app asks for clarification.
6. If no suitable match exists after clarification, the app displays a no-recommendation message.
7. If suitable knowledge is found, the app displays three recommended points.
8. Each point includes its name, a location picture if available (otherwise a text location description), and step-by-step text instructions for applying pressure. Duration and pressure guidance are shown only if the curated information includes them; the app must not invent missing values.
9. After the user has had time to try each point, the user can submit an independent 1–5-star rating for that point.
10. Attempts, outcomes, and per-point ratings are saved. The user can review them on a history page (see §12).

The feedback prompt is manual. Do not schedule reminder emails or notifications.

## 7. Recommendation Logic

### 7.1 Hybrid AI and curated knowledge

- Accept the user's original free-text symptom description.
- Use AI-assisted interpretation to map that description to predefined symptom categories and/or search terms.
- Retrieve relevant curated content and point records from Supabase PostgreSQL/`pgvector`.
- Retrieve prior helpfulness ratings relevant to the current symptom category when available. Use those ratings only as a secondary ranking signal.
- Send the symptom and relevant retrieved context to the AI provider — Amazon Bedrock (deployed: Claude on the Anthropic API with Voyage AI embeddings; see §13) — for a structured response.
- Validate the response on the backend before returning it to the frontend.

The exact model, embedding model, and prompt details are implementation choices to be finalized while building the app, with cost-consciousness and short prompts as goals.

### 7.2 Recommendation result

When there is a sufficiently relevant match, return exactly three recommendations. Each must reference an existing curated point record and include:

- `point_id`
- Point name
- A location picture or diagram when one is available in the curated point record or its referenced source; otherwise, a text description of the location
- Step-by-step text instructions for applying pressure
- Duration, if specified by the curated source
- Pressure guidance, if specified by the curated source

Prefer a curated location picture/diagram wherever one is available. If a point has no available picture, display its text location description instead. The image must come from a curated record or its source, not be invented by the model. Use or redistribute source images only when permitted by the applicable licence or rights; otherwise use a permitted alternative or the text fallback. Do not invent point IDs, images, durations, pressure guidance, or other details that are not supported by curated knowledge. Missing duration or pressure information should simply be omitted, not inferred by the model.

### 7.3 Clarification and unmatched symptoms

If the symptom is ambiguous or retrieval does not provide a sufficiently relevant match, ask the user a clarifying question rather than guessing. Persist the original input and clarification outcome. If the symptom remains unmatched, return a clear no-recommendation result. Do not fill three result slots with irrelevant points.

### 7.4 Failure and output validation

- If AI interpretation fails, do not recommend points.
- Validate that the model response follows the expected response schema.
- Validate that all three returned point IDs exist in the curated Supabase database.
- Reject malformed output, unknown IDs, or incomplete recommendations.
- On technical or validation failure, log a diagnostic event, show a generic error message, and provide a retry action.
- Do not show request IDs, stack traces, provider details, internal prompts, or secrets to the user.
- Avoid including raw symptom text in application logs unless strictly necessary.

## 8. Knowledge Base and RAG

### 8.1 Storage

Use Supabase PostgreSQL with the `pgvector` extension for vector embeddings. Do not add a separate vector database for the MVP.

The database should contain the records needed for:
- Curated acupressure points, including an optional image/diagram reference (for example, a Supabase Storage object), location text fallback, image attribution/source and usage permission where applicable, application instructions, and optional duration/pressure fields.
- Predefined symptom categories and mappings.
- Curated source/document metadata, including language and page/source references where available.
- Cleaned, chunked knowledge content and embeddings.
- Recommendation attempts, matching outcomes, and generated recommendation sets.
- User feedback ratings.

Final table design is an implementation detail. Keep it understandable and avoid unnecessary abstractions.

### 8.2 Ingestion pipeline

Create a Python ingestion pipeline that:
1. Reads curated source documents, including PDFs.
2. Extracts and cleans text; use OCR for scanned pages when needed.
3. Where a PDF includes useful point-location images or anatomical diagrams, extract or manually catalogue the relevant visuals and associate them with the point record and original page/source reference. Only use or redistribute images when permitted by the source licence or rights.
4. For non-English documents, translate the content selected for the English-language knowledge base into English and preserve the original source references, or use a multilingual retrieval approach if chosen during implementation.
5. Split source text into chunks.
6. Create embeddings.
7. Store chunks, source metadata, source language, page references where available, and embeddings in Supabase PostgreSQL/`pgvector`; store image files in Supabase Storage or retain an authorized image reference as appropriate.

The project owner will select the specific source materials after researching suitable sources. Whether ingestion accepts local files, URLs, or both remains undecided and can be chosen during implementation. Source attribution should be preserved in stored metadata where applicable.

### 8.3 Request workflow

1. Authenticate the user and accept the symptom text.
2. Store an attempt record with the original text.
3. Interpret the symptom and identify likely categories/search terms.
4. Retrieve relevant knowledge chunks and curated point records.
5. Retrieve applicable historical helpfulness signals where available.
6. Send the symptom and grounded context to the AI provider.
7. Parse and validate the structured response.
8. Check each point ID against the curated database.
9. Persist the outcome: clarification needed, no match, recommendation set, or failure.
10. Return the appropriate result to the frontend.

## 9. Feedback and Personalization

- Each of the three recommended points has its own independent 1–5-star rating.
- The user submits feedback manually after having time to try each point.
- Ratings are stored against the user, recommendation attempt, and specific point.
- Historical ratings for individual points can influence ranking only as a secondary factor and only when reasonably relevant to the current symptom/category; symptom relevance remains primary.
- Do not add a dashboard, statistical reporting UI, or automatic reminders.
- Save every attempt, including symptom descriptions, category/matching results, clarification outcomes, failures, and recommendation results where available.

## 10. Data Privacy and Retention

- Store the symptom text exactly as entered.
- Treat symptom descriptions as potentially sensitive personal data.
- Restrict private records to the owning user and authorized backend processes.
- Retain personal data until account deletion.
- Account deletion removes all personal data associated with the user.
- Retain only properly anonymized analytics after deletion, if needed.
- Do not implement independent session deletion for the MVP.
- Minimize personal data in logs and test fixtures. Do not use real personal symptom descriptions in test data.

## 11. Medical Disclaimer and Limitations

Show a general disclaimer on the home page and where recommendations are presented. It should explain that the app provides general wellness information only, does not diagnose or replace professional care, and that users should stop an activity that causes pain or discomfort and seek professional advice when concerned.

The explicit MVP decision is **general disclaimer only**, with no automated safety screening or triage. This is a known limitation, not evidence that all suggested actions are safe. The app must not represent itself as a diagnostic, emergency, or treatment service. Document the limitation in the README and do not make unsupported efficacy claims.

## 12. Pages and UI

### Authentication
- Registration.
- Login.
- Password-reset request and secure reset-link flow.
- Email verification flow based on Supabase Auth configuration.

### Authenticated home page
- Short introduction.
- General wellness disclaimer.
- Free-text symptom input.
- Submit action and loading state.
- Clarification state.
- No-match state.
- Three recommendation cards/list items, prioritizing a location picture/diagram when available and showing a text location fallback when no picture exists.
- Text application instructions; duration and pressure guidance only when present in the curated information.
- A separate 1–5-star rating control for each point.
- Generic error state with retry.

### Account settings
- Change password.
- Delete account with confirmation.
- No email change.

### History page
- Lists the user's own past attempts, newest first: date, symptom text and outcome (three points, clarification needed, or no match). Failed and in-progress attempts are not shown.
- Opening an attempt shows the three recommended points (same card as on the home page) with the user's saved rating, or the clarifying question and answer / no-match result.
- The user can add or change a 1–5-star rating from the history detail; a new rating replaces the earlier one.
- Only the signed-in user's own attempts are visible.

### UX and accessibility
- Responsive on mobile and desktop.
- Use a light theme by default. Dark mode is permitted as an optional enhancement if it can be added simply; it is not a release blocker.
- Clear labels, keyboard-accessible controls, and understandable error messages.
- Keep layouts simple; no unnecessary animations or visual features.

## 13. Technical Stack

### Repository
One public GitHub **monorepo** containing frontend, backend, knowledge ingestion, tests, infrastructure configuration, and documentation.

Suggested structure:

```text
/
├── frontend/                 # React + TypeScript + Vite
├── backend/                  # Python + FastAPI
├── ingestion/                # Python knowledge ingestion pipeline
├── tests/
│   └── integration/
├── docs/
│   └── ai-workflow.md
├── AGENTS.md
├── docker-compose.yml
├── Makefile
├── .env.example
├── .gitignore
└── README.md
```

Adapt the layout if implementation needs differ, but keep component responsibilities clear.

### Frontend
- React + TypeScript + Vite.
- npm for dependency management.
- shadcn/ui with Tailwind CSS for reusable UI components and styling.
- Native `fetch` for HTTP requests.
- TanStack Query for API request state, loading/error behavior, and retries.
- React Hook Form + Zod for form handling and validation.
- ESLint for basic code-quality checks; Prettier is not required for the MVP.
- Vitest + React Testing Library for component tests.
- Playwright for a small number of key browser end-to-end tests.
- React built-in state for simple UI state; no Redux or additional global state-management library.
- Use `.env` only for local configuration. Frontend-exposed variables must be public values, never secrets.

### Backend
- Python + FastAPI.
- `pyproject.toml` for Python dependencies and project configuration.
- Explicit request/response schemas and validation.
- OpenAPI specification and interactive API docs generated by FastAPI.
- Backend orchestration for Supabase access, retrieval, AI provider requests, output validation, persistence, and errors.
- Keep code direct and easy to learn; avoid unnecessary abstraction.

### Data and AI services
- Supabase Auth for identity and authentication flows.
- Supabase PostgreSQL for application and curated point data.
- Supabase `pgvector` for retrieval embeddings.
- Amazon Bedrock for hosted AI model access. *Deployment decision (2026-11-10): the AWS account has no Bedrock token quota, so the deployed environments use Claude on the Anthropic API with Voyage AI embeddings (`AI_PROVIDER=anthropic`); Bedrock remains a supported provider.*
- Python ingestion pipeline for curated source content.
- No separate vector database.
- No formal migration tool in the MVP; provide initial SQL setup scripts as needed.

## 14. API and OpenAPI Contract

FastAPI should generate the OpenAPI document automatically. The API contract should explicitly define request bodies, response bodies, status codes, and error shapes so that the frontend, backend, and tests agree on how they communicate. Recommendation responses must support an optional location-image reference and text fallback, and feedback requests must identify the specific point being rated.

Minimum application endpoints to consider:

- `POST /api/recommendations` — submit symptom text and receive a recommendation set, a clarification request, a no-match result, or an error.
- `POST /api/recommendations/{id}/points/{point_id}/feedback` (or an equivalent clearly documented endpoint) — submit a 1–5-star rating for an individual recommended point.

Use Supabase Auth for authentication where practical instead of recreating auth endpoints. Add only endpoints necessary for account settings or application workflow. The final URL scheme and schema names can be finalized during implementation.

## 15. Local Development

- Use Docker Compose to run the local application environment.
- Include a Makefile with common commands such as `make up`, `make down`, `make test`, and `make lint`.
- Include `.env.example` containing variable names and safe placeholders only.
- Add real `.env` files to `.gitignore`.
- Document setup, configuration, test commands, and troubleshooting in the README.
- Use environment variables for secrets; never commit API keys, tokens, or credentials.
- Use GitHub Actions Secrets for CI/CD credentials.
- Keep private AWS credentials on the backend and out of frontend bundles.

## 16. Testing Strategy

Keep testing broad enough to meet the project requirements but focused on the MVP.

- Backend unit tests for interpretation orchestration, retrieval behavior, ranking, output validation, and error paths.
- Frontend component tests for key form, loading, result, feedback, and error states.
- Integration tests for important frontend/backend/API/database boundaries where practical.
- A small number of Playwright tests for key browser flows, including authentication and submitting symptoms.
- Tests for clarification, no-match outcomes, invalid model output, unknown point IDs, retry behavior, user data isolation, and account deletion.
- Tests that a curated location image is displayed when available, text location fallback appears when no image exists, and missing duration/pressure details are omitted rather than invented.
- Mock the AI provider in most automated tests to make CI reliable and affordable. Keep live-provider testing controlled and separate from routine unit tests.

## 17. CI/CD and Security Checks

Use GitHub Actions. Run workflows on pull requests and pushes to the main branch. Include:

- Frontend install, lint, tests, and production build.
- Backend dependency setup and tests, plus a lightweight lint/type check as configured.
- Integration tests where practical.
- Docker build checks.
- Dependency vulnerability scanning for Python and frontend packages.
- Secret detection to catch accidentally committed credentials.

Use local environment variables and GitHub Actions Secrets for credentials. The user selected dependency vulnerability scanning and secret detection. More extensive PR audit reports, operational diagnosis artifacts, and formal security/DevOps policy documentation are deferred.

## 18. AI-Assisted Development Documentation

Include:
- `AGENTS.md` with repository-wide instructions for coding agents.
- `docs/ai-workflow.md` describing the AI-assisted development workflow, prompts/task delegation, relevant context files, manual code review, and verification steps.
- Reusable agent/workflow instructions or a specialist-agent definition only where they remain useful without adding unnecessary complexity.
- MCP integration is explicitly deferred and must not be added as an MVP requirement.
- The developer is responsible for reviewing generated code, tests, security-sensitive changes, and AI behavior.

## 19. Error Handling and Logging

- Log technical failures in a way that helps diagnose issues.
- Display generic, actionable messages to users with a retry action where appropriate.
- Do not expose exception details, stack traces, provider errors, internal prompts, or secrets to users.
- Do not display request IDs in the MVP.
- Avoid logging raw symptom descriptions and other unnecessary personal data.
- Record attempt outcomes so failures and no-match situations are persisted for future evaluation.

## 20. Deployment and CI/CD Plan

### 20.1 Deployment

Development order:

1. Implement and run the system locally using Docker Compose.
2. Run frontend, backend, and integration tests.
3. Fix failures and verify the complete local application.
4. Only after the complete application passes local tests, deploy it to the cloud.
5. Verify the deployed workflow end to end.
6. Document the working public deployment URL in the README.

The application must be deployed to a public cloud environment and reachable through a public URL. The deployed frontend must communicate with the deployed backend, and the backend must use the hosted Supabase database. The complete user flow must work in the deployed environment.

Supabase remains the database/auth provider. Do not deploy before local tests pass. *Deployment decision (2026-11-10): the frontend (static site) and FastAPI backend (Docker web service) run on Render's free tier in development and production environments defined in `render.yaml`, with Supabase Free; see `_docs/deployment.md`.*

### 20.2 CI/CD

GitHub Actions is the chosen CI/CD service; AWS CodePipeline is not part of the MVP.

CI runs automatically on pull requests and pushes to the `main` branch. It must include:

- Frontend install, lint, tests, and production build.
- Backend dependency setup and tests, plus a lightweight lint/type check as configured.
- Integration tests where practical.
- Docker build checks.
- Dependency vulnerability scanning for Python and frontend packages.
- Secret detection to catch accidentally committed credentials.

After a successful merge to `main`, CD automatically deploys the application to the development environment. Production deployment requires a manual deployment/approval action after the development deployment has been verified.

A failed deployment must not replace a working production version. The deployment process must provide a clear way to return to the last known working production version.

## 21. Acceptance Criteria

The MVP is ready for local end-to-end verification when all of the following are true:

1. A user can register, sign in, sign out, verify email according to Supabase configuration, and reset a password.
2. An authenticated user can submit an English free-text physical or mental/emotional symptom.
3. Every attempt is persisted with its input and outcome, including clarification and failure outcomes.
4. The backend uses retrieval over curated Supabase/`pgvector` knowledge and the AI provider (Amazon Bedrock or the Anthropic API) to generate grounded responses.
5. A sufficiently matched symptom returns exactly three recommendations with valid curated point IDs, a curated location picture/diagram when available (or text location fallback), and text application instructions. Duration and pressure guidance appear only when present in curated information.
6. Each recommended point can be rated independently from 1 to 5 stars.
7. An ambiguous or insufficiently matched symptom triggers a clarification flow.
8. A symptom that remains unmatched after clarification produces a no-recommendation result rather than fabricated content.
9. AI failure, malformed output, or unknown point IDs produce a generic error and retry option, not recommendations.
10. Historical per-point ratings, when available, act only as a secondary ranking signal.
11. The main experience is responsive on desktop and mobile.
12. Users can change their password and delete their account.
13. Account deletion removes that user's personal symptom text, attempts, recommendation results, and ratings.
14. Authorization prevents users from accessing other users' private data.
15. Docker Compose can run the local development environment, and Makefile commands cover common operations.
16. GitHub Actions runs appropriate lint, tests, build checks, dependency vulnerability checks, and secret detection.
17. FastAPI-generated OpenAPI documentation reflects the implemented contract.
18. README and AI workflow documentation explain setup, architecture, tests, AI workflow, and known limitations.
19. The application is deployed to a public cloud environment only after the complete application has passed local tests, and the deployed end-to-end workflow is verified.

## 22. Decisions Deferred to Implementation

These choices are intentionally not fixed by this specification:

- ~~Frontend hosting and FastAPI backend hosting.~~ Decided: Render (see §20.1).
- ~~Exact AWS deployment architecture and region.~~ Decided: no AWS deployment; Bedrock remains an optional provider.
- ~~Exact Amazon Bedrock model and embedding model.~~ Decided: Claude Haiku 4.5 + Voyage AI `voyage-3.5` (Anthropic API); on Bedrock, Titan Text Embeddings V2.
- Final curated source materials.
- Whether the ingestion pipeline accepts local files, URLs, or both.
- Whether non-English source content is fully translated before indexing or handled through multilingual retrieval.
- Final database schema and RLS policies.
- Exact API response shape details and status-code conventions.
- Exact lint/type-check tooling for Python.
- Whether additional agent extension files beyond `AGENTS.md` and `docs/ai-workflow.md` are worthwhile.

These details should be decided when needed during implementation, choosing the simplest approach that meets the requirements.

## 23. Known Risks and Limitations

- Quality and safety of the point recommendations depend on the selected source materials.
- RAG and ID/schema validation reduce unsupported output but cannot guarantee that every generated instruction is accurate or appropriate.
- The MVP deliberately has no automated medical safety screening; the general disclaimer does not eliminate risk.
- Symptom text may contain sensitive health information and must be access-controlled and retained only as specified.
- AI provider availability, latency, and costs (Anthropic API and Voyage AI, or Bedrock) depend on the selected models and account limits.
- Historical ratings will be sparse early in the application's life; recommendations must remain based primarily on symptom relevance and curated evidence.

## 24. Definition of Done

A requirement is done when its behavior is implemented, relevant tests pass, failures are handled without leaking sensitive details, and documentation is updated. Keep the MVP lean: do not add optional frameworks, services, abstractions, or features unless they are needed for an agreed requirement or clearly improve reliability, security, or maintainability.
