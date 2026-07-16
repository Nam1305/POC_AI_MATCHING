"""
Location Service — ước tính khoảng cách/thời gian di chuyển cho D5 (Location + Work Mode).

File này cung cấp 2 chức năng lõi phục vụ D5 (điểm số vị trí + hình thức
làm việc) trong scorer.py:
  1. Geocode địa chỉ (text) → tọa độ (lat/lng)
  2. Tính khoảng cách/thời gian lái xe giữa 2 tọa độ

Dùng 2 API công khai, miễn phí, không cần key:
  - Nominatim (OpenStreetMap) để geocode — https://nominatim.org/
  - OSRM public demo server để tính route lái xe — http://project-osrm.org/

Thiết kế stateless (không cache, không lưu DB) để khớp với kiến trúc chung
của service này (xem docs/Overview.md: "AI service is stateless, no DB, no
auth"). Mỗi lời gọi HTTP đều được bọc trong try/except kèm timeout; nếu lỗi
sẽ trả về None để nơi gọi (scorer.py) có thể fallback về điểm trung lập,
theo đúng cách xử lý lỗi từng-phần-tử (per-item error handling) đã dùng ở
những chỗ khác trong service (ví dụ /ai/parse-cv).
"""

from __future__ import annotations

import math

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL_TEMPLATE = "http://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}"

# Nominatim's usage policy requires a descriptive User-Agent identifying the
# application — requests without one are blocked with HTTP 403.
_USER_AGENT = "POC-AI-Matching/1.0 (CV-JD location scoring)"

_TIMEOUT_SECONDS = 5.0


def geocode(address_text: str) -> dict | None:
    """
    Geocode một địa chỉ tiếng Việt (chuyển từ text sang tọa độ) qua Nominatim.

    Cách làm:
      1. Thêm ", Vietnam" vào cuối chuỗi query để tăng độ chính xác.
      2. Nếu query đầy đủ không ra kết quả, thử lại chỉ với đoạn cuối cùng
         (phân tách bởi dấu phẩy — thường là tên thành phố) + ", Vietnam".

    Trả về {"lat": float, "lng": float, "display_name": str} nếu thành công,
    hoặc None nếu không tìm được / lỗi.
    """
    if not address_text or not address_text.strip():
        return None

    address_text = address_text.strip()
    candidates = [f"{address_text}, Vietnam"]

    segments = [s.strip() for s in address_text.split(",") if s.strip()]
    if segments and len(segments) > 1:
        candidates.append(f"{segments[-1]}, Vietnam")

    for query in candidates:
        result = _geocode_query(query)
        if result is not None:
            return result
    return None


def _geocode_query(query: str) -> dict | None:
    """
    Gọi thực API Nominatim cho 1 chuỗi query cụ thể, lấy kết quả khớp đầu
    tiên (limit=1). Mọi lỗi (timeout, HTTP lỗi, không có kết quả) đều được
    nuốt và trả về None — geocode() sẽ tự thử candidate tiếp theo.
    """
    try:
        resp = httpx.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        item = data[0]
        return {
            "lat": float(item["lat"]),
            "lng": float(item["lon"]),
            "display_name": item.get("display_name", ""),
        }
    except Exception:
        return None


def get_route(coord1: dict, coord2: dict) -> dict | None:
    """
    Lấy khoảng cách/thời gian lái xe giữa 2 tọa độ qua OSRM public demo
    server. coord1/coord2 có dạng {"lat": float, "lng": float}.

    Trả về {"distance_km": float, "duration_min": float} nếu thành công,
    hoặc None nếu có bất kỳ lỗi nào (timeout, HTTP không phải 2xx, hoặc
    route status trả về không phải "Ok").
    """
    try:
        url = OSRM_URL_TEMPLATE.format(
            lng1=coord1["lng"], lat1=coord1["lat"],
            lng2=coord2["lng"], lat2=coord2["lat"],
        )
        resp = httpx.get(url, params={"overview": "false"}, timeout=_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None
        route = data["routes"][0]
        return {
            "distance_km": route["distance"] / 1000.0,
            "duration_min": route["duration"] / 60.0,
        }
    except Exception:
        return None