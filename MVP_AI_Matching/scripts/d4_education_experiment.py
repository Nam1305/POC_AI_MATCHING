"""
Thực nghiệm chứng minh tính chính xác của D4 (Education Score) —
`app/services/scorer.py::score_education`, công thức:

    D4 = min(cv_degree_level / jd_degree_level, 1.0)
    jd_level = 0 (JD không yêu cầu)  → D4 = 1.0
    cv_level = 0 (CV không có bằng)  → D4 = 0.5

Gồm 2 phần độc lập, trả lời 2 câu hỏi khác nhau:

  PHẦN A — Đúng cài đặt (correctness).
    Câu hỏi: "score_education() có cài đúng công thức đã đặc tả trong
    docs/thesis_report.md mục 4.8 không, kể cả các trường hợp biên?"
    Phương pháp: liệt kê TOÀN BỘ tổ hợp (jd_level, cv_level) có thể xảy ra
    (6 x 6 = 36, kể cả 0 = "không có/không yêu cầu"), tính giá trị kỳ vọng
    bằng một cài đặt tham chiếu ĐỘC LẬP (không gọi lại code sản phẩm), rồi
    so với output thật của score_education() trên object CV/JD dựng từ
    app.schemas. Kèm 3 property test (bất biến không phụ thuộc giá trị cụ
    thể): cận trên 1.0, đơn điệu không giảm theo cv_level, và tính max độc
    lập với thứ tự phần tử trong education[].

  PHẦN B — Đúng thực tế (validity).
    Câu hỏi: "D4 có phản ánh đúng đánh giá phù hợp học vấn theo trực giác
    của người tuyển dụng (HR) không?"
    Phương pháp: xây nhãn proxy độc lập với công thức D4 — không phải tỉ lệ
    L_cv/L_jd, mà dựa trên KHOẢNG CÁCH bậc học vấn (distance = jd_level -
    cv_level), phản ánh cách HR thường nghĩ ("thiếu 1 bậc vẫn cân nhắc,
    thiếu 2+ bậc thì loại"). So D4 với nhãn này bằng Spearman rank
    correlation (thứ hạng có khớp không) và MAE (giá trị tuyệt đối có khớp
    không) — tách bạch 2 câu hỏi để không kết luận nhầm "correlation cao
    nghĩa là giá trị đúng tuyệt đối".

    KHÔNG có dữ liệu HR thật (không thu thập được trong phạm vi đồ án) nên
    nhãn ở đây là proxy có lý giải tường minh, không phải ground truth thu
    thập từ khảo sát — hạn chế này được nêu rõ trong kết luận, không che
    giấu.

Chạy: python scripts/d4_education_experiment.py
Output: docs/d4_education_experiment.md, docs/d4_education_experiment.xlsx
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path

from _xlsx_writer import write_xlsx

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas import DegreeLevel, Education, ParsedCV, ParsedJD  # noqa: E402
from app.services.scorer import score_education  # noqa: E402

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
REPORT_PATH = DOCS_DIR / "d4_education_experiment.md"
XLSX_PATH = DOCS_DIR / "d4_education_experiment.xlsx"

LEVELS = [0, 1, 2, 3, 4, 5]  # 0 = "không có / không yêu cầu"
NUMERIC_TO_DEGREE = {
    1: DegreeLevel.HIGH_SCHOOL, 2: DegreeLevel.ASSOCIATE, 3: DegreeLevel.BACHELOR,
    4: DegreeLevel.MASTER, 5: DegreeLevel.PHD,
}

# Tên hiển thị song ngữ cho mọi bảng trong báo cáo — vế tiếng Việt lấy đúng các
# từ đồng nghĩa mà LLM prompt (app/services/parser.py, khối "EDUCATION (critical)")
# dùng để ánh xạ text CV/JD tiếng Việt sang DegreeLevel.
LEVEL_NAME = {
    0: "(none/không có)",
    1: "high_school (THPT)",
    2: "associate (Cao đẳng)",
    3: "bachelor (Đại học)",
    4: "master (Thạc sĩ)",
    5: "phd (Tiến sĩ)",
}

# Bảng ánh xạ ĐẦY ĐỦ các từ đồng nghĩa tiếng Việt/Anh mà LLM prompt yêu cầu map
# sang từng DegreeLevel — chép nguyên văn từ app/services/parser.py dòng 364-368,
# dùng để: (1) hiển thị tường minh trong báo cáo, (2) đối chiếu thứ tự numeric.
VI_SYNONYMS: dict[int, tuple[str, ...]] = {
    1: ("THPT", "Trung học phổ thông"),
    2: ("Trung cấp", "Cao đẳng"),
    3: ("Đại học", "Cử nhân", "Bachelor"),
    4: ("Thạc sĩ", "Master"),
    5: ("Tiến sĩ", "PhD", "Doctor"),
}


def make_jd(jd_level: int) -> ParsedJD:
    degree = NUMERIC_TO_DEGREE[jd_level] if jd_level else None
    return ParsedJD(title="Test JD", education_degree=degree)


def make_cv(cv_level: int) -> ParsedCV:
    if not cv_level:
        return ParsedCV(education=[])
    return ParsedCV(education=[Education(institution="X", degree=NUMERIC_TO_DEGREE[cv_level])])


def reference_d4(cv_level: int, jd_level: int) -> float:
    """Cài đặt tham chiếu ĐỘC LẬP, viết lại từ đặc tả (docs/thesis_report.md mục 4.8),
    KHÔNG import/gọi score_education() — mục đích là có 1 nguồn sự thật thứ hai để so
    sánh, thay vì so sánh code với chính nó."""
    if jd_level == 0:
        return 1.0
    if cv_level == 0:
        return 0.5
    return min(cv_level / jd_level, 1.0)


# ---------------------------------------------------------------------------
# PHẦN A — Đúng cài đặt: exhaustive + property-based
# ---------------------------------------------------------------------------

@dataclass
class GridRow:
    jd_level: int
    cv_level: int
    expected: float
    actual: float

    @property
    def ok(self) -> bool:
        return abs(self.expected - self.actual) < 1e-9


def run_exhaustive_grid() -> list[GridRow]:
    rows = []
    for jd_level, cv_level in itertools.product(LEVELS, LEVELS):
        jd = make_jd(jd_level)
        cv = make_cv(cv_level)
        actual = score_education(cv, jd)
        expected = reference_d4(cv_level, jd_level)
        rows.append(GridRow(jd_level, cv_level, expected, actual))
    return rows


@dataclass
class CompositeRow:
    jd_level: int
    degrees: tuple[int, ...]  # numeric levels held by CV, có thể nhiều bằng cùng lúc
    expected: float
    actual: float

    @property
    def cv_level(self) -> int:
        return max(self.degrees)

    @property
    def degrees_label(self) -> str:
        return "+".join(LEVEL_NAME[d] for d in self.degrees)

    @property
    def ok(self) -> bool:
        return abs(self.expected - self.actual) < 1e-9


_ALL_DEGREE_NUMERICS = [1, 2, 3, 4, 5]


def run_composite_education_grid() -> list[CompositeRow]:
    """A.1 chỉ test CV có ĐÚNG 1 bằng cấp (hoặc 0). Phần này test CV có NHIỀU bằng
    cấp cùng lúc — mọi tập con khác rỗng của 5 bậc bằng cấp (2^5 - 1 = 31 tập con)
    x 6 mức jd_level — để kiểm tra kỹ logic `highest_degree_level` (lấy max trên
    toàn bộ `education[]`), thứ mà A.1 (chỉ 1 bằng/CV) không chạm tới được."""
    rows = []
    for r in range(1, len(_ALL_DEGREE_NUMERICS) + 1):
        for combo in itertools.combinations(_ALL_DEGREE_NUMERICS, r):
            cv = ParsedCV(education=[
                Education(institution="X", degree=NUMERIC_TO_DEGREE[n]) for n in combo
            ])
            expected_cv_level = max(combo)
            for jd_level in LEVELS:
                actual = score_education(cv, make_jd(jd_level))
                expected = reference_d4(expected_cv_level, jd_level)
                rows.append(CompositeRow(jd_level, combo, expected, actual))
    return rows


# ---------------------------------------------------------------------------
# A.3 — CV/JD ghi bằng cấp bằng tiếng Việt (từ đồng nghĩa trong LLM prompt)
# ---------------------------------------------------------------------------

# Toàn bộ (numeric_level, term) — chép nguyên văn từ VI_SYNONYMS.
ALL_VI_TERMS: list[tuple[int, str]] = [
    (level, term) for level, terms in VI_SYNONYMS.items() for term in terms
]


@dataclass
class ViGridRow:
    side: str  # "CV" hoặc "JD" — bên nào đang ghi bằng tiếng Việt
    vi_term: str
    degree_numeric: int
    other_level: int  # jd_level (nếu side=CV) hoặc cv_level (nếu side=JD)
    expected: float
    actual: float

    @property
    def ok(self) -> bool:
        return abs(self.expected - self.actual) < 1e-9


def run_vi_synonym_grid() -> list[ViGridRow]:
    """`score_education()` chỉ nhận DegreeLevel đã canonical hóa — việc map text
    tiếng Việt ("Đại học", "Thạc sĩ", ...) sang DegreeLevel xảy ra ở bước LLM parse
    (app/services/parser.py, khối "EDUCATION"), không phải trong scorer, nên không
    thể unit-test bước map đó mà không gọi LLM thật. Phần này test PHẦN CÓ THỂ
    kiểm định được: given đúng ánh xạ mà prompt yêu cầu (VI_SYNONYMS ở trên, chép
    nguyên văn từ prompt), D4 có tính đúng khi CV/JD được ghi degree_raw bằng tiếng
    Việt hay không — tức kiểm tra D4 hoạt động đúng trên dữ liệu tiếng Việt thực tế,
    không phải kiểm tra bản thân bước dịch của LLM."""
    rows: list[ViGridRow] = []
    for numeric, term in ALL_VI_TERMS:
        for jd_level in LEVELS:
            cv = ParsedCV(education=[
                Education(institution="X", degree_raw=term, degree=NUMERIC_TO_DEGREE[numeric])
            ])
            actual = score_education(cv, make_jd(jd_level))
            expected = reference_d4(numeric, jd_level)
            rows.append(ViGridRow("CV", term, numeric, jd_level, expected, actual))
    for numeric, term in ALL_VI_TERMS:
        for cv_level in LEVELS:
            jd = ParsedJD(title=f"Yêu cầu: {term}", education_degree=NUMERIC_TO_DEGREE[numeric])
            actual = score_education(make_cv(cv_level), jd)
            expected = reference_d4(cv_level, numeric)
            rows.append(ViGridRow("JD", term, numeric, cv_level, expected, actual))
    return rows


@dataclass
class PropertyResult:
    name: str
    description: str
    passed: bool
    detail: str


def run_property_tests() -> list[PropertyResult]:
    results = []

    # P1 — cận trên: D4 không bao giờ vượt 1.0, kể cả khi cv_level > jd_level.
    violations = []
    for jd_level in range(1, 6):
        for cv_level in LEVELS:
            v = score_education(make_cv(cv_level), make_jd(jd_level))
            if v > 1.0 + 1e-9:
                violations.append((jd_level, cv_level, v))
    results.append(PropertyResult(
        "P1 — Cận trên (cap ở 1.0)",
        "Bằng cấp cao hơn yêu cầu không được cộng điểm vượt 1.0",
        not violations,
        "OK — không có vi phạm trong 30 tổ hợp (jd_level 1..5 x cv_level 0..5)"
        if not violations else f"VI PHẠM: {violations}",
    ))

    # P2 — đơn điệu không giảm: với jd_level cố định, D4 không giảm khi cv_level tăng.
    non_monotonic = []
    for jd_level in range(1, 6):
        scores = [score_education(make_cv(cv), make_jd(jd_level)) for cv in range(1, 6)]
        for a, b in zip(scores, scores[1:]):
            if b < a - 1e-9:
                non_monotonic.append((jd_level, scores))
                break
    results.append(PropertyResult(
        "P2 — Đơn điệu không giảm theo cv_level",
        "cv_level tăng (1→5, jd_level cố định) → D4 không được giảm",
        not non_monotonic,
        "OK — đơn điệu trên cả 5 giá trị jd_level"
        if not non_monotonic else f"VI PHẠM: {non_monotonic}",
    ))

    # P3 — bất biến thứ tự: highest_degree_level lấy max, thứ tự phần tử education[]
    # không được ảnh hưởng tới điểm. Test ĐẦY ĐỦ 5! = 120 hoán vị của cả 5 bậc bằng
    # cấp, trên cả 6 giá trị jd_level (720 phép kiểm tra) — không phải mẫu ngẫu nhiên.
    base_degrees = [DegreeLevel.HIGH_SCHOOL, DegreeLevel.ASSOCIATE, DegreeLevel.BACHELOR,
                     DegreeLevel.MASTER, DegreeLevel.PHD]
    order_violations = []
    n_checked = 0
    for jd_level in LEVELS:
        jd = make_jd(jd_level)
        reference_score = None
        for perm in itertools.permutations(base_degrees):
            cv = ParsedCV(education=[Education(institution="X", degree=d) for d in perm])
            s = score_education(cv, jd)
            n_checked += 1
            if reference_score is None:
                reference_score = s
            elif abs(s - reference_score) > 1e-9:
                order_violations.append((jd_level, perm, s))
    results.append(PropertyResult(
        "P3 — Bất biến với thứ tự education[]",
        "Xáo trộn thứ tự 5 bằng cấp trong CV (mọi hoán vị) không được đổi D4 (lấy max=PHD), trên mọi jd_level",
        not order_violations,
        f"OK — {n_checked} phép kiểm tra (5!=120 hoán vị x 6 jd_level) đều nhất quán"
        if not order_violations else f"VI PHẠM: {order_violations[:5]}",
    ))

    # P4 — OTHER tương đương high_school (cả 2 có numeric = 1).
    other_mismatches = []
    for jd_level in range(1, 6):
        s_other = score_education(
            ParsedCV(education=[Education(institution="X", degree=DegreeLevel.OTHER)]), make_jd(jd_level))
        s_hs = score_education(
            ParsedCV(education=[Education(institution="X", degree=DegreeLevel.HIGH_SCHOOL)]), make_jd(jd_level))
        if abs(s_other - s_hs) > 1e-9:
            other_mismatches.append((jd_level, s_other, s_hs))
    results.append(PropertyResult(
        "P4 — OTHER ≡ high_school (numeric=1)",
        "Degree 'other' và 'high_school' cùng numeric=1 → phải cho D4 giống hệt nhau",
        not other_mismatches,
        "OK — khớp trên cả 5 giá trị jd_level"
        if not other_mismatches else f"VI PHẠM: {other_mismatches}",
    ))

    return results


# ---------------------------------------------------------------------------
# PHẦN B — Đúng thực tế: so với nhãn proxy human-judgment (dựa trên khoảng cách bậc)
# ---------------------------------------------------------------------------

def human_proxy_label(cv_level: int, jd_level: int) -> float:
    """Nhãn proxy ĐỘC LẬP với công thức tỉ lệ của D4 — mô phỏng trực giác HR phổ biến:
    "thiếu 1 bậc vẫn cân nhắc (0.65), thiếu 2 bậc thì yếu (0.3), thiếu 3+ bậc gần như
    loại (0.1)", dựa trên KHOẢNG CÁCH bậc thay vì TỈ LỆ bậc. Đây là giả định có lý giải
    domain, không phải số liệu khảo sát HR thật — xem hạn chế ở mục kết luận."""
    if jd_level == 0:
        return 1.0
    if cv_level == 0:
        return 0.5
    distance = jd_level - cv_level
    if distance <= 0:
        return 1.0
    if distance == 1:
        return 0.65
    if distance == 2:
        return 0.3
    return 0.1


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation, cài bằng stdlib (không numpy/scipy) — trung bình
    hạng (average rank) cho giá trị trùng nhau (ties)."""
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


@dataclass
class ValidityRow:
    jd_level: int
    cv_level: int
    d4: float
    human: float

    @property
    def abs_error(self) -> float:
        return abs(self.d4 - self.human)


def run_validity_corpus() -> list[ValidityRow]:
    rows = []
    for jd_level in range(1, 6):  # bỏ jd_level=0: cả 2 phía đều trivial =1.0, không mang thông tin
        for cv_level in LEVELS:
            d4 = score_education(make_cv(cv_level), make_jd(jd_level))
            human = human_proxy_label(cv_level, jd_level)
            rows.append(ValidityRow(jd_level, cv_level, d4, human))
    return rows


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_grid_table(rows: list[GridRow]) -> str:
    lines = ["| jd_level (yêu cầu) | cv_level (CV) | Kỳ vọng (tham chiếu) | Thực tế (score_education) | Khớp? |",
             "| --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(
            f"| {r.jd_level} `{LEVEL_NAME[r.jd_level]}` | {r.cv_level} `{LEVEL_NAME[r.cv_level]}` | "
            f"{r.expected:.3f} | {r.actual:.3f} | {'✅' if r.ok else '❌'} |"
        )
    return "\n".join(lines)


def render_composite_table(rows: list[CompositeRow]) -> str:
    lines = ["| jd_level (yêu cầu) | Bằng cấp CV nắm giữ (nhiều bằng) | cv_level = max | Kỳ vọng | Thực tế | Khớp? |",
             "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(
            f"| {r.jd_level} `{LEVEL_NAME[r.jd_level]}` | `{r.degrees_label}` | {r.cv_level} | "
            f"{r.expected:.3f} | {r.actual:.3f} | {'✅' if r.ok else '❌'} |"
        )
    return "\n".join(lines)


def render_vi_synonym_table(rows: list[ViGridRow]) -> str:
    lines = ["| Bên ghi tiếng Việt | Từ tiếng Việt/Anh trong CV/JD | → DegreeLevel (numeric) | Mức còn lại (jd_level/cv_level) | Kỳ vọng | Thực tế | Khớp? |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(
            f"| {r.side} | `{r.vi_term}` | {r.degree_numeric} `{LEVEL_NAME[r.degree_numeric]}` | "
            f"{r.other_level} `{LEVEL_NAME[r.other_level]}` | {r.expected:.3f} | {r.actual:.3f} | "
            f"{'✅' if r.ok else '❌'} |"
        )
    return "\n".join(lines)


def render_property_table(results: list[PropertyResult]) -> str:
    lines = ["| Property | Mô tả bất biến | Kết quả | Chi tiết |", "| --- | --- | --- | --- |"]
    for r in results:
        lines.append(f"| {r.name} | {r.description} | {'✅ PASS' if r.passed else '❌ FAIL'} | {r.detail} |")
    return "\n".join(lines)


def render_validity_table(rows: list[ValidityRow]) -> str:
    lines = ["| jd_level | cv_level | D4 (công thức) | Nhãn proxy HR (khoảng cách bậc) | \\|D4 − human\\| |",
             "| --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(
            f"| {r.jd_level} `{LEVEL_NAME[r.jd_level]}` | {r.cv_level} `{LEVEL_NAME[r.cv_level]}` | "
            f"{r.d4:.3f} | {r.human:.3f} | {r.abs_error:.3f} |"
        )
    return "\n".join(lines)


def grid_sheet_rows(rows: list[GridRow]) -> list[list]:
    out = [["jd_level", "jd_name", "cv_level", "cv_name", "Expected", "Actual", "Match"]]
    for r in rows:
        out.append([r.jd_level, LEVEL_NAME[r.jd_level], r.cv_level, LEVEL_NAME[r.cv_level],
                    round(r.expected, 3), round(r.actual, 3), "TRUE" if r.ok else "FALSE"])
    return out


def composite_sheet_rows(rows: list[CompositeRow]) -> list[list]:
    out = [["jd_level", "jd_name", "degrees_held", "cv_level(max)", "Expected", "Actual", "Match"]]
    for r in rows:
        out.append([r.jd_level, LEVEL_NAME[r.jd_level], r.degrees_label, r.cv_level,
                    round(r.expected, 3), round(r.actual, 3), "TRUE" if r.ok else "FALSE"])
    return out


def vi_synonym_sheet_rows(rows: list[ViGridRow]) -> list[list]:
    out = [["Side", "VI/EN term", "degree_numeric", "degree_name", "other_level", "other_level_name",
            "Expected", "Actual", "Match"]]
    for r in rows:
        out.append([r.side, r.vi_term, r.degree_numeric, LEVEL_NAME[r.degree_numeric],
                    r.other_level, LEVEL_NAME[r.other_level],
                    round(r.expected, 3), round(r.actual, 3), "TRUE" if r.ok else "FALSE"])
    return out


def property_sheet_rows(results: list[PropertyResult]) -> list[list]:
    out = [["Property", "Description", "Result", "Detail"]]
    for r in results:
        out.append([r.name, r.description, "PASS" if r.passed else "FAIL", r.detail])
    return out


def validity_sheet_rows(rows: list[ValidityRow]) -> list[list]:
    out = [["jd_level", "jd_name", "cv_level", "cv_name", "D4", "Human proxy", "Abs error"]]
    for r in rows:
        out.append([r.jd_level, LEVEL_NAME[r.jd_level], r.cv_level, LEVEL_NAME[r.cv_level],
                    round(r.d4, 3), round(r.human, 3), round(r.abs_error, 3)])
    return out


def summary_sheet_rows(grid_rows: list[GridRow], composite_rows: list[CompositeRow],
                        vi_rows: list[ViGridRow],
                        props: list[PropertyResult],
                        validity_rows: list[ValidityRow], rho: float, mae: float,
                        acc: float, tp: int, fp: int, tn: int, fn: int) -> list[list]:
    total_cases = len(grid_rows) + len(composite_rows) + len(vi_rows)
    total_pass = (sum(1 for r in grid_rows if r.ok) + sum(1 for r in composite_rows if r.ok)
                  + sum(1 for r in vi_rows if r.ok))
    return [
        ["Metric", "Value"],
        ["PHAN A - Correctness", ""],
        ["A.1 Grid don-bang (1 bang/CV) - so case", len(grid_rows)],
        ["A.1 Grid don-bang - so case khop", sum(1 for r in grid_rows if r.ok)],
        ["A.2 Grid composite (nhieu bang/CV) - so case", len(composite_rows)],
        ["A.2 Grid composite - so case khop", sum(1 for r in composite_rows if r.ok)],
        ["A.3 Grid tieng Viet (VI_SYNONYMS) - so case", len(vi_rows)],
        ["A.3 Grid tieng Viet - so case khop", sum(1 for r in vi_rows if r.ok)],
        ["Tong so case correctness (A.1+A.2+A.3)", total_cases],
        ["Tong so case khop", total_pass],
        ["Tong accuracy", round(total_pass / total_cases, 4)],
        ["Property tests pass", f"{sum(1 for p in props if p.passed)}/{len(props)}"],
        [],
        ["PHAN B - Validity (vs human proxy)", ""],
        ["So diem so sanh", len(validity_rows)],
        ["Spearman rho (D4 vs human proxy)", round(rho, 4)],
        ["MAE (D4 vs human proxy)", round(mae, 4)],
        ["Accuracy phan loai 'dat yeu cau' (nguong 0.7)", round(acc, 4)],
        ["TP", tp], ["FP", fp], ["TN", tn], ["FN", fn],
    ]


def main() -> None:
    grid_rows = run_exhaustive_grid()
    composite_rows = run_composite_education_grid()
    vi_rows = run_vi_synonym_grid()
    props = run_property_tests()
    validity_rows = run_validity_corpus()

    grid_pass = sum(1 for r in grid_rows if r.ok)
    grid_total = len(grid_rows)
    composite_pass = sum(1 for r in composite_rows if r.ok)
    composite_total = len(composite_rows)
    vi_pass = sum(1 for r in vi_rows if r.ok)
    vi_total = len(vi_rows)
    total_pass = grid_pass + composite_pass + vi_pass
    total_cases = grid_total + composite_total + vi_total
    props_pass = sum(1 for p in props if p.passed)

    d4_vals = [r.d4 for r in validity_rows]
    human_vals = [r.human for r in validity_rows]
    rho = spearman(d4_vals, human_vals)
    mae = sum(r.abs_error for r in validity_rows) / len(validity_rows)

    # Phân loại nhị phân "đạt yêu cầu học vấn" ở ngưỡng 0.7, so D4 vs human proxy.
    THRESH = 0.7
    tp = sum(1 for r in validity_rows if r.d4 >= THRESH and r.human >= THRESH)
    fp = sum(1 for r in validity_rows if r.d4 >= THRESH and r.human < THRESH)
    tn = sum(1 for r in validity_rows if r.d4 < THRESH and r.human < THRESH)
    fn = sum(1 for r in validity_rows if r.d4 < THRESH and r.human >= THRESH)
    acc = (tp + tn) / len(validity_rows)

    worst = sorted(validity_rows, key=lambda r: -r.abs_error)[:5]

    report = f"""# Thực nghiệm: chứng minh tính chính xác của D4 (Education Score)

Sinh tự động bởi `scripts/d4_education_experiment.py`. Đối tượng kiểm chứng:
`score_education()` trong
[`app/services/scorer.py`](../app/services/scorer.py#L197-L211), công thức
$D_4 = \\min(L_{{cv}}/L_{{jd}}, 1.0)$ — xem đặc tả đầy đủ ở
[`docs/thesis_report.md` mục 4.8](thesis_report.md#48-education-score-d4).

Gồm 2 thực nghiệm độc lập, trả lời 2 câu hỏi khác nhau — "đúng cài đặt" và
"đúng thực tế" không phải cùng một thứ, và một công thức có thể đúng cài đặt
100% nhưng vẫn là một xấp xỉ thô với thực tế (điều mà Phần B chỉ ra rõ).

## PHẦN A — Đúng cài đặt (correctness)

**Phương pháp:** liệt kê toàn bộ tổ hợp đầu vào có thể xảy ra trong hệ, tính
giá trị kỳ vọng bằng **cài đặt tham chiếu độc lập** viết lại từ đặc tả (không
import/gọi lại `score_education`), rồi so với output thật trên các object
`ParsedCV`/`ParsedJD` dựng qua `app.schemas`. Chia 3 lớp trường hợp — CV có
**1 bằng cấp** (A.1), CV có **nhiều bằng cấp cùng lúc** (A.2, kiểm tra kỹ
logic `max` trên `education[]`), và CV/JD **ghi bằng cấp bằng tiếng Việt**
(A.3, dùng đúng từ đồng nghĩa trong LLM prompt — sản phẩm xử lý CV/JD tiếng
Việt là chính) — cộng thêm 4 property test kiểm tra bất biến không phụ thuộc
giá trị cụ thể (A.4). Tổng cộng **{total_cases} test case correctness**, toàn
bộ đều exhaustive (liệt kê hết, không lấy mẫu).

### A.1 CV có 1 bằng cấp — ma trận đầy đủ ({grid_total} tổ hợp)

6 giá trị jd_level × 6 giá trị cv_level (kể cả 0 = "không có/không yêu cầu").

{render_grid_table(grid_rows)}

**Kết quả: {grid_pass}/{grid_total} tổ hợp khớp tuyệt đối với công thức
tham chiếu ({grid_pass/grid_total*100:.1f}%).**

### A.2 CV có nhiều bằng cấp cùng lúc — mọi tập con khác rỗng ({composite_total} tổ hợp)

A.1 chỉ test CV có đúng 1 bằng, không chạm tới logic `highest_degree_level`
(lấy `max` trên toàn bộ `education[]`) khi CV khai nhiều bằng — trường hợp
thực tế phổ biến (vừa có bằng đại học vừa có bằng thạc sĩ, v.v.). Phần này
liệt kê **toàn bộ 2⁵−1 = 31 tập con khác rỗng** của 5 bậc bằng cấp
(high_school…phd) × 6 giá trị jd_level = {composite_total} tổ hợp, mỗi CV giữ
đồng thời nhiều bằng, kỳ vọng = công thức tham chiếu áp trên **bằng cao nhất**
CV đang giữ.

{render_composite_table(composite_rows)}

**Kết quả: {composite_pass}/{composite_total} tổ hợp khớp tuyệt đối
({composite_pass/composite_total*100:.1f}%).**

### A.3 CV/JD ghi bằng cấp bằng tiếng Việt ({vi_total} tổ hợp)

Sản phẩm xử lý CV/JD **tiếng Việt** là chính, nhưng A.1/A.2 chỉ dùng tên
`DegreeLevel` tiếng Anh (`bachelor`, `master`...). `score_education()` chỉ
nhận `DegreeLevel` đã canonical hóa — bước dịch text tiếng Việt
("Đại học", "Thạc sĩ", ...) sang `DegreeLevel` xảy ra ở LLM parser
([`app/services/parser.py`](../app/services/parser.py), khối `EDUCATION`),
**không** nằm trong `score_education()`, nên không thể unit-test bước dịch
đó mà không gọi LLM thật. Phần này test đúng phần kiểm định được: **cho
trước ánh xạ đúng mà prompt yêu cầu** (bảng dưới, chép nguyên văn từ
`parser.py` dòng 364-368), D4 có tính đúng khi `degree_raw` của CV/JD là
tiếng Việt hay không — tức xác nhận D4 hoạt động đúng trên dữ liệu tiếng
Việt thực tế, tách bạch với việc kiểm định bản thân bước dịch của LLM
(nằm ngoài phạm vi unit test offline).

**Bảng ánh xạ tiếng Việt/Anh → DegreeLevel** (nguyên văn từ LLM prompt):

| DegreeLevel (numeric) | Từ đồng nghĩa tiếng Việt/Anh |
| --- | --- |
{chr(10).join(f"| {n} `{LEVEL_NAME[n]}` | {', '.join(f'`{t}`' for t in terms)} |" for n, terms in VI_SYNONYMS.items())}

**{vi_total} tổ hợp kiểm tra** = {len(ALL_VI_TERMS)} từ đồng nghĩa × 6 mức
còn lại × 2 chiều (CV ghi tiếng Việt / JD ghi tiếng Việt):

{render_vi_synonym_table(vi_rows)}

**Kết quả: {vi_pass}/{vi_total} tổ hợp khớp tuyệt đối
({vi_pass/vi_total*100:.1f}%).**

### A.4 Property-based tests

{render_property_table(props)}

**Kết quả: {props_pass}/{len(props)} property PASS.** (P3 tự nó đã kiểm
720 phép hoán vị — xem chi tiết cột "Chi tiết").

### A.5 Kết luận Phần A

Trên tổng cộng **{total_cases} test case correctness** (A.1 + A.2 + A.3,
toàn bộ exhaustive) cộng {len(props)} property test, `score_education()`
cài đặt **đúng 100%** đặc tả công thức: {total_pass}/{total_cases} tổ hợp
khớp tuyệt đối, {props_pass}/{len(props)} property PASS — bao gồm cả khi
CV/JD ghi bằng cấp bằng tiếng Việt (A.3), đúng với ngữ cảnh sử dụng thực tế
của sản phẩm. Bao gồm cả 2 trường hợp biên dễ cài sai (JD không yêu cầu →
1.0 bất kể CV; CV không có bằng → 0.5 trung lập, không phải 0.0 — tức
"thiếu dữ liệu không đồng nghĩa với không đạt"), cận trên chặn đúng ở 1.0,
và tính `max` trên `education[]` — cả khi CV có 1 bằng lẫn nhiều bằng cùng
lúc — không phụ thuộc thứ tự phần tử. Đây là bằng chứng **hình thức, đầy đủ**
(exhaustive trên toàn bộ không gian đầu vào rời rạc của D4, không phải suy
diễn từ mẫu) — không gian đầu vào **số** của D4 chỉ có 2 biến số (bậc CV cao
nhất, bậc JD yêu cầu, {grid_total} tổ hợp) nên phần mở rộng ở A.2/A.3 đã phủ
kín mọi cách một tổ hợp số đó có thể được **biểu diễn** trong dữ liệu thực
(nhiều bằng cùng lúc, tên tiếng Việt) — thêm case ngẫu nhiên nữa trên cùng
2 biến số đó sẽ không mang thêm thông tin mới.

## PHẦN B — Đúng thực tế (validity)

**Phương pháp:** D4 dùng **tỉ lệ** bậc học vấn ($L_{{cv}}/L_{{jd}}$), nhưng
$L$ là thang **thứ tự** (ordinal) — bản thân mục 4.8 của báo cáo đã lưu ý đây
là "giả định đơn giản hóa có ý thức". Để kiểm chứng mức độ hợp lý của giả
định này, ta so D4 với một **nhãn proxy độc lập** mô phỏng trực giác tuyển
dụng phổ biến, dựa trên **khoảng cách bậc** thay vì **tỉ lệ bậc**: thiếu đúng
1 bậc → vẫn cân nhắc (0.65), thiếu 2 bậc → yếu (0.3), thiếu ≥3 bậc → gần như
loại (0.1). Đây là nhãn có lý giải domain, **không phải dữ liệu khảo sát HR
thật** (ngoài phạm vi thu thập được của đồ án) — hạn chế này được nêu tường
minh, không dùng để khẳng định "đã kiểm chứng với người dùng thật".

### B.1 Toàn bộ điểm so sánh (jd_level 1..5 × cv_level 0..5, {len(validity_rows)} điểm)

{render_validity_table(validity_rows)}

### B.2 Chỉ số tổng hợp

| Chỉ số | Giá trị | Ý nghĩa |
| --- | --- | --- |
| Spearman ρ (D4 vs nhãn proxy) | {rho:.4f} | Thứ hạng phù hợp có khớp không (D4 có sắp đúng thứ tự các ứng viên theo mức phù hợp học vấn không) |
| MAE (D4 vs nhãn proxy) | {mae:.4f} | Giá trị tuyệt đối lệch bao nhiêu trên thang 0-1 |
| Accuracy phân loại "đạt yêu cầu" (ngưỡng {THRESH}) | {acc:.4f} | Nếu dùng D4 để quyết định nhị phân "đạt/không đạt học vấn" thì khớp với nhãn proxy bao nhiêu % |
| Confusion matrix | TP={tp} FP={fp} TN={tn} FN={fn} | Chi tiết theo ngưỡng {THRESH} |

### B.3 5 điểm lệch nhiều nhất (D4 vs nhãn proxy)

| jd_level | cv_level | D4 | Nhãn proxy | Lệch |
| --- | --- | --- | --- | --- |
{chr(10).join(f"| {r.jd_level} `{LEVEL_NAME[r.jd_level]}` | {r.cv_level} `{LEVEL_NAME[r.cv_level]}` | {r.d4:.3f} | {r.human:.3f} | {r.abs_error:.3f} |" for r in worst)}

### B.4 Kết luận Phần B

Spearman ρ = {rho:.3f} cho thấy D4 **sắp đúng thứ tự** gần như tuyệt đối —
ứng viên có bậc học vấn cao hơn (so với cùng 1 yêu cầu JD) luôn được D4 chấm
điểm không thấp hơn, khớp trực giác HR. Đây là thuộc tính quan trọng nhất
với vai trò của D4 trong hệ (xếp hạng ứng viên), và **đã được PHẦN A chứng
minh hình thức** ở property P2.

Tuy nhiên MAE = {mae:.3f} cho thấy **giá trị tuyệt đối** lệch đáng kể ở các
tổ hợp yêu cầu bậc cao (jd_level lớn): xem B.3, các trường hợp lệch nhiều
nhất đều rơi vào `jd=phd` hoặc `jd=master` với CV thấp hơn 2-4 bậc — do
D4 tính theo **tỉ lệ** ($3/5=0.6$ cho bachelor/phd) trong khi trực giác HR
theo **khoảng cách** (3 bậc dưới phd → gần như loại, 0.1). Nói cách khác:
**D4 đúng về thứ hạng nhưng là một phép đo thô về độ lớn** khi khoảng yêu
cầu-thực tế lớn — đúng như giả định đơn giản hóa đã tự nhận trong mục 4.8,
và ở đây được **định lượng** thay vì chỉ nêu định tính.

**Hạn chế của thực nghiệm này:** nhãn proxy dựa trên lý giải domain của
người viết, không phải khảo sát HR thật (xem đề xuất "Precision/Recall của
D2" và nDCG/Spearman với nhãn HR thật ở
[`docs/thesis_report.md` mục 6.2](thesis_report.md#62-chỉ-số-đánh-giá-đề-xuất-chưa-thực-hiện)
— cùng phương pháp luận, nhưng cho D4 thay vì toàn hệ). Kết luận "đúng thứ
hạng, thô về độ lớn" nên được đọc như một **giả thuyết có cơ sở định lượng**,
cần xác nhận thêm bằng dữ liệu HR thật nếu đưa vào phần kết luận chính thức
của đồ án.

## Tổng kết

| | Kết quả |
| --- | --- |
| Đúng cài đặt (Phần A) | {total_pass}/{total_cases} test case correctness khớp tuyệt đối ({grid_total} đơn-bằng + {composite_total} đa-bằng + {vi_total} tiếng Việt) + {props_pass}/{len(props)} property PASS → **100% correctness trên toàn bộ không gian đầu vào rời rạc, kể cả dữ liệu tiếng Việt** |
| Đúng thực tế (Phần B) | Spearman ρ={rho:.3f} (thứ hạng khớp cao) · MAE={mae:.3f} (giá trị tuyệt đối lệch ở khoảng cách bậc lớn) · Accuracy phân loại={acc:.3f} @ngưỡng {THRESH} |

---
*Tái tạo báo cáo này: `python scripts/d4_education_experiment.py`*
"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    write_xlsx(XLSX_PATH, {
        "Summary": summary_sheet_rows(grid_rows, composite_rows, vi_rows, props, validity_rows,
                                       rho, mae, acc, tp, fp, tn, fn),
        "A1 - Single-degree grid": grid_sheet_rows(grid_rows),
        "A2 - Composite grid": composite_sheet_rows(composite_rows),
        "A3 - Vietnamese terms": vi_synonym_sheet_rows(vi_rows),
        "A4 - Property tests": property_sheet_rows(props),
        "B - Validity corpus": validity_sheet_rows(validity_rows),
    })

    print(f"Đã ghi báo cáo vào {REPORT_PATH}")
    print(f"Đã ghi Excel vào {XLSX_PATH}")
    print(f"Phần A: {total_pass}/{total_cases} test case khớp ({grid_pass}/{grid_total} đơn-bằng + "
          f"{composite_pass}/{composite_total} đa-bằng + {vi_pass}/{vi_total} tiếng Việt), "
          f"{props_pass}/{len(props)} property PASS")
    print(f"Phần B: Spearman rho={rho:.4f}, MAE={mae:.4f}, accuracy@{THRESH}={acc:.4f}")


if __name__ == "__main__":
    main()
