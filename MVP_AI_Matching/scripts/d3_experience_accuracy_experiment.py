"""
Thực nghiệm chứng minh tính chính xác của D3 (Experience Score) —
`app/services/scorer.py::score_experience` (L167-190), dùng
`_skill_experience_ratio` (L133-164) + `_skill_group_months` (L117-130) +
`_job_matches_group` (L108-114), công thức đặc tả ở
docs/thesis_report.md mục 4.6:

    JD không yêu cầu số năm (min_experience_years = 0)      → D3 = 1.0
    JD có required_skills → với mỗi OR-group required_skill,
      cộng dồn (gộp khoảng chồng lấn) số tháng CV thực làm việc
      với skill đó (tech_stack của job), so với min_experience_years,
      rồi lấy trung bình có trọng số trên mọi required_skill
    JD không có required_skills (hoặc tổng trọng số = 0)     → sập về
      công thức cũ: min(cv_total_years / jd_min_years, 1.0)

Gồm 2 phần độc lập, trả lời 2 câu hỏi khác nhau:

  PHẦN A — Đúng cài đặt (correctness), trên bộ dữ liệu 700 test case.
    Câu hỏi: "score_experience() có cài đúng công thức đặc tả không, kể cả
    các đường rẽ nhánh (fallback, OR-group/alternatives, gộp khoảng chồng
    lấn, canonical hóa qua skill_data.json) và trường hợp biên?"
    Phương pháp: dựng 700 tổ hợp CV/JD theo thiết kế factorial (không lấy
    mẫu ngẫu nhiên — mọi tổ hợp được liệt kê tường minh, tái lập được), tính
    giá trị kỳ vọng bằng 1 cài đặt tham chiếu ĐỘC LẬP (thuật toán gộp
    khoảng thời gian viết lại từ đầu, không import merge_month_intervals/
    parse_month của app), rồi so với output thật của score_experience()
    trên object CV/JD dựng qua app.schemas. Kèm 5 property test (bất biến
    không phụ thuộc giá trị cụ thể).

  PHẦN C — Giới hạn thực tế: D3 phụ thuộc vào độ chính xác so khớp skill
    (SkillMatcher, thuộc D2), CHƯA đạt 100% trong production.
    Câu hỏi: "Phần A báo 700/700 = 100% — điều đó có nghĩa là D3 luôn cho
    kết quả đúng trên CV/JD thực tế không?" — KHÔNG. Phần A đo tính đúng của
    CÔNG THỨC (arithmetic/branching) khi đã có sẵn kết quả so khớp skill —
    phần lớn A.2/A.3 cố tình dùng token exact-match hoặc alias sạch đã có
    trong skill_data.json để tách bạch khỏi câu hỏi "so khớp có đúng không"
    (đó là phạm vi D2, không phải D3). Trên dữ liệu CV/JD thực (tên kỹ năng
    viết dưới dạng cụm mô tả, viết tắt lạ, không có trong KB...), việc so
    khớp KHÔNG đạt 100% — khi so khớp trượt, D3 âm thầm trả về 0 tháng cho
    skill đó dù ứng viên thực sự có kinh nghiệm.
    Phương pháp: (C.1) DỰA TRÊN phương pháp của
    scripts/d2_kb_coverage_experiment.py (docs/d2_kb_coverage_experiment.xlsx)
    — viết tay ~100 cặp (required_skill JD, cách diễn đạt tech_stack CV hợp
    lý mà 1 LLM-parser có thể tạo ra), trải rộng 13 nhóm công nghệ cùng tinh
    thần nhóm hóa với D2, nhân với 3 mức jd_years để có ~300 test case, chạy
    qua ĐÚNG pipeline SkillMatcher.evaluate_name() + score_experience() thật
    (không phải cài đặt tham chiếu) để đo trực tiếp bao nhiêu % trượt, và
    sai số D3 tương ứng khi trượt — khác D2 (đo 1 phía: "tên có trong KB
    không") ở chỗ đo đúng thứ D3 cần: "JD và CV viết 2 CÁCH ĐỘC LẬP cho cùng
    1 skill, D3 có nhận ra không". (C.2) bảng xác suất D3 bị lệch do ít nhất
    1 trong k required_skill của JD so khớp trượt, đối chiếu chéo 3 nguồn:
    2 số đã công bố ở docs/d2_kb_coverage_experiment.md (độ phủ 92.1%) và
    docs/d2_layer3_threshold_experiment.md (recall Layer 3 = 0.915), cộng 1
    số đo trực tiếp từ chính corpus C.1.

  PHẦN B — Đúng thực tế (validity).
    Câu hỏi: "Thiết kế D3 MỚI (đo độ sâu theo từng required_skill) có bám
    sát tín hiệu 'kinh nghiệm liên quan thực sự' tốt hơn công thức D3 CŨ
    (tỷ lệ số năm thô, không phân biệt lĩnh vực) hay không?" — đúng vấn đề
    mà D3 mới được thiết kế lại để giải quyết (xem docstring
    score_experience: "3 năm kinh nghiệm nhưng rải rác 4 công ty, mỗi công
    ty 1 skill khác nhau không nên được tính là 3 năm kinh nghiệm
    Java+React"). Phương pháp: cố định tổng số năm kinh nghiệm CV (3 năm),
    thay đổi TỶ LỆ CONCENTRATION — bao nhiêu % thời gian đó thực sự dành
    cho skill JD yêu cầu (phần còn lại ở 1 công ty khác, kỹ năng khác) —
    rồi so 2 công thức (D3 mới vs D3 cũ, cả 2 đều là code thật đang chạy
    trong scorer.py — D3 cũ chính là nhánh fallback khi required_skills
    rỗng) với nhãn proxy = chính tỷ lệ concentration đó, bằng Spearman rank
    correlation và MAE.

Chạy: python scripts/d3_experience_accuracy_experiment.py
Output: docs/d3_experience_accuracy_experiment.md, docs/d3_experience_accuracy_experiment.xlsx
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from _xlsx_writer import write_xlsx

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas import ParsedCV, ParsedJD, RequiredSkill, WorkExperience  # noqa: E402
from app.services.scorer import score_experience  # noqa: E402
from app.services.skill_matcher import SkillMatcher  # noqa: E402

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
REPORT_PATH = DOCS_DIR / "d3_experience_accuracy_experiment.md"
XLSX_PATH = DOCS_DIR / "d3_experience_accuracy_experiment.xlsx"

TOL = 1e-9

# Mốc thời gian cố định dùng để dựng start/end "YYYY-MM" cho work_experience —
# KHÔNG dùng datetime.date.today() ở bất kỳ đâu trong corpus, để toàn bộ 700
# test case xác định (deterministic), tái lập được y hệt bất kể chạy ngày nào.
ANCHOR = date(2020, 1, 1)


def add_months(d: date, n: int) -> date:
    total = d.year * 12 + (d.month - 1) + n
    return date(total // 12, total % 12 + 1, 1)


def fmt_month(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


# ---------------------------------------------------------------------------
# Thuật toán gộp khoảng thời gian ĐỘC LẬP — viết lại từ đầu, KHÔNG import
# app.schemas.merge_month_intervals/parse_month — dùng offset tháng nguyên
# (int) thay vì datetime.date, để chắc chắn không vô tình dùng lại code app.
# ---------------------------------------------------------------------------

def ref_merge_offsets(intervals: list[tuple[int, int]]) -> int:
    """Tổng số tháng bao phủ bởi các khoảng [start, end) offset nguyên, gộp
    khoảng chồng lấn/liền kề để không đếm trùng."""
    if not intervals:
        return 0
    ordered = sorted(intervals)
    total = 0
    cs, ce = ordered[0]
    for s, e in ordered[1:]:
        if s <= ce:
            ce = max(ce, e)
        else:
            total += ce - cs
            cs, ce = s, e
    total += ce - cs
    return total


# ---------------------------------------------------------------------------
# PHẦN A.1 — Fallback formula (JD không có required_skills): grid đầy đủ
# ---------------------------------------------------------------------------

@dataclass
class FallbackRow:
    cv_months: int
    jd_years: int
    expected: float
    actual: float

    @property
    def ok(self) -> bool:
        return abs(self.expected - self.actual) < TOL


def make_fallback_cv(months: int) -> ParsedCV:
    if months == 0:
        return ParsedCV(work_experience=[])
    start = add_months(ANCHOR, -months)
    return ParsedCV(work_experience=[
        WorkExperience(company="X", role="Dev", start=fmt_month(start), end=fmt_month(ANCHOR)),
    ])


def run_fallback_grid() -> list[FallbackRow]:
    rows = []
    for months in range(0, 145, 6):          # 0, 6, ..., 144 → 25 giá trị
        for years in range(0, 10):            # 0..9 → 10 giá trị
            cv = make_fallback_cv(months)
            jd = ParsedJD(title="JD", min_experience_years=years, required_skills=[])
            actual = score_experience(cv, jd)
            expected = 1.0 if years == 0 else min((months / 12) / years, 1.0)
            rows.append(FallbackRow(months, years, expected, actual))
    return rows


# ---------------------------------------------------------------------------
# PHẦN A.2 — Per-required-skill depth: thiết kế factorial đầy đủ (324 tổ hợp)
# ---------------------------------------------------------------------------

DUR = 18  # số tháng mỗi job "phụ trách" 1 required_skill

N_SKILLS = [1, 2, 3]
N_JOBS = [1, 2, 3]
JD_YEARS_A2 = [1, 2, 4]
OVERLAP = ["disjoint", "overlapping"]
ALT = [0, 1]
MISS = ["all_match", "one_missing", "flat_only"]

# Token cố ý CHỌN KHÁC XA NHAU về chuỗi ký tự (pairwise SequenceMatcher ratio
# < 0.85 — dưới ngưỡng Layer 3 fuzzy của skill_matcher.py) để tránh fuzzy match
# giả (false positive) giữa skill index này với skill index khác khi test
# "one_missing"/"flat_only" — nếu dùng tên kiểu skill0_primary/skill1_primary
# (chỉ khác 1 ký tự số) thì Layer 3 sẽ fuzzy-khớp nhầm giữa 2 skill khác nhau.
PRI_TOKENS = ["xqz_reactor", "vtn_falcon", "hjm_cobalt"]
ALT_TOKENS = ["bwk_prism", "fgy_beacon", "plr_lantern"]


@dataclass
class DepthCaseInput:
    n_skills: int
    n_jobs: int
    jd_years: int
    overlap: str
    alt: int
    miss: str
    jobs_tech: list[set]
    jobs_span: list[tuple[int, int]]
    flat_skills: list[str]


def build_depth_case(n_skills: int, n_jobs: int, jd_years: int, overlap: str, alt: int, miss: str) -> DepthCaseInput:
    jobs_tech: list[set] = [set() for _ in range(n_jobs)]
    jobs_span: list[tuple[int, int]] = []
    step = DUR if overlap == "disjoint" else DUR // 2
    for k in range(n_jobs):
        s_off = k * step
        jobs_span.append((s_off, s_off + DUR))

    for i in range(n_skills):
        owner = i % n_jobs
        token = ALT_TOKENS[i] if alt else PRI_TOKENS[i]
        jobs_tech[owner].add(token)
        # Khi overlapping và có >=2 job, cho skill đầu tiên được 2 job liền kề
        # cùng "phụ trách" (khoảng thời gian chồng lấn) — kiểm tra logic gộp
        # khoảng (merge) không đếm trùng phần chồng lấn.
        if overlap == "overlapping" and n_jobs >= 2 and i == 0:
            second = (owner + 1) % n_jobs
            jobs_tech[second].add(token)

    flat_skills: list[str] = []
    if n_skills >= 1 and miss in ("one_missing", "flat_only"):
        tok0 = ALT_TOKENS[0] if alt else PRI_TOKENS[0]
        for ts in jobs_tech:
            ts.discard(tok0)
        if miss == "flat_only":
            # Skill nằm rời rạc trong cv.skills (không gắn job cụ thể nào) —
            # D3 đo độ sâu, không được tính rời rạc khỏi job -> vẫn phải = 0.
            flat_skills.append(PRI_TOKENS[0])

    return DepthCaseInput(n_skills, n_jobs, jd_years, overlap, alt, miss, jobs_tech, jobs_span, flat_skills)


def case_to_cv_jd(c: DepthCaseInput) -> tuple[ParsedCV, ParsedJD]:
    work = []
    for k in range(c.n_jobs):
        s_off, e_off = c.jobs_span[k]
        start = add_months(ANCHOR, s_off)
        end = add_months(ANCHOR, e_off)
        work.append(WorkExperience(
            company=f"C{k}", role="Dev", start=fmt_month(start), end=fmt_month(end),
            tech_stack=sorted(c.jobs_tech[k]),
        ))
    cv = ParsedCV(work_experience=work, skills=list(c.flat_skills))

    required = []
    for i in range(c.n_skills):
        alts = [ALT_TOKENS[i]] if c.alt else []
        required.append(RequiredSkill(skill=PRI_TOKENS[i], weight=3, alternatives=alts))
    jd = ParsedJD(title="JD", min_experience_years=c.jd_years, required_skills=required)
    return cv, jd


def reference_depth(c: DepthCaseInput) -> float:
    """Cài đặt tham chiếu ĐỘC LẬP cho D3 theo chiều sâu: với mỗi required_skill,
    gộp khoảng thời gian (offset nguyên, thuật toán ref_merge_offsets ở trên)
    của các job có tech_stack khớp group (so khớp CHUỖI CHÍNH XÁC — không dùng
    SkillMatcher/canonical hóa, để tách biệt khỏi logic D2), rồi lấy trung
    bình các ratio (mọi required_skill ở đây weight=3 bằng nhau -> trung bình
    cộng)."""
    required_months = c.jd_years * 12
    ratios = []
    for i in range(c.n_skills):
        group = {PRI_TOKENS[i], ALT_TOKENS[i]} if c.alt else {PRI_TOKENS[i]}
        ivals = [
            c.jobs_span[k] for k in range(c.n_jobs)
            if c.jobs_tech[k] & group
        ]
        months = ref_merge_offsets(ivals)
        ratios.append(min(months / required_months, 1.0) if required_months > 0 else 1.0)
    return sum(ratios) / len(ratios)


@dataclass
class DepthRow:
    n_skills: int
    n_jobs: int
    jd_years: int
    overlap: str
    alt: int
    miss: str
    expected: float
    actual: float

    @property
    def ok(self) -> bool:
        return abs(self.expected - self.actual) < TOL


def run_depth_factorial() -> list[DepthRow]:
    rows = []
    for n_skills, n_jobs, jd_years, overlap, alt, miss in itertools.product(
        N_SKILLS, N_JOBS, JD_YEARS_A2, OVERLAP, ALT, MISS
    ):
        c = build_depth_case(n_skills, n_jobs, jd_years, overlap, alt, miss)
        cv, jd = case_to_cv_jd(c)
        actual = score_experience(cv, jd)
        expected = reference_depth(c)
        rows.append(DepthRow(n_skills, n_jobs, jd_years, overlap, alt, miss, expected, actual))
    return rows


# ---------------------------------------------------------------------------
# PHẦN A.3 — Canonical hóa qua skill_data.json (Layer 1): JD và CV ghi tên
# kỹ năng KHÁC NHAU (alias vs canonical) nhưng phải khớp qua resolve_canonical
# ---------------------------------------------------------------------------

# 10 cặp (alias, canonical) chép nguyên văn từ app/data/skill_data.json —
# value != key nghĩa là key là alias, cần canonical hóa mới khớp được.
ALIAS_PAIRS: list[tuple[str, str]] = [
    ("nodejs", "node.js"),
    ("golang", "go"),
    ("postgres", "postgresql"),
    ("vuejs", "vue.js"),
    ("k8s", "kubernetes"),
    ("mongo", "mongodb"),
    ("csharp", "c#"),
    ("python3", "python-3.x"),
    ("dockerfile", "docker"),
    ("java-core", "java"),
]

ALIAS_JOB_MONTHS = 24


@dataclass
class AliasRow:
    alias: str
    canonical: str
    side: str  # "JD=alias/CV=canonical" hoặc "JD=canonical/CV=alias"
    jd_years: int
    expected: float
    actual: float

    @property
    def ok(self) -> bool:
        return abs(self.expected - self.actual) < TOL


def run_alias_grid() -> list[AliasRow]:
    rows = []
    end = add_months(ANCHOR, ALIAS_JOB_MONTHS)
    for alias, canonical in ALIAS_PAIRS:
        for jd_years in [1, 2, 3, 4, 5]:
            for side, jd_term, cv_term in [
                ("JD=alias/CV=canonical", alias, canonical),
                ("JD=canonical/CV=alias", canonical, alias),
            ]:
                cv = ParsedCV(work_experience=[
                    WorkExperience(company="X", role="Dev", start=fmt_month(ANCHOR), end=fmt_month(end),
                                    tech_stack=[cv_term]),
                ])
                jd = ParsedJD(title="JD", min_experience_years=jd_years,
                              required_skills=[RequiredSkill(skill=jd_term, weight=3)])
                actual = score_experience(cv, jd)
                expected = min(ALIAS_JOB_MONTHS / (jd_years * 12), 1.0)
                rows.append(AliasRow(alias, canonical, side, jd_years, expected, actual))
    return rows


# ---------------------------------------------------------------------------
# PHẦN A.4 — Edge case: kích thước OR-group (2-4 alternatives) + trọng số 0
# ---------------------------------------------------------------------------

EDGE_JOB_MONTHS = 24


@dataclass
class OrGroupRow:
    alt_count: int
    match_idx: int  # index trong group_names khớp; == alt_count nghĩa là không khớp gì
    jd_years: int
    expected: float
    actual: float

    @property
    def ok(self) -> bool:
        return abs(self.expected - self.actual) < TOL


def run_or_group_grid() -> list[OrGroupRow]:
    rows = []
    end = add_months(ANCHOR, EDGE_JOB_MONTHS)
    for alt_count in [2, 3, 4]:
        names = ["orA_primary"] + [f"orA_alt{j}" for j in range(1, alt_count)]
        assert len(names) == alt_count
        for match_idx in range(alt_count + 1):  # alt_count = không khớp gì
            for jd_years in [1, 3]:
                tech_stack = [names[match_idx]] if match_idx < alt_count else []
                cv = ParsedCV(work_experience=[
                    WorkExperience(company="X", role="Dev", start=fmt_month(ANCHOR), end=fmt_month(end),
                                    tech_stack=tech_stack),
                ])
                jd = ParsedJD(title="JD", min_experience_years=jd_years, required_skills=[
                    RequiredSkill(skill=names[0], weight=3, alternatives=names[1:]),
                ])
                actual = score_experience(cv, jd)
                expected = 0.0 if match_idx == alt_count else min(EDGE_JOB_MONTHS / (jd_years * 12), 1.0)
                rows.append(OrGroupRow(alt_count, match_idx, jd_years, expected, actual))
    return rows


@dataclass
class ZeroWeightRow:
    n_skills: int
    expected: float
    actual: float

    @property
    def ok(self) -> bool:
        return abs(self.expected - self.actual) < TOL


def run_zero_weight_cases() -> list[ZeroWeightRow]:
    """total_w <= 0 (mọi required_skill có weight=0) -> _skill_experience_ratio
    trả None -> sập về công thức fallback cũ (cv_total_years/jd_min_years),
    dùng TOÀN BỘ kinh nghiệm CV chứ không theo từng skill nữa."""
    rows = []
    cv_months = 18
    jd_years = 3
    end = add_months(ANCHOR, cv_months)
    cv = ParsedCV(work_experience=[
        WorkExperience(company="X", role="Dev", start=fmt_month(ANCHOR), end=fmt_month(end)),
    ])
    expected = min((cv_months / 12) / jd_years, 1.0)
    for n_skills in [1, 2]:
        required = [RequiredSkill(skill=f"zw{i}", weight=0) for i in range(n_skills)]
        jd = ParsedJD(title="JD", min_experience_years=jd_years, required_skills=required)
        actual = score_experience(cv, jd)
        rows.append(ZeroWeightRow(n_skills, expected, actual))
    return rows


# ---------------------------------------------------------------------------
# PHẦN A.5 — Property-based tests
# ---------------------------------------------------------------------------

@dataclass
class PropertyResult:
    name: str
    description: str
    passed: bool
    detail: str


def run_property_tests() -> list[PropertyResult]:
    results = []

    # P1 — Cận trên: D3 không bao giờ vượt 1.0, kể cả khi job dài hơn nhiều
    # so với yêu cầu.
    violations = []
    for jd_years in [1, 2, 3]:
        for months in range(0, 121, 12):
            end = add_months(ANCHOR, months)
            cv = ParsedCV(work_experience=[
                WorkExperience(company="X", role="Dev", start=fmt_month(ANCHOR), end=fmt_month(end),
                                tech_stack=["capskill"]),
            ]) if months else ParsedCV()
            jd = ParsedJD(title="JD", min_experience_years=jd_years,
                          required_skills=[RequiredSkill(skill="capskill", weight=3)])
            v = score_experience(cv, jd)
            if v > 1.0 + TOL:
                violations.append((jd_years, months, v))
    results.append(PropertyResult(
        "P1 — Cận trên (cap ở 1.0)",
        "Số tháng làm skill vượt yêu cầu không được cộng điểm vượt 1.0",
        not violations,
        "OK — không vi phạm trong 33 tổ hợp (jd_years x months)" if not violations
        else f"VI PHẠM: {violations}",
    ))

    # P2 — Đơn điệu không giảm theo số tháng làm skill (jd_years cố định).
    non_monotonic = []
    for jd_years in [1, 2, 4]:
        scores = []
        for months in range(0, 61, 6):
            end = add_months(ANCHOR, months)
            cv = ParsedCV(work_experience=[
                WorkExperience(company="X", role="Dev", start=fmt_month(ANCHOR), end=fmt_month(end),
                                tech_stack=["monoskill"]),
            ]) if months else ParsedCV()
            jd = ParsedJD(title="JD", min_experience_years=jd_years,
                          required_skills=[RequiredSkill(skill="monoskill", weight=3)])
            scores.append(score_experience(cv, jd))
        for a, b in zip(scores, scores[1:]):
            if b < a - TOL:
                non_monotonic.append((jd_years, scores))
                break
    results.append(PropertyResult(
        "P2 — Đơn điệu không giảm theo số tháng",
        "Số tháng làm skill tăng (0->60, jd_years cố định) -> D3 không giảm",
        not non_monotonic,
        "OK — đơn điệu trên cả 3 giá trị jd_years" if not non_monotonic
        else f"VI PHẠM: {non_monotonic}",
    ))

    # P3 — Bất biến với thứ tự required_skills[] (trung bình có trọng số
    # không phụ thuộc thứ tự cộng dồn).
    order_violations = []
    base_reqs = [
        RequiredSkill(skill="ordA", weight=1),
        RequiredSkill(skill="ordB", weight=2),
        RequiredSkill(skill="ordC", weight=3),
    ]
    cv = ParsedCV(work_experience=[
        WorkExperience(company="X", role="Dev", start=fmt_month(ANCHOR), end=fmt_month(add_months(ANCHOR, 12)),
                        tech_stack=["ordA"]),
        WorkExperience(company="Y", role="Dev", start=fmt_month(add_months(ANCHOR, 12)),
                        end=fmt_month(add_months(ANCHOR, 30)), tech_stack=["ordB"]),
    ])
    reference_score = None
    for perm in itertools.permutations(base_reqs):
        jd = ParsedJD(title="JD", min_experience_years=2, required_skills=list(perm))
        s = score_experience(cv, jd)
        if reference_score is None:
            reference_score = s
        elif abs(s - reference_score) > TOL:
            order_violations.append((perm, s))
    results.append(PropertyResult(
        "P3 — Bất biến với thứ tự required_skills[]",
        "Xáo trộn thứ tự required_skills (6 hoán vị của 3 skill có weight khác nhau) không được đổi D3",
        not order_violations,
        "OK — 6 hoán vị đều cho cùng 1 điểm" if not order_violations
        else f"VI PHẠM: {order_violations}",
    ))

    # P4 — Gộp khoảng chồng lấn không đếm trùng: 2 job overlap cùng 1 skill
    # không được cho điểm cao hơn merged span thực tế.
    overlap_violations = []
    cv_overlap = ParsedCV(work_experience=[
        WorkExperience(company="X", role="Dev", start=fmt_month(ANCHOR), end=fmt_month(add_months(ANCHOR, 18)),
                        tech_stack=["mergeskill"]),
        WorkExperience(company="Y", role="Dev (freelance)", start=fmt_month(add_months(ANCHOR, 9)),
                        end=fmt_month(add_months(ANCHOR, 27)), tech_stack=["mergeskill"]),
    ])
    jd_overlap = ParsedJD(title="JD", min_experience_years=3,  # 36 tháng yêu cầu
                          required_skills=[RequiredSkill(skill="mergeskill", weight=3)])
    actual_overlap = score_experience(cv_overlap, jd_overlap)
    # Merged span thực tế = tháng 0->27 = 27 tháng (KHÔNG phải 18+18=36 nếu
    # cộng dồn ngây thơ không gộp chồng lấn).
    expected_overlap = min(27 / 36, 1.0)
    naive_sum_would_be = min(36 / 36, 1.0)  # nếu (sai) cộng dồn không gộp overlap
    if abs(actual_overlap - expected_overlap) > TOL:
        overlap_violations.append((actual_overlap, expected_overlap))
    results.append(PropertyResult(
        "P4 — Gộp khoảng chồng lấn không đếm trùng",
        "2 job overlap 9 tháng cùng 1 skill (18mo + 18mo, merged=27mo) -> D3 dùng merged span, không phải tổng thô",
        not overlap_violations,
        f"OK — D3={actual_overlap:.3f} khớp merged-span={expected_overlap:.3f} "
        f"(khác với nếu cộng dồn ngây thơ={naive_sum_would_be:.3f})" if not overlap_violations
        else f"VI PHẠM: actual={actual_overlap}, expected={expected_overlap}",
    ))

    # P5 — Skill chỉ nằm trong cv.skills (rời rạc, không gắn job) -> ratio 0
    # cho skill đó, dù CV có tổng số năm kinh nghiệm lớn ở job khác.
    flat_violations = []
    for total_months in [12, 36, 60]:
        end = add_months(ANCHOR, total_months)
        cv_flat = ParsedCV(
            work_experience=[WorkExperience(company="X", role="Dev", start=fmt_month(ANCHOR), end=fmt_month(end),
                                             tech_stack=["unrelated_tech"])],
            skills=["flatskill"],
        )
        jd_flat = ParsedJD(title="JD", min_experience_years=1,
                           required_skills=[RequiredSkill(skill="flatskill", weight=3)])
        v = score_experience(cv_flat, jd_flat)
        if v > TOL:
            flat_violations.append((total_months, v))
    results.append(PropertyResult(
        "P5 — cv.skills rời rạc không tính vào độ sâu",
        "Skill chỉ khai trong cv.skills, không gắn job nào -> D3 cho skill đó = 0, bất kể tổng năm kinh nghiệm CV",
        not flat_violations,
        "OK — 0.0 trên cả 3 mức tổng kinh nghiệm (12/36/60 tháng)" if not flat_violations
        else f"VI PHẠM: {flat_violations}",
    ))

    return results


# ---------------------------------------------------------------------------
# PHẦN C — Giới hạn thực tế: D3 phụ thuộc vào so khớp skill (D2), chưa 100%
# ---------------------------------------------------------------------------

# C.1 — Corpus lớn (dựa trên PHƯƠNG PHÁP của scripts/d2_kb_coverage_experiment.py):
# thay vì đo "1 tên kỹ năng có được resolve_canonical() nhận diện không" (D2,
# đã có sẵn 92.1%), đo "khi JD và CV mô tả CÙNG 1 kỹ năng bằng 2 CÁCH VIẾT
# ĐỘC LẬP THẬT (không suy ra máy móc từ skill_data.json — 2 lượt LLM parse
# JD/CV khác nhau hoàn toàn có thể chọn cách diễn đạt khác nhau), D3 có nhận
# ra qua ĐÚNG pipeline SkillMatcher.evaluate_name() không?". Viết tay ~100
# cặp trải rộng 13 nhóm công nghệ phổ biến trong CV/JD thật (cùng tinh thần
# nhóm hóa với D2), rồi nhân với 3 mức jd_years để có đủ số test case, đúng
# kiểu mở rộng bằng tham số số học đã dùng ở A.2/A.3 (không phải sample ngẫu
# nhiên, không phải biến thể định dạng máy móc như D2 — ở đây bản thân việc
# viết ra 2 cách diễn đạt ĐỘC LẬP là phần cốt lõi cần làm bằng tay, không thể
# tự sinh mà không làm mất tính "độc lập" đang muốn đo).
C1_PAIRS_BASE: list[tuple[str, str, str]] = [
    # -- Ngôn ngữ lập trình (8) --------------------------------------------------
    ("python", "python scripting", "Ngôn ngữ"),
    ("java", "oop java", "Ngôn ngữ"),
    ("javascript", "vanilla javascript", "Ngôn ngữ"),
    ("c++", "modern c++ (c++17)", "Ngôn ngữ"),
    ("golang", "concurrent programming in go", "Ngôn ngữ"),
    ("typescript", "typescript type system", "Ngôn ngữ"),
    ("kotlin", "kotlin coroutines", "Ngôn ngữ"),
    ("rust", "systems programming in rust", "Ngôn ngữ"),
    # -- Frontend (10) -------------------------------------------------------
    ("react", "react hooks", "Frontend"),
    ("react", "react context api", "Frontend"),
    ("vue", "vue composition api", "Frontend"),
    ("angular", "angular dependency injection", "Frontend"),
    ("redux", "state management with redux", "Frontend"),
    ("webpack", "module bundling with webpack", "Frontend"),
    ("tailwind css", "utility-first css styling", "Frontend"),
    ("sass", "css preprocessing with sass", "Frontend"),
    ("next.js", "server side rendering with next", "Frontend"),
    ("jquery", "dom manipulation with jquery", "Frontend"),
    # -- Backend (10) ---------------------------------------------------------
    ("node.js", "server-side javascript with node", "Backend"),
    ("express", "restful api with express", "Backend"),
    ("django", "python web framework django", "Backend"),
    ("spring boot", "java microservices with spring", "Backend"),
    ("laravel", "php mvc framework laravel", "Backend"),
    ("graphql", "api query language graphql", "Backend"),
    ("rest api", "restful api design", "Backend"),
    ("microservices", "microservices architecture", "Backend"),
    ("grpc", "remote procedure calls with grpc", "Backend"),
    ("websocket", "real-time communication with websocket", "Backend"),
    # -- Mobile (7) -------------------------------------------------------------
    ("react native", "cross-platform mobile with react native", "Mobile"),
    ("flutter", "flutter widget development", "Mobile"),
    ("android sdk", "native android development", "Mobile"),
    ("ios development", "building apps for iphone and ipad", "Mobile"),
    ("xamarin", "cross platform apps with xamarin", "Mobile"),
    ("ionic", "hybrid mobile apps with ionic", "Mobile"),
    ("swiftui", "declarative ui for ios", "Mobile"),
    # -- Database (10) --------------------------------------------------------
    ("postgresql", "relational database management", "Database"),
    ("mongodb", "nosql document database", "Database"),
    ("mysql", "mysql database administration", "Database"),
    ("redis", "in-memory caching with redis", "Database"),
    ("elasticsearch", "full text search with elasticsearch", "Database"),
    ("sql", "structured query language", "Database"),
    ("database design", "designing normalized database schemas", "Database"),
    ("orm", "object relational mapping", "Database"),
    ("dynamodb", "aws nosql database", "Database"),
    ("firebase", "google's mobile backend platform", "Database"),
    # -- Cloud/DevOps (12) ------------------------------------------------------
    ("aws", "amazon web services", "Cloud/DevOps"),
    ("kubernetes", "eks", "Cloud/DevOps"),
    ("kubernetes", "container orchestration", "Cloud/DevOps"),
    ("docker", "containerization with docker", "Cloud/DevOps"),
    ("terraform", "infrastructure as code with terraform", "Cloud/DevOps"),
    ("ci/cd", "continuous integration and deployment", "Cloud/DevOps"),
    ("jenkins", "build automation with jenkins", "Cloud/DevOps"),
    ("ansible", "configuration management with ansible", "Cloud/DevOps"),
    ("azure", "microsoft cloud platform", "Cloud/DevOps"),
    ("gcp", "google cloud platform", "Cloud/DevOps"),
    ("nginx", "reverse proxy configuration with nginx", "Cloud/DevOps"),
    ("linux", "linux system administration", "Cloud/DevOps"),
    # -- Data/ML (10) -----------------------------------------------------------
    ("pandas", "data manipulation with pandas", "Data/ML"),
    ("numpy", "numerical computing with numpy", "Data/ML"),
    ("tensorflow", "deep learning with tensorflow", "Data/ML"),
    ("pytorch", "neural network training with pytorch", "Data/ML"),
    ("scikit-learn", "machine learning with sklearn", "Data/ML"),
    ("power bi", "business intelligence dashboards", "Data/ML"),
    ("tableau", "data visualization with tableau", "Data/ML"),
    ("apache spark", "big data processing with spark", "Data/ML"),
    ("etl", "extract transform load pipelines", "Data/ML"),
    ("nlp", "natural language processing", "Data/ML"),
    # -- Testing/QA (8) --------------------------------------------------------
    ("jest", "unit testing with jest", "Testing/QA"),
    ("selenium", "automated browser testing", "Testing/QA"),
    ("cypress", "end to end testing with cypress", "Testing/QA"),
    ("junit", "java unit testing framework", "Testing/QA"),
    ("postman", "api testing with postman", "Testing/QA"),
    ("test automation", "writing automated test scripts", "Testing/QA"),
    ("load testing", "performance testing under load", "Testing/QA"),
    ("tdd", "test driven development", "Testing/QA"),
    # -- Design/UI-UX (6) -------------------------------------------------------
    ("figma", "figma prototyping", "Design/UI-UX"),
    ("adobe xd", "ui design with adobe xd", "Design/UI-UX"),
    ("photoshop", "adobe photoshop cc", "Design/UI-UX"),
    ("ui/ux design", "user interface and experience design", "Design/UI-UX"),
    ("wireframing", "creating low fidelity wireframes", "Design/UI-UX"),
    ("design system", "building reusable design systems", "Design/UI-UX"),
    # -- Security (6) -------------------------------------------------------------
    ("oauth", "oauth 2.0 authentication", "Security"),
    ("jwt", "json web token authentication", "Security"),
    ("penetration testing", "ethical hacking and pentesting", "Security"),
    ("owasp", "web application security best practices", "Security"),
    ("ssl/tls", "secure socket layer encryption", "Security"),
    ("firewall", "network firewall configuration", "Security"),
    # -- Process/Methodology (6) --------------------------------------------------
    ("agile", "working in scrum methodology", "Process"),
    ("scrum", "sprint planning and scrum ceremonies", "Process"),
    ("kanban", "kanban board workflow management", "Process"),
    ("git", "git version control", "Process"),
    ("jira", "project tracking with jira", "Process"),
    ("code review", "peer reviewing pull requests", "Process"),
    # -- Office/ERP/Business (6) ------------------------------------------------
    ("excel", "advanced microsoft excel", "Office/ERP"),
    ("sap", "sap erp system", "Office/ERP"),
    ("salesforce", "crm management with salesforce", "Office/ERP"),
    ("power point", "creating presentations", "Office/ERP"),
    ("google sheets", "spreadsheet analysis with google sheets", "Office/ERP"),
    ("erp", "enterprise resource planning systems", "Office/ERP"),
    # -- Blockchain/Embedded/IoT (6) ----------------------------------------------
    ("solidity", "smart contract development", "Blockchain/IoT"),
    ("ethereum", "blockchain development on ethereum", "Blockchain/IoT"),
    ("arduino", "embedded programming with arduino", "Blockchain/IoT"),
    ("raspberry pi", "iot projects with raspberry pi", "Blockchain/IoT"),
    ("mqtt", "iot messaging protocol", "Blockchain/IoT"),
    ("rtos", "real time operating systems", "Blockchain/IoT"),
]

C1_JOB_MONTHS = 24
C1_JD_YEARS_VARIANTS = [1, 2, 4]  # nhân corpus base lên 3 lần bằng tham số số học


@dataclass
class MatchFailureRow:
    category: str
    required_skill: str
    cv_tech_stack_term: str
    jd_years: int
    matched: bool
    layer: str
    d3_if_matched: float   # kỳ vọng nếu so khớp đúng (ứng viên thực sự có kinh nghiệm)
    d3_actual: float       # D3 thật trả về (0 nếu trượt)

    @property
    def attribution_error(self) -> float:
        return abs(self.d3_if_matched - self.d3_actual)


def run_match_failure_demo() -> list[MatchFailureRow]:
    matcher = SkillMatcher()
    end = add_months(ANCHOR, C1_JOB_MONTHS)
    rows = []
    for req, cv_term, category in C1_PAIRS_BASE:
        ctx = matcher.build_cv_context(ParsedCV(skills=[cv_term]))
        m = matcher.evaluate_name(req, ctx)
        cv = ParsedCV(work_experience=[
            WorkExperience(company="X", role="Dev", start=fmt_month(ANCHOR), end=fmt_month(end),
                            tech_stack=[cv_term]),
        ])
        for jd_years in C1_JD_YEARS_VARIANTS:
            jd = ParsedJD(title="JD", min_experience_years=jd_years,
                          required_skills=[RequiredSkill(skill=req, weight=3)])
            d3_actual = score_experience(cv, jd)
            d3_if_matched = min(C1_JOB_MONTHS / (jd_years * 12), 1.0)
            rows.append(MatchFailureRow(category, req, cv_term, jd_years, m.credit > 0, m.layer,
                                         d3_if_matched, d3_actual))
    return rows


def render_c1_category_summary(rows: list[MatchFailureRow]) -> str:
    cats: dict[str, list[MatchFailureRow]] = {}
    for r in rows:
        cats.setdefault(r.category, []).append(r)
    lines = ["| Nhóm | Số case | So khớp được | Tỷ lệ khớp |", "| --- | --- | --- | --- |"]
    for cat, rs in cats.items():
        matched = sum(1 for r in rs if r.matched)
        lines.append(f"| {cat} | {len(rs)} | {matched} | {matched/len(rs)*100:.1f}% |")
    return "\n".join(lines)


# C.2 — Bảng minh họa: xác suất D3 bị lệch do ít nhất 1/k required_skill so
# khớp trượt. Dùng 3 số đo ĐỘC LẬP để đối chiếu chéo — không chỉ 1 nguồn:
# (1)+(2) đã công bố sẵn ở 2 thực nghiệm D2 khác trong repo; (3) đo trực
# tiếp từ chính corpus C.1 ở trên (không phải cùng phương pháp với D2, nhưng
# đo trên chính pipeline D3 dùng — 3 số gần nhau củng cố độ tin cậy).
P_MISS_KB_COVERAGE = 1 - 0.921   # docs/d2_kb_coverage_experiment.md — độ phủ skill_data.json = 92.1%
P_MISS_FUZZY_RECALL = 1 - 0.915  # docs/d2_layer3_threshold_experiment.md — recall Layer 3 @ threshold 0.85


@dataclass
class ComplexityRiskRow:
    k_required_skills: int
    p_at_least_one_fail_kb: float
    p_at_least_one_fail_fuzzy: float
    p_at_least_one_fail_c1: float


def run_complexity_risk_table(p_miss_c1: float) -> list[ComplexityRiskRow]:
    rows = []
    for k in range(1, 11):
        p_kb = 1 - (1 - P_MISS_KB_COVERAGE) ** k
        p_fuzzy = 1 - (1 - P_MISS_FUZZY_RECALL) ** k
        p_c1 = 1 - (1 - p_miss_c1) ** k
        rows.append(ComplexityRiskRow(k, p_kb, p_fuzzy, p_c1))
    return rows


# ---------------------------------------------------------------------------
# PHẦN B — Đúng thực tế: D3 mới (theo chiều sâu) vs D3 cũ (tỷ lệ năm thô)
# so với nhãn proxy "concentration" (% thời gian dành cho skill JD yêu cầu)
# ---------------------------------------------------------------------------

TOTAL_CAREER_MONTHS = 36  # cố định 3 năm kinh nghiệm tổng cho mọi điểm Phần B
CONCENTRATIONS = [round(i / 10, 1) for i in range(11)]  # 0.0, 0.1, ..., 1.0
JD_YEARS_B = [2, 3, 4]


@dataclass
class ValidityRow:
    jd_years: int
    concentration: float
    d3_new: float
    d3_old: float
    human: float

    @property
    def abs_error_new(self) -> float:
        return abs(self.d3_new - self.human)

    @property
    def abs_error_old(self) -> float:
        return abs(self.d3_old - self.human)


def run_validity_corpus() -> list[ValidityRow]:
    rows = []
    for jd_years in JD_YEARS_B:
        for c in CONCENTRATIONS:
            target_months = round(TOTAL_CAREER_MONTHS * c)
            other_months = TOTAL_CAREER_MONTHS - target_months
            work = []
            cursor = ANCHOR
            if target_months:
                end = add_months(cursor, target_months)
                work.append(WorkExperience(company="Target Co", role="Dev", start=fmt_month(cursor),
                                            end=fmt_month(end), tech_stack=["target_skill"]))
                cursor = end
            if other_months:
                end = add_months(cursor, other_months)
                work.append(WorkExperience(company="Other Co", role="Dev", start=fmt_month(cursor),
                                            end=fmt_month(end), tech_stack=["other_skill"]))
            cv = ParsedCV(work_experience=work)

            jd_new = ParsedJD(title="JD", min_experience_years=jd_years,
                              required_skills=[RequiredSkill(skill="target_skill", weight=3)])
            jd_old = ParsedJD(title="JD", min_experience_years=jd_years, required_skills=[])

            d3_new = score_experience(cv, jd_new)
            d3_old = score_experience(cv, jd_old)
            rows.append(ValidityRow(jd_years, c, d3_new, d3_old, c))
    return rows


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation, cài bằng stdlib — trung bình hạng cho ties."""
    def ranks(vals: list[float]) -> list[float]:
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg_rank = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg_rank
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mean_rx, mean_ry = sum(rx) / n, sum(ry) / n
    cov = sum((a - mean_rx) * (b - mean_ry) for a, b in zip(rx, ry))
    var_x = sum((a - mean_rx) ** 2 for a in rx)
    var_y = sum((b - mean_ry) ** 2 for b in ry)
    if var_x == 0 or var_y == 0:
        return 1.0 if var_x == var_y else 0.0
    return cov / (var_x ** 0.5 * var_y ** 0.5)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_fallback_table(rows: list[FallbackRow]) -> str:
    lines = ["| cv_months | jd_years | Kỳ vọng | Thực tế | Khớp? |", "| --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r.cv_months} | {r.jd_years} | {r.expected:.3f} | {r.actual:.3f} | {'✅' if r.ok else '❌'} |")
    return "\n".join(lines)


def render_depth_table(rows: list[DepthRow]) -> str:
    lines = ["| n_skills | n_jobs | jd_years | overlap | alt | miss_pattern | Kỳ vọng | Thực tế | Khớp? |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(
            f"| {r.n_skills} | {r.n_jobs} | {r.jd_years} | {r.overlap} | {r.alt} | {r.miss} | "
            f"{r.expected:.3f} | {r.actual:.3f} | {'✅' if r.ok else '❌'} |"
        )
    return "\n".join(lines)


def render_alias_table(rows: list[AliasRow]) -> str:
    lines = ["| Alias | Canonical | Bên nào ghi alias | jd_years | Kỳ vọng | Thực tế | Khớp? |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(
            f"| `{r.alias}` | `{r.canonical}` | {r.side} | {r.jd_years} | "
            f"{r.expected:.3f} | {r.actual:.3f} | {'✅' if r.ok else '❌'} |"
        )
    return "\n".join(lines)


def render_or_group_table(rows: list[OrGroupRow]) -> str:
    lines = ["| Số alternatives | Khớp tại vị trí | jd_years | Kỳ vọng | Thực tế | Khớp? |",
             "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        pos = "không khớp" if r.match_idx == r.alt_count else f"vị trí {r.match_idx}"
        lines.append(
            f"| {r.alt_count} | {pos} | {r.jd_years} | {r.expected:.3f} | {r.actual:.3f} | "
            f"{'✅' if r.ok else '❌'} |"
        )
    return "\n".join(lines)


def render_zero_weight_table(rows: list[ZeroWeightRow]) -> str:
    lines = ["| Số required_skills (weight=0) | Kỳ vọng (fallback) | Thực tế | Khớp? |", "| --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r.n_skills} | {r.expected:.3f} | {r.actual:.3f} | {'✅' if r.ok else '❌'} |")
    return "\n".join(lines)


def render_property_table(results: list[PropertyResult]) -> str:
    lines = ["| Property | Mô tả bất biến | Kết quả | Chi tiết |", "| --- | --- | --- | --- |"]
    for r in results:
        lines.append(f"| {r.name} | {r.description} | {'✅ PASS' if r.passed else '❌ FAIL'} | {r.detail} |")
    return "\n".join(lines)


def render_match_failure_table(rows: list[MatchFailureRow], jd_years_filter: int) -> str:
    """Hiển thị 1 dòng/cặp (lọc theo 1 mức jd_years đại diện — khớp/trượt
    không phụ thuộc jd_years, chỉ ratio số phụ thuộc; bảng đầy đủ nằm trong
    file Excel)."""
    lines = ["| Nhóm | required_skill (JD) | tech_stack thực tế (CV) | So khớp? | Layer |",
             "| --- | --- | --- | --- | --- |"]
    for r in rows:
        if r.jd_years != jd_years_filter:
            continue
        lines.append(
            f"| {r.category} | `{r.required_skill}` | `{r.cv_tech_stack_term}` | "
            f"{'✅ khớp' if r.matched else '❌ TRƯỢT'} | {r.layer} |"
        )
    return "\n".join(lines)


def render_complexity_risk_table(rows: list[ComplexityRiskRow]) -> str:
    lines = ["| Số required_skill trong JD (k) | P(≥1 trượt) — độ phủ KB (D2) | P(≥1 trượt) — recall Layer 3 (D2) | P(≥1 trượt) — đo trực tiếp C.1 |",
             "| --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r.k_required_skills} | {r.p_at_least_one_fail_kb*100:.1f}% | "
                      f"{r.p_at_least_one_fail_fuzzy*100:.1f}% | {r.p_at_least_one_fail_c1*100:.1f}% |")
    return "\n".join(lines)


def render_validity_table(rows: list[ValidityRow]) -> str:
    lines = ["| jd_years | Concentration (nhãn proxy) | D3 mới (theo chiều sâu) | D3 cũ (tỷ lệ năm thô) | \\|D3mới−proxy\\| | \\|D3cũ−proxy\\| |",
             "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(
            f"| {r.jd_years} | {r.concentration:.1f} | {r.d3_new:.3f} | {r.d3_old:.3f} | "
            f"{r.abs_error_new:.3f} | {r.abs_error_old:.3f} |"
        )
    return "\n".join(lines)


def fallback_sheet_rows(rows: list[FallbackRow]) -> list[list]:
    out = [["cv_months", "jd_years", "Expected", "Actual", "Match"]]
    for r in rows:
        out.append([r.cv_months, r.jd_years, round(r.expected, 3), round(r.actual, 3), "TRUE" if r.ok else "FALSE"])
    return out


def depth_sheet_rows(rows: list[DepthRow]) -> list[list]:
    out = [["n_skills", "n_jobs", "jd_years", "overlap", "alt", "miss_pattern", "Expected", "Actual", "Match"]]
    for r in rows:
        out.append([r.n_skills, r.n_jobs, r.jd_years, r.overlap, r.alt, r.miss,
                    round(r.expected, 3), round(r.actual, 3), "TRUE" if r.ok else "FALSE"])
    return out


def alias_sheet_rows(rows: list[AliasRow]) -> list[list]:
    out = [["alias", "canonical", "side", "jd_years", "Expected", "Actual", "Match"]]
    for r in rows:
        out.append([r.alias, r.canonical, r.side, r.jd_years, round(r.expected, 3), round(r.actual, 3),
                    "TRUE" if r.ok else "FALSE"])
    return out


def or_group_sheet_rows(rows: list[OrGroupRow]) -> list[list]:
    out = [["alt_count", "match_idx", "jd_years", "Expected", "Actual", "Match"]]
    for r in rows:
        out.append([r.alt_count, r.match_idx, r.jd_years, round(r.expected, 3), round(r.actual, 3),
                    "TRUE" if r.ok else "FALSE"])
    return out


def zero_weight_sheet_rows(rows: list[ZeroWeightRow]) -> list[list]:
    out = [["n_skills(weight=0)", "Expected", "Actual", "Match"]]
    for r in rows:
        out.append([r.n_skills, round(r.expected, 3), round(r.actual, 3), "TRUE" if r.ok else "FALSE"])
    return out


def property_sheet_rows(results: list[PropertyResult]) -> list[list]:
    out = [["Property", "Description", "Result", "Detail"]]
    for r in results:
        out.append([r.name, r.description, "PASS" if r.passed else "FAIL", r.detail])
    return out


def match_failure_sheet_rows(rows: list[MatchFailureRow]) -> list[list]:
    out = [["category", "required_skill", "cv_tech_stack_term", "jd_years", "matched", "layer",
            "d3_if_matched", "d3_actual", "attribution_error"]]
    for r in rows:
        out.append([r.category, r.required_skill, r.cv_tech_stack_term, r.jd_years, "TRUE" if r.matched else "FALSE",
                    r.layer, round(r.d3_if_matched, 3), round(r.d3_actual, 3), round(r.attribution_error, 3)])
    return out


def complexity_risk_sheet_rows(rows: list[ComplexityRiskRow]) -> list[list]:
    out = [["k_required_skills", "P_at_least_one_fail(kb_coverage)", "P_at_least_one_fail(fuzzy_recall)",
            "P_at_least_one_fail(c1_measured)"]]
    for r in rows:
        out.append([r.k_required_skills, round(r.p_at_least_one_fail_kb, 4), round(r.p_at_least_one_fail_fuzzy, 4),
                    round(r.p_at_least_one_fail_c1, 4)])
    return out


def validity_sheet_rows(rows: list[ValidityRow]) -> list[list]:
    out = [["jd_years", "concentration", "D3_new", "D3_old", "human_proxy", "abs_error_new", "abs_error_old"]]
    for r in rows:
        out.append([r.jd_years, r.concentration, round(r.d3_new, 3), round(r.d3_old, 3), r.human,
                    round(r.abs_error_new, 3), round(r.abs_error_old, 3)])
    return out


def summary_sheet_rows(fb, depth, alias, org, zw, props, validity_rows, rho_new, mae_new, rho_old, mae_old,
                        mf_rows, risk_rows) -> list[list]:
    total_cases = len(fb) + len(depth) + len(alias) + len(org) + len(zw)
    total_pass = (sum(1 for r in fb if r.ok) + sum(1 for r in depth if r.ok) + sum(1 for r in alias if r.ok)
                  + sum(1 for r in org if r.ok) + sum(1 for r in zw if r.ok))
    mf_matched = sum(1 for r in mf_rows if r.matched)
    return [
        ["Metric", "Value"],
        ["PHAN A - Correctness CUA CONG THUC (gia dinh so khop dung san)", ""],
        ["A.1 Fallback grid - so case", len(fb)],
        ["A.1 Fallback grid - so case khop", sum(1 for r in fb if r.ok)],
        ["A.2 Per-skill depth factorial - so case", len(depth)],
        ["A.2 Per-skill depth factorial - so case khop", sum(1 for r in depth if r.ok)],
        ["A.3 Canonical alias (skill_data.json) - so case", len(alias)],
        ["A.3 Canonical alias - so case khop", sum(1 for r in alias if r.ok)],
        ["A.4a OR-group size - so case", len(org)],
        ["A.4a OR-group size - so case khop", sum(1 for r in org if r.ok)],
        ["A.4b Zero-weight fallback - so case", len(zw)],
        ["A.4b Zero-weight fallback - so case khop", sum(1 for r in zw if r.ok)],
        ["Tong so case correctness (A.1..A.4)", total_cases],
        ["Tong so case khop", total_pass],
        ["Tong accuracy (CUA CONG THUC, khong phai cua he thong that)", round(total_pass / total_cases, 4)],
        ["Property tests pass", f"{sum(1 for p in props if p.passed)}/{len(props)}"],
        [],
        ["PHAN C - Gioi han thuc te: so khop skill (D2) chua dat 100%", ""],
        ["C.1 So cap (required_skill, tech_stack thuc te)", len(mf_rows)],
        ["C.1 So cap so khop duoc", mf_matched],
        ["C.1 Ty le so khop duoc", round(mf_matched / len(mf_rows), 4)],
        ["C.2 P(>=1/5 required_skill trot) - theo do phu KB", round(risk_rows[4].p_at_least_one_fail_kb, 4)],
        ["C.2 P(>=1/5 required_skill trot) - theo recall fuzzy", round(risk_rows[4].p_at_least_one_fail_fuzzy, 4)],
        [],
        ["PHAN B - Validity (D3 moi vs D3 cu, vs nhan proxy concentration)", ""],
        ["So diem so sanh", len(validity_rows)],
        ["Spearman rho (D3 moi vs proxy)", round(rho_new, 4)],
        ["MAE (D3 moi vs proxy)", round(mae_new, 4)],
        ["Spearman rho (D3 cu vs proxy)", round(rho_old, 4)],
        ["MAE (D3 cu vs proxy)", round(mae_old, 4)],
    ]


def main() -> None:
    fb_rows = run_fallback_grid()
    depth_rows = run_depth_factorial()
    alias_rows = run_alias_grid()
    org_rows = run_or_group_grid()
    zw_rows = run_zero_weight_cases()
    props = run_property_tests()
    mf_rows = run_match_failure_demo()
    p_miss_c1 = 1 - (sum(1 for r in mf_rows if r.matched) / len(mf_rows))
    risk_rows = run_complexity_risk_table(p_miss_c1)
    validity_rows = run_validity_corpus()

    fb_pass, fb_total = sum(1 for r in fb_rows if r.ok), len(fb_rows)
    depth_pass, depth_total = sum(1 for r in depth_rows if r.ok), len(depth_rows)
    alias_pass, alias_total = sum(1 for r in alias_rows if r.ok), len(alias_rows)
    org_pass, org_total = sum(1 for r in org_rows if r.ok), len(org_rows)
    zw_pass, zw_total = sum(1 for r in zw_rows if r.ok), len(zw_rows)
    total_cases = fb_total + depth_total + alias_total + org_total + zw_total
    total_pass = fb_pass + depth_pass + alias_pass + org_pass + zw_pass
    props_pass = sum(1 for p in props if p.passed)

    d3_new_vals = [r.d3_new for r in validity_rows]
    d3_old_vals = [r.d3_old for r in validity_rows]
    human_vals = [r.human for r in validity_rows]
    rho_new = spearman(d3_new_vals, human_vals)
    mae_new = sum(r.abs_error_new for r in validity_rows) / len(validity_rows)
    rho_old = spearman(d3_old_vals, human_vals)
    mae_old = sum(r.abs_error_old for r in validity_rows) / len(validity_rows)

    mf_matched = sum(1 for r in mf_rows if r.matched)
    mf_total = len(mf_rows)
    mf_missed = mf_total - mf_matched
    mf_missed_rows = [r for r in mf_rows if not r.matched]
    mf_mean_error_when_missed = (sum(r.attribution_error for r in mf_missed_rows) / len(mf_missed_rows)
                                  if mf_missed_rows else 0.0)

    report = f"""# Thực nghiệm: chứng minh tính chính xác của D3 (Experience Score) trên bộ dữ liệu {total_cases} test case

Sinh tự động bởi `scripts/d3_experience_accuracy_experiment.py`. Đối tượng kiểm
chứng: `score_experience()` trong
[`app/services/scorer.py`](../app/services/scorer.py#L167-L190) (dùng
`_skill_experience_ratio` L133-164, `_skill_group_months` L117-130,
`_job_matches_group` L108-114) — xem đặc tả đầy đủ ở
[`docs/thesis_report.md` mục 4.6](thesis_report.md#46-experience-score-d3).

Gồm 3 thực nghiệm độc lập, trả lời 3 câu hỏi KHÁC NHAU — "đúng cài đặt",
"đúng thực tế", và "giới hạn thực tế" không phải cùng một thứ, và **kết quả
100% ở Phần A KHÔNG có nghĩa là D3 luôn đúng trên CV/JD thực** — xem Phần C.

> ⚠️ **Đọc trước khi trích dẫn con số "100%" ở Phần A:** con số này đo tính
> đúng của CÔNG THỨC (arithmetic/branching của `score_experience`), giả định
> kết quả so khớp skill (matched/missing) đã có sẵn và đúng. Phần lớn test
> case ở A.2/A.3 CỐ Ý dùng token so khớp chính xác (exact string) hoặc alias
> sạch đã có trong `skill_data.json`, để tách bạch khỏi câu hỏi "so khớp có
> đúng không" — đó là trách nhiệm của `SkillMatcher` (D2), không phải D3.
> Trên CV/JD thực (tên kỹ năng viết dưới dạng cụm mô tả, viết tắt lạ, không
> có trong KB...), việc so khớp **không đạt 100%** (độ phủ `skill_data.json`
> đo được 92.1% — xem `docs/d2_kb_coverage_experiment.md`; recall Layer 3
> fuzzy đo được 91.5% tại threshold 0.85 — xem
> `docs/d2_layer3_threshold_experiment.md`) — khi so khớp trượt, D3 âm thầm
> trả về 0 tháng cho skill đó dù ứng viên thực sự có kinh nghiệm. **Phần C**
> đo trực tiếp cơ chế này bằng chính pipeline `SkillMatcher` thật.

## PHẦN A — Đúng cài đặt (correctness) CỦA CÔNG THỨC, {total_cases} test case

**Phương pháp:** dựng {total_cases} tổ hợp CV/JD theo thiết kế factorial
(liệt kê tường minh, không lấy mẫu ngẫu nhiên — tái lập được y hệt mỗi lần
chạy vì mọi mốc thời gian dùng neo cố định `{ANCHOR.isoformat()[:7]}`, không
phụ thuộc `datetime.date.today()`), tính giá trị kỳ vọng bằng **cài đặt tham
chiếu độc lập** (thuật toán gộp khoảng thời gian viết lại từ đầu trên offset
tháng nguyên — không import `merge_month_intervals`/`parse_month` của app),
rồi so với output thật của `score_experience()` trên object `ParsedCV`/
`ParsedJD` dựng qua `app.schemas`. Chia 5 lớp trường hợp, phủ toàn bộ các
nhánh rẽ của công thức (fallback / theo chiều sâu / canonical hóa / OR-group
/ trọng số 0), cộng 5 property test kiểm tra bất biến.

### A.1 Fallback formula — JD không có required_skills ({fb_total} tổ hợp)

25 giá trị `cv_months` (0..144, bước 6) × 10 giá trị `jd_years` (0..9) —
kiểm tra nhánh fallback `min(cv_years/jd_min_years, 1.0)` và trường hợp biên
`jd_years=0 → 1.0`.

{render_fallback_table(fb_rows)}

**Kết quả: {fb_pass}/{fb_total} tổ hợp khớp tuyệt đối ({fb_pass/fb_total*100:.1f}%).**

### A.2 Per-required-skill depth — thiết kế factorial đầy đủ ({depth_total} tổ hợp)

Đây là phần lõi của D3 (thiết kế mới, đo độ sâu theo từng required_skill).
6 trục biến thiên, tích Descartes đầy đủ (không rút gọn):

| Trục | Giá trị | Ý nghĩa |
| --- | --- | --- |
| `n_skills` | 1, 2, 3 | Số required_skill (OR-group) trong JD |
| `n_jobs` | 1, 2, 3 | Số job trong CV |
| `jd_years` | 1, 2, 4 | Số năm JD yêu cầu (áp dùng chung mọi skill) |
| `overlap` | disjoint, overlapping | Các job có khoảng thời gian chồng lấn hay không |
| `alt` | 0, 1 | required_skill có 1 alternative hay không (test OR-group) |
| `miss_pattern` | all_match, one_missing, flat_only | Skill đầu tiên: có job chứng minh / không job nào chứng minh / chỉ nằm rời rạc trong `cv.skills` |

3×3×3×2×2×3 = **{depth_total} tổ hợp**.

<details><summary>Xem đầy đủ {depth_total} dòng</summary>

{render_depth_table(depth_rows)}

</details>

**Kết quả: {depth_pass}/{depth_total} tổ hợp khớp tuyệt đối ({depth_pass/depth_total*100:.1f}%).**

### A.3 Canonical hóa qua skill_data.json (Layer 1) — {alias_total} tổ hợp

`_job_matches_group` dùng lại `SkillMatcher.evaluate_name` (đúng pipeline
D2) để so khớp tech_stack của job với required_skill — nghĩa là D3 phải
canonical hóa đúng khi JD và CV ghi tên kỹ năng KHÁC NHAU (alias vs
canonical, ví dụ JD ghi `nodejs`, CV ghi `node.js`). 10 cặp alias/canonical
chép nguyên văn từ `app/data/skill_data.json` × 5 mức `jd_years` × 2 chiều
(JD ghi alias/CV ghi canonical, và ngược lại) = {alias_total} tổ hợp:

{render_alias_table(alias_rows)}

**Kết quả: {alias_pass}/{alias_total} tổ hợp khớp tuyệt đối ({alias_pass/alias_total*100:.1f}%).**

### A.4 Edge case: kích thước OR-group và trọng số 0 ({org_total + zw_total} tổ hợp)

**A.4a — Kích thước OR-group** ({org_total} tổ hợp): `alternatives` có 1-3
phần tử (tổng 2-4 tên trong group), khớp lần lượt tại từng vị trí (kể cả
"không khớp gì") × 2 mức `jd_years`:

{render_or_group_table(org_rows)}

**A.4b — Trọng số 0 (fallback)** ({zw_total} tổ hợp): mọi required_skill có
`weight=0` → `total_w <= 0` → `_skill_experience_ratio` trả `None` → sập về
công thức fallback cũ dùng TOÀN BỘ kinh nghiệm CV, không theo skill:

{render_zero_weight_table(zw_rows)}

**Kết quả A.4: {org_pass + zw_pass}/{org_total + zw_total} tổ hợp khớp tuyệt đối.**

### A.5 Property-based tests

{render_property_table(props)}

**Kết quả: {props_pass}/{len(props)} property PASS.**

### A.6 Kết luận Phần A

Trên tổng cộng **{total_cases} test case correctness** (A.1 fallback +
A.2 per-skill depth factorial + A.3 canonical alias + A.4 OR-group/trọng số
0) cộng {len(props)} property test, `score_experience()` cài đặt **đúng
{total_pass/total_cases*100:.2f}%** đặc tả công thức: {total_pass}/{total_cases}
tổ hợp khớp tuyệt đối, {props_pass}/{len(props)} property PASS — bao trùm cả
nhánh fallback (JD không có required_skills hoặc trọng số 0), nhánh chính
(độ sâu theo từng required_skill, kể cả OR-group/alternatives và gộp khoảng
chồng lấn), và tích hợp đúng với pipeline canonical hóa của D2
(`skill_data.json`).

**Đây là kết luận về CÔNG THỨC, không phải kết luận về độ chính xác của D3
trên CV/JD thực tế** — xem Phần C ngay dưới đây để biết giới hạn thực tế.

## PHẦN C — Giới hạn thực tế: D3 phụ thuộc vào so khớp skill (D2), chưa 100%

**Câu hỏi:** Phần A báo {total_pass}/{total_cases} = {total_pass/total_cases*100:.0f}% —
điều đó có nghĩa D3 luôn cho điểm đúng trên CV/JD thực không? **Không.** D3
chỉ tính đúng số tháng của 1 required_skill NẾU `_job_matches_group()` (dùng
lại đúng pipeline so khớp của D2 — `SkillMatcher.evaluate_name`, 4 tầng
layer0-3) xác định đúng job nào "có" skill đó. Trên dữ liệu thật, tên kỹ
năng trong `tech_stack` không phải lúc nào cũng viết y hệt tên trong
`required_skills` của JD — và pipeline so khớp đó **chưa đạt 100%**, như
chính các thực nghiệm D2 khác trong repo này đã đo được.

### C.1 Corpus lớn ({len(C1_PAIRS_BASE)} cặp × {len(C1_JD_YEARS_VARIANTS)} mức jd_years = {mf_total} test case), dựa trên phương pháp của `d2_kb_coverage_experiment.py`

**Khác gì với `docs/d2_kb_coverage_experiment.xlsx`?** D2's coverage experiment
đo "1 tên kỹ năng LLM trích ra có được `resolve_canonical()` nhận diện
không" — 1 phía. Ở đây đo đúng thứ D3 cần: "khi JD và CV mô tả CÙNG 1 kỹ
năng bằng 2 CÁCH VIẾT ĐỘC LẬP thật (JD và CV được 2 lượt LLM-parse khác
nhau tạo ra, hoàn toàn có thể chọn cách diễn đạt khác nhau), D3 có nhận ra
qua ĐÚNG pipeline `SkillMatcher.evaluate_name()` không?" — 2 phía, và chạy
qua **toàn bộ D3 thật** (`score_experience`), không chỉ hàm lookup canonical.

**Phương pháp:** viết tay {len(C1_PAIRS_BASE)} cặp (required_skill JD, cách
diễn đạt tech_stack CV hợp lý — tên đầy đủ, viết tắt lĩnh vực, sub-feature
của 1 framework, KHÔNG phải câu mô tả dài dòng) trải rộng {len({c for _,_,c in C1_PAIRS_BASE})}
nhóm công nghệ, cùng tinh thần nhóm hóa với `d2_kb_coverage_experiment.py`,
rồi nhân với {len(C1_JD_YEARS_VARIANTS)} mức `jd_years` (mở rộng bằng tham
số số học, cùng kỹ thuật đã dùng ở A.2/A.3) để có {mf_total} test case. Mỗi
cặp chạy qua `SkillMatcher.evaluate_name()` THẬT (không phải cài đặt tham
chiếu) và `score_experience()` THẬT.

**Độ phủ theo nhóm:**

{render_c1_category_summary(mf_rows)}

<details><summary>Xem đầy đủ {len(C1_PAIRS_BASE)} cặp (đại diện tại jd_years=2 — khớp/trượt không đổi theo jd_years, bảng {mf_total} dòng đầy đủ nằm trong file Excel)</summary>

{render_match_failure_table(mf_rows, jd_years_filter=2)}

</details>

**Kết quả: {mf_matched}/{mf_total} test case so khớp được ({mf_matched/mf_total*100:.1f}%),
{mf_missed}/{mf_total} test case trượt ({mf_missed/mf_total*100:.1f}%)** — với mỗi
cặp trượt, D3 cho skill đó tụt từ {mf_mean_error_when_missed:.3f} (điểm nếu
so khớp đúng, trung bình trên các cặp trượt) xuống 0.0, dù ứng viên trong
data test THỰC SỰ có {C1_JOB_MONTHS} tháng kinh nghiệm với skill đó.

**Lưu ý về phạm vi của C.1 (khác với A.1-A.4):** {len(C1_PAIRS_BASE)} cặp
gốc này viết tay từ tri thức miền — có thể mở rộng cỡ mẫu hơn nữa (như D2
làm với 1000 case), nhưng KHÔNG THỂ pad tự động như D2 (biến thể định dạng
`space<->dash`, đổi hoa/thường...) vì bản chất phép thử này là "2 cách viết
ĐỘC LẬP thật" — pad tự động 1 phía từ phía kia sẽ vô tình làm 2 phía LẠI phụ
thuộc nhau, phá vỡ chính tính độc lập cần đo. Đây vẫn KHÔNG phải mẫu ngẫu
nhiên đại diện tần suất chính xác trong production (cần dữ liệu CV/JD thật +
nhãn người gán để đo tần suất đó, ngoài phạm vi đồ án) — nhưng ở quy mô
{mf_total} test case / {len(C1_PAIRS_BASE)} cặp trải {len({c for _,_,c in C1_PAIRS_BASE})}
nhóm công nghệ, đây là **số đo trực tiếp trên chính pipeline D3 dùng**, không
còn là minh họa nhỏ lẻ. **Con số {mf_missed/mf_total*100:.1f}% này CAO HƠN
NHIỀU** so với 8.0%/8.5% của D2 — 2 thực nghiệm đo 2 kịch bản khác nhau, KHÔNG
mâu thuẫn nhau: D2 đo "1 tên kỹ năng viết theo phong cách LLM thông thường
(Title Case, dấu chấm, viết tắt phổ biến) có nằm trong KB không" — phần lớn
biến thể đó ĐÃ được `to_stackoverflow_format()` xử lý; C.1 cố ý chọn các
cụm diễn đạt PHÂN KỲ NHIỀU hơn (đổi hẳn sang mô tả chức năng như "restful
api design" thay vì giữ nguyên tên riêng) — đại diện tình huống KHÓ hơn
"trung bình". Sự thật production nằm ở đâu đó GIỮA 2 con số này, tùy JD/CV
thực tế phân kỳ cách diễn đạt tới đâu — không đo được chính xác nếu không
có dữ liệu CV/JD thật (cùng hạn chế đã nêu).

### C.2 Rủi ro theo độ phức tạp JD (3 kịch bản, KHÔNG phải 1 số duy nhất)

JD càng liệt kê nhiều `required_skills`, xác suất **ít nhất 1** skill bị so
khớp trượt càng cao (giả định các skill so khớp độc lập nhau — đơn giản
hóa). 3 dòng dưới đây là 3 KỊCH BẢN khác nhau (không phải đo cùng 1 hiện
tượng nên KHÔNG được gộp/lấy trung bình): 2 dòng đầu ứng với kịch bản
"JD/CV dùng cách diễn đạt gần giống nhau" (số đo D2), dòng cuối ứng với kịch
bản "JD/CV diễn đạt phân kỳ nhiều" (số đo C.1 ở trên):

{render_complexity_risk_table(risk_rows)}

Với JD điển hình yêu cầu 5 required_skill: nếu JD/CV diễn đạt gần giống
nhau, xác suất có ≥1 skill bị chấm sai khoảng **{risk_rows[4].p_at_least_one_fail_kb*100:.0f}–{risk_rows[4].p_at_least_one_fail_fuzzy*100:.0f}%**
(kịch bản D2); nếu diễn đạt phân kỳ nhiều, xác suất này gần như
**chắc chắn xảy ra ({risk_rows[4].p_at_least_one_fail_c1*100:.0f}%)** (kịch
bản C.1). **Không nhỏ ở kịch bản nào**, và khoảng cách lớn giữa 2 kịch bản
tự nó là 1 phát hiện: độ chính xác thực tế của D3 nhạy cảm CAO với việc JD
và CV được viết/parse giống nhau tới đâu — 1 yếu tố ngoài tầm kiểm soát của
cả D2 lẫn D3.

### C.3 Kết luận Phần C

D3 kế thừa giới hạn của D2 (`SkillMatcher`): độ phủ `skill_data.json` 92.1%,
recall Layer 3 fuzzy 91.5% (2 thực nghiệm D2 khác đo sẵn), VÀ đo trực tiếp
thêm ở C.1 trên chính pipeline D3 dùng: chỉ {mf_matched/mf_total*100:.1f}%
trong {mf_total} test case (viết tay, {len(C1_PAIRS_BASE)} cặp × {len(C1_JD_YEARS_VARIANTS)}
mức jd_years, trải {len({c for _,_,c in C1_PAIRS_BASE})} nhóm công nghệ) so
khớp đúng khi JD/CV dùng 2 cách diễn đạt độc lập cho cùng 1 skill. Khi so
khớp trượt, sai số của D3 không phải là "lệch nhẹ" mà là **tụt thẳng về 0**
cho skill đó (C.1) —
nghiêm trọng hơn nhiều so với các nguồn sai số khác đã đo ở Phần A/B của
chính D3. **Kết luận đúng cho toàn bộ thực nghiệm D3 này là:** công thức
D3 cài đặt đúng 100% ĐẶC TẢ CỦA NÓ (Phần A), thiết kế theo chiều sâu hợp lý
hơn hẳn công thức cũ nó thay thế (Phần B) — nhưng **độ chính xác thực tế
của D3 trên CV/JD thật bị chặn trên bởi độ chính xác so khớp skill của D2**,
hiện chưa đạt 100% (Phần C). Cải thiện D3 tiếp theo nên nhắm vào việc mở
rộng `skill_data.json`/`skill_implies.json` (D2) hơn là chỉnh công thức D3
(đã đúng đặc tả).

## PHẦN B — Đúng thực tế (validity): D3 mới so với D3 cũ

**Câu hỏi:** D3 được thiết kế lại (đo độ sâu theo từng required_skill thay
vì tỷ lệ số năm thô) — thiết kế mới có thực sự bám sát tín hiệu "kinh
nghiệm liên quan" tốt hơn thiết kế cũ hay không? Đây đúng là lý do D3 được
viết lại (xem docstring `score_experience`): "3 năm kinh nghiệm nhưng rải
rác 4 công ty, mỗi công ty 1 skill khác nhau không nên được tính là 3 năm
kinh nghiệm Java+React".

**Phương pháp:** cố định tổng kinh nghiệm CV = 3 năm ({TOTAL_CAREER_MONTHS}
tháng), thay đổi **concentration** — tỷ lệ % thời gian đó thực sự dành cho
`target_skill` mà JD yêu cầu (phần còn lại ở 1 công ty khác, làm
`other_skill` không liên quan) — từ 0.0 đến 1.0, bước 0.1, × 3 mức
`jd_years`. Nhãn proxy = chính giá trị concentration (tỷ lệ thời gian sự
nghiệp thực sự dành cho kỹ năng JD cần — đúng tín hiệu 1 HR đọc CV sẽ nhìn
vào). So 2 công thức, cả 2 đều là code thật đang chạy trong `scorer.py`
(D3 cũ chính là nhánh fallback khi `required_skills=[]`, KHÔNG phải suy
diễn), với nhãn proxy đó bằng Spearman rank correlation và MAE.

### B.1 Toàn bộ điểm so sánh ({len(validity_rows)} điểm)

{render_validity_table(validity_rows)}

### B.2 Chỉ số tổng hợp

| Chỉ số | D3 mới (theo chiều sâu) | D3 cũ (tỷ lệ năm thô) | Ý nghĩa |
| --- | --- | --- | --- |
| Spearman ρ (vs nhãn proxy concentration) | {rho_new:.4f} | {rho_old:.4f} | D3 có sắp đúng thứ tự ứng viên theo mức độ liên quan thực sự không |
| MAE (vs nhãn proxy concentration) | {mae_new:.4f} | {mae_old:.4f} | Giá trị tuyệt đối lệch bao nhiêu trên thang 0-1 |

### B.3 Kết luận Phần B

D3 mới đạt Spearman ρ = {rho_new:.3f}, MAE = {mae_new:.3f} so với nhãn
concentration — **bám sát tín hiệu "kinh nghiệm liên quan thực sự"** (lệch
chủ yếu ở vùng concentration cao/`jd_years` thấp, do D3 chặn trần ở 1.0 khi
số tháng làm skill đã vượt yêu cầu — đúng chủ ý thiết kế, không cộng thêm
điểm cho việc "thừa" kinh nghiệm). D3 cũ đạt ρ = {rho_old:.3f}, MAE =
{mae_old:.3f} — **hoàn toàn không phân biệt được** các mức concentration
khác nhau, vì D3 cũ chỉ nhìn tổng số năm kinh nghiệm ({TOTAL_CAREER_MONTHS}
tháng, không đổi trong toàn bộ Phần B) mà không biết bao nhiêu trong số đó
thực sự liên quan tới skill JD cần — đúng vấn đề D3 mới được thiết kế lại để
giải quyết, và ở đây được **định lượng** thay vì chỉ nêu định tính.

**Hạn chế của thực nghiệm này:** nhãn proxy (concentration) là tín hiệu có
lý giải domain trực tiếp từ định nghĩa vấn đề D3 giải quyết, không phải dữ
liệu khảo sát HR thật (ngoài phạm vi thu thập được của đồ án) — cùng hạn
chế đã nêu ở các thực nghiệm D2/D4 khác trong `docs/`.

## Tổng kết

| | Kết quả |
| --- | --- |
| Đúng cài đặt CỦA CÔNG THỨC (Phần A) | {total_pass}/{total_cases} test case khớp tuyệt đối ({total_pass/total_cases*100:.2f}%) + {props_pass}/{len(props)} property PASS → **cài đặt đúng đặc tả trên toàn bộ các nhánh rẽ chính (fallback, theo chiều sâu, canonical hóa, OR-group, trọng số 0)** — GIẢ ĐỊNH so khớp skill đã đúng |
| Giới hạn thực tế — so khớp skill (Phần C, corpus {mf_total} case dựa trên phương pháp D2) | {mf_matched}/{mf_total} test case so khớp được ({mf_matched/mf_total*100:.1f}%) qua pipeline D2 thật; JD 5 required_skill → {risk_rows[4].p_at_least_one_fail_kb*100:.0f}–{max(risk_rows[4].p_at_least_one_fail_kb, risk_rows[4].p_at_least_one_fail_fuzzy, risk_rows[4].p_at_least_one_fail_c1)*100:.0f}% khả năng có ≥1 skill bị chấm sai (3 nguồn số liệu đối chiếu chéo) → **độ chính xác D3 trên CV/JD thật bị chặn trên bởi độ chính xác so khớp của D2, KHÔNG phải 100%** |
| Đúng thực tế — giá trị thiết kế (Phần B) | D3 mới: ρ={rho_new:.3f}, MAE={mae_new:.3f} — D3 cũ: ρ={rho_old:.3f}, MAE={mae_old:.3f} → **khi so khớp skill đúng, thiết kế theo chiều sâu bám sát tín hiệu kinh nghiệm liên quan tốt hơn hẳn công thức tỷ lệ năm thô mà nó thay thế** |

**Kết luận ngắn gọn:** D3 đúng về mặt công thức và là một cải tiến thiết kế
hợp lý so với bản cũ — nhưng "chính xác của D3" trong thực tế phụ thuộc trực
tiếp vào "chính xác so khớp skill của D2", hiện đo được ở mức 92.1% (độ phủ
KB, `d2_kb_coverage_experiment.md`), 91.5% (recall fuzzy,
`d2_layer3_threshold_experiment.md`), và {mf_matched/mf_total*100:.1f}%
(đo trực tiếp trên {mf_total} test case JD-vs-CV ở Phần C.1 của chính thực
nghiệm này) — 3 nguồn độc lập, không nguồn nào đạt 100%.

---
*Tái tạo báo cáo này: `python scripts/d3_experience_accuracy_experiment.py`*
"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    write_xlsx(XLSX_PATH, {
        "Summary": summary_sheet_rows(fb_rows, depth_rows, alias_rows, org_rows, zw_rows, props,
                                       validity_rows, rho_new, mae_new, rho_old, mae_old,
                                       mf_rows, risk_rows),
        "A1 - Fallback grid": fallback_sheet_rows(fb_rows),
        "A2 - Depth factorial": depth_sheet_rows(depth_rows),
        "A3 - Canonical alias": alias_sheet_rows(alias_rows),
        "A4a - OR-group size": or_group_sheet_rows(org_rows),
        "A4b - Zero weight": zero_weight_sheet_rows(zw_rows),
        "A5 - Property tests": property_sheet_rows(props),
        "C1 - Real match failures": match_failure_sheet_rows(mf_rows),
        "C2 - Complexity risk": complexity_risk_sheet_rows(risk_rows),
        "B - Validity corpus": validity_sheet_rows(validity_rows),
    })

    print(f"Đã ghi báo cáo vào {REPORT_PATH}")
    print(f"Đã ghi Excel vào {XLSX_PATH}")
    print(f"Phần A: {total_pass}/{total_cases} test case khớp ({total_pass/total_cases*100:.2f}%), "
          f"{props_pass}/{len(props)} property PASS")
    print(f"Phần C: {mf_matched}/{mf_total} tech_stack thuc te khop ({mf_matched/mf_total*100:.1f}%) "
          f"qua pipeline SkillMatcher that")
    print(f"Phần B: D3 moi rho={rho_new:.4f} mae={mae_new:.4f} | D3 cu rho={rho_old:.4f} mae={mae_old:.4f}")


if __name__ == "__main__":
    main()
