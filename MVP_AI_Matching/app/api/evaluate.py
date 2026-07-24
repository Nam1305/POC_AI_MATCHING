"""
POST /ai/evaluate  — Qualitative CV-JD evaluation with LLM narrative.

Requires pre-parsed inputs (same objects stored in DB after /parse-cv and /parse-jd).
Returns structured skill breakdown + HR-readable narrative.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas import CVJobEvaluation, ParsedCV, ParsedJD
from app.services.evaluator import evaluate_cv_for_job
from pydantic import BaseModel

router = APIRouter()


class EvaluateRequest(BaseModel):
    parsed_cv: ParsedCV
    parsed_jd: ParsedJD


@router.post("/evaluate", response_model=CVJobEvaluation)
async def evaluate_endpoint(req: EvaluateRequest) -> CVJobEvaluation:
    """
    Qualitative evaluation of a CV against a JD.

    Runs 3 Python analyses (skills, experience, education) then
    a single LLM call to produce an HR-readable narrative. There is no
    recommendation/fit label — HR reads the narrative alongside final_score
    from /score and judges fit themselves.
    """
    return await evaluate_cv_for_job(req.parsed_cv, req.parsed_jd)
