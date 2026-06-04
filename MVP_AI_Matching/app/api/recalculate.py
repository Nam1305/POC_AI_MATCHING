"""
POST /ai/recalculate — Re-apply new weights to already-computed per-dimension scores.

Called when HR adjusts weight sliders. Pure arithmetic, no LLM, no embedding.
.NET sends the existing per-dimension scores; we return new final_scores.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.scorer import recalculate_final

router = APIRouter()


class ApplicationScores(BaseModel):
    id:     str
    scores: dict[str, float]   # {semantic, skills, experience, education, keywords} — values 0-100


class RecalculateRequest(BaseModel):
    applications: list[ApplicationScores]
    weights:      dict[str, float] = Field(..., description="Must sum to ~1.0")


class ApplicationResult(BaseModel):
    id:          str
    final_score: float


class RecalculateResponse(BaseModel):
    results: list[ApplicationResult]


@router.post("/recalculate", response_model=RecalculateResponse)
async def recalculate_endpoint(req: RecalculateRequest) -> RecalculateResponse:
    weight_sum = sum(req.weights.values())
    if not (0.99 <= weight_sum <= 1.01):
        raise HTTPException(
            status_code=400,
            detail=f"weights must sum to 1.0, got {weight_sum:.3f}",
        )

    results = [
        ApplicationResult(id=app.id, final_score=recalculate_final(app.scores, req.weights))
        for app in req.applications
    ]
    return RecalculateResponse(results=results)
