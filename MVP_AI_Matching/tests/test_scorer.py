"""Unit tests for the scoring engine — no LLM, no network."""

from __future__ import annotations

import pytest

from app.schemas import (
    DegreeLevel, Education, ParsedCV, ParsedJD,
    RequiredSkill, JDEducation, WorkExperience,
)
from app.services.scorer import (
    cosine_sim, normalize_cosine, score_skills, score_experience,
    score_education, score_keywords, calculate_score, recalculate_final,
)


def test_cosine_sim_identical_vectors():
    v = [1.0, 0.0, 0.0]
    assert cosine_sim(v, v) == pytest.approx(1.0)


def test_cosine_sim_orthogonal():
    assert cosine_sim([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_normalize_cosine_clamps_range():
    assert normalize_cosine(0.10) == 0.0          # below min → 0
    assert normalize_cosine(0.90) == 1.0          # above max → 1
    assert normalize_cosine(0.50) == pytest.approx(0.5)  # midpoint → 0.5


def test_score_skills_full_match():
    cv = ParsedCV(skills=["python", "fastapi", "postgresql"])
    jd = ParsedJD(
        title="Backend",
        required_skills=[
            RequiredSkill(skill="Python", weight=3),
            RequiredSkill(skill="FastAPI", weight=2),
        ],
    )
    assert score_skills(cv, jd) == 1.0


def test_score_skills_partial_with_tech_stack():
    cv = ParsedCV(
        skills=["python"],
        work_experience=[WorkExperience(tech_stack=["FastAPI", "Redis"])],
    )
    jd = ParsedJD(
        title="Backend",
        required_skills=[
            RequiredSkill(skill="Python", weight=3),
            RequiredSkill(skill="FastAPI", weight=2),
            RequiredSkill(skill="Kubernetes", weight=1),
        ],
    )
    # matched weights: 3 + 2 = 5; total = 6
    assert score_skills(cv, jd) == pytest.approx(5 / 6)


def test_score_experience_ratio_and_cap():
    cv = ParsedCV(work_experience=[WorkExperience(months=24)])  # 2 years
    jd2 = ParsedJD(title="x", min_experience_years=2)
    jd4 = ParsedJD(title="x", min_experience_years=4)
    assert score_experience(cv, jd2) == 1.0
    assert score_experience(cv, jd4) == pytest.approx(0.5)


def test_score_education_partial_when_cv_unknown():
    cv = ParsedCV()
    jd = ParsedJD(title="x", education=JDEducation(degree=DegreeLevel.BACHELOR))
    assert score_education(cv, jd) == 0.5


def test_score_education_meets_requirement():
    cv = ParsedCV(education=[Education(institution="X", degree=DegreeLevel.MASTER)])
    jd = ParsedJD(title="x", education=JDEducation(degree=DegreeLevel.BACHELOR))
    assert score_education(cv, jd) == 1.0


def test_score_keywords_overlap():
    text = "Worked with Docker, Kubernetes and PostgreSQL."
    jd = ParsedJD(title="x", keywords=["Docker", "Redis", "PostgreSQL"])
    assert score_keywords(text, jd) == pytest.approx(2 / 3)


def test_calculate_score_returns_full_breakdown():
    cv = ParsedCV(skills=["python"], work_experience=[WorkExperience(months=24)])
    jd = ParsedJD(
        title="Backend",
        required_skills=[RequiredSkill(skill="Python", weight=1)],
        min_experience_years=2,
        keywords=["Python"],
    )
    cv_vec = [1.0, 0.0]
    jd_vec = [1.0, 0.0]
    out = calculate_score(cv, jd, cv_vec, jd_vec, "I love Python", weights=None)

    assert 0 <= out["final_score"] <= 100
    for dim in ("semantic", "skills", "experience", "education", "keywords"):
        assert 0 <= out["scores"][dim] <= 100


def test_recalculate_final_weighted_sum():
    scores = {"semantic": 80, "skills": 100, "experience": 50, "education": 100, "keywords": 0}
    weights = {"semantic": 0.2, "skills": 0.5, "experience": 0.2, "education": 0.1, "keywords": 0.0}
    # 80*0.2 + 100*0.5 + 50*0.2 + 100*0.1 + 0*0.0 = 16 + 50 + 10 + 10 = 86.0
    assert recalculate_final(scores, weights) == 86.0
