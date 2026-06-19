"""
CV-Job Evaluation Service

Đánh giá mức độ phù hợp của CV với một JD cụ thể.
Khác với scorer (cho số 0-100), evaluator cho narrative định tính cho HR đọc.

Flow:
  1. Skill analysis    — Python, reuse SkillMatcher từ scorer
  2. Experience check  — Python, so sánh cv_years vs jd.min_experience_years
  3. Education check   — Python, so sánh degree level
  4. Seniority check   — Python, reuse _detect_level từ scorer
  5. LLM narrative     — 1 call duy nhất: hr_summary + strengths + weaknesses + recommendation
"""

from __future__ import annotations

from app.schemas import CVJobEvaluation, ParsedCV, ParsedJD, SkillMatchDetail
from app.services.llm_client import call_llm_text
from app.services.scorer import (
    SkillMatcher,
    _collect_cv_skills,
    _detect_level,
)

_matcher = SkillMatcher()


# ---------------------------------------------------------------------------
# Step 1 — Skill analysis
# ---------------------------------------------------------------------------

def _analyze_skills(cv: ParsedCV, jd: ParsedJD) -> dict:
    cv_skills_raw = _collect_cv_skills(cv)
    cv_skills = {_matcher.normalize_skill(s) for s in cv_skills_raw if s}

    skill_details: list[SkillMatchDetail] = []
    missing_must: list[str] = []
    missing_pref: list[str] = []
    matched_weight = 0.0
    total_weight   = sum(r.weight for r in jd.required_skills)

    for req in jd.required_skills:
        jd_norm = _matcher.normalize_skill(req.skill)
        is_matched = jd_norm in cv_skills or any(
            _matcher.fuzzy_match(jd_norm, s) for s in cv_skills
        )
        if is_matched:
            matched_weight += req.weight
            skill_details.append(SkillMatchDetail(
                skill=req.skill, status="matched", weight=req.weight
            ))
        elif req.weight >= 3:
            missing_must.append(req.skill)
            skill_details.append(SkillMatchDetail(
                skill=req.skill, status="missing_must_have", weight=req.weight
            ))
        else:
            missing_pref.append(req.skill)
            skill_details.append(SkillMatchDetail(
                skill=req.skill, status="missing_preferred", weight=req.weight
            ))

    # Bonus: CV có nhưng JD không yêu cầu
    jd_normalized = {_matcher.normalize_skill(r.skill) for r in jd.required_skills}
    jd_normalized |= {_matcher.normalize_skill(s) for s in jd.preferred_skills}
    bonus = [s for s in cv.skills if _matcher.normalize_skill(s) not in jd_normalized][:8]

    rate = round(matched_weight / total_weight * 100, 1) if total_weight > 0 else 100.0

    return {
        "skill_details":    skill_details,
        "missing_must_have": missing_must,
        "missing_preferred": missing_pref,
        "bonus_skills":      bonus,
        "skill_match_rate":  rate,
    }


# ---------------------------------------------------------------------------
# Step 2 — Experience analysis
# ---------------------------------------------------------------------------

def _analyze_experience(cv: ParsedCV, jd: ParsedJD) -> dict:
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
# Step 4 — Seniority analysis
# ---------------------------------------------------------------------------

_LEVEL_LABELS = {0: "Intern", 1: "Junior/Fresher", 2: "Mid-level", 3: "Senior/Lead", 4: "Principal/Architect"}


def _analyze_seniority(cv: ParsedCV, jd: ParsedJD) -> dict:
    if not jd.title:
        return {"match": "unknown", "detail": ""}

    jd_level = _detect_level(jd.title)
    cv_role  = cv.current_role or (cv.work_experience[0].role if cv.work_experience else "")

    if not cv_role:
        return {"match": "unknown", "detail": "Không xác định được role hiện tại của candidate"}

    cv_level = _detect_level(cv_role)
    diff     = cv_level - jd_level
    jd_label = _LEVEL_LABELS.get(jd_level, "Unknown")
    cv_label = _LEVEL_LABELS.get(cv_level, "Unknown")

    if diff == 0:
        return {"match": "match",           "detail": f"Candidate ở cấp {cv_label}, phù hợp với JD yêu cầu {jd_label}"}
    if diff > 0:
        return {"match": "over_qualified",  "detail": f"Candidate ở cấp {cv_label}, JD chỉ yêu cầu {jd_label}"}
    return     {"match": "under_qualified", "detail": f"Candidate ở cấp {cv_label}, JD yêu cầu {jd_label}"}


# ---------------------------------------------------------------------------
# Step 5 — LLM narrative (1 call)
# ---------------------------------------------------------------------------

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
Kỹ năng thêm (bonus)       : {bonus}
Kinh nghiệm       : {exp_detail}
Học vấn           : {edu_verdict}
Cấp bậc           : {seniority_detail}

=== YÊU CẦU OUTPUT ===
Viết 1 đoạn văn khoảng 10 câu. Đoạn văn phải:
- Mở đầu bằng tổng quan về ứng viên (background, định hướng nghề nghiệp)
- Đánh giá chi tiết mức độ phù hợp về kỹ năng kỹ thuật (nêu cụ thể từng nhóm skill matched/missing)
- Nhận xét về kinh nghiệm thực tế (project, work experience) so với yêu cầu JD
- Đánh giá học vấn và cấp bậc seniority
- Nêu rõ điểm mạnh nổi bật của ứng viên so với JD
- Nêu rõ những điểm còn thiếu hoặc cần cải thiện
- Đánh giá tiềm năng phát triển và khả năng onboard nhanh
- Kết luận bằng khuyến nghị hành động cụ thể cho HR (phỏng vấn ngay / cân nhắc thêm / không phù hợp, kèm lý do)
- Giọng văn tự nhiên, chuyên nghiệp, khách quan như nhận xét thực của chuyên viên tuyển dụng cấp cao

Sau đoạn văn, thêm 1 dòng riêng biệt:
RECOMMENDATION: strong_fit | possible_fit | weak_fit | poor_fit

Quy tắc chọn recommendation:
- strong_fit  : skill_match ≥ 80% VÀ đủ kinh nghiệm VÀ không thiếu must-have skill
- possible_fit: skill_match ≥ 60% VÀ thiếu tối đa 1 must-have skill
- weak_fit    : skill_match 40-60% HOẶC thiếu 2 must-have skill
- poor_fit    : skill_match < 40% HOẶC thiếu hơn 2 must-have skill
"""


async def _llm_narrative(cv: ParsedCV, jd: ParsedJD, analysis: dict) -> dict:
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
        bonus            = ", ".join(analysis["bonus_skills"]) if analysis["bonus_skills"] else "không có",
        exp_detail       = analysis["exp_detail"],
        edu_verdict      = edu_map.get(analysis["edu_verdict"], analysis["edu_verdict"]),
        seniority_detail = analysis["seniority_detail"],
    )

    raw_text = await call_llm_text(prompt, temperature=0.4, max_tokens=1200)

    # Tách narrative và recommendation từ raw text
    narrative   = raw_text
    rec         = "possible_fit"
    valid_recs  = {"strong_fit", "possible_fit", "weak_fit", "poor_fit"}

    if "RECOMMENDATION:" in raw_text:
        parts     = raw_text.split("RECOMMENDATION:")
        narrative = parts[0].strip()
        rec_raw   = parts[1].strip().lower().replace(" ", "_").split()[0]
        if rec_raw in valid_recs:
            rec = rec_raw

    return {"narrative": narrative, "recommendation": rec}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def evaluate_cv_for_job(cv: ParsedCV, jd: ParsedJD) -> CVJobEvaluation:
    """
    Evaluate how well a parsed CV fits a parsed JD.
    Returns structured qualitative report for HR.
    """
    skill_data   = _analyze_skills(cv, jd)
    exp_data     = _analyze_experience(cv, jd)
    edu_verdict  = _analyze_education(cv, jd)
    sen_data     = _analyze_seniority(cv, jd)

    # Bundle all for LLM context
    combined = {
        **skill_data,
        "exp_detail":      exp_data["detail"],
        "edu_verdict":     edu_verdict,
        "seniority_detail": sen_data["detail"],
    }

    narrative = await _llm_narrative(cv, jd, combined)

    valid_recs = {"strong_fit", "possible_fit", "weak_fit", "poor_fit"}
    rec = narrative.get("recommendation", "").strip().lower().replace(" ", "_")
    if rec not in valid_recs:
        rec = "possible_fit"

    return CVJobEvaluation(
        skill_details      = skill_data["skill_details"],
        missing_must_have  = skill_data["missing_must_have"],
        missing_preferred  = skill_data["missing_preferred"],
        bonus_skills       = skill_data["bonus_skills"],
        skill_match_rate   = skill_data["skill_match_rate"],

        experience_verdict = exp_data["verdict"],
        experience_detail  = exp_data["detail"],

        education_verdict  = edu_verdict,

        seniority_match    = sen_data["match"],
        seniority_detail   = sen_data["detail"],

        narrative          = narrative.get("narrative", ""),
        recommendation     = rec,
    )
