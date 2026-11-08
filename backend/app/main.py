from fastapi import FastAPI

app = FastAPI(title="Acupressure Recommendation API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
