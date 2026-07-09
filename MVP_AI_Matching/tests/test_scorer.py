"""Unit tests for the scoring engine — no LLM, no network."""

from __future__ import annotations

import pytest

from app.schemas import (
    CandidateLocation, DegreeLevel, Education, ParsedCV, ParsedJD,
    RequiredSkill, WorkExperience, WorkLocation,
)
from app.services import scorer as scorer_module
from app.services.scorer import (
    cosine_sim, normalize_cosine,
    score_skills, score_experience, score_education, score_keywords,
    score_location,
    calculate_score, calculate_score_with_rules,
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
    # 'js' → javascript, 'reactjs' → react via ALIASES; 'fastapi' exact.
    # "Python" is satisfied via the implied tier (fastapi implies python is a
    # guaranteed fact) before the fuzzy typo 'pythonn' is even considered —
    # so all 4 required skills get full credit.
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
    assert score_skills(cv, jd) == pytest.approx(1.0)


def test_score_skills_fuzzy_still_applies_without_implied_path():
    # Genuine fuzzy-only case: 'pythonn' (typo) with no other CV skill that
    # implies python — must still get the 0.9 fuzzy credit, not full credit.
    cv = ParsedCV(skills=["pythonn"])
    jd = ParsedJD(
        title="Backend",
        required_skills=[RequiredSkill(skill="Python", weight=1)],
    )
    assert score_skills(cv, jd) == pytest.approx(0.9)


def test_score_skills_category_partial_credit():
    # JD wants PostgreSQL (database category); CV has MySQL (same category)
    cv = ParsedCV(skills=["mysql"])
    jd = ParsedJD(
        title="Backend",
        required_skills=[RequiredSkill(skill="PostgreSQL", weight=1)],
    )
    assert score_skills(cv, jd) == pytest.approx(0.3)


def test_score_skills_implied_match_full_credit():
    # CV only lists "ReactJS" (not "JavaScript" explicitly) — React implies
    # JavaScript (IMPLIES, sourced from Wikidata P277), so this must be a
    # full-weight match, not a partial category-credit guess.
    cv = ParsedCV(skills=["reactjs"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[RequiredSkill(skill="JavaScript", weight=3)],
    )
    assert score_skills(cv, jd) == pytest.approx(1.0)


def test_score_skills_or_group_satisfied_by_one_alternative():
    # JD requires "React OR Vue OR TypeScript" as one requirement; CV has React
    # only. The whole group is satisfied → full credit, no missing skill.
    cv = ParsedCV(skills=["React.js", "TypeScript"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[
            RequiredSkill(skill="React.js", weight=3, alternatives=["Vue.js", "TypeScript"]),
        ],
    )
    assert score_skills(cv, jd) == pytest.approx(1.0)


def test_or_group_not_flagged_hard_missing():
    # A candidate with one option of an OR-group must not be penalized for
    # lacking the redundant alternatives.
    cv = ParsedCV(skills=["React.js", "TypeScript"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[
            RequiredSkill(skill="React.js", weight=3, alternatives=["Vue.js"]),
        ],
    )
    res = calculate_score_with_rules(cv, jd, [1.0, 0.0], [1.0, 0.0], "react")
    assert res["penalty_applied"] == 0.0
    assert res["penalty_reasons"] == []


def test_chartjs_implies_data_visualization():
    # Chart.js is a data-visualization library; a JD asking for "Data
    # Visualization" must count it as matched (concept implication), not missing.
    cv = ParsedCV(skills=["Chart.js"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[RequiredSkill(skill="Data Visualization", weight=3)],
    )
    assert score_skills(cv, jd) == pytest.approx(1.0)
    res = calculate_score_with_rules(cv, jd, [1.0, 0.0], [1.0, 0.0], "chart.js")
    assert res["penalty_applied"] == 0.0


def test_rest_apis_plural_alias():
    # "REST APIs" (plural) must normalize to the same canonical as "RESTful APIs".
    cv = ParsedCV(skills=["REST APIs"])
    jd = ParsedJD(
        title="Backend",
        required_skills=[RequiredSkill(skill="RESTful APIs", weight=3)],
    )
    assert score_skills(cv, jd) == pytest.approx(1.0)


def test_score_skills_implied_match_different_ecosystem():
    # CV only has "django" (implies python) — must NOT satisfy an unrelated
    # ecosystem's JD requirement (java). Guards against implied-match noise
    # leaking across languages.
    cv = ParsedCV(skills=["django"])
    jd = ParsedJD(
        title="Backend",
        required_skills=[
            RequiredSkill(skill="Python", weight=3),
            RequiredSkill(skill="Java", weight=3),
        ],
    )
    # python matched via implied (1.0), java stays unmatched (0.0)
    assert score_skills(cv, jd) == pytest.approx(0.5)


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
    for dim in ("semantic", "skills", "experience", "education", "location"):
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


def test_calculate_score_with_rules_implied_skill_no_penalty():
    # Regression test for the original reported bug: JD requires "JavaScript"
    # as a must-have, CV only lists "ReactJS" (no explicit JavaScript entry).
    # Before IMPLIES, this incurred a 0.15 hard-missing penalty even though
    # knowing React logically guarantees knowing JavaScript.
    cv = ParsedCV(skills=["reactjs"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[RequiredSkill(skill="JavaScript", weight=3)],
    )
    cv_vec = [1.0, 0.0]
    jd_vec = [1.0, 0.0]
    res = calculate_score_with_rules(cv, jd, cv_vec, jd_vec, "reactjs")
    assert res["penalty_applied"] == 0.0
    assert res["penalty_reasons"] == []


# ---------------------------------------------------------------------------
# D5: Location + Work Mode
# ---------------------------------------------------------------------------

def test_score_location_remote_jd_short_circuits():
    jd = ParsedJD(title="Backend", work_location=WorkLocation(work_mode="remote"))
    cv = ParsedCV()
    assert score_location(jd, cv) == 1.0


def test_score_location_cv_willing_to_relocate_short_circuits():
    jd = ParsedJD(title="Backend", work_location=WorkLocation(work_mode="onsite"))
    cv = ParsedCV(candidate_location=CandidateLocation(willing_to_relocate=True))
    assert score_location(jd, cv) == 1.0


def test_score_location_missing_lat_lng_returns_neutral():
    # lat/lng are geocoded at parse-time (parser.parse_jd/parse_cv); if either
    # is None here (geocoding failed, or no address was ever present), score
    # stays neutral — no geocode() call happens at score-time anymore.
    jd = ParsedJD(
        title="Backend",
        work_location=WorkLocation(work_mode="onsite", raw_address="Ha Noi"),
    )
    cv = ParsedCV(candidate_location=CandidateLocation(raw_address="Ho Chi Minh"))
    assert jd.work_location.lat is None and cv.candidate_location.lat is None
    assert score_location(jd, cv) == 0.5


def test_score_location_close_onsite_full_score(monkeypatch):
    jd = ParsedJD(
        title="Backend",
        work_location=WorkLocation(work_mode="onsite", lat=21.0, lng=105.8),
    )
    cv = ParsedCV(candidate_location=CandidateLocation(lat=21.0, lng=105.8))

    monkeypatch.setattr(
        scorer_module.location_service, "get_route",
        lambda c1, c2: {"distance_km": 0.0, "duration_min": 0.0},
    )
    assert score_location(jd, cv) == 1.0


def test_score_location_route_failure_after_retry_returns_neutral(monkeypatch):
    # get_route() failing twice (initial + one retry) must return the same
    # neutral 0.5 as missing lat/lng — no haversine distance fallback anymore.
    jd = ParsedJD(
        title="Backend",
        work_location=WorkLocation(work_mode="onsite", lat=21.0, lng=105.8),
    )
    cv = ParsedCV(candidate_location=CandidateLocation(lat=10.8, lng=106.7))

    call_count = 0

    def _always_fail(c1, c2):
        nonlocal call_count
        call_count += 1
        return None

    monkeypatch.setattr(scorer_module.location_service, "get_route", _always_fail)
    monkeypatch.setattr(scorer_module.time, "sleep", lambda seconds: None)

    assert score_location(jd, cv) == 0.5
    assert call_count == 2


def test_score_location_hybrid_onsite_preference_multiplier(monkeypatch):
    jd = ParsedJD(
        title="Backend",
        work_location=WorkLocation(work_mode="hybrid", lat=21.0, lng=105.8),
    )
    cv = ParsedCV(candidate_location=CandidateLocation(
        lat=21.0, lng=105.8, work_mode_preference="onsite",
    ))

    monkeypatch.setattr(
        scorer_module.location_service, "get_route",
        lambda c1, c2: {"distance_km": 0.0, "duration_min": 0.0},
    )
    # S_loc = 1.0 (0 minutes), M = 0.7 (hybrid JD, CV prefers onsite)
    assert score_location(jd, cv) == pytest.approx(0.7)
