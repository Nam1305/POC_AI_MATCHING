"""
Bổ sung các alias/implies phổ thông mà bộ test D2 (tests/test_d2_skills.py) phát
hiện còn thiếu — KHÔNG thuộc domain QA (đã có add_qa_skills.py). Chạy TAY, 1 lần,
commit output. Sau đó PHẢI chạy `python data/close_implies.py` để đóng bắc cầu.

Gồm:
  - REST API: gom "restful-api(s)" / "rest-apis" về canonical "rest" (skill_data
    gốc chỉ có "rest-api" -> "rest", thiếu biến thể "restful").
  - PHP: thêm canonical "php" + cạnh implies "php-7 -> php" để mọi framework PHP
    (laravel/symfony/wordpress... vốn implies "php-7") cũng thỏa yêu cầu "PHP".
    (skill_data gốc chỉ có tag phiên bản "php-7", thiếu "php" chung.)

    python data/add_misc_skills.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
SKILL_DATA_FILE = DATA_DIR / "skill_data.json"
IMPLIES_FILE = DATA_DIR / "skill_implies.json"

MISC_CANONICAL: list[str] = ["php"]

MISC_SYNONYMS: dict[str, str] = {
    "restful-api": "rest",
    "restful-apis": "rest",
    "rest-apis": "rest",
}

MISC_IMPLIES: dict[str, list[str]] = {
    "php-7": ["php"],
}


def _canonical_in(sd: dict, tok: str) -> bool:
    return tok in sd and (sd[tok] is None or sd[tok] == tok)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sd = json.loads(SKILL_DATA_FILE.read_text(encoding="utf-8"))
    si = json.loads(IMPLIES_FILE.read_text(encoding="utf-8"))

    added_c = added_s = added_i = 0
    warns: list[str] = []

    for tok in MISC_CANONICAL:
        if tok in sd:
            warns.append(f"[skip canonical] {tok!r} đã tồn tại = {sd[tok]!r}")
        else:
            sd[tok] = None
            added_c += 1

    for syn, canon in MISC_SYNONYMS.items():
        if syn in sd:
            warns.append(f"[skip synonym] {syn!r} đã tồn tại = {sd[syn]!r}")
        elif not _canonical_in(sd, canon):
            warns.append(f"[BAD synonym] {syn!r} -> {canon!r} canon không hợp lệ")
        else:
            sd[syn] = canon
            added_s += 1

    for src, targets in MISC_IMPLIES.items():
        cur = si.get(src, [])
        for t in targets:
            if t not in cur:
                cur.append(t)
                added_i += 1
        si[src] = cur

    errors = []
    for src, targets in MISC_IMPLIES.items():
        for t in targets:
            if not _canonical_in(sd, t):
                errors.append(f"implies VALUE {t!r} (từ {src!r}) không phải canonical")

    print(f"Thêm: {added_c} canonical, {added_s} synonym, {added_i} implies-edge")
    for w in warns:
        print("  " + w)
    if errors:
        print("❌ LỖI BẤT BIẾN — không ghi:")
        for e in errors:
            print("  " + e)
        return 1

    if args.dry_run:
        print("[dry-run] không ghi.")
        return 0

    SKILL_DATA_FILE.write_text(json.dumps(sd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    IMPLIES_FILE.write_text(json.dumps(si, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Đã ghi. NHỚ chạy: python data/close_implies.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
