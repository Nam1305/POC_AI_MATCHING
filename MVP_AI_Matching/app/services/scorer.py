"""
5-Dimension Scoring Engine — pure Python + numpy, NO LLM calls.

D1 Semantic   : cosine_sim(cv_embedding, jd_embedding), normalized to 0–1
D2 Skills     : weighted skill overlap with alias/implied/fuzzy/category match
D3 Experience : base ratio + relevance/recency/over-qual modifiers
D4 Education  : cv_degree_level / jd_required_degree_level, capped at 1.0
D5 Keywords   : exact / word-boundary / multi-word phrase scoring

final_score = Σ(Di × Wi) × 100
"""

from __future__ import annotations

import datetime
import difflib
import re
from typing import Optional

import numpy as np

from app.config import settings
from app.schemas import ParsedCV, ParsedJD, parse_month
from app.services.skill_implies import IMPLIES

# Concept implications Wikidata P277 ("programmed in") does not model: a concrete
# library guarantees the capability it exists to provide (Chart.js → data
# visualization) or the transport it wraps (axios → REST). Kept here rather than
# in the generated skill_implies.py so regenerating that file won't drop them.
_MANUAL_IMPLIES: dict[str, set[str]] = {
    "chartjs":    {"data_visualization", "javascript"},
    "d3js":       {"data_visualization", "javascript"},
    "recharts":   {"data_visualization", "react"},
    "highcharts": {"data_visualization", "javascript"},
    "plotly":     {"data_visualization"},
    "axios":      {"rest_api"},
}

# Effective implication graph = generated P277 data + manual concept edges.
_IMPLIES_ALL: dict[str, set[str]] = {k: set(v) for k, v in IMPLIES.items()}
for _k, _v in _MANUAL_IMPLIES.items():
    _IMPLIES_ALL.setdefault(_k, set()).update(_v)


# ---------------------------------------------------------------------------
# SkillMatcher — alias normalization, fuzzy match, category fallback
# ---------------------------------------------------------------------------

class SkillMatcher:
    """
    Normalize variants of the same skill, fuzzy-match misspellings, and
    grant partial credit for skills in the same broad category.
    """

    ALIASES: dict[str, str] = {
        # JavaScript ecosystem — including versioned forms like "JavaScript (ES6+)"
        "js": "javascript", "javascript": "javascript", "es6": "javascript",
        "es6+": "javascript", "es2015": "javascript", "es2017": "javascript",
        "ecmascript": "javascript",
        "ts": "typescript", "typescript": "typescript",
        "react": "react", "reactjs": "react", "react.js": "react",
        "node": "nodejs", "nodejs": "nodejs", "node.js": "nodejs",
        "vue": "vue", "vuejs": "vue", "vue.js": "vue",
        "angular": "angular", "angularjs": "angular",
        "next": "nextjs", "nextjs": "nextjs", "next.js": "nextjs",
        "express": "express", "expressjs": "express",
        "nestjs": "nestjs", "nest.js": "nestjs",
        # HTML / CSS — explicit versioned forms
        "html": "html", "html5": "html", "html 5": "html",
        "css": "css", "css3": "css", "css 3": "css",
        "modern css": "css", "modern css layout techniques": "css",
        "tailwind": "tailwind", "tailwind css": "tailwind",
        # Data visualization — libraries + the capability they provide
        "chart.js": "chartjs", "chartjs": "chartjs", "chart js": "chartjs",
        "d3.js": "d3js", "d3": "d3js", "d3js": "d3js", "d3 js": "d3js",
        "recharts": "recharts", "highcharts": "highcharts", "plotly": "plotly",
        "data visualization": "data_visualization",
        "data visualisation": "data_visualization",
        "data viz": "data_visualization", "dataviz": "data_visualization",
        # Frontend delivery concepts
        "responsive web design": "responsive_web_design",
        "responsive design": "responsive_web_design",
        "responsive ui": "responsive_web_design",
        "responsive web": "responsive_web_design", "rwd": "responsive_web_design",
        "cross-browser compatibility": "cross_browser",
        "cross browser compatibility": "cross_browser",
        "cross-browser": "cross_browser", "cross browser": "cross_browser",
        "ui design": "ui_design", "user interface design": "ui_design",
        "clean code": "clean_code",
        # Python
        "py": "python", "python": "python", "python3": "python",
        "django": "django", "flask": "flask", "fastapi": "fastapi",
        # .NET — ".NET Core" maps to same canonical as "ASP.NET Core"
        "c#": "csharp", "csharp": "csharp", "c sharp": "csharp",
        ".net": "dotnet", "dotnet": "dotnet", "dot net": "dotnet",
        ".net core": "aspnet", "dotnetcore": "aspnet", "dot net core": "aspnet",
        "asp.net": "aspnet", "aspnet": "aspnet", "asp.net core": "aspnet",
        "ef": "entity framework", "ef core": "entity framework",
        "entity framework": "entity framework",
        "entity framework core": "entity framework",
        "dapper": "dapper",
        "nuget": "nuget",
        # Java
        "java": "java", "spring": "spring", "spring boot": "spring",
        "springboot": "spring",
        "hibernate": "hibernate",
        "maven": "maven", "apache maven": "maven",
        "gradle": "gradle",
        "junit": "junit",
        "quarkus": "quarkus",
        "micronaut": "micronaut",
        # Databases
        "postgres": "postgresql", "postgresql": "postgresql", "psql": "postgresql",
        "mysql": "mysql", "mariadb": "mysql",
        "mongo": "mongodb", "mongodb": "mongodb",
        "sqlserver": "sqlserver", "sql server": "sqlserver", "mssql": "sqlserver",
        "redis": "redis",
        "elastic": "elasticsearch", "elasticsearch": "elasticsearch",
        # Cloud / DevOps
        "aws": "aws", "amazon web services": "aws",
        "gcp": "gcp", "google cloud": "gcp", "google cloud platform": "gcp",
        "azure": "azure", "microsoft azure": "azure",
        "k8s": "kubernetes", "kubernetes": "kubernetes",
        "docker": "docker",
        "ci/cd": "ci_cd", "cicd": "ci_cd", "ci cd": "ci_cd",
        "jenkins": "jenkins", "terraform": "terraform",
        # ML / AI — frameworks
        "tf": "tensorflow", "tensorflow": "tensorflow",
        "pytorch": "pytorch", "torch": "pytorch",
        "sklearn": "scikit-learn", "scikit-learn": "scikit-learn",
        "scikit learn": "scikit-learn",
        "keras": "keras",
        # ML / AI — domain concepts (canonical form without spaces)
        "machine learning": "machine_learning", "machine_learning": "machine_learning",
        "ml": "machine_learning",
        "deep learning": "deep_learning", "deep_learning": "deep_learning",
        "dl": "deep_learning",
        "natural language processing": "nlp", "nlp": "nlp",
        "computer vision": "computer_vision", "computer_vision": "computer_vision",
        "data preprocessing": "data_preprocessing", "data_preprocessing": "data_preprocessing",
        "data analysis": "data_analysis", "data_analysis": "data_analysis",
        "artificial intelligence": "machine_learning", "ai": "machine_learning",
        # Data
        "pandas": "pandas", "numpy": "numpy",
        "airflow": "airflow", "apache airflow": "airflow",
        "opencv": "opencv", "open cv": "opencv",
        "spacy": "spacy",
        "nltk": "nltk",
        "xgboost": "xgboost", "xg boost": "xgboost",
        "spark": "spark", "apache spark": "spark", "pyspark": "spark",
        # APIs
        "rest": "rest_api", "restful": "rest_api", "rest api": "rest_api",
        "rest apis": "rest_api", "restful api": "rest_api", "restful apis": "rest_api",
        "restful apis design": "rest_api", "restful api integration": "rest_api",
        "rest api integration": "rest_api", "api integration": "rest_api",
        "axios": "axios",
        "graphql": "graphql", "grpc": "grpc",
        # Misc
        "git": "git", "github": "github", "gitlab": "gitlab",
        "go": "go", "golang": "go",
        "sql": "sql", "nosql": "nosql",
        "agile": "agile", "scrum": "agile",
        "oop": "oop", "object oriented programming": "oop",
        # Other languages / frameworks
        "ruby": "ruby",
        "php": "php",
        "rust": "rust",
        "laravel": "laravel",
        "rails": "rails", "ruby on rails": "rails",
    }

    CATEGORIES: dict[str, set[str]] = {
        "frontend": {"react", "angular", "vue", "javascript", "typescript",
                     "html", "css", "nextjs", "tailwind"},
        "dataviz":  {"chartjs", "d3js", "recharts", "highcharts", "plotly",
                     "data_visualization"},
        "backend":  {"django", "flask", "fastapi", "spring", "express",
                     "nestjs", "aspnet", "dotnet", "nodejs"},
        "dotnet":   {"dotnet", "aspnet", "csharp", "entity framework"},
        "database": {"mysql", "postgresql", "mongodb", "redis", "sqlserver",
                     "elasticsearch", "sql", "nosql"},
        "cloud":    {"aws", "gcp", "azure"},
        "devops":   {"docker", "kubernetes", "ci_cd", "jenkins", "terraform"},
        # ml_frameworks: concrete frameworks give category credit for ML/DL domain skills
        "ml_frameworks": {"tensorflow", "pytorch", "keras", "scikit-learn",
                          "machine_learning", "deep_learning"},
        "ml_domain":     {"machine_learning", "deep_learning", "nlp",
                          "computer_vision", "data_preprocessing"},
        "data":     {"pandas", "numpy", "data_preprocessing", "data_analysis"},
        "api":      {"rest_api", "graphql", "grpc"},
        "language": {"python", "javascript", "typescript", "csharp", "java",
                     "go", "ruby", "php", "rust"},
    }

    # Categories where having related tools at category_match ≥ 0.4 justifies
    # skipping the hard penalty (D2 already reflects the skill gap via partial credit).
    # "frontend" is included because TypeScript+ReactJS strongly implies JavaScript.
    # "language" is excluded — knowing Python does NOT cover Java, Go, etc.
    PENALTY_SKIP_CATEGORIES: set[str] = {
        "ml_frameworks", "ml_domain", "dotnet", "devops", "cloud", "frontend",
        "dataviz",
    }

    def normalize_skill(self, skill: str) -> str:
        if not skill:
            return ""
        key = skill.lower().strip()
        if key in self.ALIASES:
            return self.ALIASES[key]
        # Strip parenthetical suffix: "JavaScript (ES6+)" → "javascript"
        stripped = re.sub(r'\s*\([^)]*\)', '', key).strip()
        if stripped and stripped != key:
            return self.ALIASES.get(stripped, stripped)
        return key

    def fuzzy_match(self, skill1: str, skill2: str, threshold: float = 0.85) -> bool:
        if not skill1 or not skill2:
            return False
        ratio = difflib.SequenceMatcher(None, skill1, skill2).ratio()
        return ratio >= threshold

    def _category_of(self, skill: str) -> Optional[str]:
        for cat, members in self.CATEGORIES.items():
            if skill in members:
                return cat
        return None

    def category_match(self, cv_skills: set[str], jd_skill: str) -> float:
        """
        Partial credit when JD skill belongs to a category that the CV
        already covers via other skills. Score scales with how many
        same-category skills the CV has.
        """
        cat = self._category_of(jd_skill)
        if not cat:
            return 0.0
        overlap = len(cv_skills & self.CATEGORIES[cat])
        if overlap == 0:
            return 0.0
        # 1 overlap → 0.3, 2 → 0.4, ≥3 → 0.5
        return min(0.3 + 0.1 * (overlap - 1), 0.5)

    def implied_skills(self, skill: str) -> set[str]:
        """
        One-way transitive closure over IMPLIES (e.g. nextjs → react → javascript).
        "Knowing X guarantees knowing Y" — sourced from Wikidata P277, not a guess.
        """
        seen: set[str] = set()
        stack = [skill]
        while stack:
            for nxt in _IMPLIES_ALL.get(stack.pop(), ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen

    def expand_implied(self, skills: set[str]) -> set[str]:
        """Add every skill logically guaranteed by the given skill set."""
        expanded = set(skills)
        for s in skills:
            expanded |= self.implied_skills(s)
        return expanded

    def normalized_cv_skills(self, cv: ParsedCV) -> tuple[set[str], set[str]]:
        """Return (normalized CV skills, same set expanded with implied skills)."""
        cv_skills = {self.normalize_skill(s) for s in _collect_cv_skills(cv) if s}
        return cv_skills, self.expand_implied(cv_skills)

    def is_fuzzy(self, jd_skill: str, cv_skills: set[str]) -> bool:
        """True if any CV skill fuzzy-matches the (normalized) JD skill."""
        return any(self.fuzzy_match(jd_skill, cv_s) for cv_s in cv_skills)

    # -- OR-group (alternatives) aware matching --------------------------------
    #
    # A RequiredSkill may carry `alternatives`: the requirement is satisfied by
    # ANY of {skill} ∪ alternatives. All group logic funnels through here so the
    # scorer, penalty rules, and evaluator agree.

    # status priority for picking the best alternative in a group
    _STATUS_RANK = {"matched": 2, "matched_implied": 1, "missing": 0}

    def group_names(self, req) -> list[str]:
        """Normalized skill names in a requirement's OR-group."""
        return [self.normalize_skill(n) for n in [req.skill, *req.alternatives] if n]

    def group_label(self, req) -> str:
        """Human-readable label for a requirement — 'A / B / C' for OR-groups."""
        names = [n for n in [req.skill, *req.alternatives] if n]
        return " / ".join(dict.fromkeys(names))

    def evaluate_skill(self, jd_norm: str, cv_skills: set[str],
                       cv_skills_expanded: set[str]) -> tuple[str, float]:
        """
        Classify one normalized JD skill against the CV.
        Returns (status, credit) where status ∈ matched|matched_implied|missing
        and credit ∈ [0,1] mirrors score_skills tiers (exact/implied=1.0,
        fuzzy=0.9, else category partial credit).
        """
        if jd_norm in cv_skills:
            return "matched", 1.0
        if jd_norm in cv_skills_expanded:
            return "matched_implied", 1.0
        if self.is_fuzzy(jd_norm, cv_skills):
            return "matched", 0.9
        return "missing", self.category_match(cv_skills, jd_norm)

    def evaluate_group(self, req, cv_skills: set[str],
                       cv_skills_expanded: set[str]) -> tuple[str, float]:
        """Best (status, credit) over every alternative in the requirement."""
        best: tuple[str, float] = ("missing", 0.0)
        for jd_norm in self.group_names(req):
            status, credit = self.evaluate_skill(jd_norm, cv_skills, cv_skills_expanded)
            if (self._STATUS_RANK[status], credit) > (self._STATUS_RANK[best[0]], best[1]):
                best = (status, credit)
        return best

    def is_group_hard_missing(self, req, cv_skills: set[str],
                              cv_skills_expanded: set[str]) -> bool:
        """
        A requirement is 'hard missing' only when NO alternative matches
        (exact/implied/fuzzy) AND no alternative has strong same-category
        coverage in a penalty-skip category. Mirrors the single-skill rule but
        satisfied by any one option in the group.
        """
        status, _ = self.evaluate_group(req, cv_skills, cv_skills_expanded)
        if status != "missing":
            return False
        for jd_norm in self.group_names(req):
            cat = self._category_of(jd_norm)
            if cat in self.PENALTY_SKIP_CATEGORIES and self.category_match(cv_skills, jd_norm) >= 0.4:
                return False
        return True


_skill_matcher = SkillMatcher()


# ---------------------------------------------------------------------------
# D1: Semantic
# ---------------------------------------------------------------------------

def cosine_sim(v1: list[float], v2: list[float]) -> float:
    """Cosine similarity between two vectors. Returns [-1, 1] (typically [0, 1] for text)."""
    a, b = np.asarray(v1, dtype=np.float32), np.asarray(v2, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


def normalize_cosine(raw: float, min_val: float = 0.55, max_val: float = 0.90) -> float:
    """
    Stretch [min_val, max_val] → [0, 1] so D1 scoring uses the full range.
    Calibrated for gemini-embedding-001: floor ~0.55 (unrelated fields), ceiling ~0.90 (same-stack).
    """
    return max(0.0, min((raw - min_val) / (max_val - min_val), 1.0))


# ---------------------------------------------------------------------------
# D2: Skills — alias + fuzzy + category
# ---------------------------------------------------------------------------

def _collect_cv_skills(cv: ParsedCV) -> set[str]:
    """Aggregate skills from cv.skills + work_experience.tech_stack + projects.tech_stack."""
    skills: set[str] = {s.lower() for s in cv.skills}
    for exp in cv.work_experience:
        skills.update(s.lower() for s in exp.tech_stack)
    for proj in cv.projects:
        skills.update(s.lower() for s in proj.tech_stack)
    return skills


def score_skills(
    cv: ParsedCV,
    jd: ParsedJD,
    matcher: Optional[SkillMatcher] = None,
) -> float:
    """
    Tiered skill matching (per requirement, satisfied by any OR-alternative):
      1. Normalize CV + JD skills via alias map
      2. Exact match   → full weight
      3. Implied match → full weight (e.g. CV has "react" → JD "javascript" is
         logically guaranteed, sourced from IMPLIES / Wikidata P277)
      4. Fuzzy match   → 0.9 × weight
      5. Category match (same domain) → 0.3–0.5 × weight
    """
    if not jd.required_skills:
        return 1.0
    matcher = matcher or _skill_matcher

    cv_skills, cv_skills_expanded = matcher.normalized_cv_skills(cv)

    total_w = sum(s.weight for s in jd.required_skills)
    matched_w = 0.0

    for req in jd.required_skills:
        _, credit = matcher.evaluate_group(req, cv_skills, cv_skills_expanded)
        matched_w += req.weight * credit

    return matched_w / total_w if total_w > 0 else 0.0


# ---------------------------------------------------------------------------
# D3: Experience — relevance + recency + over-qualification
# ---------------------------------------------------------------------------

def _months_since(dt: datetime.date) -> int:
    today = datetime.date.today()
    return (today.year - dt.year) * 12 + (today.month - dt.month)


def _jd_domain_tokens(jd: ParsedJD) -> list[str]:
    """
    Derive domain hints from JD title + keywords.
    Filter to longer tokens to avoid generic noise.
    """
    tokens: set[str] = set()
    if jd.title:
        for t in re.findall(r"\w+", jd.title):
            if len(t) > 3:
                tokens.add(t.lower())
    for kw in jd.keywords or []:
        for t in re.findall(r"\w+", kw):
            if len(t) > 3:
                tokens.add(t.lower())
    return list(tokens)


def score_experience(cv: ParsedCV, jd: ParsedJD) -> float:
    """
    Base: min(cv_years / jd_min_years, 1.0).

    Modifiers (clamped final to [0, 1]):
      + up to 0.20 if work history overlaps JD domain tokens
      + 0.10 if latest job ended < 3 months ago (or is current)
      - 0.10 if latest job ended > 12 months ago
      - 0.05 if cv_years > 2 × jd_min_years (over-qualification)
    """
    if not jd.min_experience_years:
        return 1.0

    cv_years = cv.total_exp_months / 12.0
    base = min(cv_years / jd.min_experience_years, 1.0)
    modifiers = 0.0

    domain_tokens = _jd_domain_tokens(jd)
    if domain_tokens and cv.work_experience:
        relevant_months = 0
        for exp in cv.work_experience:
            haystack = " ".join(filter(None, [exp.role or "", exp.description or ""])).lower()
            if any(tok in haystack for tok in domain_tokens):
                relevant_months += (exp.months or 0)
        if relevant_months > 0:
            relevant_years = relevant_months / 12.0
            relevance_ratio = min(relevant_years / jd.min_experience_years, 1.0)
            modifiers += 0.20 * relevance_ratio

    if cv.work_experience:
        latest = cv.work_experience[0]
        if latest.is_current:
            modifiers += 0.10
        else:
            end_dt = parse_month(latest.end)
            if end_dt:
                months_ago = _months_since(end_dt)
                if months_ago < 3:
                    modifiers += 0.10
                elif months_ago > 12:
                    modifiers -= 0.10

    if cv_years > 2 * jd.min_experience_years:
        modifiers -= 0.05

    return max(0.0, min(base + modifiers, 1.0))


# ---------------------------------------------------------------------------
# D4: Education
# ---------------------------------------------------------------------------

def score_education(cv: ParsedCV, jd: ParsedJD) -> float:
    """cv_degree_level / jd_required_degree_level, capped at 1.0."""
    jd_level = jd.required_degree_level
    if not jd_level:
        return 1.0
    cv_level = cv.highest_degree_level
    if not cv_level:
        return 0.5
    return min(cv_level / jd_level, 1.0)


# ---------------------------------------------------------------------------
# D5: Keywords — exact / word-boundary / multi-word
# ---------------------------------------------------------------------------

def _clean_text_for_match(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())


def score_keywords(cv_raw_text: str, jd: ParsedJD) -> float:
    """
    Per-keyword score:
      - exact substring or word-boundary match → 1.0
      - multi-word phrase, all subwords present → 0.7
      - otherwise → 0.0
    Final = mean of keyword scores.
    """
    if not jd.keywords:
        return 1.0

    text_cleaned = _clean_text_for_match(cv_raw_text)

    keyword_scores: list[float] = []
    for kw in jd.keywords:
        if not kw or not kw.strip():
            continue
        kw_clean = _clean_text_for_match(kw).strip()
        if not kw_clean:
            continue

        if kw_clean in text_cleaned:
            keyword_scores.append(1.0)
            continue

        try:
            if re.search(rf"\b{re.escape(kw_clean)}\b", text_cleaned):
                keyword_scores.append(1.0)
                continue
        except re.error:
            pass

        words = kw_clean.split()
        if len(words) > 1 and all(
            re.search(rf"\b{re.escape(w)}\b", text_cleaned) for w in words
        ):
            keyword_scores.append(0.7)
            continue

        keyword_scores.append(0.0)

    if not keyword_scores:
        return 1.0
    return sum(keyword_scores) / len(keyword_scores)


# ---------------------------------------------------------------------------
# Seniority detection — shared with the evaluator's seniority analysis
# ---------------------------------------------------------------------------

# Explicit seniority words. Generic role nouns (developer/engineer/...) carry
# no seniority signal on their own, so a title with none of these defaults to
# mid-level (2). Listing "senior" before matching means "Junior Developer"
# reads as Junior — not Mid — because the seniority word wins over the role noun.
_LEVEL_KEYWORDS: list[tuple[str, int]] = [
    ("intern",    0),
    ("fresher",   1),
    ("junior",    1),
    ("entry",     1),
    ("mid",       2),
    ("middle",    2),
    ("senior",    3),
    ("lead",      3),
    ("manager",   3),
    ("staff",     4),
    ("principal", 4),
    ("architect", 4),
    ("director",  4),
]


def _detect_level(title: str) -> int:
    """Seniority level 0–4 from a job title. Defaults to mid-level (2)."""
    if not title:
        return 2
    t = title.lower()
    levels = [lvl for kw, lvl in _LEVEL_KEYWORDS if kw in t]
    return max(levels) if levels else 2


# ---------------------------------------------------------------------------
# Aggregate — calculate_score
# ---------------------------------------------------------------------------

def calculate_score(
    parsed_cv:    ParsedCV,
    parsed_jd:    ParsedJD,
    cv_embedding: list[float],
    jd_embedding: list[float],
    cv_raw_text:  str = "",
    weights:      dict[str, float] | None = None,
    cosine_min:   float | None = None,
    cosine_max:   float | None = None,
) -> dict:
    """Compute all 5 dimensions + final weighted score (0-100)."""
    w = weights or settings.default_weights
    cosine_min = settings.cosine_min if cosine_min is None else cosine_min
    cosine_max = settings.cosine_max if cosine_max is None else cosine_max
    if not cv_raw_text:
        cv_raw_text = parsed_cv.build_embed_text()

    dims = {
        "semantic":   normalize_cosine(cosine_sim(cv_embedding, jd_embedding), cosine_min, cosine_max),
        "skills":     score_skills(parsed_cv, parsed_jd),
        "experience": score_experience(parsed_cv, parsed_jd),
        "education":  score_education(parsed_cv, parsed_jd),
        "keywords":   score_keywords(cv_raw_text, parsed_jd),
    }

    final = 100 * sum(value * w.get(name, 0.0) for name, value in dims.items())

    return {
        "final_score": round(final, 1),
        "scores":      {name: round(value * 100, 1) for name, value in dims.items()},
    }


# ---------------------------------------------------------------------------
# Business rules — must-have skills + minimum experience floor
# ---------------------------------------------------------------------------

def calculate_score_with_rules(
    parsed_cv:         ParsedCV,
    parsed_jd:         ParsedJD,
    cv_embedding:      list[float],
    jd_embedding:      list[float],
    cv_raw_text:       str = "",
    weights:           dict[str, float] | None = None,
    cosine_min:        float | None = None,
    cosine_max:        float | None = None,
    enforce_must_have: bool = True,
) -> dict:
    """
    Wrap calculate_score and apply hard-rule penalties:
      - Each hard-missing must-have skill (weight ≥ 3): 0.15 penalty, cap 0.55.
      - cv_years < 0.8 × jd.min_experience_years: 0.20 penalty.
      - Total penalty capped at 0.70 (never crush a candidate to near-zero).
    Adds `penalty_applied` and `penalty_reasons` to the result.
    """
    result = calculate_score(
        parsed_cv, parsed_jd, cv_embedding, jd_embedding, cv_raw_text,
        weights=weights, cosine_min=cosine_min, cosine_max=cosine_max,
    )
    if not enforce_must_have:
        result["penalty_applied"] = 0.0
        result["penalty_reasons"] = []
        return result

    matcher = _skill_matcher
    cv_skills, cv_skills_expanded = matcher.normalized_cv_skills(parsed_cv)

    penalty = 0.0
    reasons: list[str] = []

    hard_missing = [
        matcher.group_label(req) for req in parsed_jd.required_skills
        if req.weight >= 3
        and matcher.is_group_hard_missing(req, cv_skills, cv_skills_expanded)
    ]
    if hard_missing:
        penalty += min(0.15 * len(hard_missing), 0.55)
        reasons.append(f"missing must-have skills: {hard_missing}")

    if parsed_jd.min_experience_years:
        cv_years = parsed_cv.total_exp_months / 12.0
        min_required = 0.8 * parsed_jd.min_experience_years
        if cv_years < min_required:
            penalty += 0.20
            reasons.append(f"insufficient experience: {cv_years:.1f}y < {min_required:.1f}y")

    penalty = min(penalty, 0.70)
    result["final_score"]     = round(result["final_score"] * (1 - penalty), 1)
    result["penalty_applied"] = round(penalty, 3)
    result["penalty_reasons"] = reasons
    return result

