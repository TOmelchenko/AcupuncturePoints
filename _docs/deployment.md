# Deployment

The MVP runs on free tiers. The Claude API is the only usage-based cost.

| Piece | Development | Production |
|---|---|---|
| Database, Auth, Storage | Supabase Free project `acupressure-dev` | the same project (shared; see below) |
| Backend (FastAPI, Docker) | Render free web service `acupressure-api-dev` | Render free web service `acupressure-api-prod` |
| Frontend (static) | Render static site `acupressure-web-dev` | Render static site `acupressure-web-prod` |
| AI | Claude Haiku 4.5 on the Anthropic API + Voyage AI `voyage-3.5` embeddings | same |

Everything is defined in `render.yaml` (Render Blueprint) and two workflows:

- **`.github/workflows/deploy-dev.yml`** runs automatically after CI passes on `main`. It applies the `db/` scripts to the dev database, deploys that exact commit (backend, then frontend), and smoke-tests it.
- **`.github/workflows/deploy-prod.yml`** runs manually (Actions → *Deploy to production* → Run workflow). It only accepts a commit that passed CI and was deployed to development, waits for approval on the `production` environment, then deploys and smoke-tests it.

**Render gotcha:** `fromService … property: host` resolves to Render's *internal* hostname (e.g. `acupressure-api-dev`), which browsers cannot reach. That is why `render.yaml` sets the public URLs explicitly in `VITE_API_BASE_URL` and `CORS_ALLOWED_ORIGINS`. Environment changes in `render.yaml` apply only after a Blueprint sync, not on a commit deploy.

**Shared Supabase project:** production currently uses the development Supabase project, so both environments share users, ratings, history and the knowledge base. `PROD_DATABASE_URL` and the prod services' Supabase settings hold the dev project's values, and the prod frontend URL is in its Auth *Redirect URLs*. To separate them later, create `acupressure-prod` (step 2), load the knowledge base there, and update those values.

**Free-tier trade-offs:**
- Free Render web services sleep after 15 minutes idle, so the first request then takes about a minute. The upgrade is $7/month per service.
- Free Supabase projects pause after 7 days without activity until you restore them in the dashboard.

## One-time setup

For the full sequence including local tools, the `gh` CLI and Claude Code, see [`setup-guide.md`](setup-guide.md).

Do these steps in order. Keep secret values out of chat and commits: paste them only into the AWS, Supabase, Render and GitHub dashboards, or into `gh secret set`.

### 1. AI provider keys

The AWS account has no Bedrock token quota, so the app uses Claude on the Anthropic API and Voyage AI for embeddings (`AI_PROVIDER=anthropic`). Bedrock is still supported by the code (`AI_PROVIDER=bedrock`).

1. **Anthropic.** At console.anthropic.com, add a few dollars of credit under *Billing*, then create an API key under *API Keys*.
2. **Voyage AI.** At dash.voyageai.com, create an API key, and add a payment method: without one the rate limit is 3 requests per minute, which is too slow for ingestion. The first 200M tokens are free.
3. **Check locally.** Put both keys in your local `.env` (`ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`) and run the opt-in smoke test (two small billable calls):

   ```sh
   cd backend && set -a && . ../.env && set +a && RUN_LIVE_AI=1 uv run pytest tests/test_ai.py -k live_anthropic
   ```

### 2. Supabase (twice: dev and prod)

1. **Create the project** at supabase.com: a Free plan project named `acupressure-dev` (later `acupressure-prod`), region Frankfurt.
2. **Collect the settings** from *Project Settings → API*: the **Project URL**, **anon key** and **service_role key**. From *Connect*, take the **Session pooler** connection string; it supports IPv4, which Render and GitHub runners need.
3. **Configure Auth.** Under *Authentication → URL Configuration*, set **Site URL** to the frontend URL (filled in after step 3, e.g. `https://acupressure-web-dev.onrender.com`) and add `<frontend URL>/**` to **Redirect URLs**. Keep *Confirm email* on. Under *Sign In / Providers → Email*, set **Minimum password length** to 8, matching the frontend and `supabase/config.toml`.

   **Email limit:** the project uses Supabase's built-in email service, so confirmation and reset emails come from Supabase's no-reply address and are limited to about 2 per hour across all users. Above that, registration and password reset show "Too many emails were requested. Please try again in an hour." To lift the limit, set up an SMTP provider under *Authentication → Emails → SMTP Settings* (the sender address is visible to users), then raise the email limit under *Authentication → Rate Limits*.
4. **Apply the schema** from your machine:

   ```sh
   make db-setup DATABASE_URL="<session pooler connection string>"
   ```

5. **Add content.** The development project can use the invented demo data so the app can be tried end to end:

   ```sh
   psql "<dev connection string>" -v ON_ERROR_STOP=1 -f db/seed/seed.sql
   cd ingestion && SUPABASE_URL=<dev project URL> SUPABASE_SERVICE_ROLE_KEY=<dev service_role key> \
     DATABASE_URL="<dev connection string>" uv run python -m ingestion.images ../db/seed/images.json
   ```

   Production needs the real curated knowledge base, loaded with the ingestion pipeline (README → Knowledge ingestion). Until it exists, every symptom returns "no match".

### 3. Render

1. **Create the services.** Sign up at render.com with GitHub, then choose *New → Blueprint*, pick this repository, and confirm the four services from `render.yaml`.
2. **Fill in the secrets** Render asks for: the `sync: false` values for each service, from the matching Supabase project and the Anthropic and Voyage keys. The `VITE_` values are the public Project URL and anon key.
3. **Collect the IDs.** Note each service's ID (`srv-…`, on its *Settings* page) and URL. Create an API key under *Account Settings → API Keys*.
4. **Finish Auth.** Go back to Supabase step 2.3 and enter the frontend URLs.

### 4. GitHub

1. **Environments.** Under *Settings → Environments*, create `development` and `production`. For `production`, add yourself as a **required reviewer**; that gives the manual approval step.
2. **Secrets.** Add the environment secrets (you'll be prompted for each value; `RENDER_API_KEY` goes into both environments):

   ```sh
   for s in RENDER_API_KEY RENDER_DEV_API_SERVICE_ID RENDER_DEV_WEB_SERVICE_ID DEV_DATABASE_URL; do
     gh secret set "$s" --env development
   done
   for s in RENDER_API_KEY RENDER_PROD_API_SERVICE_ID RENDER_PROD_WEB_SERVICE_ID PROD_DATABASE_URL; do
     gh secret set "$s" --env production
   done
   ```

3. **Variables.** Add the repository variables (public URLs):

   ```sh
   gh variable set DEV_API_URL --body https://acupressure-api-dev.onrender.com
   gh variable set DEV_WEB_URL --body https://acupressure-web-dev.onrender.com
   gh variable set PROD_API_URL --body https://acupressure-api-prod.onrender.com
   gh variable set PROD_WEB_URL --body https://acupressure-web-prod.onrender.com
   ```

### 5. First deployment

1. **Deploy to development.** Re-run the latest *Deploy to development* workflow, or push to `main`.
2. **Verify development end to end.** Register, confirm the email, submit a symptom, rate a point, and delete the test account.
3. **Deploy to production.** Run *Deploy to production* and approve it.
4. **Verify production the same way**, then add the production URL to the README's Deployment section.

## Releasing and rolling back

- **Release:** merge to `main` → CI → automatic deploy to development → verify → run *Deploy to production* (it defaults to the latest successful development deployment) → approve.
- **A failed deploy never replaces the working version.** Render switches traffic only after the new version builds and passes `/api/health`. If it fails, the workflow fails and the previous version keeps serving.
- **Rollback:** run *Deploy to production* with the **commit** input set to the last known good SHA, taken from the history of successful production runs. Render's dashboard also offers *Rollback* on any earlier deploy.
- **The database is not rolled back.** The `db/` scripts are additive and idempotent, so older code keeps working with a newer schema. Never put destructive changes in them.
