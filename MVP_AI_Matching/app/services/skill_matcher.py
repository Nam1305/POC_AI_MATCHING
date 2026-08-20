"""
Skill Matching — pipeline 3 tầng (layer) dựa trên 2 file dữ liệu tĩnh, thay
cho cơ chế fuzzy/category cũ. Cho điểm NHỊ PHÂN: mỗi yêu cầu kỹ năng của JD
hoặc được thỏa (full credit) hoặc thiếu (0), không còn partial credit.

Ba tầng chạy TUẦN TỰ, mỗi tầng chỉ xét phần requirement CHƯA thỏa từ tầng
trước (ở đây gộp trong evaluate_group: mỗi requirement dừng ngay ở tầng sớm
nhất thỏa nó):

  Layer 0 — Direct match: so trực tiếp (lowercase+strip) output LLM của CV và
            JD, chưa cần canonicalize. Fast-path rẻ tiền cho các case hiển nhiên.
  Layer 1 — Identity qua skill_data.json: chuẩn hóa cả CV lẫn JD về tên chuẩn
            (canonical) rồi so exact. Bắc cầu giữa format Title-Case của LLM và
            format Stack Overflow tag (lowercase, space→hyphen) của skill_data.
  Layer 2 — Entailment qua skill_implies.json: "biết X thì biết Y". Dữ liệu đã
            được flatten theo bao đóng bắc cầu sẵn nên chỉ cần tra list trực
            tiếp, KHÔNG duyệt graph ở runtime.
  Layer 3 — Fuzzy fallback: SequenceMatcher (ngưỡng 0.85) trên output LLM thô,
            bắt biến thể chính tả/format nhỏ ("Postgresql" vs "PostgreSQL") mà 3
            tầng trên (exact + canonical + entailment) chưa thỏa. Đặt CUỐI vì
            đắt hơn và lỏng hơn — chỉ chạy khi các tầng chính xác đã trượt.

Ngoài 3 tầng còn 1 tầng phụ cho TRÌNH ĐỘ NGÔN NGỮ (JLPT/HSK/TOPIK/IELTS/
TOEIC/TOEFL/CEFR) — so theo thứ bậc (ordinal) trong cùng framework, vì các
chứng chỉ này không nằm trong skill_data/skill_implies và không thể so exact
(N2 thỏa yêu cầu N3 dù chuỗi khác nhau).

Tách riêng khỏi scorer.py để evaluator.py (tường thuật cho HR) tái sử dụng
được logic so khớp — score_skills() chỉ cần con số 0-1, evaluator cần evidence
chi tiết (matched_layer + matched_via) mà evaluate_all_skills() trả về.
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import NamedTuple, Optional

from app.schemas import ParsedCV


# ---------------------------------------------------------------------------
# Nạp dữ liệu tĩnh: skill_data.json (Layer 1) + skill_implies.json (Layer 2)
#
# skill_data.json : dict phẳng {tag_raw: canonical | null}. value=null nghĩa là
#   CHÍNH key đó đã là canonical (không có synonym trỏ vào), KHÔNG phải "bỏ qua".
# skill_implies.json : dict {skill_canonical: [list skill_canonical bị kéo theo]},
#   đã flatten bắc cầu sẵn — cả key lẫn value đều ở dạng canonical (SO tag style).
# ---------------------------------------------------------------------------

def _load_json(filename: str) -> dict:
    """
    Tra file dữ liệu ở app/data/ (đi cùng app/ nên được COPY vào Docker image),
    có fallback sang repo_root/data để tương thích layout cũ. Trả về dict rỗng
    chỉ khi thực sự không tìm thấy (để test/tooling không crash lúc import).
    """
    here = Path(__file__).resolve()
    for base in (here.parents[1], here.parents[2]):  # app/data, repo_root/data
        candidate = base / "data" / filename
        if candidate.is_file():
            with candidate.open(encoding="utf-8") as f:
                return json.load(f)
    return {}


SKILL_DATA: dict[str, Optional[str]] = _load_json("skill_data.json")
SKILL_IMPLIES: dict[str, list[str]] = _load_json("skill_implies.json")


# ---------------------------------------------------------------------------
# Chuẩn hóa format: bắc cầu giữa output LLM (Title Case, có space) và
# skill_data.json (Stack Overflow tag style: lowercase, space→hyphen).
# ---------------------------------------------------------------------------

def to_stackoverflow_format(skill: str) -> list[str]:
    """
    Trả về danh sách CÁC BIẾN THỂ hợp lý để tra vào skill_data.json, theo thứ
    tự ưu tiên (biến thể gần format SO nhất trước). Ví dụ:
      "ASP.NET Core" -> ["asp.net core", "asp.net-core", "asp.netcore", ...]
      "Node.js"      -> ["node.js", "nodejs", ...]
      "React Native" -> ["react native", "react-native", ...]
    Giữ nguyên dấu chấm (SO tag dùng dấu chấm: "asp.net-core", "node.js"); thử
    thêm biến thể bỏ dấu chấm để bắt "node.js" -> "nodejs". Danh sách được dedup
    giữ nguyên thứ tự; biến thể thừa (không có trong data) là vô hại vì
    resolve_canonical chỉ dừng ở biến thể ĐẦU TIÊN khớp.
    """
    base = skill.strip().lower()
    if not base:
        return []
    no_dot = base.replace(".", "")
    variants = [
        base,                       # "asp.net core", "node.js"
        base.replace(" ", "-"),     # "asp.net-core", "react-native"
        base.replace(" ", ""),      # "asp.netcore"
        no_dot,                     # "nodejs", "aspnet core"
        no_dot.replace(" ", "-"),   # "aspnet-core"
        no_dot.replace(" ", ""),    # "nodejs" (đã có), "aspnetcore"
    ]
    # dedup giữ thứ tự
    seen: set[str] = set()
    out: list[str] = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


# ---------------------------------------------------------------------------
# Layer 3 fuzzy fallback — bắt các sai lệch nhỏ về ký tự giữa output LLM của CV
# và JD ("Postgresql" vs "PostgreSQL", "Node JS" vs "Node.js") SAU khi 3 tầng
# chính xác (exact + canonical + entailment) đã trượt. Dùng difflib.Sequence-
# Matcher (ratio 0..1); ngưỡng cao (0.85) để tránh gộp nhầm các skill khác nhau
# nhưng gần giống ("N4" vs "N3", "Java" vs "JavaScript" đều dưới ngưỡng nên
# KHÔNG khớp ở đây).
# ---------------------------------------------------------------------------

_LAYER3_FUZZY_THRESHOLD = 0.85


def _fuzzy_best_match(name: str, candidates: set[str],
                      threshold: float = _LAYER3_FUZZY_THRESHOLD) -> Optional[str]:
    """
    Trả candidate có tỉ lệ tương đồng cao nhất với `name` nếu >= threshold, ngược
    lại None. So trên chuỗi đã lowercase/strip (caller đảm bảo). Ngưỡng mặc định
    0.85 — đủ chặt để chỉ bắt biến thể chính tả/format, không gộp skill khác nhau.
    """
    best_ratio = threshold
    best: Optional[str] = None
    for cand in candidates:
        ratio = SequenceMatcher(None, name, cand).ratio()
        if ratio >= best_ratio:
            best_ratio = ratio
            best = cand
    return best


def resolve_canonical(skill: str, skill_data: dict = SKILL_DATA) -> str:
    """
    Chuẩn hóa 1 kỹ năng về tên chuẩn (canonical) qua skill_data.json:
      - Thử từng biến thể (to_stackoverflow_format) cho tới khi tìm thấy 1 entry.
      - Nếu entry có value khác null -> trả value đó (canonical thật sự).
      - Nếu value là null -> CHÍNH key vừa tìm thấy đã là canonical -> trả key đó.
      - Không tìm thấy ở bất kỳ biến thể nào -> fallback về input đã lowercase/
        strip (coi như skill lạ, không có trong danh mục).
    """
    for variant in to_stackoverflow_format(skill):
        if variant in skill_data:
            value = skill_data[variant]
            return value if value is not None else variant
    return skill.strip().lower()


# ---------------------------------------------------------------------------
# Language-proficiency frameworks — ordinal, language-agnostic
# Các hệ khung chứng chỉ trình độ ngôn ngữ — có thứ bậc, không phụ thuộc ngôn
# ngữ cụ thể. Một mức yêu cầu được thỏa bởi BẤT KỲ mức nào bằng-hoặc-cao-hơn
# trong CÙNG framework (JLPT/HSK/TOPIK/IELTS/TOEIC/TOEFL/CEFR). Đây là tầng phụ
# nằm ngoài skill_data/skill_implies: "N4" giống 86% "N3" về ký tự nhưng thực
# chất THẤP HƠN, nên không thể so exact/identity mà phải so theo thứ bậc.
# ---------------------------------------------------------------------------

_CEFR_RANK = {"a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6}

# (compiled pattern, framework, rank-from-match). Rank đơn điệu trong 1
# framework: càng cao = càng giỏi. Thứ tự quan trọng — khớp đầu tiên thắng.
_PROFICIENCY_PATTERNS: list[tuple[re.Pattern, str, "callable"]] = [
    (re.compile(r"\bjlpt\s*n\s*([1-5])\b"),              "jlpt",  lambda m: 6 - int(m.group(1))),  # N1 highest
    (re.compile(r"\bhsk\s*([1-9])\b"),                   "hsk",   lambda m: float(m.group(1))),
    (re.compile(r"\btopik\s*([1-6])\b"),                 "topik", lambda m: float(m.group(1))),
    (re.compile(r"\bielts\s*([0-9](?:\.[05])?)\b"),      "ielts", lambda m: float(m.group(1))),
    (re.compile(r"\btoeic\s*([0-9]{2,3})\b"),            "toeic", lambda m: float(m.group(1))),
    (re.compile(r"\btoefl(?:\s*ibt)?\s*([0-9]{2,3})\b"), "toefl", lambda m: float(m.group(1))),
    (re.compile(r"\b([abc][12])\b"),                     "cefr",  lambda m: float(_CEFR_RANK[m.group(1)])),
]


def _parse_proficiency(token: str) -> Optional[tuple[str, float]]:
    """
    Trích (framework, rank) cho 1 token trình độ ngôn ngữ chuẩn hóa (ví dụ
    "JLPT N3", "TOEIC 835"), trả None nếu không khớp framework nào. Rank chỉ so
    sánh được trong CÙNG framework (số càng cao càng giỏi).
    """
    t = token.lower()
    for pattern, framework, rank_of in _PROFICIENCY_PATTERNS:
        m = pattern.search(t)
        if m:
            return framework, rank_of(m)
    return None


# ---------------------------------------------------------------------------
# _collect_cv_skills — gom skill thô từ CV (chưa canonicalize)
# ---------------------------------------------------------------------------

# Separators inside a credential string: "Japanese - JLPT N3", "English: TOEIC 835".
_CREDENTIAL_SPLIT_RE = re.compile(r"[-–—:,/()]+")


def _expand_credential(text: str) -> set[str]:
    """
    Một mục ngôn ngữ/chứng chỉ thường mang trình độ như 1 sub-token, ví dụ
    "Japanese - JLPT N3". Trả cả chuỗi nguyên bản LẪN các phần tách ra
    ("japanese", "jlpt n3") để 1 kỹ năng JD như "JLPT N3" khớp được sub-token đó.
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
    Gộp toàn bộ kỹ năng thô (đã lowercase) từ cv.skills + work_experience.
    tech_stack + projects.tech_stack, cộng languages/certifications (tách thành
    sub-token để chứng chỉ như "JLPT N3" trong "Japanese - JLPT N3" cũng trở
    thành kỹ năng so khớp được). Đây là input cho cả Layer 0 (so trực tiếp) lẫn
    Layer 1/2 (sau khi canonicalize).
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


# ---------------------------------------------------------------------------
# CV context + Match — kết quả so khớp 1 requirement
# ---------------------------------------------------------------------------

class CVContext(NamedTuple):
    """
    Các tập kỹ năng CV đã tiền xử lý 1 lần cho cả pipeline (tránh
    canonicalize/tra implies lặp lại cho từng requirement):

      raw            : skill thô đã lowercase (Layer 0 + proficiency)
      canonical      : skill đã canonical hóa (Layer 1)
      canonical_src  : canonical -> 1 skill CV thô đại diện (để làm matched_via)
      implied        : union mọi skill bị CV kéo theo, dạng canonical (Layer 2)
      implied_src    : implied_skill -> skill CV thô đã kéo theo nó (matched_via)
    """
    raw: set[str]
    canonical: set[str]
    canonical_src: dict[str, str]
    implied: set[str]
    implied_src: dict[str, str]


class Match(NamedTuple):
    """
    Kết quả so khớp 1 requirement (đã gộp OR-group).
      status : "matched" | "matched_implied" | "missing"  (để evaluator phân loại)
      credit : 1.0 nếu matched, 0.0 nếu missing (scoring nhị phân)
      layer  : "layer0" | "layer1" | "layer2" | "layer3" | "proficiency" | "missing"
      via    : chuỗi skill CV cụ thể đã thỏa requirement (để giải thích cho HR)
    """
    status: str
    credit: float
    layer: str
    via: str


# Trọng số cố định cho 2 tier skill phụ của JD. required_skills có weight riêng
# từng skill (RequiredSkill.weight, LLM gán 1-3) nên không cần hằng số; còn
# preferred_skills/nice_to_have_skills là list string phẳng — cả tier dùng 1
# trọng số, thấp hơn must-have (3) theo đúng thứ bậc required > preferred >
# nice_to_have mà form đăng tin bên .NET đã phân sẵn.
PREFERRED_SKILL_WEIGHT    = 2
NICE_TO_HAVE_SKILL_WEIGHT = 1


class TierResult(NamedTuple):
    """
    Kết quả so khớp 1 yêu cầu skill của JD, kèm tier và trọng số đã quy đổi.
      label  : nhãn hiển thị ("A / B / C" nếu là OR-group)
      weight : trọng số dùng để tính điểm D2
      tier   : "required" | "preferred" | "nice_to_have"
      match  : Match tương ứng
    """
    label: str
    weight: int
    tier: str
    match: Match


# Ưu tiên khi chọn alternative tốt nhất trong 1 OR-group: tầng sớm hơn thắng,
# matched luôn hơn missing. Fuzzy (layer3) và proficiency xếp sau các tầng chính
# xác exact/identity/implied.
_LAYER_RANK = {"layer0": 5, "layer1": 4, "layer2": 3, "layer3": 2, "proficiency": 1, "missing": 0}


# ---------------------------------------------------------------------------
# SkillMatcher — pipeline 3 tầng + proficiency
# ---------------------------------------------------------------------------

class SkillMatcher:
    """
    Toàn bộ logic so khớp kỹ năng dùng cho D2 (scorer.py) lẫn tường thuật chi
    tiết (evaluator.py). Không thuần túy fuzzy match; scoring nhị phân theo pipeline
    3 tầng + tầng phụ proficiency.
    """

    # -- Tiền xử lý CV 1 lần ---------------------------------------------------

    def build_cv_context(self, cv: ParsedCV) -> CVContext:
        """Gom + canonical hóa + mở rộng implied cho CV, trả CVContext dùng lại."""
        raw = _collect_cv_skills(cv)
        canonical: set[str] = set()
        canonical_src: dict[str, str] = {}
        implied: set[str] = set()
        implied_src: dict[str, str] = {}
        for tok in raw:
            c = resolve_canonical(tok)
            canonical.add(c)
            canonical_src.setdefault(c, tok)
            # Dữ liệu đã flatten bắc cầu -> tra list trực tiếp, không duyệt graph.
            for imp in SKILL_IMPLIES.get(c, ()):
                implied.add(imp)
                implied_src.setdefault(imp, tok)
        return CVContext(raw, canonical, canonical_src, implied, implied_src)

    # -- So khớp 1 tên kỹ năng đơn qua 3 tầng + proficiency --------------------

    def evaluate_name(self, name: str, ctx: CVContext) -> Match:
        """
        So khớp 1 tên kỹ năng JD (chưa canonicalize) với CV qua các tầng theo
        thứ tự; trả Match ngay ở tầng sớm nhất thỏa. Không tầng nào thỏa -> missing.
        """
        n = name.strip().lower()
        if not n:
            return Match("missing", 0.0, "missing", "")

        # Layer 0 — direct match trên output LLM thô (exact, chưa canonicalize).
        if n in ctx.raw:
            return Match("matched", 1.0, "layer0", n)

        # Layer 1 — identity qua skill_data.json (canonical hóa cả 2 phía)
        canon = resolve_canonical(name)
        if canon in ctx.canonical:
            return Match("matched", 1.0, "layer1", ctx.canonical_src[canon])

        # Layer 2 — entailment qua skill_implies.json (đã flatten sẵn)
        if canon in ctx.implied:
            return Match("matched_implied", 1.0, "layer2", ctx.implied_src[canon])

        # Layer 3 — fuzzy fallback (>=0.85) trên output LLM thô, khi 3 tầng chính
        # xác đã trượt. KHÔNG fuzzy cho token trình độ ngôn ngữ: "N4" giống 86%
        # "N3" nhưng THẤP HƠN, phải để tầng phụ proficiency so theo thứ bậc.
        if _parse_proficiency(n) is None:
            fuzzy = _fuzzy_best_match(n, ctx.raw)
            if fuzzy is not None:
                return Match("matched", 1.0, "layer3", fuzzy)

        # Tầng phụ — trình độ ngôn ngữ (ordinal, cùng framework)
        prof = self._match_proficiency(n, ctx.raw)
        if prof is not None:
            status, credit, via = prof
            return Match(status, credit, "proficiency", via)

        return Match("missing", 0.0, "missing", "")

    def _match_proficiency(self, jd_token: str,
                           cv_skills: set[str]) -> Optional[tuple[str, float, str]]:
        """
        So khớp trình độ ngôn ngữ theo thứ bậc. Trả (status, credit, via) khi JD
        yêu cầu 1 chứng chỉ chuẩn hóa VÀ CV có chứng chỉ cùng framework; None nếu
        JD không phải token trình độ (để nhường tầng khác). Mức CV bằng-hoặc-cao-
        hơn -> matched; thấp hơn -> missing (vẫn là verdict dứt điểm, không rơi
        xuống tầng khác vì đã biết chắc cùng framework).
        """
        req = _parse_proficiency(jd_token)
        if req is None:
            return None
        framework, req_rank = req
        best_rank: Optional[float] = None
        best_src = ""
        for cv_s in cv_skills:
            cp = _parse_proficiency(cv_s)
            if cp and cp[0] == framework and (best_rank is None or cp[1] > best_rank):
                best_rank = cp[1]
                best_src = cv_s
        if best_rank is None:
            return None
        if best_rank >= req_rank:
            return ("matched", 1.0, best_src)
        return ("missing", 0.0, best_src)

    # -- OR-group: thỏa 1 alternative là đủ -----------------------------------

    def group_names(self, req) -> list[str]:
        """Danh sách tên kỹ năng thô trong 1 OR-group (requirement + alternatives)."""
        return [n for n in [req.skill, *req.alternatives] if n]

    def group_label(self, req) -> str:
        """Nhãn hiển thị 'A / B / C' cho 1 OR-group."""
        return " / ".join(dict.fromkeys(self.group_names(req)))

    def evaluate_group(self, req, ctx: CVContext) -> Match:
        """
        Trả Match tốt nhất trong mọi alternative của 1 requirement (OR-group:
        thỏa 1 cái là đủ). "Tốt nhất" = tầng sớm nhất, ưu tiên matched.
        """
        best = Match("missing", 0.0, "missing", "")
        for name in self.group_names(req):
            m = self.evaluate_name(name, ctx)
            if (_LAYER_RANK[m.layer], m.credit) > (_LAYER_RANK[best.layer], best.credit):
                best = m
        return best

    # -- Gộp 3 tier skill của JD thành 1 danh sách có trọng số ------------------

    def evaluate_tiers(self, jd, ctx: CVContext) -> list[TierResult]:
        """
        Duyệt CẢ 3 tier skill của JD (required / preferred / nice_to_have) và
        trả kết quả so khớp kèm trọng số của từng tier — nguồn duy nhất cho cả
        D2 (scorer.score_skills) lẫn phần hiển thị cho HR (evaluator), để 2 chỗ
        không bao giờ lệch công thức.

        Trọng số: required dùng chính req.weight (LLM gán 1-3; skill đến từ tag
        list "Required Skills:" luôn là 3), preferred và nice_to_have dùng hằng
        số cố định theo tier (2 và 1) vì 2 list này là string phẳng, không có
        khái niệm weight riêng từng skill.

        KHÔNG dedup chéo giữa 3 tier — JD_EXTRACT_PROMPT đã ràng buộc LLM chỉ
        được bổ sung skill từ prose khi skill đó CHƯA nằm trong 3 list do .NET
        gửi xuống (3 list đó vốn đã canonical vì load từ skill_data).
        """
        out: list[TierResult] = []
        for req in jd.required_skills:
            out.append(TierResult(
                label  = self.group_label(req),
                weight = req.weight,
                tier   = "required",
                match  = self.evaluate_group(req, ctx),
            ))
        for name in jd.preferred_skills:
            out.append(TierResult(
                label  = name,
                weight = PREFERRED_SKILL_WEIGHT,
                tier   = "preferred",
                match  = self.evaluate_name(name, ctx),
            ))
        for name in jd.nice_to_have_skills:
            out.append(TierResult(
                label  = name,
                weight = NICE_TO_HAVE_SKILL_WEIGHT,
                tier   = "nice_to_have",
                match  = self.evaluate_name(name, ctx),
            ))
        return out

    # -- Evidence chi tiết cho evaluator.py ------------------------------------

    def evaluate_all_skills(self, cv: ParsedCV, jd) -> list[dict]:
        """
        Trả evidence chi tiết cho TỪNG required_skill của JD (dùng cho HR):
        [{label, weight, status, matched_layer, matched_via, credit}, ...].
        matched_layer ∈ layer0|layer1|layer2|layer3|proficiency|missing để
        evaluator giải thích được đã khớp qua đâu; matched_via là skill CV cụ thể
        đã thỏa.
        """
        ctx = self.build_cv_context(cv)
        out: list[dict] = []
        for req in jd.required_skills:
            m = self.evaluate_group(req, ctx)
            out.append({
                "label":         self.group_label(req),
                "weight":        req.weight,
                "status":        m.status,
                "matched_layer": m.layer,
                "matched_via":   m.via,
                "credit":        m.credit,
            })
        return out


_skill_matcher = SkillMatcher()
