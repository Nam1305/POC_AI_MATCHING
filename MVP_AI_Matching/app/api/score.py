"""
POST /ai/score  — Compute 5-dimension score for one CV against one JD.

All required inputs come from .NET (no DB lookup here):
  - parsed_cv, parsed_jd  : already-extracted Pydantic models
  - cv_embedding, jd_embedding  : pre-computed vectors
  - cv_raw_text  : for D5 keyword overlap
  - weights      : optional, defaults to config
"""

from __future__ import annotations

from typing import Optional

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
    weights:      Optional[dict[str, float]] = None


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
    result = calculate_score(
        parsed_cv    = req.parsed_cv,
        parsed_jd    = req.parsed_jd,
        cv_embedding = req.cv_embedding,
        jd_embedding = req.jd_embedding,
        weights      = req.weights or settings.default_weights,
        cosine_min   = settings.cosine_min,
        cosine_max   = settings.cosine_max,
    )
    return ScoreResponse(
        final_score=result["final_score"],
        scores=ScoresBreakdown(**result["scores"]),
    )
