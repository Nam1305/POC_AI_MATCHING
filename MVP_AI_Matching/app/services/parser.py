"""
Stage 2 — Structured Extraction via LLM

Parses raw CV/JD text into Pydantic models (ParsedCV / ParsedJD) using either:
  - Anthropic Claude (production)
  - Groq Llama (free dev/fallback)

Provider is selected via .env LLM_PROVIDER. The functions are async so FastAPI
endpoints don't block; sync SDK calls are wrapped in a thread executor.

Robustness improvements:
  - WorkExperience.start extracted → Python calculates months (not LLM)
  - Completeness check after first parse: auto-retry null work_experience / skills
  - Retry prompts are focused (shorter context → higher accuracy)
  - Retries run in parallel via asyncio.gather
"""

from __future__ import annotations

import asyncio

from app.schemas import ParsedCV, ParsedJD, WorkExperience
from app.services.llm_client import call_llm_json


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

CV_EXTRACT_PROMPT = """Extract information from the CV text below.
Return ONLY valid JSON. No explanation, no markdown fences.

JSON structure:
{
  "name": "candidate full name or empty string",
  "summary": "professional summary / objective or empty string",
  "skills": ["flat list of all technical skill names found anywhere in the CV"],
  "work_experience": [
    {
      "company": "company name",
      "role": "job title / position",
      "start": "YYYY-MM",
      "end": "YYYY-MM or present",
      "is_current": true or false,
      "tech_stack": ["all technologies / tools used in this role"],
      "description": "key responsibilities and achievements (2-4 sentences)"
    }
  ],
  "education": [
    {
      "institution": "school or university name",
      "degree": "MUST be exactly one of: high_school, associate, bachelor, master, phd, other",
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

DATE CONVERSION RULES (apply to every start/end field):
Convert any date format found in the CV to YYYY-MM. Examples:
  "Jan 2021" / "January 2021"         → "2021-01"
  "06/2021" / "2021/06" / "2021.06"   → "2021-06"
  "Mar. 2022" / "March, 2022"         → "2022-03"
  "Q2 2020" / "Summer 2020"           → "2020-06"  (use mid-quarter/season month)
  "2019" (year only)                  → "2019-01"
  "Tháng 3/2021" / "T3/2021" / "3/2021" → "2021-03"  (Vietnamese formats)
  "09-2023" / "09.2023"               → "2023-09"
  Any of: "Present", "Now", "Current", "To date", "Ongoing",
          "Hiện tại", "Nay", "Đến nay", "Till now"  → "present"
  Missing or unknown date             → ""

GENERAL RULES:
- Extract ALL work experiences, even internships and part-time roles.
- For skills: scan the entire CV — skills section, work experience, projects, summary.
- Do NOT calculate months — only provide start and end date strings.
- If a field has no data, use [] for arrays or "" for strings.

CV text:
"""


WORK_EXP_RETRY_PROMPT = """The CV below contains work experience that needs to be extracted.
Focus ONLY on the employment / work history section.
Return ONLY valid JSON — no explanation, no markdown.

{
  "work_experience": [
    {
      "company": "company name",
      "role": "job title",
      "start": "YYYY-MM or empty string",
      "end": "YYYY-MM or present or empty string",
      "is_current": true or false,
      "tech_stack": ["technologies used"],
      "description": "responsibilities and achievements"
    }
  ]
}

Include ALL jobs — full-time, part-time, internships, freelance.

DATE CONVERSION — convert any format to YYYY-MM:
  "Jan 2021" / "01/2021" / "1/2021"   → "2021-01"
  "Tháng 3/2021" / "T3/2021" / "3/2021" → "2021-03"
  "2019" (year only)                  → "2019-01"
  "Mar. 2022" / "March 2022"          → "2022-03"
  "Q1 2020" / "Spring 2020"           → "2020-03"
  "Present" / "Now" / "Hiện tại" / "Nay" / "Đến nay" → "present"
  Unknown or missing                  → ""

CV text:
"""


SKILLS_RETRY_PROMPT = """Extract ALL technical skills from the CV below.
Scan every section: skills/technologies section, work experience, projects, summary.
Return ONLY valid JSON — no explanation, no markdown.

{
  "skills": ["skill1", "skill2", "skill3", ...]
}

Include: programming languages, frameworks, libraries, databases, tools, cloud platforms, DevOps tools.
Each skill should be a single clean string (e.g. "Python", "React", "PostgreSQL").

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
# Retry helpers
# ---------------------------------------------------------------------------

async def _retry_work_experience(cv_text: str) -> list[WorkExperience]:
    """Focused re-extraction of work experience when the full parse missed it."""
    try:
        raw   = await call_llm_json(WORK_EXP_RETRY_PROMPT, cv_text)
        items = raw.get("work_experience", []) if isinstance(raw, dict) else []
        result: list[WorkExperience] = []
        for item in items:
            try:
                result.append(WorkExperience.model_validate(item))
            except Exception:
                pass
        return result
    except Exception:
        return []


async def _retry_skills(cv_text: str) -> list[str]:
    """Focused re-extraction of skills when the full parse missed them."""
    try:
        raw   = await call_llm_json(SKILLS_RETRY_PROMPT, cv_text)
        items = raw.get("skills", []) if isinstance(raw, dict) else []
        return [s for s in items if isinstance(s, str)]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Public API — CV / JD parsing
# ---------------------------------------------------------------------------

async def parse_cv(cv_text: str) -> ParsedCV:
    """
    Extract structured CV from raw text.

    Flow:
      1. Full extraction via LLM
      2. Completeness check — work_experience and skills are critical
      3. If either is empty, run focused retry prompts in parallel
      4. Merge retry results into the CV object
    """
    raw = await call_llm_json(CV_EXTRACT_PROMPT, cv_text)
    cv  = ParsedCV.model_validate(raw)

    needs_exp    = not cv.work_experience
    needs_skills = not cv.skills

    if not needs_exp and not needs_skills:
        return cv

    # Build only the tasks we actually need
    retry_coros = []
    if needs_exp:
        retry_coros.append(_retry_work_experience(cv_text))
    if needs_skills:
        retry_coros.append(_retry_skills(cv_text))

    results = await asyncio.gather(*retry_coros, return_exceptions=True)

    idx = 0
    if needs_exp:
        if isinstance(results[idx], list) and results[idx]:
            cv.work_experience = results[idx]
        idx += 1
    if needs_skills:
        if isinstance(results[idx], list) and results[idx]:
            cv.skills = results[idx]

    return cv


async def parse_jd(jd_text: str) -> ParsedJD:
    """Extract structured JD from raw text. Validates against ParsedJD schema."""
    raw = await call_llm_json(JD_EXTRACT_PROMPT, jd_text)
    return ParsedJD.model_validate(raw)
