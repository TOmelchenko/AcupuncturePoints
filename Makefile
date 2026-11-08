.PHONY: install test test-backend test-frontend

install:
	cd backend && uv sync
	cd frontend && npm ci

test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm test
