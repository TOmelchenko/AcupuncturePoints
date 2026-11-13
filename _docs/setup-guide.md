# Setup Guide: GitHub, Claude Code, Supabase and Render

Every account, tool and dashboard setting this project needs, in the order to do them. Following it from top to bottom takes a fresh machine and empty accounts to a running local app and the two deployed environments.

Related documents: [`deployment.md`](deployment.md) (release, rollback and free-tier trade-offs), [`ai-workflow.md`](ai-workflow.md) (how the coding agent is used), the [README](../README.md) (configuration reference and troubleshooting).

**Rule for secrets:** never paste a key into chat, a commit or an issue. Secret values go only into the local `.env` (git-ignored), the Supabase, Render and GitHub dashboards, or `gh secret set`, which prompts for the value.

## Overview

| # | Step | Where | Result |
|---|---|---|---|
| 1 | Install local tools | your machine | Docker, Node.js, uv, psql, gh |
| 2 | GitHub repository and `gh` CLI | github.com, terminal | repository cloned, `gh` signed in |
| 3 | Claude Code | terminal | agent runs in the repository with the project rules |
| 4 | Local Supabase and `.env` | terminal | app runs locally with the offline demo AI |
| 5 | AI provider keys | Anthropic and Voyage consoles | real AI works locally |
| 6 | Hosted Supabase project | supabase.com | database, Auth and Storage in the cloud |
| 7 | Render services | render.com | four services created from `render.yaml` |
| 8 | Supabase Auth URLs | supabase.com | confirmation and reset links point at the deployed frontend |
| 9 | GitHub Actions settings | github.com or `gh` | environments, secrets and variables for the deploy workflows |
| 10 | First deployment | GitHub Actions | development and production are live |

Steps 6–8 depend on each other: Render needs the Supabase keys (step 6), and Supabase Auth needs the Render frontend URLs (step 7). That is why Auth is finished in step 8.

## 1. Install local tools

| Tool | Needed for |
|---|---|
| Docker Desktop | local Supabase, `make up`, secret scanning |
| Node.js 22 | frontend, Supabase CLI (run through `npx`), Claude Code |
| [uv](https://docs.astral.sh/uv/) | backend, ingestion and integration-test Python environments |
| `psql` (PostgreSQL client) | `make db-setup`, `make db-seed` |
| [GitHub CLI `gh`](https://cli.github.com/) | issues, pull requests, secrets, variables |
| Tesseract | only for ingestion of scanned PDFs |

The Supabase CLI is not installed separately: the `Makefile` runs a pinned version with `npx -y supabase@3.0.0`.

## 2. GitHub repository and `gh` CLI

1. **Repository.** The project lives in `TOmelchenko/AcupuncturePoints` (public, default branch `main`). Tasks are GitHub issues in the same repository.
2. **Sign in with the CLI** (opens the browser once):

   ```sh
   gh auth login
   ```

   Choose *GitHub.com*, *HTTPS*, and *Login with a web browser*.
3. **Clone and install:**

   ```sh
   gh repo clone TOmelchenko/AcupuncturePoints
   cd AcupuncturePoints
   make install
   ```

4. **Check access:** `gh issue list` should show the project issues.

Changes go to `main` through pull requests; CI (`.github/workflows/ci.yml`) runs on every pull request and every push to `main`. The Actions settings needed for deployment come later, in step 9.

## 3. Claude Code

1. **Install and sign in:**

   ```sh
   npm install -g @anthropic-ai/claude-code
   cd AcupuncturePoints
   claude
   ```

   The first start asks you to sign in with a Claude account. Always start `claude` from the repository root so it finds the project files.
2. **Project instructions (already in the repository).** Nothing to configure; Claude Code loads these automatically:

   | File | Purpose |
   |---|---|
   | `CLAUDE.md` | entry point; imports `AGENTS.md` and adds the `gh`, role and commit/push rules |
   | `AGENTS.md` | stack, commands and the non-negotiable project rules |
   | `_docs/process.md`, `_docs/roles/*.md` | the per-issue loop and the Developer, Reviewer and QA roles |

3. **Personal permissions (optional).** `.claude/settings.local.json` holds your own allow-list so Claude Code does not ask every time. It is git-ignored (see `.gitignore`), so each developer creates their own. The one used in this project:

   ```json
   {
     "permissions": {
       "allow": ["Bash(gh pr merge *)"]
     }
   }
   ```

4. **GitHub access.** Claude Code uses the `gh` session from step 2; there is no separate token to configure.
5. **What stays with you.** The agent stops and asks for anything only the owner can do: creating cloud accounts, entering credentials, and approving billable or public actions (live AI calls, deployments).

Typical prompts are `start issue #12` or "play the reviewer role for the current diff"; see `ai-workflow.md`.

## 4. Local Supabase and `.env`

1. **Start local Supabase** (Postgres with `pgvector`, Auth, Storage, Mailpit). The first run downloads Docker images:

   ```sh
   make supabase-start
   ```

2. **Create `.env`** from `.env.example` and fill in the local URL and keys:

   ```sh
   make supabase-env
   ```

3. **Apply the schema and load the invented development data:**

   ```sh
   make db-setup
   make db-seed
   ```

4. **Choose the offline AI** for now: set `AI_PROVIDER=fake` in `.env`.
5. **Run the app:**

   ```sh
   make up
   ```

   | Address | What |
   |---|---|
   | http://localhost:5173 | frontend |
   | http://localhost:8000/docs | backend API |
   | http://127.0.0.1:54323 | Supabase Studio |
   | http://127.0.0.1:54324 | Mailpit: local confirmation and reset emails |

The local Auth settings are in `supabase/config.toml` and need no dashboard: site URL `http://localhost:5173`, redirect URLs `http://localhost:5173/**`, email confirmation on, minimum password length 8. The hosted project must match them (step 6).

## 5. AI provider keys

The deployed app uses Claude on the Anthropic API and Voyage AI embeddings (`AI_PROVIDER=anthropic`), because the AWS account has no Bedrock quota.

1. **Anthropic.** At console.anthropic.com, add a few dollars of credit under *Billing*, then create a key under *API Keys*.
2. **Voyage AI.** At dash.voyageai.com, create an API key and add a payment method. Without one the limit is 3 requests per minute, too slow for ingestion. The first 200M tokens are free.
3. **Local `.env`:**

   ```sh
   AI_PROVIDER=anthropic
   ANTHROPIC_API_KEY=<your key>
   VOYAGE_API_KEY=<your key>
   ```

4. **Check** with the opt-in smoke test (two small billable calls):

   ```sh
   cd backend && set -a && . ../.env && set +a && RUN_LIVE_AI=1 uv run pytest tests/test_ai.py -k live_anthropic
   ```

## 6. Hosted Supabase project

One free project, `acupressure-dev`, currently serves both development and production (see *Shared Supabase project* in `deployment.md`).

1. **Create the project** at supabase.com: Free plan, name `acupressure-dev`, region Frankfurt. Save the database password.
2. **Collect four values:**

   | Value | Where in the dashboard | Used as |
   |---|---|---|
   | Project URL | *Project Settings → API* | `SUPABASE_URL`, `VITE_SUPABASE_URL` |
   | anon key | *Project Settings → API* | `VITE_SUPABASE_ANON_KEY` (public) |
   | service_role key | *Project Settings → API* | `SUPABASE_SERVICE_ROLE_KEY` (backend only) |
   | Session pooler connection string | *Connect* | `DATABASE_URL`, `DEV_DATABASE_URL`, `PROD_DATABASE_URL` |

   Use the **Session pooler** string, not the direct connection: it supports IPv4, which Render and GitHub runners need.
3. **Email sign-in settings.** Under *Authentication → Sign In / Providers → Email*: keep **Confirm email** on and set **Minimum password length** to 8.
4. **Apply the schema** from your machine (schema, RLS policies, storage bucket):

   ```sh
   make db-setup DATABASE_URL="<session pooler connection string>"
   ```

5. **Load content.** Either the invented demo data:

   ```sh
   psql "<connection string>" -v ON_ERROR_STOP=1 -f db/seed/seed.sql
   cd ingestion && SUPABASE_URL=<project URL> SUPABASE_SERVICE_ROLE_KEY=<service_role key> \
     DATABASE_URL="<connection string>" uv run python -m ingestion.images ../db/seed/images.json
   ```

   or the real knowledge base with the ingestion pipeline (README → *Knowledge ingestion*). Without content every symptom returns "no match".

**Email limit.** The project uses Supabase's built-in email service: about 2 emails per hour across all users. Above that the app shows "Too many emails were requested. Please try again in an hour." To lift it, configure an SMTP provider under *Authentication → Emails → SMTP Settings*, then raise the limit under *Authentication → Rate Limits*.

**Pausing.** A free project pauses after 7 days without activity; restore it in the dashboard.

## 7. Render services

1. **Sign up** at render.com with your GitHub account and give Render access to the repository.
2. **Create the services.** *New → Blueprint*, pick `TOmelchenko/AcupuncturePoints`, and confirm the four services defined in `render.yaml`:

   | Service | Type | URL |
   |---|---|---|
   | `acupressure-api-dev` | Docker web service (free, Frankfurt) | https://acupressure-api-dev.onrender.com |
   | `acupressure-web-dev` | static site | https://acupressure-web-dev.onrender.com |
   | `acupressure-api-prod` | Docker web service (free, Frankfurt) | https://acupressure-api-prod.onrender.com |
   | `acupressure-web-prod` | static site | https://acupressure-web-prod.onrender.com |

3. **Enter the secrets** Render asks for (the `sync: false` values in `render.yaml`):

   | Service | Variable | Value |
   |---|---|---|
   | both API services | `SUPABASE_URL` | Project URL |
   | | `SUPABASE_SERVICE_ROLE_KEY` | service_role key |
   | | `DATABASE_URL` | Session pooler connection string |
   | | `ANTHROPIC_API_KEY` | Anthropic key |
   | | `VOYAGE_API_KEY` | Voyage key |
   | both web services | `VITE_SUPABASE_URL` | Project URL |
   | | `VITE_SUPABASE_ANON_KEY` | anon key |

   The remaining variables (`AI_PROVIDER`, model IDs, `CORS_ALLOWED_ORIGINS`, `VITE_API_BASE_URL`) are set in `render.yaml` and need no input.
4. **Collect the service IDs.** Each service's *Settings* page shows its ID (`srv-…`). Note all four.
5. **Create a Render API key** under *Account Settings → API Keys*. GitHub Actions uses it to trigger deploys.

Things to know:

- **Auto-deploy is off** (`autoDeployTrigger: "off"`). Render deploys only when the GitHub workflows call its API through `scripts/render-deploy.sh`.
- **Public URLs are written out in `render.yaml`.** `fromService … property: host` gives Render's internal hostname, which browsers cannot reach, so `VITE_API_BASE_URL` and `CORS_ALLOWED_ORIGINS` hold the public `onrender.com` URLs.
- **Changing an environment variable in `render.yaml`** takes effect only after a Blueprint sync in the Render dashboard, not on a normal deploy.
- **Free web services sleep** after 15 minutes idle; the first request then takes about a minute.

## 8. Supabase Auth URLs

Back in the Supabase dashboard, under *Authentication → URL Configuration*:

1. **Site URL:** the frontend URL, e.g. `https://acupressure-web-dev.onrender.com`.
2. **Redirect URLs:** add one entry per deployed frontend:
   - `https://acupressure-web-dev.onrender.com/**`
   - `https://acupressure-web-prod.onrender.com/**`

Without these, the links in confirmation and password-reset emails are rejected or lead to the wrong site.

## 9. GitHub Actions settings

The two deploy workflows read their settings from GitHub environments.

1. **Create the environments** under *Settings → Environments*: `development` and `production`. On `production`, enable **Required reviewers** and add yourself; this is the manual approval before a production deploy.
2. **Add the environment secrets.** `gh` prompts for each value:

   ```sh
   for s in RENDER_API_KEY RENDER_DEV_API_SERVICE_ID RENDER_DEV_WEB_SERVICE_ID DEV_DATABASE_URL; do
     gh secret set "$s" --env development
   done
   for s in RENDER_API_KEY RENDER_PROD_API_SERVICE_ID RENDER_PROD_WEB_SERVICE_ID PROD_DATABASE_URL; do
     gh secret set "$s" --env production
   done
   ```

   | Secret | Environment | Value |
   |---|---|---|
   | `RENDER_API_KEY` | both | Render API key (step 7.5) |
   | `RENDER_DEV_API_SERVICE_ID`, `RENDER_DEV_WEB_SERVICE_ID` | development | `srv-…` IDs of the dev services |
   | `RENDER_PROD_API_SERVICE_ID`, `RENDER_PROD_WEB_SERVICE_ID` | production | `srv-…` IDs of the prod services |
   | `DEV_DATABASE_URL` | development | Session pooler connection string |
   | `PROD_DATABASE_URL` | production | the same string while the Supabase project is shared |

3. **Add the repository variables** (public URLs, used for the smoke tests and the environment links):

   ```sh
   gh variable set DEV_API_URL --body https://acupressure-api-dev.onrender.com
   gh variable set DEV_WEB_URL --body https://acupressure-web-dev.onrender.com
   gh variable set PROD_API_URL --body https://acupressure-api-prod.onrender.com
   gh variable set PROD_WEB_URL --body https://acupressure-web-prod.onrender.com
   ```

4. **Check:**

   ```sh
   gh secret list --env development
   gh secret list --env production
   gh variable list
   ```

CI itself needs no secrets: it runs against a local Supabase stack with the AI provider mocked. Until `RENDER_API_KEY` is set, the development deploy workflow skips its steps with a notice instead of failing.

The environments named `main - acupressure-…` in the list are created by Render's GitHub integration to show deploy status; leave them as they are.

## 10. First deployment

1. **Deploy to development.** Push to `main` (or re-run the latest *Deploy to development* run). After CI passes, the workflow applies the `db/` scripts, deploys the backend and then the frontend, and smoke-tests both.
2. **Verify development** at https://acupressure-web-dev.onrender.com: register, confirm the email, submit a symptom, rate a point, delete the test account.
3. **Deploy to production.** *Actions → Deploy to production → Run workflow*, or:

   ```sh
   gh workflow run deploy-prod.yml
   ```

   Leave the commit input empty to take the latest commit deployed to development, then approve the run on the `production` environment.
4. **Verify production** the same way at https://acupressure-web-prod.onrender.com.

From here on, releasing and rolling back follow `deployment.md`.

## Where each value lives

| Value | Local `.env` | Render | GitHub | Supabase dashboard |
|---|---|---|---|---|
| Supabase Project URL | `SUPABASE_URL`, `VITE_SUPABASE_URL` | same names | – | source |
| Supabase anon key | `VITE_SUPABASE_ANON_KEY` | web services | – | source |
| Supabase service_role key | `SUPABASE_SERVICE_ROLE_KEY` | API services | – | source |
| Database connection string | `DATABASE_URL` | API services | `DEV_DATABASE_URL`, `PROD_DATABASE_URL` (environment secrets) | source |
| Anthropic API key | `ANTHROPIC_API_KEY` | API services | – | – |
| Voyage API key | `VOYAGE_API_KEY` | API services | – | – |
| Render API key and service IDs | – | source | environment secrets | – |
| Public app URLs | – | `render.yaml` | repository variables | Auth *Site URL* and *Redirect URLs* |

Locally, `make supabase-env` fills the Supabase rows with the local stack's values; the hosted values are only needed in `.env` when you run `make db-setup` or ingestion against the hosted project.
