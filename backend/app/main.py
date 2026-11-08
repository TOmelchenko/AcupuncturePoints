from fastapi import FastAPI

from app.errors import ApiError, api_error_handler

app = FastAPI(title="Acupressure Recommendation API")
app.add_exception_handler(ApiError, api_error_handler)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
