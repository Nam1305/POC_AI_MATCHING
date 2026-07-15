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
D3 Experience : tỷ lệ số năm kinh nghiệm cơ bản + các hệ số điều chỉnh theo
                độ liên quan/độ mới/over-qualification
D4 Education  : cv_degree_level / jd_required_degree_level, chặn trần ở 1.0
D5 Location   : ước tính thời gian di chuyển (route OSRM dựa trên lat/lng
                đã geocode lúc parse) × mức độ phù hợp hình thức làm việc

final_score = Σ(Di × Wi) × 100   (Wi là trọng số từng chiều, cấu hình trong settings)
"""

from __future__ import annotations

import datetime
import difflib
import re
import time
from typing import Optional

import numpy as np

from app.config import settings
from app.schemas import ParsedCV, ParsedJD, parse_month
from app.services import location_service
from app.services.skill_data import ALIASES, CATEGORIES, IMPLIES_ALL


# ---------------------------------------------------------------------------
# SkillMatcher — alias normalization, fuzzy match, category fallback
# Lớp chịu trách nhiệm toàn bộ logic so khớp kỹ năng (dùng cho cả D2 ở đây
# lẫn evaluator.py khi phân tích chi tiết cho HR).
# ---------------------------------------------------------------------------

class SkillMatcher:
    """
    Chuẩn hóa các biến thể cách viết của cùng 1 kỹ năng, so khớp gần đúng
    (fuzzy) khi viết sai chính tả, và cho điểm một phần (partial credit)
    khi 2 kỹ năng cùng thuộc 1 nhóm lĩnh vực rộng (category) dù không khớp
    chính xác.
    """

    # Data tables live in skill_data.py; bound here as class attributes so
    # `matcher.ALIASES` / `SkillMatcher.CATEGORIES` keep working as before.
    ALIASES = ALIASES
    CATEGORIES = CATEGORIES

    def normalize_skill(self, skill: str) -> str:
        """
        Chuẩn hóa 1 chuỗi kỹ năng thô về tên kỹ năng chuẩn (canonical) qua
        bảng ALIASES. Nếu không có trong bảng, thử bỏ phần trong ngoặc đơn
        (ví dụ "JavaScript (ES6+)" → "javascript") rồi tra lại ALIASES;
        nếu vẫn không khớp, trả về chính chuỗi đã lowercase/strip.
        """
        if not skill:
            return ""
        key = skill.lower().strip()
        if key in self.ALIASES:
            return self.ALIASES[key]
        # Strip parenthetical suffix: "JavaScript (ES6+)" → "javascript"
        stripped = re.sub(r'\s*\([^)]*\)', '', key).strip()
        if stripped and stripped != key:
            return self.ALIASES.get(stripped, stripped)
        return key

    def fuzzy_match(self, skill1: str, skill2: str, threshold: float = 0.85) -> bool:
        """
        So khớp gần đúng (fuzzy) 2 chuỗi kỹ năng bằng tỷ lệ tương đồng ký
        tự (difflib.SequenceMatcher). Trả về True nếu tỷ lệ >= threshold
        (mặc định 0.85) — dùng để bắt các trường hợp viết khác 1 chút
        (ví dụ lỗi chính tả) mà không khớp qua ALIASES.
        """
        if not skill1 or not skill2:
            return False
        ratio = difflib.SequenceMatcher(None, skill1, skill2).ratio()
        return ratio >= threshold

    def _category_of(self, skill: str) -> Optional[str]:
        """Trả về tên nhóm lĩnh vực (trong CATEGORIES) mà `skill` thuộc về, hoặc None nếu không thuộc nhóm nào."""
        for cat, members in self.CATEGORIES.items():
            if skill in members:
                return cat
        return None

    def category_match(self, cv_skills: set[str], jd_skill: str) -> float:
        """
        Cho điểm một phần (partial credit) khi kỹ năng JD yêu cầu thuộc 1
        nhóm lĩnh vực mà CV đã có kỹ năng khác cùng nhóm đó bao phủ. Điểm
        tăng dần theo số lượng kỹ năng cùng nhóm mà CV có.
        """
        cat = self._category_of(jd_skill)
        if not cat:
            return 0.0
        overlap = len(cv_skills & self.CATEGORIES[cat])
        if overlap == 0:
            return 0.0
        # 1 overlap → 0.3, 2 → 0.4, ≥3 → 0.5
        return min(0.3 + 0.1 * (overlap - 1), 0.5)

    def implied_skills(self, skill: str) -> set[str]:
        """
        Bao đóng bắc cầu một chiều (one-way transitive closure) trên đồ thị
        IMPLIES (ví dụ: nextjs → react → javascript — biết nextjs thì suy
        ra biết cả react lẫn javascript).
        "Biết X thì chắc chắn biết Y" — dữ liệu lấy từ Wikidata P277, không
        phải suy đoán.
        """
        seen: set[str] = set()
        stack = [skill]
        while stack:
            for nxt in IMPLIES_ALL.get(stack.pop(), ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen

    def expand_implied(self, skills: set[str]) -> set[str]:
        """Thêm vào tập skills mọi kỹ năng được đảm bảo (suy luận) một cách logic từ các kỹ năng đã có."""
        expanded = set(skills)
        for s in skills:
            expanded |= self.implied_skills(s)
        return expanded

    def normalized_cv_skills(self, cv: ParsedCV) -> tuple[set[str], set[str]]:
        """Trả về (tập kỹ năng CV đã chuẩn hóa, tập đó được mở rộng thêm các kỹ năng suy luận được)."""
        cv_skills = {self.normalize_skill(s) for s in _collect_cv_skills(cv) if s}
        return cv_skills, self.expand_implied(cv_skills)

    def is_fuzzy(self, jd_skill: str, cv_skills: set[str]) -> bool:
        """True nếu có bất kỳ kỹ năng nào trong CV so khớp gần đúng (fuzzy) với kỹ năng JD (đã chuẩn hóa)."""
        return any(self.fuzzy_match(jd_skill, cv_s) for cv_s in cv_skills)

    # -- OR-group (alternatives) aware matching --------------------------------
    #
    # A RequiredSkill may carry `alternatives`: the requirement is satisfied by
    # ANY of {skill} ∪ alternatives. All group logic funnels through here so the
    # scorer and evaluator agree.

    # status priority for picking the best alternative in a group
    _STATUS_RANK = {"matched": 2, "matched_implied": 1, "missing": 0}

    def group_names(self, req) -> list[str]:
        """Danh sách tên kỹ năng đã chuẩn hóa trong 1 nhóm OR (requirement + alternatives)."""
        return [self.normalize_skill(n) for n in [req.skill, *req.alternatives] if n]

    def group_label(self, req) -> str:
        """Nhãn hiển thị dễ đọc cho 1 requirement — dạng 'A / B / C' cho các nhóm OR (OR-group)."""
        names = [n for n in [req.skill, *req.alternatives] if n]
        return " / ".join(dict.fromkeys(names))

    def evaluate_skill(self, jd_norm: str, cv_skills: set[str],
                       cv_skills_expanded: set[str]) -> tuple[str, float]:
        """
        Phân loại 1 kỹ năng JD (đã chuẩn hóa) so với CV.
        Trả về (status, credit) với status ∈ matched|matched_implied|missing
        và credit ∈ [0,1] tương ứng các bậc trong score_skills (khớp chính
        xác/suy luận = 1.0, khớp gần đúng = 0.9, còn lại là điểm một phần
        theo nhóm lĩnh vực).
        """
        if jd_norm in cv_skills:
            return "matched", 1.0
        if jd_norm in cv_skills_expanded:
            return "matched_implied", 1.0
        # Language proficiency: when the JD asks for a standardized level, credit
        # the CV only via same-framework ordinal comparison (an equal-or-higher
        # level matches; a lower one does not), never fuzzy on the level code.
        prof = self._match_proficiency(jd_norm, cv_skills)
        if prof is not None:
            return prof
        if self.is_fuzzy(jd_norm, cv_skills):
            return "matched", 0.9
        return "missing", self.category_match(cv_skills, jd_norm)

    def _match_proficiency(self, jd_norm: str,
                           cv_skills: set[str]) -> Optional[tuple[str, float]]:
        """
        So khớp trình độ ngôn ngữ theo thứ bậc (ordinal). Trả về verdict
        (status, credit) khi kỹ năng JD yêu cầu là 1 chứng chỉ trình độ
        chuẩn hóa (ví dụ JLPT, TOEIC...) VÀ CV có chứng chỉ cùng hệ khung
        (framework) đó; ngược lại trả về None (để nhường cho fuzzy/category
        xử lý tiếp).
        """
        req = _parse_proficiency(jd_norm)
        if req is None:
            return None
        framework, req_rank = req
        best: Optional[float] = None
        for cv_s in cv_skills:
            cp = _parse_proficiency(cv_s)
            if cp and cp[0] == framework:
                best = cp[1] if best is None else max(best, cp[1])
        if best is None:
            return None
        return ("matched", 1.0) if best >= req_rank else ("missing", 0.0)

    def evaluate_group(self, req, cv_skills: set[str],
                       cv_skills_expanded: set[str]) -> tuple[str, float]:
        """Trả về (status, credit) tốt nhất trong số mọi lựa chọn thay thế (alternative) của 1 requirement."""
        best: tuple[str, float] = ("missing", 0.0)
        for jd_norm in self.group_names(req):
            status, credit = self.evaluate_skill(jd_norm, cv_skills, cv_skills_expanded)
            if (self._STATUS_RANK[status], credit) > (self._STATUS_RANK[best[0]], best[1]):
                best = (status, credit)
        return best


# ---------------------------------------------------------------------------
# Language-proficiency frameworks — ordinal, language-agnostic
# Các hệ khung (framework) chứng chỉ trình độ ngôn ngữ — có thứ bậc, không
# phụ thuộc ngôn ngữ cụ thể.
# ---------------------------------------------------------------------------
#
# Standardized language certificates are ordered: a required level is satisfied
# by ANY equal-or-higher level in the SAME framework, for every language —
# JLPT (Japanese), HSK (Chinese), TOPIK (Korean), TOEIC/TOEFL/IELTS (English),
# CEFR (language-neutral). This replaces fuzzy-matching on level codes, which
# can't tell direction apart ("N4" looks 86% similar to "N3" yet is BELOW it).
#
# Các chứng chỉ ngôn ngữ chuẩn hóa được xếp theo thứ bậc: một mức yêu cầu
# được thỏa mãn bởi BẤT KỲ mức nào bằng hoặc cao hơn trong CÙNG 1 hệ khung,
# áp dụng cho mọi ngôn ngữ — JLPT (tiếng Nhật), HSK (tiếng Trung), TOPIK
# (tiếng Hàn), TOEIC/TOEFL/IELTS (tiếng Anh), CEFR (không phân biệt ngôn
# ngữ). Cách này thay thế cho so khớp gần đúng (fuzzy) trên mã trình độ —
# vốn không phân biệt được chiều hơn/kém (ví dụ "N4" giống 86% với "N3"
# nhưng thực chất THẤP HƠN).

_CEFR_RANK = {"a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6}

# (compiled pattern, framework, rank-from-match). Rank is monotonic within a
# framework: higher = more proficient. Order matters — first match wins.
_PROFICIENCY_PATTERNS: list[tuple[re.Pattern, str, "callable"]] = [
    (re.compile(r"\bjlpt\s*n\s*([1-5])\b"),          "jlpt",  lambda m: 6 - int(m.group(1))),  # N1 highest
    (re.compile(r"\bhsk\s*([1-9])\b"),               "hsk",   lambda m: float(m.group(1))),
    (re.compile(r"\btopik\s*([1-6])\b"),             "topik", lambda m: float(m.group(1))),
    (re.compile(r"\bielts\s*([0-9](?:\.[05])?)\b"),  "ielts", lambda m: float(m.group(1))),
    (re.compile(r"\btoeic\s*([0-9]{2,3})\b"),        "toeic", lambda m: float(m.group(1))),
    (re.compile(r"\btoefl(?:\s*ibt)?\s*([0-9]{2,3})\b"), "toefl", lambda m: float(m.group(1))),
    (re.compile(r"\b([abc][12])\b"),                 "cefr",  lambda m: float(_CEFR_RANK[m.group(1)])),
]


def _parse_proficiency(token: str) -> Optional[tuple[str, float]]:
    """
    Trích ra (framework, rank) cho 1 token trình độ ngôn ngữ chuẩn hóa
    (ví dụ "JLPT N3", "TOEIC 835"), trả về None nếu token không khớp
    framework nào. Rank chỉ so sánh được trong CÙNG 1 framework (số càng
    cao càng giỏi).
    """
    t = token.lower()
    for pattern, framework, rank_of in _PROFICIENCY_PATTERNS:
        m = pattern.search(t)
        if m:
            return framework, rank_of(m)
    return None


_skill_matcher = SkillMatcher()


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
# D2: Skills — alias + fuzzy + category
# Điểm kỹ năng — so khớp qua alias, rồi gần đúng (fuzzy), rồi cùng nhóm (category)
# ---------------------------------------------------------------------------

# Separators inside a credential string: "Japanese - JLPT N3", "English: TOEIC 835".
_CREDENTIAL_SPLIT_RE = re.compile(r"[-–—:,/()]+")


def _expand_credential(text: str) -> set[str]:
    """
    Một mục ngôn ngữ/chứng chỉ thường mang theo trình độ như 1 sub-token,
    ví dụ "Japanese - JLPT N3". Trả về cả chuỗi nguyên bản LẪN các phần
    tách ra ("japanese", "jlpt n3") để 1 kỹ năng JD như "JLPT N3" có thể
    khớp chính xác với sub-token đó.
    """
    out: set[str] = set()
    whole = text.strip().lower()
    if not whole:
        return out
    out.add(whole)
    for part in _CREDENTIAL_SPLIT_RE.split(whole):
        part = part.strip()
        if part:
            out.add(part)
    return out


def _collect_cv_skills(cv: ParsedCV) -> set[str]:
    """
    Gộp toàn bộ kỹ năng từ cv.skills + work_experience.tech_stack +
    projects.tech_stack, cộng thêm languages/certifications (được tách
    thành sub-token để các chứng chỉ như "JLPT N3" nằm trong "Japanese -
    JLPT N3" cũng trở thành kỹ năng có thể so khớp được).
    """
    skills: set[str] = {s.lower() for s in cv.skills}
    for exp in cv.work_experience:
        skills.update(s.lower() for s in exp.tech_stack)
    for proj in cv.projects:
        skills.update(s.lower() for s in proj.tech_stack)
    for lang in cv.languages:
        skills |= _expand_credential(lang)
    for cert in cv.certifications:
        skills |= _expand_credential(cert)
    return skills


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
# D3: Experience — relevance + recency + over-qualification
# Điểm kinh nghiệm — tỷ lệ cơ bản + điều chỉnh theo độ liên quan/độ mới/over-qualification
# ---------------------------------------------------------------------------

def _months_since(dt: datetime.date) -> int:
    """Số tháng tròn tính từ ngày `dt` đến hôm nay."""
    today = datetime.date.today()
    return (today.year - dt.year) * 12 + (today.month - dt.month)


def _jd_domain_tokens(jd: ParsedJD) -> list[str]:
    """
    Suy ra các từ khóa gợi ý lĩnh vực (domain hints) từ title + keywords
    của JD. Chỉ lấy các từ đủ dài (>3 ký tự) để tránh nhiễu bởi các từ
    chung chung, ít mang thông tin.
    """
    tokens: set[str] = set()
    if jd.title:
        for t in re.findall(r"\w+", jd.title):
            if len(t) > 3:
                tokens.add(t.lower())
    for kw in jd.keywords or []:
        for t in re.findall(r"\w+", kw):
            if len(t) > 3:
                tokens.add(t.lower())
    return list(tokens)


def score_experience(cv: ParsedCV, jd: ParsedJD) -> float:
    """
    Điểm cơ bản: min(cv_years / jd_min_years, 1.0).

    Các hệ số điều chỉnh (modifier, kết quả cuối được chặn trong [0, 1]):
      + tối đa 0.20 nếu lịch sử làm việc trùng với các từ khóa lĩnh vực của JD
      + 0.10 nếu công việc gần nhất kết thúc < 3 tháng trước (hoặc đang làm)
      - 0.10 nếu công việc gần nhất kết thúc > 12 tháng trước
      - 0.05 nếu cv_years > 2 × jd_min_years (over-qualification — thừa kinh nghiệm)
    """
    if not jd.min_experience_years:
        return 1.0

    cv_years = cv.total_exp_months / 12.0
    base = min(cv_years / jd.min_experience_years, 1.0)
    modifiers = 0.0

    domain_tokens = _jd_domain_tokens(jd)
    if domain_tokens and cv.work_experience:
        relevant_months = 0
        for exp in cv.work_experience:
            haystack = " ".join(filter(None, [exp.role or "", exp.description or ""])).lower()
            if any(tok in haystack for tok in domain_tokens):
                relevant_months += (exp.months or 0)
        if relevant_months > 0:
            relevant_years = relevant_months / 12.0
            relevance_ratio = min(relevant_years / jd.min_experience_years, 1.0)
            modifiers += 0.20 * relevance_ratio

    if cv.work_experience:
        latest = cv.work_experience[0]
        if latest.is_current:
            modifiers += 0.10
        else:
            end_dt = parse_month(latest.end)
            if end_dt:
                months_ago = _months_since(end_dt)
                if months_ago < 3:
                    modifiers += 0.10
                elif months_ago > 12:
                    modifiers -= 0.10

    if cv_years > 2 * jd.min_experience_years:
        modifiers -= 0.05

    return max(0.0, min(base + modifiers, 1.0))


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
