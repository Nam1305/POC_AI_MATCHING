"""
Bổ sung data domain QA/QC (kiểm thử phần mềm) vào skill_data.json +
skill_implies.json — chạy TAY, 1 lần, commit output.

Lý do: skill_data/skill_implies gốc build từ tag lập trình Stack Overflow nên
thiếu taxonomy kiểm thử (test types, test design techniques, QA tools). Case QA
thực tế cho thấy Layer 1/2 vô dụng ở domain này (chỉ Layer 0 khớp chuỗi). Pack
này thêm:
  1. Canonical các loại test + kỹ thuật thiết kế test + vài tool còn thiếu
  2. Synonym gom biến thể cách viết về cùng canonical
  3. Implies (entailment) domain QA — CHỈ các cạnh "biết X chắc chắn biết Y"
     (precision-first: cạnh sai tệ hơn cạnh thiếu vì nó cho FULL credit)

An toàn/idempotent: KHÔNG ghi đè entry đã tồn tại (chỉ thêm mới, in cảnh báo khi
trùng). Sau khi chạy script này, PHẢI chạy tiếp `python data/close_implies.py`
để đóng bắc cầu lại.

    python data/add_qa_skills.py            # thêm + ghi 2 file
    python data/add_qa_skills.py --dry-run  # chỉ kiểm tra + in, không ghi
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
SKILL_DATA_FILE = DATA_DIR / "skill_data.json"
IMPLIES_FILE = DATA_DIR / "skill_implies.json"


# ── 1. Canonical QA tokens (value=None => key CHÍNH LÀ canonical) ────────────
# Chỉ liệt kê token CHƯA có (functional-testing/integration-testing/
# performance-testing/load-testing đã tồn tại nên không thêm lại).
QA_CANONICAL: list[str] = [
    # test types / levels
    "web-testing", "mobile-testing", "api-testing", "automation-testing",
    "manual-testing", "regression-testing", "smoke-testing", "sanity-testing",
    "system-testing", "acceptance-testing", "end-to-end-testing",
    "exploratory-testing", "usability-testing", "ui-testing",
    "security-testing", "stress-testing", "black-box-testing",
    "white-box-testing", "compatibility-testing",
    # test design / management
    "test-case-design", "test-execution", "test-planning", "test-reporting",
    "boundary-value-analysis", "equivalence-partitioning", "decision-table",
    "bug-tracking", "uat",
    # tools còn thiếu (làm implies key/value)
    "webdriverio", "k6", "locust", "selenium-webdriver",
]

# ── 2. Synonyms (syn -> canonical) — gom biến thể cách viết ──────────────────
QA_SYNONYMS: dict[str, str] = {
    # automation
    "test-automation": "automation-testing",
    "automated-testing": "automation-testing",
    "automation-test": "automation-testing",
    # api
    "api-test": "api-testing",
    "rest-api-testing": "api-testing",
    "apitesting": "api-testing",
    # mobile / web
    "mobile-app-testing": "mobile-testing",
    "mobile-application-testing": "mobile-testing",
    "web-app-testing": "web-testing",
    "web-application-testing": "web-testing",
    # end-to-end
    "e2e": "end-to-end-testing",
    "e2e-testing": "end-to-end-testing",
    "e2e-tests": "end-to-end-testing",
    "end-to-end": "end-to-end-testing",
    # ux / usability
    "ux-testing": "usability-testing",
    # test design / mgmt
    "test-design": "test-case-design",
    "test-plan": "test-planning",
    "decision-table-testing": "decision-table",
    "user-acceptance-testing": "uat",
    "user-acceptance-test": "uat",
    "acceptance-test": "acceptance-testing",
    # exec-type shorthands
    "smoke-test": "smoke-testing",
    "sanity-test": "sanity-testing",
    "regression-test": "regression-testing",
}

# ── 3. Implies (X -> Y: "biết X chắc chắn biết Y") — precision-first ─────────
# Key/value BẮT BUỘC là canonical (đã có trong skill_data hoặc thêm ở mục 1/2).
QA_IMPLIES: dict[str, list[str]] = {
    # kỹ thuật thiết kế test -> thiết kế test case
    "boundary-value-analysis": ["test-case-design"],
    "equivalence-partitioning": ["test-case-design"],
    "decision-table": ["test-case-design"],
    # tool tự động hóa -> automation testing
    "selenium-webdriver": ["automation-testing"],
    "cypress": ["automation-testing"],
    "playwright": ["automation-testing"],
    "webdriverio": ["automation-testing"],
    "cucumber": ["automation-testing"],
    "appium": ["automation-testing", "mobile-testing"],  # Appium = mobile automation
    # tool API -> api testing
    "postman": ["api-testing"],
    "rest-assured": ["api-testing"],
    # tool hiệu năng -> performance testing
    "jmeter": ["performance-testing"],
    "k6": ["performance-testing"],
    "locust": ["performance-testing"],
    "gatling": ["performance-testing"],
    # quan hệ loại test (subtype/synonym -> khái niệm rộng hơn)
    "black-box-testing": ["functional-testing"],   # black-box ≈ functional
    "end-to-end-testing": ["functional-testing"],  # E2E kiểm chức năng xuyên hệ thống
    "load-testing": ["performance-testing"],
    "stress-testing": ["performance-testing"],
}


def _canonical_in(skill_data: dict, token: str) -> bool:
    """token có phải 1 canonical hợp lệ trong skill_data (self hoặc value=None)?"""
    if token not in skill_data:
        return False
    v = skill_data[token]
    return v is None or v == token


def main() -> int:
    ap = argparse.ArgumentParser(description="Thêm data QA/QC")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sd: dict[str, str | None] = json.loads(SKILL_DATA_FILE.read_text(encoding="utf-8"))
    si: dict[str, list[str]] = json.loads(IMPLIES_FILE.read_text(encoding="utf-8"))

    added_canon = added_syn = added_impl = 0
    warns: list[str] = []

    # 1. canonical
    for tok in QA_CANONICAL:
        if tok in sd:
            warns.append(f"[skip canonical] {tok!r} đã tồn tại = {sd[tok]!r}")
        else:
            sd[tok] = None
            added_canon += 1

    # 2. synonyms
    for syn, canon in QA_SYNONYMS.items():
        if syn in sd:
            warns.append(f"[skip synonym] {syn!r} đã tồn tại = {sd[syn]!r}")
        elif not _canonical_in(sd, canon):
            warns.append(f"[BAD synonym] {syn!r} -> {canon!r} nhưng canon không hợp lệ")
        else:
            sd[syn] = canon
            added_syn += 1

    # 3. implies (merge, dedup, giữ thứ tự)
    for src, targets in QA_IMPLIES.items():
        cur = si.get(src, [])
        for t in targets:
            if t not in cur:
                cur.append(t)
                added_impl += 1
        si[src] = cur

    # ── Kiểm tra bất biến: mọi implies key/value phải là canonical hợp lệ ──
    errors: list[str] = []
    for src, targets in QA_IMPLIES.items():
        if not _canonical_in(sd, src) and sd.get(src) is None and src not in sd:
            errors.append(f"implies KEY {src!r} không có trong skill_data")
        for t in targets:
            if not _canonical_in(sd, t):
                errors.append(f"implies VALUE {t!r} (từ {src!r}) không phải canonical")

    print(f"Thêm: {added_canon} canonical, {added_syn} synonym, {added_impl} implies-edge")
    if warns:
        print(f"\nCảnh báo ({len(warns)}):")
        for w in warns:
            print("  " + w)
    if errors:
        print(f"\n❌ LỖI BẤT BIẾN ({len(errors)}) — KHÔNG ghi file:")
        for e in errors:
            print("  " + e)
        return 1

    if args.dry_run:
        print("\n[dry-run] không ghi file.")
        return 0

    SKILL_DATA_FILE.write_text(json.dumps(sd, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    IMPLIES_FILE.write_text(json.dumps(si, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print(f"\nĐã ghi {SKILL_DATA_FILE.name} + {IMPLIES_FILE.name}.")
    print("NHỚ chạy tiếp: python data/close_implies.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
