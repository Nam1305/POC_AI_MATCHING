"""Unit tests for evaluator._analyze_skills — no LLM, no network."""

from __future__ import annotations

from app.schemas import ParsedCV, ParsedJD, RequiredSkill
from app.services.evaluator import _analyze_skills


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


def test_analyze_skills_preferred_reported_but_not_scored():
    # Preferred skills are surfaced as missing_preferred for HR, but must NOT
    # affect skill_match_rate (which is required-only) nor become must-have.
    cv = ParsedCV(skills=["React", "Chart.js"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[RequiredSkill(skill="React.js", weight=3)],
        preferred_skills=["Chart.js", "Laravel"],
    )
    result = _analyze_skills(cv, jd)
    assert result["skill_match_rate"] == 100.0          # required-only, unaffected
    assert result["missing_must_have"] == []
    assert result["missing_preferred"] == ["Laravel"]    # Chart.js is present → not missing
