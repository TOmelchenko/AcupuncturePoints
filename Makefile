.PHONY: install env up down logs test test-backend test-frontend lint lint-backend lint-frontend

install:
	cd backend && uv sync
	cd frontend && npm ci

# Create .env from the template on first run
env:
	@test -f .env || cp .env.example .env

up: env
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm test

lint: lint-backend lint-frontend

lint-backend:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app tests

lint-frontend:
	cd frontend && npm run lint
