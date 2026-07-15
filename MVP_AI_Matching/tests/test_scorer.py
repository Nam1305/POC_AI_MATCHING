"""Unit tests for the scoring engine — no LLM, no network."""

from __future__ import annotations

import datetime

import pytest

from app.schemas import (
    CandidateLocation, DegreeLevel, Education, ParsedCV, ParsedJD,
    RequiredSkill, WorkExperience, WorkLocation,
    merge_month_intervals, parse_month,
)
from app.services import scorer as scorer_module
from app.services.scorer import (
    cosine_sim, normalize_cosine,
    score_skills, score_experience, score_education, score_keywords,
    score_location,
    calculate_score,
)


def _months_ago(n: int) -> str:
    """'YYYY-MM' string for n calendar months before today, for date-based fixtures."""
    today = datetime.date.today()
    total = today.year * 12 + (today.month - 1) - n
    year, month0 = divmod(total, 12)
    return f"{year:04d}-{month0 + 1:02d}"


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


def test_chartjs_implies_data_visualization():
    # Chart.js is a data-visualization library; a JD asking for "Data
    # Visualization" must count it as matched (concept implication), not missing.
    cv = ParsedCV(skills=["Chart.js"])
    jd = ParsedJD(
        title="Frontend",
        required_skills=[RequiredSkill(skill="Data Visualization", weight=3)],
    )
    assert score_skills(cv, jd) == pytest.approx(1.0)


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
    # start/end 24 calendar months apart, ending mid-range (6mo ago) so no
    # recency modifier kicks in and only the base ratio is exercised.
    cv = ParsedCV(work_experience=[
        WorkExperience(company="Company A", start=_months_ago(30), end=_months_ago(6))
    ])
    jd2 = ParsedJD(title="x", min_experience_years=2)
    jd4 = ParsedJD(title="x", min_experience_years=4)
    assert score_experience(cv, jd2) == 1.0
    assert score_experience(cv, jd4) == pytest.approx(0.5)


def test_score_experience_relevance_bonus():
    cv = ParsedCV(
        work_experience=[WorkExperience(
            company="Company A", role=".NET Developer",
            start=_months_ago(30), end=_months_ago(6), tech_stack=[".NET"],
        )]
    )
    jd = ParsedJD(title=".NET Developer", min_experience_years=2)
    # base=1.0 + relevance bonus → capped at 1.0
    assert score_experience(cv, jd) == 1.0


def test_score_experience_recency_bonus():
    cv = ParsedCV(work_experience=[WorkExperience(
        company="Company A", role="Dev", start=_months_ago(12), is_current=True,
    )])
    jd = ParsedJD(title="Dev", min_experience_years=2)
    # base=0.5, recency bonus=+0.1 → 0.6
    assert score_experience(cv, jd) == pytest.approx(0.6)


def test_score_experience_over_qualification_penalty():
    cv = ParsedCV(work_experience=[
        WorkExperience(company="Company A", start=_months_ago(126), end=_months_ago(6))
    ])
    jd = ParsedJD(title="Dev", min_experience_years=2)
    # base=1.0, over-qual penalty=-0.05 → 0.95
    assert score_experience(cv, jd) == pytest.approx(0.95)


def test_total_exp_months_merges_overlapping_jobs():
    """W4: concurrent freelance + full-time must not double-count the overlap."""
    cv = ParsedCV(work_experience=[
        WorkExperience(company="Full-time", start="2020-01", end="2023-01"),   # 36mo
        WorkExperience(company="Freelance", start="2021-01", end="2022-01"),   # 12mo, fully inside the above
    ])
    # Naive sum would give 48; the merged calendar span is 36.
    assert cv.total_exp_months == 36


def test_total_exp_months_sums_non_overlapping_jobs():
    cv = ParsedCV(work_experience=[
        WorkExperience(company="Job A", start="2018-01", end="2019-01"),  # 12mo
        WorkExperience(company="Job B", start="2020-01", end="2021-01"),  # 12mo, no overlap
    ])
    assert cv.total_exp_months == 24


def test_score_experience_overlapping_jobs_not_double_counted():
    """W4 regression via score_experience: overlap must not inflate the D3 base ratio."""
    # Full-time ends 6mo ago (inside the [3,12] no-recency-modifier window), so
    # the only thing under test is the base ratio. Freelance sits fully inside
    # the full-time span, so merged = 36mo; naive sum would be 36+12 = 48mo.
    cv = ParsedCV(work_experience=[
        WorkExperience(company="Full-time", start=_months_ago(42), end=_months_ago(6)),
        WorkExperience(company="Freelance", start=_months_ago(30), end=_months_ago(18)),
    ])
    jd = ParsedJD(title="x", min_experience_years=3)
    jd_strict = ParsedJD(title="x", min_experience_years=4)
    assert score_experience(cv, jd) == pytest.approx(1.0)          # 36/36 = 1.0
    assert score_experience(cv, jd_strict) == pytest.approx(0.75)  # 36/48, not 48/48=1.0


def test_merge_month_intervals_touching_boundaries_no_gap_no_double_count():
    """Back-to-back jobs (one ends exactly where the next starts) must merge
    into one continuous span — the shared boundary month is neither lost nor
    counted twice."""
    intervals = [
        (parse_month("2020-01"), parse_month("2021-01")),  # 12mo
        (parse_month("2021-01"), parse_month("2022-01")),  # 12mo, starts exactly where the first ends
    ]
    assert merge_month_intervals(intervals) == 24


def test_merge_month_intervals_real_gap_kept_separate():
    """A genuine 1-month gap between jobs must not be merged away."""
    intervals = [
        (parse_month("2020-01"), parse_month("2021-01")),  # 12mo
        (parse_month("2021-02"), parse_month("2022-02")),  # 12mo, starts 1mo after the first ends
    ]
    assert merge_month_intervals(intervals) == 24  # no overlap: same as naive sum


def test_merge_month_intervals_chain_overlap_order_independent():
    """A overlaps B and B overlaps C, but A and C don't touch directly —
    all three must still collapse into one continuous span regardless of
    input order."""
    a = (parse_month("2018-01"), parse_month("2019-01"))  # 12mo
    b = (parse_month("2018-07"), parse_month("2019-07"))  # overlaps A by 6mo
    c = (parse_month("2019-06"), parse_month("2020-06"))  # overlaps B by 1mo, doesn't touch A
    # Overall span 2018-01 -> 2020-06 = 29mo; naive sum would be 36.
    assert merge_month_intervals([a, b, c]) == 29
    assert merge_month_intervals([c, a, b]) == 29
    assert merge_month_intervals([b, c, a]) == 29


def test_merge_month_intervals_empty_list_returns_zero():
    assert merge_month_intervals([]) == 0


def test_total_exp_months_skips_entry_with_unparseable_start():
    """An entry with no usable start date is excluded, not counted as 0
    months and not allowed to crash the total."""
    cv = ParsedCV(work_experience=[
        WorkExperience(company="Job A", start="2020-01", end="2021-01"),  # 12mo
        WorkExperience(company="Bad entry", start="", end="2021-01"),      # unparseable start
    ])
    assert cv.total_exp_months == 12


def test_total_exp_months_ongoing_job_counts_to_today():
    cv = ParsedCV(work_experience=[
        WorkExperience(company="Current job", start=_months_ago(10), end="present"),
    ])
    assert cv.total_exp_months == 10


def test_total_exp_months_empty_work_experience_returns_zero():
    assert ParsedCV(work_experience=[]).total_exp_months == 0


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
