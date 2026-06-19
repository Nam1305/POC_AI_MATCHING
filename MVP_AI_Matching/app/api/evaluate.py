"""
POST /ai/evaluate  — Qualitative CV-JD evaluation with LLM narrative.

Requires pre-parsed inputs (same objects stored in DB after /parse-cv and /parse-jd).
Returns structured skill breakdown + HR-readable narrative + recommendation label.
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

    Runs 4 Python analyses (skills, experience, education, seniority) then
    a single LLM call to produce an HR-readable narrative and recommendation.

    Recommendation labels:
    - **strong_fit**   : skill_match ≥ 80%, sufficient experience, no missing must-have
    - **possible_fit** : skill_match ≥ 60%, missing at most 1 must-have
    - **weak_fit**     : skill_match 40–60%, or missing 2 must-have skills
    - **poor_fit**     : skill_match < 40%, or missing > 2 must-have skills
    """
    return await evaluate_cv_for_job(req.parsed_cv, req.parsed_jd)
