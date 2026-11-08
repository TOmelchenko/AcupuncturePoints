.PHONY: install env up down logs test test-backend test-frontend test-ingestion lint lint-backend lint-frontend lint-ingestion \
	security audit-backend audit-frontend audit-ingestion pip-audit secrets \
	supabase-start supabase-stop db-setup db-reset db-seed

SUPABASE = npx -y supabase@3.0.0
# Local Supabase database unless DATABASE_URL is set (for example in .env)
-include .env
DATABASE_URL ?= postgresql://postgres:postgres@127.0.0.1:54322/postgres

install:
	cd backend && uv sync
	cd frontend && npm ci
	cd ingestion && uv sync

# Create .env from the template on first run
env:
	@test -f .env || cp .env.example .env

up: env
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

test: test-backend test-frontend test-ingestion

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm test

test-ingestion:
	cd ingestion && uv run pytest

lint: lint-backend lint-frontend lint-ingestion

lint-backend:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app tests

lint-frontend:
	cd frontend && npm run lint

lint-ingestion:
	cd ingestion && uv run ruff check . && uv run ruff format --check . && uv run mypy ingestion tests

# Dependency vulnerability scanning and secret detection (same checks as CI)
security: audit-backend audit-frontend audit-ingestion secrets

audit-backend:
	$(MAKE) pip-audit DIR=backend

audit-ingestion:
	$(MAKE) pip-audit DIR=ingestion

pip-audit:
	cd $(DIR) && req=$$(mktemp) && uv export --frozen --no-emit-project --format requirements-txt -q -o $$req \
		&& uvx pip-audit --disable-pip -r $$req; status=$$?; rm -f $$req; exit $$status

audit-frontend:
	cd frontend && npm audit --audit-level=high

secrets:
	docker run --rm -v "$$PWD":/repo ghcr.io/gitleaks/gitleaks:v8.30.0 git /repo

# Local Supabase (Postgres + pgvector, Auth, Storage, Mailpit) via the Supabase CLI
supabase-start:
	$(SUPABASE) start

supabase-stop:
	$(SUPABASE) stop

# Apply SQL setup scripts in file-name order (idempotent)
db-setup:
	for f in db/[0-9]*.sql; do PGOPTIONS=--client-min-messages=warning psql "$(DATABASE_URL)" -v ON_ERROR_STOP=1 -q -f $$f || exit 1; done

# Local only: recreate the local Supabase database, then apply the scripts
db-reset:
	$(SUPABASE) db reset --local
	$(MAKE) db-setup

# Local only: load invented development data and upload its images to Storage
db-seed:
	@case "$(DATABASE_URL)" in *127.0.0.1*|*localhost*) ;; *) echo "db-seed is for the local database only"; exit 1;; esac
	PGOPTIONS=--client-min-messages=warning psql "$(DATABASE_URL)" -v ON_ERROR_STOP=1 -q -f db/seed/seed.sql
	@eval "$$($(SUPABASE) status -o env 2>/dev/null)"; \
	for f in db/seed/images/*; do \
		curl -sf -o /dev/null -X POST "$$API_URL/storage/v1/object/point-images/dev/$$(basename $$f)" \
			-H "Authorization: Bearer $$SERVICE_ROLE_KEY" -H "x-upsert: true" \
			-H "Content-Type: image/svg+xml" --data-binary @$$f \
			&& echo "uploaded dev/$$(basename $$f)" || { echo "upload failed: $$f"; exit 1; }; \
	done
