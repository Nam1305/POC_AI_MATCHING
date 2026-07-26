"""
Đóng bắc cầu (transitive closure) cho skill_implies.json — chạy TAY, 1 lần,
commit output. Sau khi chạy, mỗi skill liệt kê ĐẦY ĐỦ mọi skill nó kéo theo kể
cả gián tiếp (nestjs -> typescript -> javascript  =>  nestjs cũng liệt kê
javascript), để Layer 2 trong app/services/skill_matcher.py chỉ cần tra list
trực tiếp mà không bỏ sót.

Giữ NGUYÊN thứ tự cạnh trực tiếp do người viết; chỉ APPEND các cạnh dẫn xuất
mới (sorted) vào cuối mỗi list -> diff tối thiểu, dễ review cạnh nào là suy ra.

    python data/close_implies.py            # đóng bắc cầu + ghi đè file
    python data/close_implies.py --dry-run  # chỉ in số cạnh sẽ thêm, không ghi

Lưu ý: đồ thị implies là DAG (không chu trình) nên closure luôn dừng. Nếu về sau
sửa skill_implies.json bằng tay, NHỚ chạy lại script này để đóng bắc cầu lại.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

IMPLIES_FILE = Path(__file__).parent / "skill_implies.json"


def transitive_closure(graph: dict[str, list[str]]) -> dict[str, set[str]]:
    """Bao đóng bắc cầu một chiều. DAG nhỏ -> tới fixpoint sau vài vòng lặp."""
    closed: dict[str, set[str]] = {k: set(v) for k, v in graph.items()}
    changed = True
    while changed:
        changed = False
        for node, targets in closed.items():
            expanded = set(targets)
            for t in list(targets):
                expanded |= closed.get(t, set())  # t có thể là leaf -> set() rỗng
            expanded.discard(node)                # không để X -> X
            if expanded != targets:
                closed[node] = expanded
                changed = True
    return closed


def main() -> int:
    ap = argparse.ArgumentParser(description="Đóng bắc cầu skill_implies.json")
    ap.add_argument("--dry-run", action="store_true",
                    help="chỉ in thống kê, không ghi file")
    args = ap.parse_args()

    raw: dict[str, list[str]] = json.loads(IMPLIES_FILE.read_text(encoding="utf-8"))
    closed = transitive_closure(raw)

    # Giữ thứ tự cạnh gốc, append cạnh dẫn xuất mới (sorted) vào cuối.
    result: dict[str, list[str]] = {}
    added_total = 0
    for node, direct in raw.items():
        derived = sorted(closed[node] - set(direct))
        added_total += len(derived)
        result[node] = list(direct) + derived

    before = sum(len(v) for v in raw.values())
    after = sum(len(v) for v in result.values())
    print(f"Keys: {len(raw)} | cạnh trước: {before} | sau: {after} "
          f"(+{added_total} cạnh dẫn xuất)")
    changed_keys = [k for k in raw if result[k] != list(raw[k])]
    print(f"Số skill được bổ sung cạnh: {len(changed_keys)}")
    for k in changed_keys[:10]:
        print(f"  {k}: +{sorted(set(result[k]) - set(raw[k]))}")

    if args.dry_run:
        print("\n[dry-run] không ghi file.")
        return 0

    IMPLIES_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nĐã ghi: {IMPLIES_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
