"""
Stages 5–10 — Natural Language Search

Given an HR query (e.g. "React 3 năm, có kinh nghiệm team lead") and a list of
pre-scored applications, return a re-ranked list with match explanations.

Pipeline:
  Stage 5  Query Understanding   — LLM parses query → structured filters
  Stage 6  Query Embedding       — embedder
  Stage 7  Vector Similarity     — cosine sim of query_vec vs cv_embedding
  Stage 8  Metadata Filtering    — keep apps whose parsed_cv satisfies filters
  Stage 9  Re-ranking            — combined = final_score×0.4 + similarity×60
  Stage 10 Match Reason (optional) — LLM generates 1-line explanation for top N
"""

from __future__ import annotations

import asyncio

from app.config import settings
from app.schemas import ParsedCV
from app.services.embedder import embed
from app.services.llm_client import call_llm_json, call_llm_text
from app.services.scorer import cosine_sim, normalize_cosine


# ---------------------------------------------------------------------------
# Stage 5 — Query understanding
# ---------------------------------------------------------------------------

QUERY_PARSE_PROMPT = """Parse this natural language candidate-search query into structured filters.
Return ONLY valid JSON. No explanation, no markdown.

JSON structure:
{
  "required_skills": [
    {"skill": "string", "min_years": integer or null}
  ],
  "soft_skills": ["leadership", "communication", ...],
  "min_experience_years": integer or null,
  "keywords": ["other notable terms"]
}

Query:
"""


async def parse_nl_query(query: str) -> dict:
    """Stage 5: LLM parses HR query into a structured filter dict."""
    return await call_llm_json(QUERY_PARSE_PROMPT, query)


# ---------------------------------------------------------------------------
# Stage 8 — Metadata filtering
# ---------------------------------------------------------------------------

_STOP_WORDS = {"a", "an", "the", "and", "or", "in", "of", "with", "for",
               "to", "at", "on", "by", "from", "as", "is", "are", "be"}


def _cv_has_skill(parsed_cv: ParsedCV, skill: str) -> bool:
    """Check skill presence across skills + tech_stack + descriptions.

    Matching strategy (most → least strict):
    1. Exact substring: needle in any skill token or token in needle.
    2. Word-level: all significant words of the needle appear in any single token.
    3. Free-text: needle (or any significant word of it) found in descriptions/summary.
    """
    needle = skill.lower().strip()
    all_tokens = (
        [s.lower() for s in parsed_cv.skills]
        + [s.lower() for exp in parsed_cv.work_experience for s in exp.tech_stack]
        + [s.lower() for proj in parsed_cv.projects for s in proj.tech_stack]
    )

    # 1. Substring match
    for token in all_tokens:
        if needle in token or token in needle:
            return True

    # 2. Word-level match: every non-stop word of the needle found somewhere
    #    in skill tokens or descriptions (with simple suffix stripping).
    words = [w for w in needle.replace("-", " ").split() if w not in _STOP_WORDS and len(w) > 2]
    if words:
        skill_blob = " ".join(all_tokens)
        desc_blob = " ".join(filter(None, [
            parsed_cv.summary,
            *(e.description for e in parsed_cv.work_experience),
            *(e.role for e in parsed_cv.work_experience),
        ])).lower()
        combined = skill_blob + " " + desc_blob

        def _in_combined(w: str) -> bool:
            if w in combined:
                return True
            # Simple suffix stripping: try without trailing s/es/ing/ed
            for suffix in ("ing", "ed", "es", "s"):
                if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                    stem = w[: -len(suffix)]
                    if stem in combined:
                        return True
            return False

        if all(_in_combined(w) for w in words):
            return True

    # 3. Full phrase in descriptions
    return _cv_mentions(parsed_cv, needle)


def _cv_mentions(parsed_cv: ParsedCV, term: str) -> bool:
    """Search a free-text term in work_experience.description / summary."""
    needle = term.lower()
    if parsed_cv.summary and needle in parsed_cv.summary.lower():
        return True
    for exp in parsed_cv.work_experience:
        if exp.description and needle in exp.description.lower():
            return True
        if exp.role and needle in exp.role.lower():
            return True
    return False


def apply_filters(applications: list[dict], filters: dict) -> list[dict]:
    """
    Keep only applications whose parsed_cv satisfies the filters.
    `parsed_cv` in each dict is expected to be a ParsedCV instance (or compatible dict).
    """
    required_skills = filters.get("required_skills", []) or []
    soft_skills     = filters.get("soft_skills", []) or []
    min_years       = filters.get("min_experience_years")

    kept: list[dict] = []
    for app in applications:
        cv = app["parsed_cv"]
        if not isinstance(cv, ParsedCV):
            cv = ParsedCV.model_validate(cv)

        ok = True
        for rs in required_skills:
            skill = rs["skill"] if isinstance(rs, dict) else rs
            if not _cv_has_skill(cv, skill):
                ok = False
                break
        if not ok:
            continue

        if min_years and cv.total_exp_months / 12.0 < min_years:
            continue

        soft_hits = sum(1 for s in soft_skills if _cv_mentions(cv, s))
        app["_soft_match"] = soft_hits / len(soft_skills) if soft_skills else 0.0
        kept.append(app)
    return kept


# ---------------------------------------------------------------------------
# Stage 10 — Match reason (optional, top N only)
# ---------------------------------------------------------------------------

MATCH_REASON_PROMPT = """Write a one-sentence explanation (max 20 words) of why this candidate
matches the recruiter's query. Be concrete (mention years, role, tech). No fluff.

Query: {query}

Candidate facts:
- Skills: {skills}
- Recent role: {role}
- Total experience: {years} years
- Notable: {notable}

Explanation:"""


async def build_match_reason(query: str, parsed_cv: ParsedCV) -> str:
    skills_str = ", ".join(parsed_cv.skills[:10])
    if parsed_cv.work_experience:
        exp = parsed_cv.work_experience[0]
        role = f"{exp.role} at {exp.company}" if exp.role and exp.company else (exp.role or "")
    else:
        role = "—"
    notable = parsed_cv.summary[:120] if parsed_cv.summary else ""

    prompt = MATCH_REASON_PROMPT.format(
        query=query,
        skills=skills_str,
        role=role,
        years=parsed_cv.total_exp_years,
        notable=notable,
    )
    return await call_llm_text(prompt, temperature=0.2, max_tokens=120)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def search(query: str, applications: list[dict], top_n_reasons: int = 5) -> dict:
    """
    Full NL search pipeline. `applications` items must contain:
      - id            : str
      - cv_embedding  : list[float]
      - final_score   : float (0-100)
      - parsed_cv     : ParsedCV or dict
    """
    # Stage 5 + 6 in parallel
    filters_task   = asyncio.create_task(parse_nl_query(query))
    query_vec_task = asyncio.create_task(embed(query))
    filters   = await filters_task
    query_vec = await query_vec_task

    # Stage 7 — cosine sim
    for app in applications:
        raw = cosine_sim(query_vec, app["cv_embedding"])
        app["similarity_score"] = normalize_cosine(raw, settings.cosine_min, settings.cosine_max)

    # Stage 8 — structured filter
    filtered = apply_filters(applications, filters)

    # Stage 9 — re-rank: final_score×0.4 + similarity×60 + soft_match×10
    for app in filtered:
        soft = app.get("_soft_match", 0.0)
        app["combined_score"] = round(
            app["final_score"] * 0.4 + app["similarity_score"] * 60 + soft * 10,
            1,
        )
    filtered.sort(key=lambda x: x["combined_score"], reverse=True)

    # Stage 10 — match reasons for top N (parallel LLM calls)
    top = filtered[:top_n_reasons]
    reasons = await asyncio.gather(*[
        build_match_reason(query, _ensure_parsed_cv(app["parsed_cv"])) for app in top
    ], return_exceptions=True)
    for app, reason in zip(top, reasons):
        app["match_reason"] = reason if isinstance(reason, str) else ""

    results = []
    for app in filtered:
        results.append({
            "id":               app["id"],
            "similarity_score": round(app["similarity_score"], 3),
            "combined_score":   app["combined_score"],
            "match_reason":     app.get("match_reason", ""),
        })

    return {"query_parsed": filters, "results": results}


def _ensure_parsed_cv(cv) -> ParsedCV:
    return cv if isinstance(cv, ParsedCV) else ParsedCV.model_validate(cv)
