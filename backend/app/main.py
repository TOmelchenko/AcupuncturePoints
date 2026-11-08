import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import EXCEPTION_HANDLERS, configure_logging
from app.routes import account, recommendations

configure_logging(os.environ.get("LOG_LEVEL", "INFO"))

app = FastAPI(
    title="Acupressure Recommendation API",
    description="General wellness information only; not a diagnosis or medical advice.",
    version="0.1.0",
)
for exception_class, handler in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exception_class, handler)
# Locally the frontend proxies /api (same origin); hosted frontends call the API cross-origin.
if origins := get_settings().cors_allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
app.include_router(recommendations.router)
app.include_router(account.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
