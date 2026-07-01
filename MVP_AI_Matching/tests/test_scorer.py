"""Unit tests for the scoring engine — no LLM, no network."""

from __future__ import annotations

import pytest

from app.schemas import (
    DegreeLevel, Education, ParsedCV, ParsedJD,
    RequiredSkill, WorkExperience,
)
from app.services.scorer import (
    cosine_sim, normalize_cosine,
    score_skills, score_experience, score_education, score_keywords,
    calculate_score, calculate_score_with_rules, recalculate_final,
)


# ---------------------------------------------------------------------------
# D1: Semantic
# ---------------------------------------------------------------------------

def test_cosine_sim_identical_vectors():
    v = [1.0, 0.0, 0.0]
    assert cosine_sim(v, v) == pytest.approx(1.0)


def test_cosine_sim_orthogonal():
    assert cosine_sim([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_normalize_cosine_clamps_range():
    assert normalize_cosine(0.10, 0.10, 0.90) == 0.0
    assert normalize_cosine(0.90, 0.10, 0.90) == 1.0
    assert normalize_cosine(0.50, 0.10, 0.90) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# D2: Skills — exact, alias, fuzzy, category
# ---------------------------------------------------------------------------

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
        work_experience=[WorkExperience(company="Company A", tech_stack=["FastAPI", "Redis"])],
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


def test_score_skills_alias_and_fuzzy():
    # 'js' → javascript, 'reactjs' → react via ALIASES
    # 'fastapi' exact, 'pythonn' (typo) → fuzzy match python (0.9 credit)
    cv = ParsedCV(skills=["js", "reactjs", "fastapi", "pythonn"])
    jd = ParsedJD(
        title="Backend",
        required_skills=[
            RequiredSkill(skill="JavaScript", weight=1),
            RequiredSkill(skill="React", weight=1),
            RequiredSkill(skill="FastAPI", weight=1),
            RequiredSkill(skill="Python", weight=1),
        ],
    )
    # total = (1 + 1 + 1 + 0.9) / 4 = 3.9 / 4
    assert score_skills(cv, jd) == pytest.approx(3.9 / 4)


def test_score_skills_category_partial_credit():
    # JD wants PostgreSQL (database category); CV has MySQL (same category)
    cv = ParsedCV(skills=["mysql"])
    jd = ParsedJD(
        title="Backend",
        required_skills=[RequiredSkill(skill="PostgreSQL", weight=1)],
    )
    assert score_skills(cv, jd) == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# D3: Experience
# ---------------------------------------------------------------------------

def test_score_experience_ratio_and_cap():
    cv = ParsedCV(work_experience=[WorkExperience(company="Company A", months=24)])
    jd2 = ParsedJD(title="x", min_experience_years=2)
    jd4 = ParsedJD(title="x", min_experience_years=4)
    assert score_experience(cv, jd2) == 1.0
    assert score_experience(cv, jd4) == pytest.approx(0.5)


def test_score_experience_relevance_bonus():
    cv = ParsedCV(
        work_experience=[WorkExperience(company="Company A", role=".NET Developer", months=24, tech_stack=[".NET"])]
    )
    jd = ParsedJD(title=".NET Developer", min_experience_years=2)
    # base=1.0 + relevance bonus → capped at 1.0
    assert score_experience(cv, jd) == 1.0


def test_score_experience_recency_bonus():
    cv = ParsedCV(work_experience=[WorkExperience(company="Company A", role="Dev", months=12, is_current=True)])
    jd = ParsedJD(title="Dev", min_experience_years=2)
    # base=0.5, recency bonus=+0.1 → 0.6
    assert score_experience(cv, jd) == pytest.approx(0.6)


def test_score_experience_over_qualification_penalty():
    cv = ParsedCV(work_experience=[WorkExperience(company="Company A", months=120)])
    jd = ParsedJD(title="Dev", min_experience_years=2)
    # base=1.0, over-qual penalty=-0.05 → 0.95
    assert score_experience(cv, jd) == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# D4: Education
# ---------------------------------------------------------------------------

def test_score_education_partial_when_cv_unknown():
    cv = ParsedCV()
    jd = ParsedJD(title="x", education_degree=DegreeLevel.BACHELOR)
    assert score_education(cv, jd) == 0.5


def test_score_education_meets_requirement():
    cv = ParsedCV(education=[Education(institution="X", degree=DegreeLevel.MASTER)])
    jd = ParsedJD(title="x", education_degree=DegreeLevel.BACHELOR)
    assert score_education(cv, jd) == 1.0


# ---------------------------------------------------------------------------
# D5: Keywords
# ---------------------------------------------------------------------------

def test_score_keywords_overlap():
    text = "Worked with Docker, Kubernetes and PostgreSQL."
    jd = ParsedJD(title="x", keywords=["Docker", "Redis", "PostgreSQL"])
    assert score_keywords(text, jd) == pytest.approx(2 / 3)


def test_score_keywords_word_boundary():
    text = "Expert in React and Node.js development."
    jd = ParsedJD(title="x", keywords=["React", "Node"])
    assert score_keywords(text, jd) == 1.0


def test_score_keywords_multiword_partial():
    jd = ParsedJD(title="x", keywords=["Cloud Computing"])
    text = "Worked with Cloud and Computing systems."
    # both words present individually → 0.7
    assert score_keywords(text, jd) == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

def test_calculate_score_returns_full_breakdown():
    cv = ParsedCV(skills=["python"], work_experience=[WorkExperience(company="Company A", months=24)])
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


def test_calculate_score_with_rules_must_have_and_exp():
    cv = ParsedCV(skills=["python"])  # missing Java
    jd = ParsedJD(
        title="Backend",
        required_skills=[
            RequiredSkill(skill="Python", weight=1),
            RequiredSkill(skill="Java", weight=3),  # must-have
        ],
        min_experience_years=1,
    )
    cv_vec = [1.0, 0.0]
    jd_vec = [1.0, 0.0]
    # 1 hard missing must-have → 0.15 penalty; 0 yrs < 0.8*1 → 0.20 penalty; total=0.35
    res = calculate_score_with_rules(cv, jd, cv_vec, jd_vec, "python")
    assert res["penalty_applied"] == pytest.approx(0.35)
    assert "missing must-have skills" in res["penalty_reasons"][0]
    assert "insufficient experience" in res["penalty_reasons"][1]


def test_recalculate_final_weighted_sum():
    scores = {"semantic": 80, "skills": 100, "experience": 50, "education": 100, "keywords": 0}
    weights = {"semantic": 0.2, "skills": 0.5, "experience": 0.2, "education": 0.1, "keywords": 0.0}
    # 80*0.2 + 100*0.5 + 50*0.2 + 100*0.1 + 0*0.0 = 16+50+10+10 = 86.0
    assert recalculate_final(scores, weights) == 86.0
