"""
POST /ai/score  — Compute 5-dimension score + qualitative CV evaluation.

Required inputs (from .NET, pre-fetched from DB):
  - parsed_cv, parsed_jd        : structured extraction stored as JSONB
  - cv_embedding, jd_embedding  : pre-computed vectors stored as vector(N)

Returns:
  - final_score + scores breakdown  (pure Python, ~1ms)
  - evaluation: skill breakdown, experience/education verdicts, LLM narrative, recommendation

.NET saves the response to applications table:
  final_score      FLOAT
  scores           JSONB
  evaluation       JSONB
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas import CVJobEvaluation, ParsedCV, ParsedJD
from app.services.evaluator import evaluate_cv_for_job
from app.services.scorer import calculate_score_with_rules

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
    final_score:     float = Field(..., ge=0, le=100)   # after hard-rule penalties
    scores:          ScoresBreakdown
    penalty_applied: float = Field(0.0, ge=0, le=1)     # fraction subtracted from final_score
    penalty_reasons: list[str] = Field(default_factory=list)
    evaluation:      CVJobEvaluation


@router.post("/score", response_model=ScoreResponse)
async def score_endpoint(req: ScoreRequest) -> ScoreResponse:
    score_task = asyncio.to_thread(
        calculate_score_with_rules,
        req.parsed_cv,
        req.parsed_jd,
        req.cv_embedding,
        req.jd_embedding,
    )

    score_result, evaluation = await asyncio.gather(
        score_task,
        evaluate_cv_for_job(req.parsed_cv, req.parsed_jd),
    )

    return ScoreResponse(
        final_score     = score_result["final_score"],
        scores          = ScoresBreakdown(**score_result["scores"]),
        penalty_applied = score_result["penalty_applied"],
        penalty_reasons = score_result["penalty_reasons"],
        evaluation      = evaluation,
    )
