# Acupressure Recommendation App

A responsive web app that suggests acupressure points for a described symptom, using curated knowledge and AI-assisted retrieval. See `_docs/specification.md` for requirements.

> General wellness information only — not a diagnosis or a substitute for professional medical care.

## Development commands

| Command | What it does |
|---|---|
| `make install` | Install backend (uv) and frontend (npm) dependencies |
| `make up` / `make down` / `make logs` | Start, stop and follow the Docker Compose environment (frontend on http://localhost:5173, backend on http://localhost:8000) |
| `make test` | Run backend and frontend tests |
| `make lint` | Run ruff, mypy and ESLint |
| `make security` | Scan dependencies (pip-audit, npm audit) and detect committed secrets (gitleaks, via Docker) |

The same checks run in GitHub Actions on every pull request and push to `main`.
