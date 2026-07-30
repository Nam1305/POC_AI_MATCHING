"""
CV-Job Evaluation Service

Đánh giá mức độ phù hợp của CV với một JD cụ thể.
Khác với scorer (cho số 0-100), evaluator cho narrative định tính cho HR đọc.

Flow:
  1. Skill analysis    — Python, reuse SkillMatcher từ skill_matcher.py
  2. Experience check  — Python, so sánh cv_years vs jd.min_experience_years
  3. Education check   — Python, so sánh degree level
  4. LLM narrative     — 1 call duy nhất: hr_summary + strengths + weaknesses

Không có "recommendation" (strong_fit/possible_fit/...) — nhãn phù hợp do
final_score. Narrative
chỉ mô tả, không tự đưa kết luận riêng để tránh mâu thuẫn với điểm số.
"""

from __future__ import annotations

from app.schemas import CVJobEvaluation, ParsedCV, ParsedJD, SkillMatchDetail
from app.services.llm_client import call_llm_text
from app.services.skill_matcher import _skill_matcher, resolve_canonical

_matcher = _skill_matcher


# ---------------------------------------------------------------------------
# Step 1 — Skill analysis
# ---------------------------------------------------------------------------

def _analyze_skills(cv: ParsedCV, jd: ParsedJD) -> dict:
    """
    Phân tích chi tiết mức độ khớp kỹ năng giữa CV và JD (bản mở rộng của
    scorer.score_skills — ở đây cần trả về chi tiết từng skill để hiển thị
    cho HR, không chỉ 1 con số tổng).

    Duyệt cả 3 tier skill của JD qua SkillMatcher.evaluate_tiers — CÙNG nguồn
    mà scorer.score_skills dùng, nên skill_match_rate hiển thị cho HR luôn khớp
    với điểm D2 thực tế dùng để xếp hạng ứng viên (không còn required-only).

    Mỗi yêu cầu (kể cả OR-group/alternatives) được phân loại thành: đã khớp
    (matched/matched_implied), hoặc thiếu — và khi thiếu thì vào đúng bucket
    của tier nó thuộc về: missing_must_have (tier required, weight >= 3),
    missing_preferred (tier preferred, hoặc tier required weight < 3), hoặc
    missing_nice_to_have (tier nice_to_have). Cuối cùng tính thêm
    "bonus_skills" — kỹ năng CV có mà JD không nêu ở bất kỳ tier nào.

    Trả về dict gồm: skill_details (danh sách SkillMatchDetail),
    missing_must_have, missing_preferred, missing_nice_to_have, bonus_skills,
    và skill_match_rate (tỷ lệ % trọng số đã khớp trên tổng trọng số của cả 3 tier).
    """
    ctx     = _matcher.build_cv_context(cv)
    results = _matcher.evaluate_tiers(jd, ctx)

    skill_details: list[SkillMatchDetail] = []
    missing_must: list[str] = []
    missing_pref: list[str] = []
    missing_nice: list[str] = []
    matched_weight = 0.0
    total_weight   = sum(r.weight for r in results)

    for r in results:
        matched_weight += r.weight * r.match.credit
        if r.match.status in ("matched", "matched_implied"):
            status = r.match.status
        elif r.tier == "nice_to_have":
            status = "missing_nice_to_have"
            missing_nice.append(r.label)
        elif r.tier == "preferred" or r.weight < 3:
            status = "missing_preferred"
            missing_pref.append(r.label)
        else:
            status = "missing_must_have"
            missing_must.append(r.label)
        skill_details.append(SkillMatchDetail(
            skill=r.label, status=status, weight=r.weight
        ))

    # Bonus: CV có nhưng JD không yêu cầu (kể cả các alternative của OR-group).
    # So sánh trên dạng canonical để "React" trong CV không bị coi là bonus khi
    # JD đã yêu cầu "React.js".
    jd_normalized: set[str] = set()
    for r in jd.required_skills:
        jd_normalized |= {resolve_canonical(n) for n in _matcher.group_names(r)}
    jd_normalized |= {resolve_canonical(s) for s in jd.preferred_skills}
    jd_normalized |= {resolve_canonical(s) for s in jd.nice_to_have_skills}
    bonus = [s for s in cv.skills if resolve_canonical(s) not in jd_normalized][:8]

    rate = round(matched_weight / total_weight * 100, 1) if total_weight > 0 else 100.0

    return {
        "skill_details":       skill_details,
        "missing_must_have":   missing_must,
        "missing_preferred":   missing_pref,
        "missing_nice_to_have": missing_nice,
        "bonus_skills":        bonus,
        "skill_match_rate":    rate,
    }


# ---------------------------------------------------------------------------
# Step 2 — Experience analysis
# ---------------------------------------------------------------------------

def _analyze_experience(cv: ParsedCV, jd: ParsedJD) -> dict:
    """
    So sánh tổng số năm kinh nghiệm của candidate (cv.total_exp_years) với
    số năm JD yêu cầu tối thiểu (jd.min_experience_years), trả về verdict
    định tính cho HR đọc (không chỉ là con số):

      - "not_required"   : JD không yêu cầu số năm kinh nghiệm cụ thể
      - "over_qualified"  : CV có số năm >= gấp đôi yêu cầu
      - "sufficient"      : CV có số năm >= 80% yêu cầu (coi là đủ)
      - "insufficient"    : CV có số năm ít hơn 80% yêu cầu (thiếu kinh nghiệm)

    Trả về dict {"verdict": ..., "detail": chuỗi mô tả tiếng Việt để hiển
    thị trực tiếp cho HR}.
    """
    if not jd.min_experience_years:
        return {
            "verdict": "not_required",
            "detail":  "JD không yêu cầu số năm kinh nghiệm cụ thể",
        }

    cv_years  = cv.total_exp_years
    required  = jd.min_experience_years

    if cv_years >= required * 2:
        return {
            "verdict": "over_qualified",
            "detail":  f"CV có {cv_years} năm, JD yêu cầu {required} năm (vượt gấp đôi — có thể over-qualified)",
        }
    if cv_years >= required * 0.8:
        return {
            "verdict": "sufficient",
            "detail":  f"CV có {cv_years} năm, JD yêu cầu {required} năm ✓",
        }
    gap = round(required - cv_years, 1)
    return {
        "verdict": "insufficient",
        "detail":  f"CV có {cv_years} năm, JD yêu cầu {required} năm (thiếu {gap} năm)",
    }


# ---------------------------------------------------------------------------
# Step 3 — Education analysis
# ---------------------------------------------------------------------------

def _analyze_education(cv: ParsedCV, jd: ParsedJD) -> str:
    """
    So sánh bằng cấp cao nhất của CV (cv.highest_degree_level) với bằng cấp
    JD yêu cầu (jd.required_degree_level, đã quy đổi thành số thứ tự — level).

    Trả về 1 trong 4 verdict dạng string:
      - "not_required" : JD không yêu cầu bằng cấp cụ thể
      - "exceeds"       : CV có bằng cấp cao hơn yêu cầu
      - "meets"         : CV có bằng cấp đúng bằng yêu cầu
      - "below"         : CV có bằng cấp thấp hơn yêu cầu
    """
    jd_level = jd.required_degree_level
    if not jd_level:
        return "not_required"
    cv_level = cv.highest_degree_level
    if cv_level > jd_level:
        return "exceeds"
    if cv_level == jd_level:
        return "meets"
    return "below"


# ---------------------------------------------------------------------------
# Step 4 — LLM narrative (1 call)
# ---------------------------------------------------------------------------

# Prompt sinh đoạn nhận xét (narrative) bằng tiếng Việt cho HR, dựa trên kết
# quả phân tích Python ở 3 bước trên (skill/experience/education).
# LLM chỉ đóng vai trò "viết văn" tự nhiên từ dữ liệu đã có sẵn — mọi con số
# (tỷ lệ khớp skill, số năm kinh nghiệm...) đều do Python tính trước, LLM
# không tự suy luận số liệu và không tự đưa ra kết luận phù hợp/không phù hợp
# (không có recommendation) — HR tự đánh giá dựa trên final_score/scores.
_NARRATIVE_PROMPT = """\
Bạn là chuyên viên tuyển dụng cấp cao. Hãy viết một đoạn đánh giá ứng viên \
bằng tiếng Việt, theo phong cách nhận xét chuyên nghiệp như người thật viết cho người thật — \
KHÔNG dùng bullet points, KHÔNG dùng tiêu đề, chỉ viết thành đoạn văn liền mạch.

=== THÔNG TIN ĐẦU VÀO ===
Vị trí tuyển dụng : {jd_title}
Ứng viên          : {cv_name}
Role hiện tại     : {cv_role}
Tổng kinh nghiệm  : {cv_years} năm

Kỹ năng match     : {skill_match_rate}% ({matched})
Kỹ năng bắt buộc còn thiếu : {missing_must}
Kỹ năng ưu tiên còn thiếu  : {missing_pref}
Kỹ năng cộng điểm còn thiếu : {missing_nice}
Kỹ năng thêm (bonus)       : {bonus}
Kinh nghiệm       : {exp_detail}
Học vấn           : {edu_verdict}

=== YÊU CẦU OUTPUT ===
Viết 1 đoạn văn khoảng 10 câu. Đoạn văn phải:
- Mở đầu bằng tổng quan về ứng viên (background, định hướng nghề nghiệp)
- Đánh giá chi tiết mức độ phù hợp về kỹ năng kỹ thuật (nêu cụ thể từng nhóm skill matched/missing)
- Nhận xét về kinh nghiệm thực tế (project, work experience) so với yêu cầu JD
- Đánh giá học vấn
- Nêu rõ điểm mạnh nổi bật của ứng viên so với JD
- Nêu rõ những điểm còn thiếu hoặc cần cải thiện
- Đánh giá tiềm năng phát triển và khả năng onboard nhanh
- Kết thúc bằng 1-2 câu tổng kết ngắn gọn mức độ phù hợp tổng thể, KHÔNG đưa ra
  khuyến nghị hành động (phỏng vấn / loại...) — quyết định đó do HR tự đánh giá
  dựa trên điểm số hệ thống đã tính, không phải bạn.
- Giọng văn tự nhiên, chuyên nghiệp, khách quan như nhận xét thực của chuyên viên tuyển dụng cấp cao
"""


async def _llm_narrative(cv: ParsedCV, jd: ParsedJD, analysis: dict) -> str:
    """
    Gọi LLM đúng 1 lần để sinh đoạn nhận xét (narrative) bằng tiếng Việt,
    dựa trên kết quả phân tích Python (skill/experience/education)
    đã gộp sẵn trong `analysis`. Trả về đoạn văn narrative, không kèm nhãn
    phân loại (recommendation) — HR tự đánh giá dựa trên final_score/scores.
    """
    matched = [d.skill for d in analysis["skill_details"] if d.status == "matched"]

    edu_map = {
        "exceeds":      "Bằng cấp vượt yêu cầu",
        "meets":        "Bằng cấp đáp ứng yêu cầu",
        "below":        "Bằng cấp chưa đủ yêu cầu",
        "not_required": "JD không yêu cầu bằng cấp cụ thể",
    }

    prompt = _NARRATIVE_PROMPT.format(
        jd_title         = jd.title,
        cv_name          = cv.name or "Ứng viên",
        cv_role          = cv.current_role or (cv.work_experience[0].role if cv.work_experience else "Chưa xác định"),
        cv_years         = cv.total_exp_years,
        skill_match_rate = analysis["skill_match_rate"],
        matched          = ", ".join(matched) if matched else "chưa xác định được",
        missing_must     = ", ".join(analysis["missing_must_have"]) if analysis["missing_must_have"] else "không có",
        missing_pref     = ", ".join(analysis["missing_preferred"]) if analysis["missing_preferred"] else "không có",
        missing_nice     = ", ".join(analysis["missing_nice_to_have"]) if analysis["missing_nice_to_have"] else "không có",
        bonus            = ", ".join(analysis["bonus_skills"]) if analysis["bonus_skills"] else "không có",
        exp_detail       = analysis["exp_detail"],
        edu_verdict      = edu_map.get(analysis["edu_verdict"], analysis["edu_verdict"]),
    )

    raw_text = await call_llm_text(prompt, temperature=0.4, max_tokens=1200)
    return raw_text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def evaluate_cv_for_job(cv: ParsedCV, jd: ParsedJD, *, include_narrative: bool = True) -> CVJobEvaluation:
    """
    Evaluate how well a parsed CV fits a parsed JD.
    Returns structured qualitative report for HR.

    include_narrative=False skips the LLM call (e.g. /score only needs the
    numeric breakdown, not the HR narrative — that is /evaluate's job).
    """
    skill_data   = _analyze_skills(cv, jd)
    exp_data     = _analyze_experience(cv, jd)
    edu_verdict  = _analyze_education(cv, jd)

    narrative = ""
    if include_narrative:
        # Bundle all for LLM context
        combined = {
            **skill_data,
            "exp_detail":      exp_data["detail"],
            "edu_verdict":     edu_verdict,
        }
        narrative = await _llm_narrative(cv, jd, combined)

    return CVJobEvaluation(
        skill_details        = skill_data["skill_details"],
        missing_must_have    = skill_data["missing_must_have"],
        missing_preferred    = skill_data["missing_preferred"],
        missing_nice_to_have = skill_data["missing_nice_to_have"],
        bonus_skills         = skill_data["bonus_skills"],
        skill_match_rate     = skill_data["skill_match_rate"],

        experience_verdict = exp_data["verdict"],
        experience_detail  = exp_data["detail"],

        education_verdict  = edu_verdict,

        narrative          = narrative,
    )
