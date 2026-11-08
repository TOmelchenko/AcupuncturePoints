# Deployment

The MVP runs on free tiers. Bedrock is the only usage-based cost.

| Piece | Development | Production |
|---|---|---|
| Database, Auth, Storage | Supabase Free project `acupressure-dev` | Supabase Free project `acupressure-prod` |
| Backend (FastAPI, Docker) | Render free web service `acupressure-api-dev` | Render free web service `acupressure-api-prod` |
| Frontend (static) | Render static site `acupressure-web-dev` | Render static site `acupressure-web-prod` |
| AI | Amazon Bedrock: Claude Haiku 4.5 + Titan Text Embeddings V2 | same |

Everything is defined in `render.yaml` (Render Blueprint) and two workflows:

- **`.github/workflows/deploy-dev.yml`** runs automatically after CI passes on `main`. It applies the `db/` scripts to the dev database, deploys that exact commit (backend, then frontend), and smoke-tests it.
- **`.github/workflows/deploy-prod.yml`** runs manually (Actions → *Deploy to production* → Run workflow). It only accepts a commit that passed CI and was deployed to development, waits for approval on the `production` environment, then deploys and smoke-tests it.

**Free-tier trade-offs:**
- Free Render web services sleep after 15 minutes idle, so the first request then takes about a minute. The upgrade is $7/month per service.
- Free Supabase projects pause after 7 days without activity until you restore them in the dashboard.

## One-time setup

Do these steps in order. Keep secret values out of chat and commits: paste them only into the AWS, Supabase, Render and GitHub dashboards, or into `gh secret set`.

### 1. AWS Bedrock

1. **Model access.** In the AWS console, pick a Bedrock region (e.g. `eu-central-1` or `us-east-1`) and make sure **Claude Haiku 4.5** and **Titan Text Embeddings V2** are enabled under *Model access*.
2. **Deploy user.** Create an IAM user (or role) for the app whose only permission is `bedrock:InvokeModel` on those two models. Create an access key for it.
3. **Check locally.** Put the key in your local `.env` (`AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) and run the opt-in smoke test (two small billable calls):

   ```sh
   cd backend && BEDROCK_TEXT_MODEL_ID=anthropic.claude-haiku-4-5 RUN_LIVE_AI=1 uv run pytest tests/test_ai.py -k live
   ```

### 2. Supabase (twice: dev and prod)

1. **Create the project** at supabase.com: a Free plan project named `acupressure-dev` (later `acupressure-prod`), region Frankfurt.
2. **Collect the settings** from *Project Settings → API*: the **Project URL**, **anon key** and **service_role key**. From *Connect*, take the **Session pooler** connection string; it supports IPv4, which Render and GitHub runners need.
3. **Configure Auth.** Under *Authentication → URL Configuration*, set **Site URL** to the frontend URL (filled in after step 3, e.g. `https://acupressure-web-dev.onrender.com`) and add `<frontend URL>/**` to **Redirect URLs**. Keep *Confirm email* on.
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
2. **Fill in the secrets** Render asks for: the `sync: false` values for each service, from the matching Supabase project and AWS key. The `VITE_` values are the public Project URL and anon key.
3. **Collect the IDs.** Note each service's ID (`srv-…`, on its *Settings* page) and URL. Create an API key under *Account Settings → API Keys*.
4. **Finish Auth.** Go back to Supabase step 2.3 and enter the frontend URLs.

### 4. GitHub

1. **Environments.** Under *Settings → Environments*, create `development` and `production`. For `production`, add yourself as a **required reviewer**; that gives the manual approval step.
2. **Secrets.** Add the repository secrets (you'll be prompted for each value):

   ```sh
   for s in RENDER_API_KEY RENDER_DEV_API_SERVICE_ID RENDER_DEV_WEB_SERVICE_ID \
            RENDER_PROD_API_SERVICE_ID RENDER_PROD_WEB_SERVICE_ID DEV_DATABASE_URL PROD_DATABASE_URL; do
     gh secret set "$s"
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
