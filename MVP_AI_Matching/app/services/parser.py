"""
Stage 2 — Structured Extraction via LLM

Parses raw CV/JD text into Pydantic models (ParsedCV / ParsedJD) using either:
  - Anthropic Claude (production)
  - Groq Llama (free dev/fallback)

Provider is selected via .env LLM_PROVIDER. The functions are async so FastAPI
endpoints don't block; sync SDK calls are wrapped in a thread executor.
"""

from __future__ import annotations

import asyncio
import json

from openai import OpenAI               # used as Groq-compatible client
import anthropic

from app.config import settings
from app.schemas import ParsedCV, ParsedJD


# ---------------------------------------------------------------------------
# Lazy singleton clients
# ---------------------------------------------------------------------------

_anthropic_client: anthropic.Anthropic | None = None
_groq_client:      OpenAI | None             = None


def _get_anthropic() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
        _anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _get_groq() -> OpenAI:
    global _groq_client
    if _groq_client is None:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY not set in .env")
        _groq_client = OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _groq_client


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

CV_EXTRACT_PROMPT = """Extract information from the CV text below.
Return ONLY valid JSON. No explanation, no markdown.

JSON structure:
{
  "name": "candidate full name or empty string",
  "summary": "professional summary/objective or empty string",
  "skills": ["flat list of technical skill names"],
  "work_experience": [
    {
      "company": "company name",
      "role": "job title",
      "end": "YYYY-MM or present",
      "months": integer (calculate from start to end; use 2026-05 for present),
      "is_current": true or false,
      "tech_stack": ["technologies used"],
      "description": "responsibilities and achievements"
    }
  ],
  "education": [
    {
      "institution": "school name",
      "degree": "(MUST be one of: high_school, associate, bachelor, master, phd, other)",
      "degree_raw": "exact degree text from CV (e.g. 'Bachelor of Software Engineering')",
      "major": "field of study or empty string"
    }
  ],
  "projects": [
    {
      "name": "project name",
      "tech_stack": ["technologies used"],
      "description": "what the project does and your contribution"
    }
  ],
  "certifications": ["Certificate Name 1", "Certificate Name 2"],
  "languages": ["English - TOEIC 835", "Vietnamese - Native"]
}

Important: For degree field, extract the highest degree level ONLY (e.g. 'bachelor', 'master', 'phd').
Put the full degree name (including major) in degree_raw field.

CV text:
"""


JD_EXTRACT_PROMPT = """Extract structured information from the Job Description below.
Return ONLY valid JSON. No explanation, no markdown.

JSON structure:
{
  "title": "job title",
  "required_skills": [
    {"skill": "skill name", "weight": 1 or 2 or 3}
  ],
  "preferred_skills": ["nice-to-have skill names"],
  "min_experience_years": integer (0 if not specified),
  "education_degree": "bachelor or master or phd or associate or high_school or other or null",
  "keywords": ["important technical keywords from the JD"]
}

Weight guide: 3 = must-have, 2 = important, 1 = nice-to-have.

JD text:
"""


# ---------------------------------------------------------------------------
# Provider-agnostic completion call (sync, runs in executor)
# ---------------------------------------------------------------------------

def _call_llm_sync(prompt: str, text: str) -> dict:
    """Run completion via the configured provider, return parsed JSON dict."""
    full_prompt = prompt + text

    if settings.llm_provider == "anthropic":
        client = _get_anthropic()
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            temperature=0,
            messages=[{"role": "user", "content": full_prompt}],
        )
        # Anthropic returns content as a list of blocks; first block is text.
        content = response.content[0].text
        # Claude sometimes wraps JSON in ```json fences — strip them.
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        return json.loads(content)

    # Default: Groq (OpenAI-compatible)
    client = _get_groq()
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": full_prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


async def _call_llm(prompt: str, text: str) -> dict:
    """Async wrapper: SDKs are sync, so push to executor to avoid blocking."""
    return await asyncio.get_event_loop().run_in_executor(
        None, _call_llm_sync, prompt, text
    )


# ---------------------------------------------------------------------------
# Public API — CV / JD parsing
# ---------------------------------------------------------------------------

async def parse_cv(cv_text: str) -> ParsedCV:
    """Extract structured CV from raw text. Validates against ParsedCV schema."""
    raw = await _call_llm(CV_EXTRACT_PROMPT, cv_text)
    return ParsedCV.model_validate(raw)


async def parse_jd(jd_text: str) -> ParsedJD:
    """Extract structured JD from raw text. Validates against ParsedJD schema."""
    raw = await _call_llm(JD_EXTRACT_PROMPT, jd_text)
    return ParsedJD.model_validate(raw)
