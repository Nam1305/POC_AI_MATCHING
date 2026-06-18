"""
POST /ai/search  — Natural-language candidate search.

Input: HR query + list of pre-scored applications (id, cv_embedding,
final_score, parsed_cv). Output: re-ranked list with similarity_score,
combined_score, and a one-line match_reason for top results.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas import ParsedCV
from app.services.nl_search import search as run_search

router = APIRouter()


class ApplicationInput(BaseModel):
    id:            str
    cv_embedding:  list[float]
    final_score:   float = Field(..., ge=0, le=100)
    parsed_cv:     ParsedCV


class SearchRequest(BaseModel):
    query:        str
    applications: list[ApplicationInput]
    top_n_reasons: int = Field(5, ge=0, le=20, description="LLM explanations for top N results")


class SearchResultItem(BaseModel):
    id:               str
    similarity_score: float
    combined_score:   float
    match_reason:     str


class SearchResponse(BaseModel):
    results: list[SearchResultItem]


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(req: SearchRequest) -> SearchResponse:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query is empty")
    if not req.applications:
        raise HTTPException(status_code=400, detail="applications list is empty")

    apps = [
        {
            "id":           a.id,
            "cv_embedding": a.cv_embedding,
            "final_score":  a.final_score,
            "parsed_cv":    a.parsed_cv,
        }
        for a in req.applications
    ]

    result = await run_search(req.query, apps, top_n_reasons=req.top_n_reasons)
    return SearchResponse(results=[SearchResultItem(**r) for r in result["results"]])
