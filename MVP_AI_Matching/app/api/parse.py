"""
POST /ai/parse-jd  — raw JD text → ParsedJD + embedding
POST /ai/parse-cv  — S3/R2 URL(s) → cv_raw_text + ParsedCV + embedding (per URL)
"""

from __future__ import annotations

import asyncio
import json
import re

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator, model_validator

from app.schemas import ParsedCV, ParsedJD
from app.services.pdf_extractor import extract_text
from app.services.parser import parse_cv as parse_cv_text
from app.services.parser import parse_jd as parse_jd_text
from app.services.embedder import embed

router = APIRouter()

_MAX_CVS_PER_REQUEST = 10


# ---------------------------------------------------------------------------
# /parse-jd
# ---------------------------------------------------------------------------

class ParseJDRequest(BaseModel):
    jd_text: str


class ParseJDResponse(BaseModel):
    parsed_jd:    ParsedJD
    jd_embedding: list[float]
    error:        str | None = None


@router.post(
    "/parse-jd",
    response_model=ParseJDResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["jd_text"],
                        "properties": {
                            "jd_text": {"type": "string", "description": "Raw JD text"}
                        },
                    },
                    "example": {"jd_text": "Job Title: Junior .NET Backend Developer\n..."},
                },
                "text/plain": {
                    "schema": {"type": "string"},
                    "example": "Job Title: Junior .NET Backend Developer\n...",
                },
            },
        }
    },
)
async def parse_jd_endpoint(request: Request) -> ParseJDResponse:
    """
    Parse a Job Description into structured JSON + dense embedding.

    Accepts JD as either:
      - **application/json**: `{"jd_text": "..."}`
      - **text/plain**: raw JD text in body

    Auto-detects: if body parses as JSON with a `jd_text` field → uses it;
    otherwise treats the entire body as raw JD text. This is forgiving of
    Content-Type mismatches between .NET and FastAPI.
    """
    body = await request.body()
    if not body or not body.strip():
        raise HTTPException(status_code=400, detail="Request body is empty")

    text = body.decode("utf-8", errors="replace").strip()

    # Try JSON first — if it's an object with "jd_text", use that
    jd_text: str = ""
    if text.startswith("{"):
        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and "jd_text" in payload:
                jd_text = str(payload["jd_text"] or "")
            else:
                jd_text = text
        except json.JSONDecodeError:
            jd_text = text
    else:
        jd_text = text

    jd_text = jd_text.strip()
    if not jd_text:
        raise HTTPException(status_code=400, detail="jd_text is empty")

    parsed = await parse_jd_text(jd_text)
    jd_embedding = None
    error_message = None
    try:
        jd_embedding = await embed(jd_text)
    except Exception as e:
        error_message = f"Embed failed: {e}"
        # Log the error for debugging purposes
        import logging
        logging.error(f"Error embedding JD: {e}")

    return ParseJDResponse(parsed_jd=parsed, jd_embedding=jd_embedding, error=error_message)


# ---------------------------------------------------------------------------
# /parse-cv — accepts S3/R2 URL(s), downloads + processes each concurrently
# ---------------------------------------------------------------------------

class ParseCVRequest(BaseModel):
    """
    Accepts either a single URL or an array of URLs:
      {"cv_url":  "https://s3.amazonaws.com/.../cv.pdf"}
      {"cv_urls": ["https://...", "https://..."]}
    """
    cv_url:  str | None = None
    cv_urls: list[str] | None = None

    @model_validator(mode="after")
    def _normalize(self) -> "ParseCVRequest":
        if self.cv_url and not self.cv_urls:
            self.cv_urls = [self.cv_url]
        if not self.cv_urls:
            raise ValueError("cv_url or cv_urls is required")
        if len(self.cv_urls) > _MAX_CVS_PER_REQUEST:
            raise ValueError(f"Maximum {_MAX_CVS_PER_REQUEST} CVs per request")
        return self

    @field_validator("cv_urls", mode="before")
    @classmethod
    def _validate_urls(cls, v: list[str] | None) -> list[str] | None:
        if not v:
            return v
        for url in v:
            if not str(url).startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL (must start with http/https): {url}")
        return v


class ParseCVResult(BaseModel):
    url:          str
    cv_raw_text:  str | None = None
    parsed_cv:    ParsedCV | None = None
    cv_embedding: list[float] | None = None
    error:        str | None = None


class ParseCVResponse(BaseModel):
    results: list[ParseCVResult]


async def _fetch_file(url: str, client: httpx.AsyncClient) -> tuple[bytes, str]:
    """Download file from URL. Returns (bytes, filename). Retries up to 3x on transient errors."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = await client.get(url, follow_redirects=True, timeout=30.0)
            resp.raise_for_status()
            break
        except (httpx.TransportError, httpx.ConnectError) as e:
            last_exc = e
            await asyncio.sleep(1.5 * (attempt + 1))
    else:
        raise last_exc

    # Try Content-Disposition header first
    filename = ""
    cd = resp.headers.get("content-disposition", "")
    if cd:
        m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)', cd, re.IGNORECASE)
        if m:
            filename = m.group(1).strip().strip('"\'')

    # Fallback: last path segment (strip query string)
    if not filename:
        filename = url.split("?")[0].rstrip("/").split("/")[-1]

    # Ensure recognizable extension
    if "." not in filename.rsplit("/", 1)[-1]:
        ct = resp.headers.get("content-type", "")
        ext = ".docx" if ("wordprocessingml" in ct or "docx" in ct) else ".pdf"
        filename += ext

    return resp.content, filename


async def _process_one(url: str, client: httpx.AsyncClient) -> ParseCVResult:
    """Full pipeline for a single CV URL: download → extract → parse → embed."""
    try:
        file_bytes, filename = await _fetch_file(url, client)
    except httpx.HTTPStatusError as e:
        return ParseCVResult(url=url, error=f"HTTP {e.response.status_code} when downloading file")
    except httpx.RequestError as e:
        return ParseCVResult(url=url, error=f"Network error: {e}")

    try:
        raw_text = extract_text(file_bytes, filename)
    except ValueError as e:
        return ParseCVResult(url=url, error=str(e))

    if not raw_text.strip():
        return ParseCVResult(url=url, error="No text could be extracted from file")

    try:
        parsed = await parse_cv_text(raw_text)
        cv_embedding = await embed(parsed.build_embed_text())
    except Exception as e:
        return ParseCVResult(url=url, error=f"Parse/embed failed: {e}")

    return ParseCVResult(
        url=url,
        cv_raw_text=raw_text,
        parsed_cv=parsed,
        cv_embedding=cv_embedding,
    )


@router.post(
    "/parse-cv",
    response_model=ParseCVResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "oneOf": [
                            {
                                "type": "object",
                                "required": ["cv_url"],
                                "properties": {"cv_url": {"type": "string", "format": "uri"}},
                                "example": {"cv_url": "https://s3.amazonaws.com/bucket/cv.pdf"},
                            },
                            {
                                "type": "object",
                                "required": ["cv_urls"],
                                "properties": {
                                    "cv_urls": {
                                        "type": "array",
                                        "items": {"type": "string", "format": "uri"},
                                        "maxItems": _MAX_CVS_PER_REQUEST,
                                    }
                                },
                                "example": {
                                    "cv_urls": [
                                        "https://s3.amazonaws.com/bucket/cv1.pdf",
                                        "https://s3.amazonaws.com/bucket/cv2.pdf",
                                    ]
                                },
                            },
                        ]
                    }
                }
            },
        }
    },
)
async def parse_cv_endpoint(body: ParseCVRequest) -> ParseCVResponse:
    """
    Download and parse CV(s) from S3/R2/presigned URLs.

    - **cv_url**: single URL → `results` array with 1 item
    - **cv_urls**: array of URLs → `results` array with N items (processed concurrently)

    Each result includes `cv_raw_text`, `parsed_cv`, `embedding` on success,
    or `error` (non-null) if that individual CV failed — other CVs are unaffected.
    """
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[_process_one(url, client) for url in body.cv_urls]
        )
    return ParseCVResponse(results=list(results))
