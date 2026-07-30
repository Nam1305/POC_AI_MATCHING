"""
Bộ test toàn diện cho D2 (Skill Scoring) — phủ toàn bộ pipeline 3 tầng +
proficiency + scoring + evaluator + bất biến dữ liệu + composite thực tế.

Theo danh mục A–L đã duyệt. Dùng parametrize cho các nhóm lặp (entailment,
proficiency, identity) để gọn mà vẫn rõ từng case.

Không LLM/network. Assert dựa trên data tĩnh data/skill_data.json +
data/skill_implies.json.
"""

from __future__ import annotations

import pytest

from app.schemas import ParsedCV, ParsedJD, Project, RequiredSkill, WorkExperience
from app.services.evaluator import _analyze_skills
from app.services.scorer import score_skills
from app.services.skill_matcher import (
    SKILL_DATA,
    SKILL_IMPLIES,
    SkillMatcher,
    resolve_canonical,
    to_stackoverflow_format,
    _skill_matcher as M,
)


def _cv(*skills, tech=None, projects=None, certs=None, langs=None):
    return ParsedCV(
        skills=list(skills),
        work_experience=[WorkExperience(company="C", tech_stack=tech)] if tech else [],
        projects=[Project(name="P", tech_stack=projects)] if projects else [],
        certifications=certs or [],
        languages=langs or [],
    )


def _req(skill, weight=3, alternatives=None):
    return RequiredSkill(skill=skill, weight=weight, alternatives=alternatives or [])


def _jd(*reqs, preferred=None):
    return ParsedJD(title="x", required_skills=list(reqs), preferred_skills=preferred or [])


def _name(cv_skill, jd_skill):
    """Tiện ích: đánh giá 1 JD skill với 1 CV chỉ chứa cv_skill."""
    return M.evaluate_name(jd_skill, M.build_cv_context(_cv(cv_skill)))


# ═══════════════════════════════════════════════════════════════════════════
# A. Chuẩn hóa format
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("skill,expected_variant", [
    ("ASP.NET Core", "asp.net-core"),
    ("Node.js", "nodejs"),
    ("React Native", "react-native"),
    ("Spring Boot", "spring-boot"),
])
def test_A_to_so_generates_expected_variant(skill, expected_variant):
    assert expected_variant in to_stackoverflow_format(skill)


@pytest.mark.parametrize("skill,canonical", [
    ("Golang", "go"), ("VueJS", "vue.js"), ("C#", "c#"), ("ReactJS", "reactjs"),
    ("Node.js", "node.js"), ("ASP.NET Core", "asp.net-core"),
    ("Django", "django"), ("Kotlin", "kotlin"),          # null-value => key itself
])
def test_A_resolve_canonical(skill, canonical):
    assert resolve_canonical(skill) == canonical


def test_A_unknown_falls_back_lowercased():
    assert resolve_canonical("  Foobar QuuxLang ") == "foobar quuxlang"


@pytest.mark.parametrize("s", ["", "   "])
def test_A_empty_input(s):
    assert to_stackoverflow_format(s) == []


def test_A8_rest_api_synonyms_unify():
    # "REST API" / "RESTful API" / "RESTful APIs" phải cùng canonical -> khớp nhau.
    assert _name("REST API", "RESTful API").status != "missing"
    assert _name("RESTful APIs", "REST API").status != "missing"


# ═══════════════════════════════════════════════════════════════════════════
# B. Layer 0 — direct match
# ═══════════════════════════════════════════════════════════════════════════

def test_B_direct_exact_and_case_insensitive():
    ctx = M.build_cv_context(_cv("Python"))
    assert M.evaluate_name("Python", ctx).layer == "layer0"
    assert M.evaluate_name("python", ctx).layer == "layer0"


def test_B_direct_from_tech_stack_and_projects():
    cv = _cv("Python", tech=["FastAPI"], projects=["Redis"])
    ctx = M.build_cv_context(cv)
    assert M.evaluate_name("FastAPI", ctx).layer == "layer0"
    assert M.evaluate_name("Redis", ctx).layer == "layer0"


def test_B_whitespace_trimmed():
    ctx = M.build_cv_context(_cv("Python"))
    assert M.evaluate_name("  Python  ", ctx).status == "matched"


# ═══════════════════════════════════════════════════════════════════════════
# C. Layer 1 — identity (canonical 2 phía)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cv_skill,jd_skill", [
    ("NodeJS", "Node.js"), ("Golang", "Go"), ("VueJS", "Vue.js"),
    ("React.js", "ReactJS"), ("C sharp", "C#"),
])
def test_C_identity_cross_format(cv_skill, jd_skill):
    m = _name(cv_skill, jd_skill)
    assert m.status == "matched" and m.layer in ("layer0", "layer1")


def test_C_distinct_canonicals_do_not_match():
    assert _name("MySQL", "PostgreSQL").status == "missing"


# ═══════════════════════════════════════════════════════════════════════════
# D. Layer 2 — entailment
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cv_skill,jd_skill", [
    ("Django", "Python"), ("FastAPI", "Python"), ("Keras", "TensorFlow"),
    ("Keras", "Python"), ("Express", "Node.js"), ("NestJS", "JavaScript"),
    ("TypeScript", "JavaScript"), ("Spring Boot", "Java"), ("Spring Boot", "Spring"),
    ("Kubernetes", "Docker"), ("GitHub", "Git"), ("Sass", "CSS"),
    ("Deep Learning", "Machine Learning"), ("Chart.js", "JavaScript"),
    ("Next.js", "React"),
])
def test_D_entailment_matches(cv_skill, jd_skill):
    assert _name(cv_skill, jd_skill).status == "matched_implied"


@pytest.mark.parametrize("cv_skill,jd_skill", [
    ("Django", "Java"),          # no cross-language leak
    ("JavaScript", "React"),     # one-directional (js không kéo react)
    ("MySQL", "MongoDB"),        # sibling DBs
])
def test_D_entailment_does_not_leak(cv_skill, jd_skill):
    assert _name(cv_skill, jd_skill).status == "missing"


def test_D12_laravel_implies_php():
    # Laravel -> php-7 -> php (sau khi bổ sung php canonical + php-7->php).
    assert _name("Laravel", "PHP").status == "matched_implied"


# ═══════════════════════════════════════════════════════════════════════════
# E. Proficiency ngôn ngữ (ordinal, cùng framework)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cv_cert,jd_skill,expected", [
    ("JLPT N2", "JLPT N3", "matched"),      # cao hơn
    ("JLPT N3", "JLPT N3", "matched"),      # bằng
    ("JLPT N4", "JLPT N3", "missing"),      # thấp hơn
    ("TOEIC 850", "TOEIC 700", "matched"),
    ("TOEIC 850", "TOEIC 900", "missing"),
    ("IELTS 7.5", "IELTS 6.5", "matched"),
    ("IELTS 6.0", "IELTS 7.0", "missing"),
    ("CEFR B2", "CEFR B1", "matched"),
    ("HSK 5", "HSK 4", "matched"),
    ("TOPIK 6", "TOPIK 4", "matched"),
    ("JLPT N1", "TOEIC 800", "missing"),    # cross-framework
])
def test_E_proficiency_ordinal(cv_cert, jd_skill, expected):
    m = M.evaluate_name(jd_skill, M.build_cv_context(_cv(certs=[cv_cert])))
    assert m.status == expected
    # Chỉ khi chuỗi khác nhau mới đi qua tầng proficiency; nếu cert trùng khít
    # yêu cầu (JLPT N3 vs JLPT N3) thì Layer 0 bắt trước — vẫn đúng.
    if expected == "matched" and cv_cert.lower() != jd_skill.lower():
        assert m.layer == "proficiency"


def test_E_credential_subtoken_and_best_of_many():
    # cert dạng "Japanese - JLPT N2" tách sub-token; nhiều cert lấy mức cao nhất.
    ctx = M.build_cv_context(_cv(certs=["Japanese - JLPT N4", "Japanese - JLPT N1"]))
    assert M.evaluate_name("JLPT N2", ctx).status == "matched"


# ═══════════════════════════════════════════════════════════════════════════
# F. OR-group (alternatives)
# ═══════════════════════════════════════════════════════════════════════════

def test_F_or_group_satisfied_by_primary_or_alternative():
    ctx = M.build_cv_context(_cv("TypeScript"))
    assert M.evaluate_group(_req("React", alternatives=["Vue", "TypeScript"]), ctx).credit == 1.0
    ctx2 = M.build_cv_context(_cv("React"))
    assert M.evaluate_group(_req("React", alternatives=["Vue"]), ctx2).credit == 1.0


def test_F_or_group_all_missing():
    ctx = M.build_cv_context(_cv("Python"))
    assert M.evaluate_group(_req("React", alternatives=["Vue", "Angular"]), ctx).status == "missing"


def test_F_group_label():
    assert M.group_label(_req("Jira", alternatives=["GitLab"])) == "Jira / GitLab"


# ═══════════════════════════════════════════════════════════════════════════
# G. Thứ tự ưu tiên tầng + evidence
# ═══════════════════════════════════════════════════════════════════════════

def test_G_layer0_beats_layer1_beats_layer2():
    # direct thắng
    ctx = M.build_cv_context(_cv("ReactJS", "JavaScript"))
    assert M.evaluate_name("JavaScript", ctx).layer == "layer0"
    # identity thắng implied: CV "NodeJS" (canon node.js) vs JD "Node.js" -> layer1,
    # dù express (không có) mới implies node.js.
    ctx2 = M.build_cv_context(_cv("NodeJS"))
    assert M.evaluate_name("Node.js", ctx2).layer == "layer1"


def test_G_matched_via_points_to_cv_skill():
    ctx = M.build_cv_context(_cv("Next.js"))
    m = M.evaluate_name("React", ctx)
    assert (m.layer, m.via) == ("layer2", "next.js")


# ═══════════════════════════════════════════════════════════════════════════
# H. Scoring — score_skills (nhị phân + trọng số)
# ═══════════════════════════════════════════════════════════════════════════

def test_H_full_match():
    cv = _cv("python", "fastapi", "postgresql")
    jd = _jd(_req("Python", 3), _req("FastAPI", 2))
    assert score_skills(cv, jd) == pytest.approx(1.0)


def test_H_weighted_partial():
    cv = _cv("python", tech=["FastAPI"])
    jd = _jd(_req("Python", 3), _req("FastAPI", 2), _req("Kubernetes", 1))
    assert score_skills(cv, jd) == pytest.approx(5 / 6)


def test_H_all_missing():
    assert score_skills(_cv("cobol"), _jd(_req("Rust", 3))) == pytest.approx(0.0)


def test_H_empty_required_is_neutral():
    assert score_skills(_cv("python"), _jd()) == 1.0


def test_H_binary_only_zero_or_one():
    cv = _cv("python")
    jd = _jd(_req("Python", 3), _req("MySQL", 2), _req("Kubernetes", 1))
    ctx = M.build_cv_context(cv)
    assert {M.evaluate_group(r, ctx).credit for r in jd.required_skills} <= {0.0, 1.0}


def test_H_weight_affects_contribution():
    # thiếu must-have (w3) hại điểm hơn thiếu nice-to-have (w1)
    cv = _cv("python")
    miss_must = score_skills(cv, _jd(_req("Python", 1), _req("Rust", 3)))
    miss_nice = score_skills(cv, _jd(_req("Python", 3), _req("Rust", 1)))
    assert miss_nice > miss_must


# ═══════════════════════════════════════════════════════════════════════════
# I. Evaluator integration — _analyze_skills
# ═══════════════════════════════════════════════════════════════════════════

def test_I_statuses_and_missing_buckets():
    cv = _cv("ReactJS")
    jd = _jd(_req("JavaScript", 3), _req("Python", 3), _req("Docker", 1))
    r = _analyze_skills(cv, jd)
    st = {d.skill: d.status for d in r["skill_details"]}
    assert st["JavaScript"] == "matched_implied"     # reactjs -> javascript
    assert r["missing_must_have"] == ["Python"]      # w3, miss
    assert r["missing_preferred"] == ["Docker"]      # w1, miss


def test_I_exact_match_priority_over_implied():
    cv = _cv("reactjs", "javascript")
    r = _analyze_skills(cv, _jd(_req("JavaScript", 3)))
    st = {d.skill: d.status for d in r["skill_details"]}
    assert st["JavaScript"] == "matched"


def test_I_preferred_lowers_rate_and_bonus_excludes_jd_skills():
    # D2 now merges required (weight=3) + preferred (weight=2/skill): a
    # missing preferred skill still lowers skill_match_rate, just less than
    # a missing required one. total_w=3+2+2=7, matched_w=3(React.js)+2
    # (Chart.js)+0(Laravel missing)=5 -> 71.4%.
    cv = _cv("React", "Chart.js", "Python")
    jd = _jd(_req("React.js", 3), preferred=["Chart.js", "Laravel"])
    r = _analyze_skills(cv, jd)
    assert r["skill_match_rate"] == pytest.approx(71.4)
    assert r["missing_must_have"] == []
    assert "Laravel" in r["missing_preferred"]        # preferred miss
    assert "Python" in r["bonus_skills"]              # CV có, JD không yêu cầu


# ═══════════════════════════════════════════════════════════════════════════
# J. Domain QA/QC
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cv_skill,jd_skill", [
    ("Black Box Testing", "Functional testing"),
    ("End-to-end Testing", "Functional testing"),
    ("Boundary Value Analysis", "Test Case Design"),
    ("Equivalence Partitioning", "Test Case Design"),
    ("Decision Table Testing", "Test Case Design"),
    ("Selenium", "Automation Testing"),
    ("Cypress", "Automation Testing"),
    ("Playwright", "Automation Testing"),
    ("WebdriverIO", "Automation Testing"),
    ("Appium", "Mobile Testing"),
    ("Appium", "Automation Testing"),
    ("JMeter", "Performance Testing"),
    ("k6", "Performance Testing"),
    ("Locust", "Performance Testing"),
    ("Postman", "API Testing"),
    ("Load Testing", "Performance Testing"),
])
def test_J_qa_entailment(cv_skill, jd_skill):
    assert _name(cv_skill, jd_skill).status == "matched_implied"


def test_J_automation_synonyms_unify():
    assert resolve_canonical("Automation Testing") == "automation-testing"
    assert resolve_canonical("Test Automation") == "automation-testing"


@pytest.mark.xfail(strict=True, reason="Compound term 'A/B' chưa được tách ở tầng "
                   "chuẩn hóa JD; cần code (OR-group split), không phải data.")
def test_J9_ui_ux_compound_term():
    # CV có cả "UI Testing" lẫn "UX Testing"; JD gộp "UI/UX testing" nên miss.
    ctx = M.build_cv_context(_cv("UI Testing", "UX Testing"))
    assert M.evaluate_name("UI/UX testing", ctx).status != "missing"


# ═══════════════════════════════════════════════════════════════════════════
# K. Edge cases / robustness
# ═══════════════════════════════════════════════════════════════════════════

def test_K_empty_cv_all_missing():
    assert M.evaluate_name("Python", M.build_cv_context(_cv())).status == "missing"


def test_K_empty_skill_name():
    assert M.evaluate_name("  ", M.build_cv_context(_cv("Python"))).status == "missing"


def test_K_duplicate_skills_no_crash():
    ctx = M.build_cv_context(_cv("Python", "python", "PYTHON"))
    assert M.evaluate_name("Python", ctx).status == "matched"


@pytest.mark.parametrize("skill", ["C++", "C#", ".NET", "F#"])
def test_K_special_chars_resolve(skill):
    # không crash và trả canonical hợp lệ (không rỗng)
    assert resolve_canonical(skill)


def test_K_skill_only_in_certifications():
    ctx = M.build_cv_context(_cv(certs=["AWS Certified Solutions Architect"]))
    assert "aws certified solutions architect" in ctx.raw


def test_K_stateless_matcher():
    ctx = SkillMatcher().build_cv_context(_cv("Django"))
    assert SkillMatcher().evaluate_name("Python", ctx).layer == "layer2"


# ═══════════════════════════════════════════════════════════════════════════
# L. Bất biến dữ liệu + composite thực tế
# ═══════════════════════════════════════════════════════════════════════════

def test_L1_implies_transitively_closed():
    gaps = [(x, z) for x, ys in SKILL_IMPLIES.items() for y in ys
            for z in SKILL_IMPLIES.get(y, []) if z != x and z not in set(ys)]
    assert gaps == []


def test_L2_implies_values_are_canonical():
    def is_canon(t): return t in SKILL_DATA and (SKILL_DATA[t] is None or SKILL_DATA[t] == t)
    bad = {v for vs in SKILL_IMPLIES.values() for v in vs if not is_canon(v)}
    assert bad == set()


def test_L3_implies_keys_are_canonical():
    def is_canon(t): return t in SKILL_DATA and (SKILL_DATA[t] is None or SKILL_DATA[t] == t)
    assert [k for k in SKILL_IMPLIES if not is_canon(k)] == []


def test_L4_composite_qa_profile():
    # Case QA thực tế: hồ sơ QA mạnh nhưng JD nhiều loại test CV không nêu literal.
    cv = _cv("API Testing", "Automation Testing", "Integration Testing", "Manual Testing",
             "Black Box Testing", "Test Case Design", "Test Execution", "Web Testing",
             "Mobile Testing", "Postman", "Swagger", "Jira", "SQL", "Boundary Value Analysis")
    jd = _jd(
        _req("Web testing", 3), _req("Mobile testing", 3), _req("Test case design", 3),
        _req("Functional testing", 3), _req("Integration testing", 3), _req("API testing", 3),
        _req("Postman", 3, ["Swagger"]), _req("SQL", 3), _req("Jira", 3, ["GitLab"]),
        _req("Regression testing", 3),
    )
    score = score_skills(cv, jd)
    # Functional khớp qua black-box (Layer2); Regression miss (CV không nêu) -> ~0.9
    assert 0.85 <= score <= 0.95


def test_L5_composite_backend_strong_fit():
    cv = _cv("Python", "Django", "PostgreSQL", "Docker", "Redis", tech=["FastAPI"])
    jd = _jd(_req("Python", 3), _req("Django", 3), _req("PostgreSQL", 2),
             _req("Docker", 2), _req("FastAPI", 1))
    assert score_skills(cv, jd) == pytest.approx(1.0)


def test_L6_composite_cross_domain_low_fit():
    # Frontend CV vs Data-science JD -> điểm thấp, chống false-positive.
    cv = _cv("React", "JavaScript", "CSS", "HTML")
    jd = _jd(_req("Python", 3), _req("TensorFlow", 3), _req("Pandas", 3),
             _req("Machine Learning", 3))
    assert score_skills(cv, jd) < 0.2
