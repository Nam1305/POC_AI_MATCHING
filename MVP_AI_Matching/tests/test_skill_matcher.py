"""
Unit tests cho pipeline so khớp kỹ năng 3 tầng (app/services/skill_matcher.py).

Bao phủ:
  - to_stackoverflow_format() / resolve_canonical()  (bắc cầu format LLM <-> SO tag)
  - build_cv_context()                                (gom + canonical + implied)
  - Layer 0 direct / Layer 1 identity / Layer 2 entailment / proficiency
  - Thứ tự ưu tiên giữa các tầng + evidence (matched_layer, matched_via)
  - OR-group, scoring nhị phân, evaluate_all_skills()
  - Bắc cầu gián tiếp (data đã đóng transitive closure) + data domain QA/QC
  - Edge cases

Không LLM, không network. Các assert dựa trên dữ liệu tĩnh trong
data/skill_data.json + data/skill_implies.json (facts đã verify tại thời điểm
viết: reactjs/vue.js/go/c# canonical, django->python, express->node.js, v.v.).
"""

from __future__ import annotations

from app.schemas import ParsedCV, ParsedJD, Project, RequiredSkill, WorkExperience
from app.services.skill_matcher import (
    SKILL_DATA,
    SKILL_IMPLIES,
    SkillMatcher,
    resolve_canonical,
    to_stackoverflow_format,
    _skill_matcher,
)

M = _skill_matcher


def _req(skill, weight=3, alternatives=None):
    return RequiredSkill(skill=skill, weight=weight, alternatives=alternatives or [])


def _jd(*reqs, preferred=None):
    return ParsedJD(title="x", required_skills=list(reqs),
                    preferred_skills=preferred or [])


# ---------------------------------------------------------------------------
# Dữ liệu tĩnh nạp được (sanity — nếu file lệch chỗ, cả pipeline vô nghĩa)
# ---------------------------------------------------------------------------

def test_static_data_loaded():
    assert len(SKILL_DATA) > 1000
    assert len(SKILL_IMPLIES) > 100
    # value=null nghĩa là key IS canonical (không phải bỏ qua)
    assert any(v is None for v in SKILL_DATA.values())


# ---------------------------------------------------------------------------
# to_stackoverflow_format — sinh biến thể để tra skill_data.json
# ---------------------------------------------------------------------------

def test_to_so_space_to_hyphen_variant():
    variants = to_stackoverflow_format("ASP.NET Core")
    assert "asp.net core" in variants          # lowercase gốc
    assert "asp.net-core" in variants          # space -> hyphen (khớp SO tag)


def test_to_so_dot_stripped_variant_for_nodejs():
    variants = to_stackoverflow_format("Node.js")
    assert variants[0] == "node.js"            # giữ dấu chấm, ưu tiên trước
    assert "nodejs" in variants                # bỏ dấu chấm -> khớp synonym SO


def test_to_so_react_native():
    assert "react-native" in to_stackoverflow_format("React Native")


def test_to_so_preserves_order_and_dedups():
    variants = to_stackoverflow_format("Go")
    assert variants == list(dict.fromkeys(variants))   # không trùng lặp
    assert variants[0] == "go"


def test_to_so_empty_input():
    assert to_stackoverflow_format("   ") == []
    assert to_stackoverflow_format("") == []


# ---------------------------------------------------------------------------
# resolve_canonical — chuẩn hóa về canonical qua skill_data.json
# ---------------------------------------------------------------------------

def test_resolve_synonym_to_canonical():
    # value khác null -> trả canonical đó
    assert resolve_canonical("Golang") == "go"
    assert resolve_canonical("VueJS") == "vue.js"
    assert resolve_canonical("C#") == "c#"
    assert resolve_canonical("ReactJS") == "reactjs"


def test_resolve_null_value_returns_key_itself():
    # django có value=null trong skill_data -> chính key 'django' là canonical,
    # KHÔNG được coi null là "bỏ qua"/không hợp lệ.
    assert SKILL_DATA.get("django") is None
    assert resolve_canonical("Django") == "django"
    assert resolve_canonical("Kotlin") == "kotlin"


def test_resolve_titlecase_llm_output_bridges_format():
    # Output LLM (Title Case, có space/dot) phải bắc cầu sang SO tag style.
    assert resolve_canonical("Node.js") == "node.js"
    assert resolve_canonical("Vue.js") == "vue.js"
    assert resolve_canonical("ASP.NET Core") == "asp.net-core"


def test_resolve_unknown_skill_falls_back_lowercased():
    # Không có trong danh mục ở bất kỳ biến thể nào -> input lowercase/strip.
    assert resolve_canonical("  Foobar QuuxLang  ") == "foobar quuxlang"


def test_resolve_first_matching_variant_wins():
    # "Node.js": biến thể đầu "node.js" đã khớp -> dừng, không cần "nodejs".
    assert resolve_canonical("NODE.JS") == "node.js"


# ---------------------------------------------------------------------------
# build_cv_context — gom skill từ mọi nguồn của CV
# ---------------------------------------------------------------------------

def test_context_collects_from_all_sources():
    cv = ParsedCV(
        skills=["Python"],
        work_experience=[WorkExperience(company="A", tech_stack=["FastAPI"])],
        projects=[Project(name="P", tech_stack=["Redis"])],
        certifications=["Japanese - JLPT N2"],
    )
    ctx = M.build_cv_context(cv)
    assert "python" in ctx.raw
    assert "fastapi" in ctx.raw           # từ work_experience.tech_stack
    assert "redis" in ctx.raw             # từ projects.tech_stack
    assert "jlpt n2" in ctx.raw           # cert được tách sub-token


def test_context_canonical_and_implied_sets():
    cv = ParsedCV(skills=["Django"])
    ctx = M.build_cv_context(cv)
    assert "django" in ctx.canonical
    assert ctx.canonical_src["django"] == "django"
    # django implies python (Layer 2 data)
    assert "python" in ctx.implied
    assert ctx.implied_src["python"] == "django"


# ---------------------------------------------------------------------------
# Layer 0 — direct match trên output LLM thô
# ---------------------------------------------------------------------------

def test_layer0_direct_exact():
    ctx = M.build_cv_context(ParsedCV(skills=["Python"]))
    m = M.evaluate_name("Python", ctx)
    assert (m.status, m.layer, m.credit) == ("matched", "layer0", 1.0)
    assert m.via == "python"


def test_layer0_case_insensitive():
    ctx = M.build_cv_context(ParsedCV(skills=["FastAPI"]))
    assert M.evaluate_name("fastapi", ctx).layer == "layer0"


# ---------------------------------------------------------------------------
# Layer 1 — identity qua skill_data.json (canonical hóa 2 phía)
# ---------------------------------------------------------------------------

def test_layer1_cross_format_identity():
    # CV "NodeJS" vs JD "Node.js": khác chuỗi thô, cùng canonical node.js.
    ctx = M.build_cv_context(ParsedCV(skills=["NodeJS"]))
    m = M.evaluate_name("Node.js", ctx)
    assert (m.status, m.layer) == ("matched", "layer1")
    assert m.via == "nodejs"              # skill CV thô đã thỏa


def test_layer1_synonym_identity():
    # Golang (CV) vs Go (JD) -> cùng canonical 'go'
    ctx = M.build_cv_context(ParsedCV(skills=["Golang"]))
    assert M.evaluate_name("Go", ctx).layer == "layer1"


def test_layer1_not_matched_for_distinct_canonicals():
    # MySQL và PostgreSQL là 2 canonical khác nhau, không entailment -> missing
    ctx = M.build_cv_context(ParsedCV(skills=["MySQL"]))
    assert M.evaluate_name("PostgreSQL", ctx).status == "missing"


# ---------------------------------------------------------------------------
# Layer 2 — entailment qua skill_implies.json (tra list trực tiếp)
# ---------------------------------------------------------------------------

def test_layer2_framework_implies_language():
    ctx = M.build_cv_context(ParsedCV(skills=["Django"]))
    m = M.evaluate_name("Python", ctx)
    assert (m.status, m.layer, m.via) == ("matched_implied", "layer2", "django")


def test_layer2_multi_target_and_flattened_hop():
    # keras -> [tensorflow, python] (đã flatten 1 hop keras->tensorflow->python)
    ctx = M.build_cv_context(ParsedCV(skills=["Keras"]))
    assert M.evaluate_name("TensorFlow", ctx).layer == "layer2"
    assert M.evaluate_name("Python", ctx).layer == "layer2"


def test_layer2_express_implies_nodejs():
    ctx = M.build_cv_context(ParsedCV(skills=["Express"]))
    assert M.evaluate_name("Node.js", ctx).status == "matched_implied"


def test_layer2_no_cross_language_leak():
    # django implies python, KHÔNG implies java
    ctx = M.build_cv_context(ParsedCV(skills=["Django"]))
    assert M.evaluate_name("Java", ctx).status == "missing"


# ---------------------------------------------------------------------------
# Proficiency — trình độ ngôn ngữ theo thứ bậc (ordinal)
# ---------------------------------------------------------------------------

def test_proficiency_equal_or_higher_matches():
    ctx = M.build_cv_context(ParsedCV(certifications=["Japanese - JLPT N2"]))
    m = M.evaluate_name("JLPT N3", ctx)   # N2 cao hơn N3 -> thỏa
    assert (m.status, m.layer, m.credit) == ("matched", "proficiency", 1.0)


def test_proficiency_lower_does_not_match():
    ctx = M.build_cv_context(ParsedCV(certifications=["Japanese - JLPT N4"]))
    assert M.evaluate_name("JLPT N3", ctx).credit == 0.0


def test_proficiency_toeic_numeric_ordinal():
    ctx = M.build_cv_context(ParsedCV(certifications=["English - TOEIC 850"]))
    assert M.evaluate_name("TOEIC 700", ctx).status == "matched"
    assert M.evaluate_name("TOEIC 900", ctx).status == "missing"


def test_proficiency_cross_framework_no_match():
    # CV có JLPT nhưng JD hỏi TOEIC -> khác framework -> không so được -> missing
    ctx = M.build_cv_context(ParsedCV(certifications=["Japanese - JLPT N1"]))
    assert M.evaluate_name("TOEIC 800", ctx).status == "missing"


# ---------------------------------------------------------------------------
# Thứ tự ưu tiên giữa các tầng — tầng sớm hơn thắng, evidence đúng
# ---------------------------------------------------------------------------

def test_layer0_beats_layer2_when_both_apply():
    # CV có cả "javascript" (direct) lẫn "reactjs" (implies javascript).
    # JD "JavaScript" phải báo layer0 (tầng sớm nhất), không phải layer2.
    ctx = M.build_cv_context(ParsedCV(skills=["ReactJS", "JavaScript"]))
    m = M.evaluate_name("JavaScript", ctx)
    assert m.layer == "layer0"


def test_group_picks_best_layer_across_alternatives():
    # OR-group [Kubernetes(missing) / Django(implies python)]; JD hỏi Python
    # không áp dụng ở đây — dùng group để chọn alternative tốt nhất:
    # req skill Vue (implies js) vs alt "JavaScript" trực tiếp có trong CV.
    ctx = M.build_cv_context(ParsedCV(skills=["JavaScript"]))
    req = _req("Vue", alternatives=["JavaScript"])
    m = M.evaluate_group(req, ctx)
    assert m.layer == "layer0"            # alt JavaScript khớp trực tiếp, tốt hơn


# ---------------------------------------------------------------------------
# OR-group — thỏa 1 alternative là đủ
# ---------------------------------------------------------------------------

def test_or_group_satisfied_by_alternative():
    ctx = M.build_cv_context(ParsedCV(skills=["TypeScript"]))
    req = _req("React", weight=3, alternatives=["Vue", "TypeScript"])
    m = M.evaluate_group(req, ctx)
    assert m.credit == 1.0


def test_or_group_all_missing():
    ctx = M.build_cv_context(ParsedCV(skills=["Python"]))
    req = _req("React", alternatives=["Vue", "Angular"])
    assert M.evaluate_group(req, ctx).status == "missing"


# ---------------------------------------------------------------------------
# evaluate_all_skills — evidence chi tiết cho HR
# ---------------------------------------------------------------------------

def test_evaluate_all_skills_evidence_shape():
    cv = ParsedCV(skills=["Next.js", "FastAPI"], certifications=["JLPT N2"])
    jd = _jd(
        _req("React", weight=3),               # layer2 via next.js
        _req("Python", weight=2),              # layer2 via fastapi
        _req("JLPT N3", weight=1),             # proficiency
        _req("Kubernetes", weight=1, alternatives=["Docker"]),  # missing
    )
    ev = {e["label"]: e for e in M.evaluate_all_skills(cv, jd)}

    assert ev["React"]["matched_layer"] == "layer2"
    assert ev["React"]["matched_via"] == "next.js"
    assert ev["Python"]["matched_layer"] == "layer2"
    assert ev["JLPT N3"]["matched_layer"] == "proficiency"
    km = ev["Kubernetes / Docker"]
    assert km["matched_layer"] == "missing" and km["credit"] == 0.0
    # mọi key evidence đều có mặt
    assert set(ev["React"]) == {"label", "weight", "status",
                                "matched_layer", "matched_via", "credit"}


def test_group_label_or_group_formatting():
    assert M.group_label(_req("React", alternatives=["Vue", "Angular"])) == \
        "React / Vue / Angular"


# ---------------------------------------------------------------------------
# Scoring nhị phân — matched=1.0, missing=0.0 (không partial)
# ---------------------------------------------------------------------------

def test_binary_scoring_no_partial_credit():
    cv = ParsedCV(skills=["Python"])
    jd = _jd(_req("Python", weight=3), _req("Kubernetes", weight=1))
    credits = [M.evaluate_group(r, M.build_cv_context(cv)).credit
               for r in jd.required_skills]
    assert set(credits) <= {0.0, 1.0}     # chỉ có 0 hoặc 1, không giá trị giữa


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_skill_name_is_missing():
    ctx = M.build_cv_context(ParsedCV(skills=["Python"]))
    assert M.evaluate_name("   ", ctx).status == "missing"


def test_empty_cv_all_missing():
    ctx = M.build_cv_context(ParsedCV())
    assert M.evaluate_name("Python", ctx).status == "missing"


def test_stateless_matcher_new_instance_same_result():
    # SkillMatcher không giữ state -> instance mới cho cùng kết quả (an toàn dùng
    # chung singleton _skill_matcher giữa scorer.py và evaluator.py).
    ctx = SkillMatcher().build_cv_context(ParsedCV(skills=["Django"]))
    assert SkillMatcher().evaluate_name("Python", ctx).layer == "layer2"


# ---------------------------------------------------------------------------
# Bắc cầu gián tiếp — skill_implies.json đã được đóng bắc cầu sẵn ở tầng dữ liệu
# (data/close_implies.py). Nhờ vậy nestjs liệt kê javascript trực tiếp dù quan
# hệ thật là nestjs->typescript/node.js->javascript, nên Layer 2 (tra list trực
# tiếp, không traversal) vẫn bắt được. Đây là regression test cho việc đóng
# bắc cầu: nếu file bị sửa tay mà quên chạy lại close_implies.py, test này đỏ.
# ---------------------------------------------------------------------------

def test_layer2_transitive_implication_nestjs_to_javascript():
    ctx = M.build_cv_context(ParsedCV(skills=["NestJS"]))
    assert M.evaluate_name("JavaScript", ctx).status == "matched_implied"


def test_layer2_transitive_implication_aspnet_core_to_dotnet():
    # asp.net-core -> asp.net/c# -> .net : cạnh dẫn xuất phải có mặt sau closure.
    ctx = M.build_cv_context(ParsedCV(skills=["ASP.NET Core"]))
    assert M.evaluate_name(".NET", ctx).status == "matched_implied"


def test_skill_implies_is_transitively_closed():
    # Bất biến dữ liệu: mọi X->Y->Z phải kéo theo X->Z trực tiếp trong file
    # (nếu không, Layer 2 direct-lookup sẽ bỏ sót). Canh cho lần sửa data sau.
    from app.services.skill_matcher import SKILL_IMPLIES
    gaps = [(x, z) for x, ys in SKILL_IMPLIES.items() for y in ys
            for z in SKILL_IMPLIES.get(y, []) if z != x and z not in set(ys)]
    assert gaps == []


# ---------------------------------------------------------------------------
# Domain QA/QC — data pack bổ sung (data/add_qa_skills.py). Kiểm thử phần mềm
# không nằm trong tag lập trình SO gốc; pack này thêm canonical loại test, kỹ
# thuật thiết kế test, tool QA + implies "biết X chắc chắn biết Y".
# ---------------------------------------------------------------------------

def test_qa_black_box_implies_functional_testing():
    # CV chỉ có "Black Box Testing"; JD cần "Functional testing" -> khớp Layer 2
    # (black-box ≈ functional). Đây là false-negative đã sửa từ case QA thực tế.
    ctx = M.build_cv_context(ParsedCV(skills=["Black Box Testing"]))
    m = M.evaluate_name("Functional testing", ctx)
    assert (m.status, m.layer) == ("matched_implied", "layer2")


def test_qa_design_technique_implies_test_case_design():
    ctx = M.build_cv_context(ParsedCV(skills=["Boundary Value Analysis"]))
    assert M.evaluate_name("Test Case Design", ctx).status == "matched_implied"


def test_qa_selenium_implies_automation_testing():
    # "Selenium" -> canonical selenium-webdriver -> implies automation-testing
    ctx = M.build_cv_context(ParsedCV(skills=["Selenium"]))
    assert M.evaluate_name("Automation Testing", ctx).status == "matched_implied"


def test_qa_appium_implies_mobile_and_automation():
    ctx = M.build_cv_context(ParsedCV(skills=["Appium"]))
    assert M.evaluate_name("Mobile Testing", ctx).status == "matched_implied"
    assert M.evaluate_name("Automation Testing", ctx).status == "matched_implied"


def test_qa_perf_and_api_tools_imply_their_testing():
    ctx = M.build_cv_context(ParsedCV(skills=["JMeter", "Postman"]))
    assert M.evaluate_name("Performance Testing", ctx).status == "matched_implied"
    assert M.evaluate_name("API Testing", ctx).status == "matched_implied"


def test_qa_automation_synonyms_unify():
    # "Automation Testing" và "Test Automation" cùng canonical automation-testing.
    assert resolve_canonical("Automation Testing") == "automation-testing"
    assert resolve_canonical("Test Automation") == "automation-testing"
