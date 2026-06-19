"""
FastAPI entry point for AI Service.

Endpoints (all under /ai prefix, see app/api/*.py):
  POST /ai/parse-jd     — JD text → parsed JSON + embedding
  POST /ai/parse-cv     — CV file(s) → parsed JSON + embedding
  POST /ai/score        — CV ↔ JD → 5-dimension score (pure Python, no LLM)

Plus:
  GET /health           — health check
  GET /docs             — Swagger UI
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import evaluate, parse, score

app = FastAPI(
    title="AI Service — CV/JD Matching",
    version="0.3.0",
    description="Stateless microservice for CV parsing, JD parsing, and scoring.",
)

# Internal Docker network only — wide-open CORS is safe.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount feature routers
app.include_router(parse.router,    prefix="/ai", tags=["parse"])
app.include_router(score.router,    prefix="/ai", tags=["score"])
app.include_router(evaluate.router, prefix="/ai", tags=["evaluate"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=True,
    )
