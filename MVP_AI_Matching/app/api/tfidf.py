"""
POST /ai/tfidf-score — Rank CV(s) against a JD using TF-IDF + cosine similarity.

A lighter-weight alternative to the /ai/parse-jd -> /ai/parse-cv -> /ai/score
pipeline: phase 1 (raw text extraction) is the same, but phase 2 is plain
TF-IDF vectorization + cosine similarity instead of LLM parsing, dense
embeddings, and rule-based scoring.
"""

from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from app.services.fetch import fetch_file
from app.services.pdf_extractor import extract_text
from app.services.tfidf_scorer import rank_cvs_tfidf

router = APIRouter()

_MAX_CVS_PER_REQUEST = 50


class TfidfScoreRequest(BaseModel):
    jd_text: str
    cv_urls: list[str]

    @field_validator("jd_text")
    @classmethod
    def _validate_jd_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("jd_text is empty")
        return v

    @field_validator("cv_urls")
    @classmethod
    def _validate_urls(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("cv_urls is required")
        if len(v) > _MAX_CVS_PER_REQUEST:
            raise ValueError(f"Maximum {_MAX_CVS_PER_REQUEST} CVs per request")
        for url in v:
            if not str(url).startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL (must start with http/https): {url}")
        return v


class TfidfCVResult(BaseModel):
    url:         str
    tfidf_score: float | None = None   # 0-100, cosine similarity * 100
    rank:        int | None = None
    error:       str | None = None


class TfidfScoreResponse(BaseModel):
    results: list[TfidfCVResult]


async def _extract_one(url: str, client: httpx.AsyncClient) -> tuple[TfidfCVResult, str | None]:
    """Download + extract raw text for one CV URL. Returns (result_stub, raw_text | None)."""
    try:
        file_bytes, filename = await fetch_file(url, client)
    except httpx.HTTPStatusError as e:
        return TfidfCVResult(url=url, error=f"HTTP {e.response.status_code} when downloading file"), None
    except httpx.RequestError as e:
        return TfidfCVResult(url=url, error=f"Network error: {e}"), None

    try:
        raw_text = extract_text(file_bytes, filename)
    except ValueError as e:
        return TfidfCVResult(url=url, error=str(e)), None

    if not raw_text.strip():
        return TfidfCVResult(url=url, error="No text could be extracted from file"), None

    return TfidfCVResult(url=url), raw_text


@router.post("/tfidf-score", response_model=TfidfScoreResponse)
async def tfidf_score_endpoint(req: TfidfScoreRequest) -> TfidfScoreResponse:
    """
    Rank CV(s) against a JD using TF-IDF + cosine similarity (no LLM calls).

    1. Download + extract raw text for each CV URL (same extraction as /ai/parse-cv).
    2. Fit a TF-IDF vectorizer over the JD text + all CV texts and rank by cosine similarity.

    Results are sorted by `tfidf_score` descending. CVs that fail to download
    or extract are returned with `error` set and excluded from ranking.
    """
    jd_text = req.jd_text.strip()

    async with httpx.AsyncClient() as client:
        extracted = await asyncio.gather(*[_extract_one(url, client) for url in req.cv_urls])

    ok_results = [r for r, text in extracted if text is not None]
    ok_texts = [text for _, text in extracted if text is not None]
    failed_results = [r for r, text in extracted if text is None]

    if ok_results:
        scores = rank_cvs_tfidf(jd_text, ok_texts)
        for r, score in zip(ok_results, scores):
            r.tfidf_score = score
        ok_results.sort(key=lambda r: r.tfidf_score, reverse=True)
        for i, r in enumerate(ok_results, start=1):
            r.rank = i

    return TfidfScoreResponse(results=ok_results + failed_results)
