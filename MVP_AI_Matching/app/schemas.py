"""
Shared Pydantic v2 schemas — CV + JD.
Only fields actually used in AI scoring/search/embed are kept.
Computed helpers are plain @property (not serialized to JSON).
"""

from __future__ import annotations

import datetime
import math
import re
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Date helpers — single source of truth for month parsing
# ---------------------------------------------------------------------------

# Non-empty tokens meaning "still ongoing"; an empty string is handled by the
# caller (unknown date), which is a different case from an explicit "present".
PRESENT_TOKENS = {"present", "nay", "now", "current"}


def parse_month(s: str) -> Optional[datetime.date]:
    """
    Parse a 'YYYY-MM' date (also accepting '/', '.' separators or year-only)
    into the first day of that month. 'present'/'now'/'nay'/'current' resolve
    to the current month. Empty or unparseable input returns None.
    """
    s = (s or "").strip().lower()
    if not s:
        return None
    if s in PRESENT_TOKENS:
        return datetime.date.today().replace(day=1)
    m = re.match(r"(\d{4})(?:[-/.](\d{1,2}))?", s)
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else 1
    try:
        return datetime.date(year, max(1, min(12, month)), 1)
    except ValueError:
        return None


def _diff_months(start: str, end: str) -> int:
    """Calendar months between two dates. Unknown dates fall back to the current month."""
    today = datetime.date.today().replace(day=1)
    s = parse_month(start) or today
    e = parse_month(end) or today
    if e < s:
        e = s
    return (e.year - s.year) * 12 + (e.month - s.month)


def _months_between(s: datetime.date, e: datetime.date) -> int:
    return (e.year - s.year) * 12 + (e.month - s.month)


def merge_month_intervals(intervals: list[tuple[datetime.date, datetime.date]]) -> int:
    """
    Total months covered by a list of (start, end) date intervals, with
    overlapping or touching intervals merged so overlap is counted once
    (e.g. concurrent freelance + full-time jobs).
    """
    if not intervals:
        return 0
    ordered = sorted(intervals, key=lambda iv: iv[0])
    total = 0
    cur_start, cur_end = ordered[0]
    for s, e in ordered[1:]:
        if s <= cur_end:
            cur_end = max(cur_end, e)
        else:
            total += _months_between(cur_start, cur_end)
            cur_start, cur_end = s, e
    total += _months_between(cur_start, cur_end)
    return total


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DegreeLevel(str, Enum):
    HIGH_SCHOOL = "high_school"
    ASSOCIATE   = "associate"
    BACHELOR    = "bachelor"
    MASTER      = "master"
    PHD         = "phd"
    OTHER       = "other"

    @property
    def numeric(self) -> int:
        return {"high_school": 1, "associate": 2, "bachelor": 3,
                "master": 4, "phd": 5, "other": 1}[self.value]


# ---------------------------------------------------------------------------
# CV sub-models
# ---------------------------------------------------------------------------

class WorkExperience(BaseModel):
    company:     str       = ""
    role:        str       = ""
    start:       str       = ""   # "YYYY-MM"
    end:         str       = ""   # "YYYY-MM" or "present"
    months:      int       = 0
    is_current:  bool      = False
    tech_stack:  list[str] = Field(default_factory=list)
    description: str       = ""

    @field_validator("description", mode="before")
    @classmethod
    def _coerce_desc(cls, v: object) -> str:
        return v if isinstance(v, str) else ""

    @model_validator(mode="after")
    def _set_current_and_months(self) -> "WorkExperience":
        if self.end and self.end.strip().lower() in PRESENT_TOKENS:
            self.is_current = True
        # Prefer Python calculation over LLM-provided value for accuracy
        if self.start:
            self.months = _diff_months(self.start, self.end)
        return self


class Education(BaseModel):
    institution: str                   = ""
    degree:      Optional[DegreeLevel] = None
    degree_raw:  str                   = ""
    major:       str                   = ""

    @field_validator("institution", "degree_raw", "major", mode="before")
    @classmethod
    def _coerce_str(cls, v: object) -> str:
        return v if isinstance(v, str) else ""

    @field_validator("degree", mode="before")
    @classmethod
    def _normalize_degree(cls, v: object) -> Optional[str]:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            return v
        s = v.lower().strip()
        valid = {"high_school", "associate", "bachelor", "master", "phd", "other"}
        if s in valid:
            return s
        if any(x in s for x in ("phd", "doctorate", "doctor of")):
            return "phd"
        if any(x in s for x in ("master", "msc", "mba", "m.sc", "m.eng")):
            return "master"
        if any(x in s for x in ("bachelor", "bsc", "b.sc", "b.eng", "beng", "undergraduate", "licens")):
            return "bachelor"
        if "associate" in s:
            return "associate"
        if any(x in s for x in ("high school", "secondary", "phổ thông")):
            return "high_school"
        return "other"


class CandidateLocation(BaseModel):
    """
    Location info for a CV. `raw_address` is free-text as stated in the CV;
    `lat`/`lng` are geocoded once at parse-time (see parser.parse_cv) via
    location_service.geocode() and persisted alongside cv_embedding — mirrors
    how cv_embedding is computed once at parse-time rather than per score
    call. None if no address was found or geocoding failed.
    """
    raw_address:          Optional[str]                              = None
    lat:                  Optional[float]                            = None
    lng:                  Optional[float]                            = None
    # True only if the CV explicitly states willingness to relocate; never inferred.
    willing_to_relocate:  Optional[bool]                              = None

    @field_validator("raw_address", mode="before")
    @classmethod
    def _coerce_raw_address(cls, v: object) -> Optional[str]:
        if not isinstance(v, str) or not v.strip():
            return None
        return v


class Project(BaseModel):
    name:        str       = ""
    tech_stack:  list[str] = Field(default_factory=list)
    description: str       = ""

    @field_validator("description", mode="before")
    @classmethod
    def _coerce_desc(cls, v: object) -> str:
        return v if isinstance(v, str) else ""


# ---------------------------------------------------------------------------
# CV Evaluation schemas
# ---------------------------------------------------------------------------

class SkillMatchDetail(BaseModel):
    skill:  str
    # "matched" | "matched_implied" | "missing_must_have" | "missing_preferred"
    status: str
    weight: int = 1


class CVJobEvaluation(BaseModel):
    # Structured — dùng cho UI (badges, charts)
    skill_details:      list[SkillMatchDetail] = Field(default_factory=list)
    missing_must_have:  list[str]              = Field(default_factory=list)
    missing_preferred:  list[str]              = Field(default_factory=list)
    bonus_skills:       list[str]              = Field(default_factory=list)
    skill_match_rate:   float = 0.0

    experience_verdict: str = ""   # sufficient | insufficient | over_qualified | not_required
    experience_detail:  str = ""
    education_verdict:  str = ""   # exceeds | meets | below | not_required

    # Narrative — HR đọc như người viết
    narrative:          str = ""


# ---------------------------------------------------------------------------
# JD sub-models
# ---------------------------------------------------------------------------

class RequiredSkill(BaseModel):
    skill:  str
    weight: int = 1   # 1 nice-to-have → 3 must-have
    # Interchangeable alternatives — when the JD lists skills as "A, B, or C",
    # the group is satisfied by ANY one of {skill} ∪ alternatives. `skill` is the
    # representative; `alternatives` holds the rest. Empty for a plain requirement.
    alternatives: list[str] = Field(default_factory=list)

    @field_validator("alternatives", mode="before")
    @classmethod
    def _coerce_alternatives(cls, v: object) -> list:
        if not isinstance(v, list):
            return []
        return [s for s in v if isinstance(s, str) and s.strip()]


# Generic soft-skills / meta-competencies that JD parsers sometimes emit as
# discrete required skills (e.g. "Programming Fundamentals", "Problem Solving").
# They never appear as literal, matchable tokens on a CV, so keeping them as
# hard requirements guarantees a phantom "missing must-have" for EVERY candidate
# and silently deflates skill_match_rate. They are dropped from the JD skill
# lists — the concrete signal they stand for (e.g. actually knowing a language)
# is already captured by the real technical skills the JD lists alongside them.
GENERIC_NON_SKILLS: frozenset[str] = frozenset({
    "programming", "programming fundamentals", "programming basics",
    "programming knowledge", "coding fundamentals", "basic programming",
    "software development", "software engineering", "computer science",
    "problem solving", "analytical thinking", "analytical skills",
    "critical thinking", "logical thinking", "logical reasoning",
    "communication", "communication skills", "interpersonal skills",
    "teamwork", "team player", "teamworking", "collaboration",
    "self learning", "self study", "self motivated", "self motivation",
    "willingness to learn", "eager to learn", "fast learner", "quick learner",
    "learning ability", "continuous learning", "responsibility",
    "sense of responsibility", "time management", "leadership", "creativity",
    "adaptability", "attention to detail", "work ethic", "proactive",
    "hard working", "detail oriented", "multitasking",
})


def _normalize_skill_key(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace — for denylist lookup."""
    key = re.sub(r"[^\w\s]", " ", name.lower())
    return re.sub(r"\s+", " ", key).strip()


def is_generic_non_skill(name: str) -> bool:
    """True when `name` is a soft-skill / meta-competency, not a matchable skill."""
    return _normalize_skill_key(name) in GENERIC_NON_SKILLS


# ---------------------------------------------------------------------------
# ParsedCV
# ---------------------------------------------------------------------------

class ParsedCV(BaseModel):
    name:            str = ""
    summary:         str = ""
    skills:          list[str]            = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education:       list[Education]      = Field(default_factory=list)
    projects:        list[Project]        = Field(default_factory=list)
    certifications:  list[str]            = Field(default_factory=list)
    languages:       list[str]            = Field(default_factory=list)
    candidate_location: CandidateLocation = Field(default_factory=CandidateLocation)

    @field_validator("name", "summary", mode="before")
    @classmethod
    def _coerce_str(cls, v: object) -> str:
        return v if isinstance(v, str) else ""

    @field_validator("skills", "work_experience", "education", "projects", "languages", mode="before")
    @classmethod
    def _coerce_list(cls, v: object) -> list:
        return v if isinstance(v, list) else []

    @model_validator(mode="after")
    def _filter_empty_entries(self) -> "ParsedCV":
        # Remove hallucinated placeholder entries that have no real content
        # A real work entry needs a company, OR a role paired with at least
        # one concrete detail (description or a start date). This removes
        # LLM-hallucinated placeholders like {role:"Internship/Fresher",
        # company:"", description:"", start:""}.
        self.work_experience = [
            e for e in self.work_experience
            if e.company or (e.role and (e.description or e.start))
        ]
        self.education = [
            e for e in self.education
            if e.institution or e.degree_raw
        ]
        self.projects = [
            p for p in self.projects
            if p.name or p.description
        ]
        self.skills = [s for s in self.skills if s and s.strip()]
        return self

    @field_validator("certifications", mode="before")
    @classmethod
    def _normalize_certs(cls, v: object) -> list:
        if not v:
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(item.get("name") or item.get("title") or str(item))
        return result

    # --- Internal helpers (not serialized) ---

    @property
    def total_exp_months(self) -> int:
        """
        Months of experience covered by work_experience, with overlapping
        jobs (e.g. freelance run in parallel with a full-time role) merged
        so the overlap isn't double-counted.
        """
        today = datetime.date.today().replace(day=1)
        intervals: list[tuple[datetime.date, datetime.date]] = []
        for e in self.work_experience:
            s = parse_month(e.start)
            if not s:
                continue
            en = parse_month(e.end) or today
            if en < s:
                en = s
            intervals.append((s, en))
        return merge_month_intervals(intervals)

    @property
    def total_exp_years(self) -> float:
        return round(self.total_exp_months / 12, 1)

    @property
    def highest_degree_level(self) -> int:
        levels = [e.degree.numeric for e in self.education if e.degree]
        return max(levels) if levels else 0

    @property
    def current_role(self) -> Optional[str]:
        for exp in self.work_experience:
            if exp.is_current:
                return exp.role
        return None

    # --- Embed text ---

    def build_embed_text(self) -> str:
        parts: list[str] = []

        if self.summary:
            parts.append(self.summary)

        if self.skills:
            parts.append("Skills: " + ", ".join(self.skills))

        for exp in self.work_experience:
            tokens = [f"{exp.role} at {exp.company}"]
            if exp.months:
                tokens.append(f"({exp.months} months)")
            if exp.tech_stack:
                tokens.append("Tech: " + ", ".join(exp.tech_stack))
            if exp.description:
                tokens.append(exp.description)
            parts.append(" ".join(tokens))

        for proj in self.projects:
            tokens = [f"Project: {proj.name}"]
            if proj.tech_stack:
                tokens.append("Tech: " + ", ".join(proj.tech_stack))
            if proj.description:
                tokens.append(proj.description)
            parts.append(" ".join(tokens))

        for edu in self.education:
            label = edu.degree_raw or (edu.degree.value if edu.degree else "")
            tokens = [f"{label} at {edu.institution}"]
            if edu.major:
                tokens.append(f"major {edu.major}")
            parts.append(" ".join(tokens))

        if self.certifications:
            parts.append("Certifications: " + ", ".join(self.certifications))

        if self.languages:
            parts.append("Languages: " + ", ".join(self.languages))

        return "\n".join(parts)


class WorkLocation(BaseModel):
    """
    JD work location. `city` is intentionally hardcoded to the 3 cities the
    business operates in — do not widen this to free text.

    `lat`/`lng` are geocoded once at parse-time (see parser.parse_jd) via
    location_service.geocode() and persisted alongside jd_embedding — mirrors
    how jd_embedding is computed once at parse-time rather than per score
    call. None if geocoding failed.
    """
    city:        Literal["Ha Noi", "Ho Chi Minh", "Da Nang"] = "Ha Noi"
    raw_address: str                                          = ""
    work_mode:   Literal["onsite", "hybrid", "remote"]        = "onsite"
    lat:         Optional[float]                              = None
    lng:         Optional[float]                              = None

    @field_validator("city", mode="before")
    @classmethod
    def _normalize_city(cls, v: object) -> str:
        if not isinstance(v, str):
            return "Ha Noi"
        s = v.lower().strip()
        if "ha noi" in s or "hanoi" in s or s in {"hn"}:
            return "Ha Noi"
        if "ho chi minh" in s or "hcm" in s or "saigon" in s or "sai gon" in s:
            return "Ho Chi Minh"
        if "da nang" in s or "danang" in s:
            return "Da Nang"
        return "Ha Noi"

    @field_validator("raw_address", mode="before")
    @classmethod
    def _coerce_raw_address(cls, v: object) -> str:
        return v if isinstance(v, str) else ""

    @field_validator("work_mode", mode="before")
    @classmethod
    def _normalize_work_mode(cls, v: object) -> str:
        # Defaults to "onsite" when the JD gives no explicit signal — this is
        # a heuristic assumption (most JDs without a stated mode ARE onsite
        # in this market), not a neutral default. Revisit if that stops holding.
        if not isinstance(v, str):
            return "onsite"
        s = v.lower().strip()
        return s if s in {"onsite", "hybrid", "remote"} else "onsite"


# ---------------------------------------------------------------------------
# ParsedJD
# ---------------------------------------------------------------------------

class ParsedJD(BaseModel):
    title:                str
    required_skills:      list[RequiredSkill] = Field(default_factory=list)
    preferred_skills:     list[str]           = Field(default_factory=list)
    min_experience_years: int                 = 0
    education_degree:     Optional[DegreeLevel] = None
    work_location:        WorkLocation        = Field(default_factory=WorkLocation)

    @field_validator("education_degree", mode="before")
    @classmethod
    def _coerce_degree(cls, v: object) -> Optional[str]:
        # LLMs sometimes emit the literal string "null"/"none"/"" instead of a
        # JSON null; treat those as "no requirement" rather than 500-ing.
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("", "null", "none", "n/a", "na"):
                return None
        return v

    @field_validator("min_experience_years", mode="before")
    @classmethod
    def _coerce_exp(cls, v: object) -> int:
        if v is None or v == "":
            return 0
        try:
            return math.ceil(float(v))
        except (TypeError, ValueError):
            return 0

    @model_validator(mode="after")
    def _drop_generic_skills(self) -> "ParsedJD":
        """
        Remove soft-skill / meta-competency entries the parser mistook for
        concrete skills. A discrete "Programming Fundamentals" or "Teamwork"
        requirement can never be matched against a CV and would show as a
        permanent missing must-have, so it is filtered out here.
        """
        self.required_skills = [
            r for r in self.required_skills if not is_generic_non_skill(r.skill)
        ]
        self.preferred_skills = [
            p for p in self.preferred_skills if not is_generic_non_skill(p)
        ]
        return self

    # --- Internal helpers (not serialized) ---

    @property
    def required_degree_level(self) -> int:
        return self.education_degree.numeric if self.education_degree else 0

    @property
    def all_skill_names(self) -> list[str]:
        names: list[str] = []
        for s in self.required_skills:
            names.append(s.skill)
            names.extend(s.alternatives)
        return names + self.preferred_skills

    # --- Embed text ---

    def build_embed_text(self) -> str:
        parts = [self.title]

        if self.required_skills:
            skill_strs = []
            for s in self.required_skills:
                label = " or ".join([s.skill, *s.alternatives]) if s.alternatives else s.skill
                skill_strs.append(f"{label} [required]" if s.weight == 3 else label)
            parts.append("Required skills: " + ", ".join(skill_strs))

        if self.preferred_skills:
            parts.append("Preferred skills: " + ", ".join(self.preferred_skills))

        if self.min_experience_years:
            parts.append(f"Experience: minimum {self.min_experience_years} years")

        if self.education_degree:
            label = self.education_degree.value.replace("_", " ").title()
            parts.append(f"Education: {label} or above")

        return "\n".join(parts)
