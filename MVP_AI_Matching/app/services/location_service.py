"""
Location + travel-time estimation for D5 (Location + Work Mode) scoring.

Uses two free, no-key public APIs:
  - Nominatim (OpenStreetMap) for geocoding — https://nominatim.org/
  - OSRM public demo server for driving routes — http://project-osrm.org/

Stateless by design (no caching, no DB) to match this service's existing
architecture (see docs/Overview.md: "AI service is stateless, no DB, no auth").
Every HTTP call is wrapped in try/except with a timeout; failures return None
so callers (scorer.py) can fall back gracefully, mirroring the per-item error
handling already used elsewhere in this service (e.g. /ai/parse-cv).
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
    Geocode a Vietnamese address via Nominatim.

    Appends ", Vietnam" to the query. If the full-address query returns no
    result, falls back to just the last comma-separated segment (usually the
    city) + ", Vietnam".

    Returns {"lat": float, "lng": float, "display_name": str} or None.
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
    Get driving distance/duration between two coords via the OSRM public
    demo server. coord1/coord2: {"lat": float, "lng": float}.

    Returns {"distance_km": float, "duration_min": float} or None on any
    failure (timeout, non-2xx, non-"Ok" route status).
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


def haversine_fallback_minutes(coord1: dict, coord2: dict, avg_speed_kmh: float = 20) -> float:
    """
    DEPRECATED / unused — kept for rollback. score_location() in scorer.py no
    longer falls back to this; a failed get_route() (after one retry) now
    returns the neutral score directly instead of estimating from straight-
    line distance. Not called anywhere.

    Pure-Python straight-line distance fallback (no external call). Estimates
    driving time assuming a constant average speed.
    """
    lat1, lng1 = math.radians(coord1["lat"]), math.radians(coord1["lng"])
    lat2, lng2 = math.radians(coord2["lat"]), math.radians(coord2["lng"])

    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    earth_radius_km = 6371.0
    distance_km = earth_radius_km * c

    return (distance_km / avg_speed_kmh) * 60.0
