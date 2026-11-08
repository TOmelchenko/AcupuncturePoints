from fastapi import FastAPI

from app.errors import EXCEPTION_HANDLERS
from app.routes import recommendations

app = FastAPI(
    title="Acupressure Recommendation API",
    description="General wellness information only; not a diagnosis or medical advice.",
    version="0.1.0",
)
for exception_class, handler in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exception_class, handler)
app.include_router(recommendations.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
