"""Unit tests for evaluator._analyze_skills — no LLM, no network."""

from __future__ import annotations

import pytest

from app.schemas import ParsedCV, ParsedJD, RequiredSkill
from app.services import evaluator
from app.services.evaluator import _analyze_skills, _is_valid_cv, evaluate_cv_for_job


def test_analyze_skills_implied_match_status():
    # Regression test: CV only lists "ReactJS", JD requires "JavaScript".
    # reactjs implies javascript (Layer 2, skill_implies.json), so the
    # requirement is satisfied as "matched_implied", not "missing_must_have".
    cv = ParsedCV(skills=["reactjs"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[RequiredSkill(skill="JavaScript", weight=3)],
    )
    result = _analyze_skills(cv, jd)

    assert result["missing_must_have"] == []
    assert result["skill_match_rate"] == 100.0
    statuses = {d.skill: d.status for d in result["skill_details"]}
    assert statuses["JavaScript"] == "matched_implied"


def test_analyze_skills_exact_match_takes_priority_over_implied():
    # When CV has both React AND JavaScript explicitly, status must stay
    # "matched" (exact), not be reclassified as "matched_implied".
    cv = ParsedCV(skills=["reactjs", "javascript"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[RequiredSkill(skill="JavaScript", weight=3)],
    )
    result = _analyze_skills(cv, jd)
    statuses = {d.skill: d.status for d in result["skill_details"]}
    assert statuses["JavaScript"] == "matched"


def test_analyze_skills_no_cross_language_leak():
    # CV has "django" (implies python) — must not satisfy an unrelated
    # language requirement like Java.
    cv = ParsedCV(skills=["django"])
    jd = ParsedJD(
        title="Backend",
        required_skills=[RequiredSkill(skill="Java", weight=3)],
    )
    result = _analyze_skills(cv, jd)
    assert result["missing_must_have"] == ["Java"]


def test_analyze_skills_preferred_reported_and_scored_at_lower_weight():
    # Preferred skills are surfaced as missing_preferred for HR AND now
    # contribute to skill_match_rate (weight=2/skill vs required's weight=3),
    # never becoming must-have. total_w=3+2+2=7, matched_w=3(React.js)+2
    # (Chart.js)+0(Laravel missing)=5 -> 71.4%.
    cv = ParsedCV(skills=["React", "Chart.js"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[RequiredSkill(skill="React.js", weight=3)],
        preferred_skills=["Chart.js", "Laravel"],
    )
    result = _analyze_skills(cv, jd)
    assert result["skill_match_rate"] == pytest.approx(71.4)
    assert result["missing_must_have"] == []
    assert result["missing_preferred"] == ["Laravel"]    # Chart.js is present → not missing


def test_analyze_skills_nice_to_have_kept_separate_from_preferred():
    # nice_to_have_skills is a third, lower tier (weight=1/skill vs
    # preferred's weight=2) — tracked in its own bucket (missing_nice_to_have),
    # never merged into missing_preferred, but it DOES contribute to
    # skill_match_rate now. total_w=3+2+1+1=7, matched_w=3(React.js)+0
    # (Laravel missing)+1(Agile matched)+0(Scrum missing)=4 -> 57.1%.
    cv = ParsedCV(skills=["React", "Agile"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[RequiredSkill(skill="React.js", weight=3)],
        preferred_skills=["Laravel"],
        nice_to_have_skills=["Agile", "Scrum"],
    )
    result = _analyze_skills(cv, jd)
    assert result["skill_match_rate"] == pytest.approx(57.1)
    assert result["missing_preferred"] == ["Laravel"]
    assert result["missing_nice_to_have"] == ["Scrum"]   # Agile is present → not missing
    statuses = {d.skill: d.status for d in result["skill_details"]}
    assert statuses["Scrum"] == "missing_nice_to_have"


def test_analyze_skills_bonus_excludes_nice_to_have():
    # A CV skill that the JD already lists as nice_to_have is not a "bonus"
    # (JD did mention it, just at the lowest tier).
    cv = ParsedCV(skills=["React", "Agile"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[RequiredSkill(skill="React.js", weight=3)],
        nice_to_have_skills=["Agile"],
    )
    result = _analyze_skills(cv, jd)
    assert "Agile" not in result["bonus_skills"]


# ---------------------------------------------------------------------------
# _is_valid_cv / narrative short-circuit for non-CV documents
#
# Regression coverage for: uploading a non-CV PDF (e.g. a research paper)
# must not produce a fabricated HR narrative built around empty placeholder
# data ("Ứng viên", "Chưa xác định", 0.0 years).
# ---------------------------------------------------------------------------

def test_is_valid_cv_false_when_llm_flags_not_a_resume():
    # LLM explicitly determined the document isn't a CV — even if it
    # happens to contain a stray recognizable skill word.
    cv = ParsedCV(is_resume=False, skills=["python"])
    assert _is_valid_cv(cv) is False


def test_is_valid_cv_false_when_completely_empty():
    # Legacy ParsedCV records predate `is_resume` (defaults to True) — the
    # emptiness heuristic is the fallback signal for those.
    cv = ParsedCV(is_resume=True)
    assert _is_valid_cv(cv) is False


def test_is_valid_cv_true_for_real_fresher_with_zero_experience():
    # A genuine fresher CV has no work_experience, but does have a name
    # and/or education — must not be misclassified as "not a CV".
    from app.schemas import Education

    cv = ParsedCV(name="Nguyen Van A", education=[Education(institution="HUST", degree_raw="Bachelor")])
    assert _is_valid_cv(cv) is True


@pytest.mark.asyncio
async def test_evaluate_cv_for_job_skips_llm_narrative_for_non_cv(monkeypatch):
    # When the document isn't a CV, evaluate_cv_for_job must not call the
    # LLM narrative prompt at all — it should return a plain notice instead
    # of fabricating a professional assessment around placeholder data.
    async def _fail_if_called(*args, **kwargs):
        raise AssertionError("LLM narrative must not be called for a non-CV document")

    monkeypatch.setattr(evaluator, "call_llm_text", _fail_if_called)

    cv = ParsedCV(is_resume=False)
    jd = ParsedJD(
        title=".NET Developer",
        required_skills=[RequiredSkill(skill=".NET", weight=3)],
        min_experience_years=2,
    )

    result = await evaluate_cv_for_job(cv, jd, include_narrative=True)

    assert result.is_valid_cv is False
    assert result.narrative == evaluator._NOT_A_CV_NOTICE
