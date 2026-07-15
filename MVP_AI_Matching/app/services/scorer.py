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

import re
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


def normalize_cosine(raw: float, min_val: float = 0.55, max_val: float = 0.90) -> float:
    """
    Kéo giãn (stretch) khoảng [min_val, max_val] → [0, 1] để điểm D1 tận
    dụng hết toàn bộ thang điểm. Đã hiệu chỉnh (calibrate) riêng cho model
    gemini-embedding-001: sàn ~0.55 (2 lĩnh vực không liên quan), trần ~0.90
    (cùng 1 stack công nghệ).
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
    So khớp kỹ năng theo từng bậc (tiered), mỗi requirement được thỏa mãn
    bởi bất kỳ lựa chọn thay thế nào trong OR-group của nó:
      1. Chuẩn hóa kỹ năng CV + JD qua bảng alias
      2. Khớp chính xác     → tính đủ trọng số
      3. Khớp suy luận      → tính đủ trọng số (ví dụ CV có "react" → JD
         cần "javascript" thì coi như đã đảm bảo có, theo dữ liệu
         IMPLIES / Wikidata P277)
      4. Khớp gần đúng (fuzzy) → 0.9 × trọng số
      5. Khớp cùng nhóm lĩnh vực (category) → 0.3–0.5 × trọng số
    """
    if not jd.required_skills:
        return 1.0
    matcher = matcher or _skill_matcher

    cv_skills, cv_skills_expanded = matcher.normalized_cv_skills(cv)

    total_w = sum(s.weight for s in jd.required_skills)
    matched_w = 0.0

    for req in jd.required_skills:
        _, credit = matcher.evaluate_group(req, cv_skills, cv_skills_expanded)
        matched_w += req.weight * credit

    return matched_w / total_w if total_w > 0 else 0.0


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
      3. Thiếu lat/lng ở 1 trong 2 bên (việc geocode đã chạy lúc parse —
         xem parser.parse_jd/parse_cv — và bị lỗi hoặc không có địa chỉ để
         geocode) → 0.5 (điểm trung lập, không phạt vì thiếu dữ liệu)
      4. t = số phút lái xe qua route OSRM; nếu lỗi thì thử lại 1 lần sau
         0.5s; nếu vẫn lỗi → 0.5 (cùng quy tắc trung lập như thiếu lat/lng —
         không tính fallback theo khoảng cách đường chim bay)
      5. T_max = 45 phút (onsite) hoặc 75 phút (hybrid)
      6. S_loc = max(0, 1 - t / T_max)
      7. M = hệ số phù hợp hình thức làm việc (xem bảng bên dưới trong code)
      trả về round(S_loc * M, 3)
    """
    work_mode = parsed_jd.work_location.work_mode
    if work_mode == "remote":
        return 1.0

    if parsed_cv.candidate_location.willing_to_relocate:
        return 1.0

    jd_loc, cv_loc = parsed_jd.work_location, parsed_cv.candidate_location
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

    cv_pref = parsed_cv.candidate_location.work_mode_preference
    if work_mode == "onsite":
        m = 0.3 if cv_pref == "remote" else 1.0
    else:  # hybrid
        if cv_pref == "onsite":
            m = 0.7
        elif cv_pref == "remote":
            m = 0.3
        else:
            m = 1.0

    return round(s_loc * m, 3)


# ---------------------------------------------------------------------------
# D5 (deprecated) — Keywords: exact / word-boundary / multi-word
# Cách chấm D5 cũ bằng từ khóa — ĐÃ NGƯNG DÙNG
#
# Superseded by score_location() above. Kept unused, not deleted, in case of
# rollback. Not called anywhere in calculate_score() / calculate_score_with_rules().
#
# Đã được thay thế bởi score_location() ở trên. Vẫn giữ lại (không xóa)
# phòng khi cần rollback. Không được gọi ở bất kỳ đâu trong
# calculate_score() / calculate_score_with_rules().
# ---------------------------------------------------------------------------

def _clean_text_for_match(text: str) -> str:
    """Lowercase văn bản và thay mọi ký tự không phải chữ/số/khoảng trắng bằng khoảng trắng, chuẩn bị cho so khớp từ khóa."""
    return re.sub(r"[^\w\s]", " ", text.lower())


def score_keywords(cv_raw_text: str, jd: ParsedJD) -> float:
    """
    Điểm cho từng từ khóa (keyword):
      - khớp chuỗi con hoặc khớp theo ranh giới từ (word-boundary) → 1.0
      - cụm nhiều từ, tất cả các từ con đều xuất hiện → 0.7
      - còn lại → 0.0
    Điểm cuối = trung bình cộng điểm của tất cả từ khóa.
    """
    if not jd.keywords:
        return 1.0

    text_cleaned = _clean_text_for_match(cv_raw_text)

    keyword_scores: list[float] = []
    for kw in jd.keywords:
        if not kw or not kw.strip():
            continue
        kw_clean = _clean_text_for_match(kw).strip()
        if not kw_clean:
            continue

        if kw_clean in text_cleaned:
            keyword_scores.append(1.0)
            continue

        try:
            if re.search(rf"\b{re.escape(kw_clean)}\b", text_cleaned):
                keyword_scores.append(1.0)
                continue
        except re.error:
            pass

        words = kw_clean.split()
        if len(words) > 1 and all(
            re.search(rf"\b{re.escape(w)}\b", text_cleaned) for w in words
        ):
            keyword_scores.append(0.7)
            continue

        keyword_scores.append(0.0)

    if not keyword_scores:
        return 1.0
    return sum(keyword_scores) / len(keyword_scores)


# ---------------------------------------------------------------------------
# Seniority detection — shared with the evaluator's seniority analysis
# Nhận diện cấp bậc (seniority) — dùng chung với phần phân tích seniority
# trong evaluator.py, đảm bảo 2 nơi luôn tính ra kết quả nhất quán.
# ---------------------------------------------------------------------------

# Explicit seniority words. Generic role nouns (developer/engineer/...) carry
# no seniority signal on their own, so a title with none of these defaults to
# mid-level (2). Listing "senior" before matching means "Junior Developer"
# reads as Junior — not Mid — because the seniority word wins over the role noun.
_LEVEL_KEYWORDS: list[tuple[str, int]] = [
    ("intern",    0),
    ("fresher",   1),
    ("junior",    1),
    ("entry",     1),
    ("mid",       2),
    ("middle",    2),
    ("senior",    3),
    ("lead",      3),
    ("manager",   3),
    ("staff",     4),
    ("principal", 4),
    ("architect", 4),
    ("director",  4),
]


def _explicit_title_level(title: str) -> Optional[int]:
    """Xác định cấp bậc từ 1 từ khóa tường minh trong title, hoặc None nếu title không chứa từ khóa cấp bậc nào (ví dụ 'Software Engineer' trơn)."""
    if not title:
        return None
    t = title.lower()
    levels = [lvl for kw, lvl in _LEVEL_KEYWORDS if kw in t]
    return max(levels) if levels else None


def _detect_level(title: str) -> int:
    """Cấp bậc (0–4) suy ra từ 1 job title. Mặc định là mid-level (2) nếu không có từ khóa cấp bậc rõ ràng."""
    lvl = _explicit_title_level(title)
    return lvl if lvl is not None else 2


def jd_seniority_level(jd: ParsedJD) -> int:
    """
    Cấp bậc thực sự mà JD đang tuyển. Từ khóa tường minh trong title được
    ưu tiên trước ('Senior Engineer' → 3); nếu không có, suy ra từ số năm
    kinh nghiệm yêu cầu — vì một vị trí mở cho sinh viên mới ra trường (0
    năm yêu cầu) là entry-level thực sự, KHÔNG nên mặc định về mid-level
    như khi chỉ dựa vào title trơn.
    """
    explicit = _explicit_title_level(jd.title)
    if explicit is not None:
        return explicit
    yrs = jd.min_experience_years
    if yrs <= 0:   # zero / unspecified years, no seniority word → entry-level
        return 0
    if yrs <= 2:
        return 1
    if yrs <= 5:
        return 2
    if yrs <= 8:
        return 3
    return 4


# ---------------------------------------------------------------------------
# Aggregate — calculate_score
# Tổng hợp — hàm chính tính ra điểm cuối cùng từ 5 chiều
# ---------------------------------------------------------------------------

def calculate_score(
    parsed_cv:    ParsedCV,
    parsed_jd:    ParsedJD,
    cv_embedding: list[float],
    jd_embedding: list[float],
    cv_raw_text:  str = "",
    weights:      dict[str, float] | None = None,
    cosine_min:   float | None = None,
    cosine_max:   float | None = None,
) -> dict:
    """
    Tính toàn bộ 5 chiều (D1-D5) + điểm tổng hợp cuối cùng (0-100), có trọng
    số theo cấu hình.

    Nếu không truyền `weights`, dùng settings.default_weights; tương tự với
    cosine_min/cosine_max dùng để normalize D1. Nếu không truyền
    cv_raw_text, tự build từ parsed_cv (dùng để tính score_keywords nếu cần).

    Trả về dict {"final_score": điểm tổng 0-100 (làm tròn 1 chữ số thập
    phân), "scores": {tên chiều: điểm 0-100 của chiều đó}}.
    """
    w = weights or settings.default_weights
    cosine_min = settings.cosine_min if cosine_min is None else cosine_min
    cosine_max = settings.cosine_max if cosine_max is None else cosine_max
    if not cv_raw_text:
        cv_raw_text = parsed_cv.build_embed_text()

    dims = {
        "semantic":   normalize_cosine(cosine_sim(cv_embedding, jd_embedding), cosine_min, cosine_max),
        "skills":     score_skills(parsed_cv, parsed_jd),
        "experience": score_experience(parsed_cv, parsed_jd),
        "education":  score_education(parsed_cv, parsed_jd),
        "location":   score_location(parsed_jd, parsed_cv),
    }

    final = 100 * sum(value * w.get(name, 0.0) for name, value in dims.items())

    return {
        "final_score": round(final, 1),
        "scores":      {name: round(value * 100, 1) for name, value in dims.items()},
    }
