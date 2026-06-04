"""
Shared Pydantic v2 schemas — CV + JD.
Only fields actually used in AI scoring/search/embed are kept.
Computed helpers are plain @property (not serialized to JSON).
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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
    def _set_current(self) -> "WorkExperience":
        if self.end and self.end.lower() in ("present", "nay", "now", "current"):
            self.is_current = True
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
