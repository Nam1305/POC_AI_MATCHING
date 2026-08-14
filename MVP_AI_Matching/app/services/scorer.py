"""
5-Dimension Scoring Engine (Bộ máy chấm điểm 5 chiều) — thuần Python +
numpy, KHÔNG gọi LLM.

Đây là bước cuối cùng trong pipeline so khớp CV-JD: nhận vào CV/JD đã được
parse có cấu trúc (từ parser.py) cùng embedding của chúng (từ embedder.py),
rồi tính ra 1 điểm số tổng hợp 0-100 dựa trên 5 chiều (dimension) độc lập:

D1 Semantic   : cosine_sim(cv_embedding, jd_embedding), normalize về 0–1
D2 Skills     : so khớp trọng số kỹ năng (weighted skill overlap), có hỗ
                trợ alias/suy luận (implied)/gần đúng (fuzzy)/cùng nhóm
                (category)
D3 Experience : tỷ lệ số năm kinh nghiệm (cv_years / jd_min_years), chặn
                trần ở 1.0 — không đánh giá độ liên quan lĩnh vực (D1/D2
                đã đảm nhiệm phần đó)
D4 Education  : cv_degree_level / jd_required_degree_level, chặn trần ở 1.0
D5 Location   : ước tính thời gian di chuyển (route OSRM dựa trên lat/lng
                đã geocode lúc parse) × mức độ phù hợp hình thức làm việc

final_score = Σ(Di × Wi) × 100   (Wi là trọng số từng chiều, cấu hình trong settings)
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from app.config import settings
from app.schemas import ParsedCV, ParsedJD
from app.services import location_service
from app.services.skill_matcher import SkillMatcher, _skill_matcher


# ---------------------------------------------------------------------------
# D1: Semantic — điểm ngữ nghĩa dựa trên cosine similarity giữa 2 embedding
# ---------------------------------------------------------------------------

def cosine_sim(v1: list[float], v2: list[float]) -> float:
    """Tính cosine similarity giữa 2 vector. Trả về [-1, 1] (thường nằm trong [0, 1] với văn bản)."""
    a, b = np.asarray(v1, dtype=np.float32), np.asarray(v2, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


def normalize_cosine(
    raw: float,
    min_val: float = settings.cosine_min,
    max_val: float = settings.cosine_max,
) -> float:
    """
    Kéo giãn (stretch) khoảng [min_val, max_val] → [0, 1] để điểm D1 tận
    dụng hết toàn bộ thang điểm. min_val/max_val mặc định lấy từ
    settings.cosine_min / settings.cosine_max (env: COSINE_MIN / COSINE_MAX,
    xem app/config.py).
    """
    return max(0.0, min((raw - min_val) / (max_val - min_val), 1.0))


# ---------------------------------------------------------------------------
# D2: Skills — weighted skill overlap, dùng SkillMatcher (skill_matcher.py)
# Điểm kỹ năng — tổng hợp có trọng số, logic so khớp nằm ở skill_matcher.py
# ---------------------------------------------------------------------------

def score_skills(
    cv: ParsedCV,
    jd: ParsedJD,
    matcher: Optional[SkillMatcher] = None,
) -> float:
    """
    So khớp kỹ năng theo pipeline 3 tầng (skill_matcher.py), scoring NHỊ PHÂN:
    mỗi requirement (OR-group — thỏa 1 alternative là đủ) hoặc matched (full
    trọng số) hoặc missing (0), không còn partial credit fuzzy/category:
      Layer 0 — direct match trên output LLM thô
      Layer 1 — identity qua skill_data.json (canonical hóa 2 phía)
      Layer 2 — entailment qua skill_implies.json (đã flatten bắc cầu sẵn)
      + tầng phụ: trình độ ngôn ngữ (JLPT/TOEIC...) so theo thứ bậc ordinal

    Tính trên CẢ 3 tier skill của JD (required / preferred / nice_to_have) theo
    trọng số giảm dần của từng tier — xem SkillMatcher.evaluate_tiers. Thiếu 1
    skill preferred/nice_to_have vẫn kéo điểm xuống, nhưng nhẹ hơn thiếu 1
    skill bắt buộc. JD không nêu skill nào ở cả 3 tier → 1.0 (neutral, cùng
    quy tắc "JD không yêu cầu → không có gì để thiếu" như D3/D4).
    """
    matcher = matcher or _skill_matcher

    ctx = matcher.build_cv_context(cv)
    results = matcher.evaluate_tiers(jd, ctx)

    total_w = sum(r.weight for r in results)
    if total_w <= 0:
        return 1.0

    matched_w = sum(r.weight * r.match.credit for r in results)

    return matched_w / total_w


# ---------------------------------------------------------------------------
# D3: Experience — years ratio
# Điểm kinh nghiệm — tỷ lệ số năm kinh nghiệm so với yêu cầu JD
# ---------------------------------------------------------------------------

def score_experience(cv: ParsedCV, jd: ParsedJD) -> float:
    """
    D3 = min(cv_years / jd_min_years, 1.0). Không JD yêu cầu → 1.0 (neutral).

    Chỉ đo SỐ LƯỢNG năm kinh nghiệm; việc năm kinh nghiệm đó có đúng lĩnh
    vực/kỹ năng hay không đã do D1 (semantic) và D2 (skills) đảm nhiệm —
    tránh D3 đếm trùng cùng một tín hiệu "liên quan" theo cách khác.
    """
    if not jd.min_experience_years:
        return 1.0
    cv_years = cv.total_exp_months / 12.0
    return min(cv_years / jd.min_experience_years, 1.0)


# ---------------------------------------------------------------------------
# D4: Education — điểm học vấn
# ---------------------------------------------------------------------------

def score_education(cv: ParsedCV, jd: ParsedJD) -> float:
    """
    Tỷ lệ cv_degree_level / jd_required_degree_level, chặn trần ở 1.0
    (bằng cấp cao hơn yêu cầu vẫn chỉ được tối đa điểm tuyệt đối, không
    được cộng thêm). Nếu JD không yêu cầu bằng cấp cụ thể → 1.0. Nếu CV
    không có thông tin bằng cấp → 0.5 (điểm trung lập, không phạt nặng vì
    thiếu dữ liệu).
    """
    jd_level = jd.required_degree_level
    if not jd_level:
        return 1.0
    cv_level = cv.highest_degree_level
    if not cv_level:
        return 0.5
    return min(cv_level / jd_level, 1.0)


# ---------------------------------------------------------------------------
# D5: Location + Work Mode — driving-time estimate × work-mode compatibility
# Điểm vị trí + hình thức làm việc — ước tính thời gian lái xe × mức độ phù
# hợp hình thức làm việc (onsite/hybrid/remote)
# ---------------------------------------------------------------------------

_ROUTE_RETRY_DELAY_SECONDS = 0.5


def score_location(parsed_jd: ParsedJD, parsed_cv: ParsedCV) -> float:
    """
    D5 thay thế cho cách so khớp bằng từ khóa (keyword) trước đây. Công thức:
      1. JD là remote                          → 1.0
      2. CV nói rõ sẵn sàng chuyển chỗ ở (relocate) → 1.0
      3. CV không có raw_address (chỉ có city hoặc không có gì, nên không
         geocode được — xem parser.parse_cv):
           - city JD trùng city CV              → 0.5 (trung lập, cùng thành
             phố nhưng không biết khoảng cách cụ thể trong thành phố)
           - city JD khác city CV, hoặc CV không có cả city → 0.0 (không
             cùng thành phố, coi như không phù hợp về vị trí)
      4. Thiếu lat/lng dù có raw_address (geocode lúc parse bị lỗi) → 0.5
         (điểm trung lập, không phạt vì thiếu dữ liệu)
      5. t = số phút lái xe qua route OSRM; nếu lỗi thì thử lại 1 lần sau
         0.5s; nếu vẫn lỗi → 0.5 (cùng quy tắc trung lập như thiếu lat/lng —
         không tính fallback theo khoảng cách đường chim bay)
      6. T_max = 45 phút (onsite) hoặc 75 phút (hybrid)
      7. S_loc = max(0, 1 - t / T_max)
      trả về round(S_loc, 3)
    """
    work_mode = parsed_jd.work_location.work_mode
    if work_mode == "remote":
        return 1.0

    if parsed_cv.candidate_location.willing_to_relocate:
        return 1.0

    jd_loc, cv_loc = parsed_jd.work_location, parsed_cv.candidate_location

    if not cv_loc.raw_address:
        if not cv_loc.city:
            return 0.5  # thiếu dữ liệu hoàn toàn, trung lập
        return 0.5 if cv_loc.city == jd_loc.city else 0.0

    if jd_loc.lat is None or jd_loc.lng is None or cv_loc.lat is None or cv_loc.lng is None:
        return 0.5

    jd_coord = {"lat": jd_loc.lat, "lng": jd_loc.lng}
    cv_coord = {"lat": cv_loc.lat, "lng": cv_loc.lng}

    route = location_service.get_route(cv_coord, jd_coord)
    if route is None:
        print("score_location: get_route() failed, retrying once after 0.5s")
        time.sleep(_ROUTE_RETRY_DELAY_SECONDS)
        route = location_service.get_route(cv_coord, jd_coord)

    if route is None:
        print("score_location: get_route() failed again after retry, returning neutral 0.5")
        return 0.5

    t = route["duration_min"]

    t_max = 45.0 if work_mode == "onsite" else 75.0
    s_loc = max(0.0, 1 - t / t_max)

    return round(s_loc, 3)


# ---------------------------------------------------------------------------
# Aggregate — calculate_score
# Tổng hợp — hàm chính tính ra điểm cuối cùng từ 5 chiều
# ---------------------------------------------------------------------------

def calculate_score(
    parsed_cv:    ParsedCV,
    parsed_jd:    ParsedJD,
    cv_embedding: list[float] | None,
    jd_embedding: list[float] | None,
    cv_raw_text:  str = "",
    weights:      dict[str, float] | None = None,
    cosine_min:   float | None = None,
    cosine_max:   float | None = None,
) -> dict:
    """
    Tính toàn bộ 5 chiều (D1-D5) + điểm tổng hợp cuối cùng (0-100), có trọng
    số theo cấu hình.

    Nếu không truyền `weights`, dùng settings.default_weights; tương tự với
    cosine_min/cosine_max dùng để normalize D1.

    Trả về dict {"final_score": điểm tổng 0-100 (làm tròn 1 chữ số thập
    phân), "scores": {tên chiều: điểm 0-100 của chiều đó}}.
    """
    w = weights or settings.default_weights
    cosine_min = settings.cosine_min if cosine_min is None else cosine_min
    cosine_max = settings.cosine_max if cosine_max is None else cosine_max
    if not cv_raw_text:
        cv_raw_text = parsed_cv.build_embed_text()

    dims = {}
    if cv_embedding and jd_embedding:
        dims["semantic"] = normalize_cosine(cosine_sim(cv_embedding, jd_embedding), cosine_min, cosine_max)
    else:
        dims["semantic"] = 0.5  # thiếu embedding → neutral, nhất quán với quy tắc "thiếu dữ liệu → 0.5" ở D4/D5

    dims.update({
        "skills":     score_skills(parsed_cv, parsed_jd),
        "experience": score_experience(parsed_cv, parsed_jd),
        "education":  score_education(parsed_cv, parsed_jd),
        "location":   score_location(parsed_jd, parsed_cv),
    })

    final = 100 * sum(value * w.get(name, 0.0) for name, value in dims.items())

    return {
        "final_score": round(final, 1),
        "scores":      {name: round(value * 100, 1) for name, value in dims.items()},
    }
