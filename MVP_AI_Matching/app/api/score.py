"""
POST /ai/score  — Compute 5-dimension score (pure Python, no LLM).

Required inputs (from .NET, pre-fetched from DB):
  - parsed_cv, parsed_jd  : structured extraction stored as JSONB
  - cv_embedding, jd_embedding  : pre-computed vectors stored as vector(N)

Returns:
  - final_score + scores breakdown  (~1ms, no LLM call)

.NET saves the response to applications table:
  final_score      FLOAT
  scores           JSONB
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings
from app.schemas import ParsedCV, ParsedJD
from app.services.scorer import calculate_score

router = APIRouter()


class ScoreRequest(BaseModel):
    parsed_cv:    ParsedCV
    parsed_jd:    ParsedJD
    cv_embedding: list[float]
    jd_embedding: list[float]


class ScoresBreakdown(BaseModel):
    semantic:   float = Field(..., ge=0, le=100)
    skills:     float = Field(..., ge=0, le=100)
    experience: float = Field(..., ge=0, le=100)
    education:  float = Field(..., ge=0, le=100)
    keywords:   float = Field(..., ge=0, le=100)


class ScoreResponse(BaseModel):
    final_score: float = Field(..., ge=0, le=100)
    scores:      ScoresBreakdown


@router.post("/score", response_model=ScoreResponse)
async def score_endpoint(req: ScoreRequest) -> ScoreResponse:
    score_result = await asyncio.to_thread(
        calculate_score,
        req.parsed_cv,
        req.parsed_jd,
        req.cv_embedding,
        req.jd_embedding,
        weights    = settings.default_weights,
        cosine_min = settings.cosine_min,
        cosine_max = settings.cosine_max,
    )

    return ScoreResponse(
        final_score = score_result["final_score"],
        scores      = ScoresBreakdown(**score_result["scores"]),
    )
