"""
Shared Pydantic v2 schemas — CV + JD.
Only fields actually used in AI scoring/search/embed are kept.
Computed helpers are plain @property (not serialized to JSON).
"""

from __future__ import annotations

import datetime
import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _diff_months(start: str, end: str) -> int:
    """Calculate calendar months between two 'YYYY-MM' strings.
    'present' / 'now' / 'nay' resolve to the current month.
    """
    _PRESENT = {"present", "nay", "now", "current", ""}

    def _parse(s: str) -> datetime.date:
        s = (s or "").strip().lower()
        if s in _PRESENT:
            return datetime.date.today().replace(day=1)
        parts = s.split("-")
        try:
            year  = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            return datetime.date(year, max(1, min(12, month)), 1)
        except (ValueError, IndexError):
            return datetime.date.today().replace(day=1)

    try:
        s = _parse(start)
        e = _parse(end)
        if e < s:
            e = s
        return (e.year - s.year) * 12 + (e.month - s.month)
    except Exception:
        return 0


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
        if self.end and self.end.lower() in ("present", "nay", "now", "current"):
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
    status: str   # "matched" | "missing_must_have" | "missing_preferred"
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
    seniority_match:    str = ""   # match | over_qualified | under_qualified | unknown
    seniority_detail:   str = ""

    recommendation:     str = ""   # strong_fit | possible_fit | weak_fit | poor_fit

    # Narrative — HR đọc như người viết
    narrative:          str = ""


# ---------------------------------------------------------------------------
# JD sub-models
# ---------------------------------------------------------------------------

class RequiredSkill(BaseModel):
    skill:  str
    weight: int = 1   # 1 nice-to-have → 3 must-have


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
        return sum(e.months for e in self.work_experience)

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


# ---------------------------------------------------------------------------
# ParsedJD
# ---------------------------------------------------------------------------

class ParsedJD(BaseModel):
    title:                str
    required_skills:      list[RequiredSkill] = Field(default_factory=list)
    preferred_skills:     list[str]           = Field(default_factory=list)
    min_experience_years: int                 = 0
    education_degree:     Optional[DegreeLevel] = None
    keywords:             list[str]           = Field(default_factory=list)

    @field_validator("min_experience_years", mode="before")
    @classmethod
    def _coerce_exp(cls, v: object) -> int:
        if v is None or v == "":
            return 0
        try:
            return math.ceil(float(v))
        except (TypeError, ValueError):
            return 0

    # --- Internal helpers (not serialized) ---

    @property
    def required_degree_level(self) -> int:
        return self.education_degree.numeric if self.education_degree else 0

    @property
    def all_skill_names(self) -> list[str]:
        return [s.skill for s in self.required_skills] + self.preferred_skills

    # --- Embed text ---

    def build_embed_text(self) -> str:
        parts = [self.title]

        if self.required_skills:
            skill_strs = [
                f"{s.skill} [required]" if s.weight == 3 else s.skill
                for s in self.required_skills
            ]
            parts.append("Required skills: " + ", ".join(skill_strs))

        if self.preferred_skills:
            parts.append("Preferred skills: " + ", ".join(self.preferred_skills))

        if self.min_experience_years:
            parts.append(f"Experience: minimum {self.min_experience_years} years")

        if self.education_degree:
            label = self.education_degree.value.replace("_", " ").title()
            parts.append(f"Education: {label} or above")

        if self.keywords:
            parts.append("Keywords: " + ", ".join(self.keywords))

        return "\n".join(parts)
