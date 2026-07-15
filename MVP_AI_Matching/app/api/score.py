"""
POST /ai/score  — Compute 5-dimension score + qualitative CV evaluation.

Required inputs (from .NET, pre-fetched from DB):
  - parsed_cv, parsed_jd        : structured extraction stored as JSONB
  - cv_embedding, jd_embedding  : pre-computed vectors stored as vector(N)

Returns:
  - final_score + scores breakdown  (pure Python, ~1ms)
  - evaluation: skill breakdown, experience/education verdicts, recommendation
                (LLM narrative included only if include_narrative=true in the request)

.NET saves the response to applications table:
  final_score      FLOAT
  scores           JSONB
  evaluation       JSONB
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from app.config import SCORE_DIMENSIONS, settings
from app.schemas import CVJobEvaluation, ParsedCV, ParsedJD
from app.services.evaluator import evaluate_cv_for_job
from app.services.scorer import calculate_score

router = APIRouter()

_WEIGHT_DIMENSIONS = set(SCORE_DIMENSIONS)  # HR-customizable weights must cover exactly these


class ScoreRequest(BaseModel):
    parsed_cv:    ParsedCV
    parsed_jd:    ParsedJD
    cv_embedding: list[float]
    jd_embedding: list[float]
    weights:      dict[str, float] | None = None  # Wi overrides; None → settings.default_weights
    include_narrative: bool = False  # True → also run the LLM narrative (same cost as calling /evaluate)

    @field_validator("weights")
    @classmethod
    def _validate_weights(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        if v is None:
            return v
        if set(v) != _WEIGHT_DIMENSIONS:
            raise ValueError(f"weights must have exactly the keys {sorted(_WEIGHT_DIMENSIONS)}, got {sorted(v)}")
        if any(not (0.0 <= wi <= 1.0) for wi in v.values()):
            raise ValueError("each weight must be between 0 and 1")
        total = sum(v.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {total}")
        return v


class ScoresBreakdown(BaseModel):
    semantic:   float = Field(..., ge=0, le=100)
    skills:     float = Field(..., ge=0, le=100)
    experience: float = Field(..., ge=0, le=100)
    education:  float = Field(..., ge=0, le=100)
    location:   float = Field(..., ge=0, le=100)


class ScoreResponse(BaseModel):
    final_score:     float = Field(..., ge=0, le=100)
    scores:          ScoresBreakdown
    weights_used:    dict[str, float]                   # Wi actually applied (request override or defaults)
    evaluation:      CVJobEvaluation


@router.post("/score", response_model=ScoreResponse)
async def score_endpoint(req: ScoreRequest) -> ScoreResponse:
    score_task = asyncio.to_thread(
        calculate_score,
        req.parsed_cv,
        req.parsed_jd,
        req.cv_embedding,
        req.jd_embedding,
        weights=req.weights,
    )

    score_result, evaluation = await asyncio.gather(
        score_task,
        evaluate_cv_for_job(req.parsed_cv, req.parsed_jd, include_narrative=req.include_narrative),
    )

    return ScoreResponse(
        final_score     = score_result["final_score"],
        scores          = ScoresBreakdown(**score_result["scores"]),
        weights_used    = req.weights or settings.default_weights,
        evaluation      = evaluation,
    )
