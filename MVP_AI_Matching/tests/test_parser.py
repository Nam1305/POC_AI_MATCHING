"""Unit tests for parse_cv/parse_jd location extraction — no LLM, no network.

call_llm_json is monkeypatched to return canned JSON (as if the LLM had
already extracted it), and location_service.geocode is monkeypatched (both
parse_cv and parse_jd geocode their address once at parse-time), so these
tests validate the schema/geocode-query handling around parse_cv/parse_jd's
output, not the LLM prompt itself or a real Nominatim call.
"""

from __future__ import annotations

import pytest

from app.services import location_service, parser


def _stub_llm(monkeypatch, raw: dict):
    async def _fake_call_llm_json(prompt: str, text: str) -> dict:
        return raw

    monkeypatch.setattr(parser, "call_llm_json", _fake_call_llm_json)


def _stub_geocode(monkeypatch, result: dict | None):
    monkeypatch.setattr(location_service, "geocode", lambda address: result)


@pytest.mark.asyncio
async def test_parse_cv_with_explicit_address(monkeypatch):
    raw = {
        "name": "Nguyen Van A",
        "skills": ["python"],
        "work_experience": [{"company": "ABC", "role": "Dev", "start": "2020-01"}],
        "candidate_location": {
            "raw_address": "123 Nguyen Trai, Thanh Xuan, Ha Noi",
            "willing_to_relocate": None,
        },
    }
    _stub_llm(monkeypatch, raw)
    _stub_geocode(monkeypatch, {"lat": 21.03, "lng": 105.8, "display_name": "Thanh Xuan, Ha Noi"})

    cv = await parser.parse_cv("dummy cv text")

    assert cv.candidate_location.raw_address == "123 Nguyen Trai, Thanh Xuan, Ha Noi"
    assert cv.candidate_location.lat == pytest.approx(21.03)
    assert cv.candidate_location.lng == pytest.approx(105.8)
    assert cv.candidate_location.willing_to_relocate is None


@pytest.mark.asyncio
async def test_parse_cv_with_no_address(monkeypatch):
    raw = {
        "name": "Tran Thi B",
        "skills": ["java"],
        "work_experience": [{"company": "XYZ", "role": "Dev", "start": "2019-01"}],
        "candidate_location": {
            "raw_address": None,
            "willing_to_relocate": None,
        },
    }
    _stub_llm(monkeypatch, raw)
    # No raw_address means parse_cv must skip geocoding entirely.
    monkeypatch.setattr(
        location_service, "geocode",
        lambda address: (_ for _ in ()).throw(AssertionError("geocode should not be called")),
    )

    cv = await parser.parse_cv("dummy cv text")

    assert cv.candidate_location.raw_address is None
    assert cv.candidate_location.lat is None
    assert cv.candidate_location.lng is None
    assert cv.candidate_location.willing_to_relocate is None


@pytest.mark.asyncio
async def test_parse_jd_geocode_concatenates_address_and_city(monkeypatch):
    # company_branch (BE .NET) stores address and city as separate columns;
    # parse_jd must join raw_address + city into one geocode query so
    # Nominatim gets full context (raw_address alone may just be a street).
    raw = {
        "title": "Backend Developer",
        "required_skills": [],
        "work_location": {
            "city": "Da Nang",
            "raw_address": "45 Le Loi",
            "work_mode": "onsite",
        },
    }
    _stub_llm(monkeypatch, raw)

    captured: dict = {}

    def _fake_geocode(address: str):
        captured["address"] = address
        return {"lat": 16.05, "lng": 108.2, "display_name": "Da Nang"}

    monkeypatch.setattr(location_service, "geocode", _fake_geocode)

    jd = await parser.parse_jd("dummy jd text")

    assert captured["address"] == "45 Le Loi, Da Nang"
    assert jd.work_location.lat == pytest.approx(16.05)
    assert jd.work_location.lng == pytest.approx(108.2)


@pytest.mark.asyncio
async def test_parse_jd_null_skill_lists_do_not_crash(monkeypatch):
    # BE .NET omits the "Preferred Skills:"/"Nice to Have Skills:" lines
    # entirely when those lists are empty/null, so the LLM sometimes emits
    # JSON null instead of [] for the corresponding fields — must not raise.
    raw = {
        "title": "Backend Developer",
        "required_skills": None,
        "preferred_skills": None,
        "nice_to_have_skills": None,
        "work_location": {"city": "Ha Noi", "raw_address": "", "work_mode": "onsite"},
    }
    _stub_llm(monkeypatch, raw)
    _stub_geocode(monkeypatch, None)

    jd = await parser.parse_jd("dummy jd text")

    assert jd.required_skills == []
    assert jd.preferred_skills == []
    assert jd.nice_to_have_skills == []


@pytest.mark.asyncio
async def test_parse_jd_geocode_falls_back_to_city_when_no_address(monkeypatch):
    raw = {
        "title": "Backend Developer",
        "required_skills": [],
        "work_location": {
            "city": "Ha Noi",
            "raw_address": "",
            "work_mode": "onsite",
        },
    }
    _stub_llm(monkeypatch, raw)

    captured: dict = {}

    def _fake_geocode(address: str):
        captured["address"] = address
        return {"lat": 21.03, "lng": 105.8, "display_name": "Ha Noi"}

    monkeypatch.setattr(location_service, "geocode", _fake_geocode)

    await parser.parse_jd("dummy jd text")

    assert captured["address"] == "Ha Noi"


@pytest.mark.asyncio
async def test_parse_cv_with_relocate_phrase(monkeypatch):
    raw = {
        "name": "Le Van C",
        "skills": ["react"],
        "work_experience": [{"company": "DEF", "role": "Dev", "start": "2021-01"}],
        "candidate_location": {
            "raw_address": "45 Le Loi, Da Nang",
            "willing_to_relocate": True,
        },
    }
    _stub_llm(monkeypatch, raw)
    _stub_geocode(monkeypatch, {"lat": 16.05, "lng": 108.2, "display_name": "Da Nang"})

    cv = await parser.parse_cv("dummy cv text")

    assert cv.candidate_location.willing_to_relocate is True
