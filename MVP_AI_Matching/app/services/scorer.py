"""
5-Dimension Scoring Engine — pure Python + numpy, NO LLM calls.

D1 Semantic   : cosine_sim(cv_embedding, jd_embedding), normalized to 0–1
D2 Skills     : weighted skill overlap with alias/fuzzy/category match
D3 Experience : base ratio + relevance/recency/over-qual modifiers
D4 Education  : cv_degree_level / jd_required_degree_level, capped at 1.0
D5 Keywords   : exact / word-boundary / multi-word phrase scoring
D6 Role Fit   : (optional) title similarity + seniority level match

final_score = Σ(Di × Wi) × 100
"""

from __future__ import annotations

import difflib
import re
from datetime import datetime
from typing import Optional

import numpy as np

from app.config import settings
from app.schemas import ParsedCV, ParsedJD


# ---------------------------------------------------------------------------
# 6D weights including role_fit — used when use_role_fit=True
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS_WITH_ROLE: dict[str, float] = {
    "semantic":   0.25,
    "skills":     0.30,
    "experience": 0.20,
    "education":  0.10,
    "keywords":   0.05,
    "role_fit":   0.10,
}


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
        # Java
        "java": "java", "spring": "spring", "spring boot": "spring",
        "springboot": "spring",
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
        # APIs
        "rest": "rest_api", "restful": "rest_api", "rest api": "rest_api",
        "restful api": "rest_api", "restful apis": "rest_api",
        "restful apis design": "rest_api",
        "graphql": "graphql", "grpc": "grpc",
        # Misc
        "git": "git", "github": "github", "gitlab": "gitlab",
        "go": "go", "golang": "go",
        "sql": "sql", "nosql": "nosql",
        "agile": "agile", "scrum": "agile",
        "oop": "oop", "object oriented programming": "oop",
    }

    CATEGORIES: dict[str, set[str]] = {
        "frontend": {"react", "angular", "vue", "javascript", "typescript",
                     "html", "css", "nextjs", "tailwind"},
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
    Tiered skill matching:
      1. Normalize CV + JD skills via alias map
      2. Exact match  → full weight
      3. Fuzzy match  → 0.9 × weight
      4. Category match (same domain) → 0.3–0.5 × weight
    """
    if not jd.required_skills:
        return 1.0
    matcher = matcher or _skill_matcher

    cv_skills_raw = _collect_cv_skills(cv)
    cv_skills = {matcher.normalize_skill(s) for s in cv_skills_raw if s}

    total_w = sum(s.weight for s in jd.required_skills)
    matched_w = 0.0

    for req in jd.required_skills:
        jd_skill = matcher.normalize_skill(req.skill)

        if jd_skill in cv_skills:
            matched_w += req.weight
            continue

        if any(matcher.fuzzy_match(jd_skill, cv_s) for cv_s in cv_skills):
            matched_w += 0.9 * req.weight
            continue

        cat_score = matcher.category_match(cv_skills, jd_skill)
        if cat_score > 0:
            matched_w += req.weight * cat_score

    return matched_w / total_w if total_w > 0 else 0.0


# ---------------------------------------------------------------------------
# D3: Experience — relevance + recency + over-qualification
# ---------------------------------------------------------------------------

def _parse_yyyy_mm(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    s = date_str.strip().lower()
    if s in ("present", "now", "nay", "current"):
        return datetime.now()
    for fmt in ("%Y-%m", "%Y/%m", "%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _months_since(dt: datetime) -> int:
    now = datetime.now()
    return (now.year - dt.year) * 12 + (now.month - dt.month)


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
            end_dt = _parse_yyyy_mm(latest.end)
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
# D6: Role Fit (optional)
# ---------------------------------------------------------------------------

_LEVEL_KEYWORDS: list[tuple[str, int]] = [
    ("intern",     0),
    ("fresher",    1),
    ("junior",     1),
    ("entry",      1),
    ("mid",        2),
    ("middle",     2),
    ("developer",  2),
    ("engineer",   2),
    ("specialist", 2),
    ("senior",     3),
    ("lead",       3),
    ("manager",    3),
    ("staff",      4),
    ("principal",  4),
    ("architect",  4),
    ("director",   4),
]


def _detect_level(title: str) -> int:
    if not title:
        return 2
    t = title.lower()
    best: Optional[int] = None
    for kw, lvl in _LEVEL_KEYWORDS:
        if kw in t and (best is None or lvl > best):
            best = lvl
    return best if best is not None else 2


def score_role_fit(cv: ParsedCV, jd: ParsedJD, recent_n: int = 3) -> float:
    """
    Title similarity + seniority level match against the N most recent roles.
    Returns the best combined score across those roles.
    """
    if not jd.title:
        return 1.0
    if not cv.work_experience:
        return 0.0

    jd_title = jd.title.lower()
    jd_level = _detect_level(jd_title)

    scores: list[float] = []
    for exp in cv.work_experience[:recent_n]:
        if not exp.role:
            continue
        exp_title = exp.role.lower()
        title_sim = difflib.SequenceMatcher(None, jd_title, exp_title).ratio()
        exp_level = _detect_level(exp_title)
        level_score = max(0.0, 1 - 0.25 * abs(jd_level - exp_level))
        scores.append(title_sim * 0.6 + level_score * 0.4)

    return max(scores) if scores else 0.0


# ---------------------------------------------------------------------------
# AdaptiveWeights — JD-aware weight tuning
# ---------------------------------------------------------------------------

class AdaptiveWeights:
    """
    Suggest weights based on JD characteristics. Output sums to 1.0.
    Optional: not used by default in calculate_score; pass result into
    `weights=` to apply.
    """

    BASE: dict[str, float] = dict(DEFAULT_WEIGHTS_WITH_ROLE)

    def calculate_weights(self, jd: ParsedJD) -> dict[str, float]:
        w = dict(self.BASE)

        if jd.required_skills and len(jd.required_skills) > 5:
            w["skills"]   += 0.10
            w["semantic"] = max(0.0, w["semantic"] - 0.05)
            w["keywords"] = max(0.0, w["keywords"] - 0.05)

        if jd.min_experience_years and jd.min_experience_years >= 5:
            w["experience"] += 0.10
            w["education"]  = max(0.0, w["education"] - 0.05)
            w["keywords"]   = max(0.0, w["keywords"] - 0.05)

        if jd.required_degree_level >= 4:
            w["education"] += 0.10
            w["skills"]    = max(0.0, w["skills"] - 0.05)
            w["keywords"]  = max(0.0, w["keywords"] - 0.05)

        total = sum(w.values())
        if total > 0:
            for k in w:
                w[k] = round(w[k] / total, 4)
        return w


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
    cosine_min:   float = 0.20,
    cosine_max:   float = 0.80,
    use_role_fit: bool = False,
) -> dict:
    """
    Compute all dimensions + final weighted score (0-100).
    If use_role_fit=True, the `scores` dict additionally includes `role_fit`.
    """
    w = weights or (DEFAULT_WEIGHTS_WITH_ROLE if use_role_fit else settings.default_weights)
    if not cv_raw_text:
        cv_raw_text = parsed_cv.build_embed_text()

    d1 = normalize_cosine(cosine_sim(cv_embedding, jd_embedding), cosine_min, cosine_max)
    d2 = score_skills(parsed_cv, parsed_jd)
    d3 = score_experience(parsed_cv, parsed_jd)
    d4 = score_education(parsed_cv, parsed_jd)
    d5 = score_keywords(cv_raw_text, parsed_jd)
    d6 = score_role_fit(parsed_cv, parsed_jd) if use_role_fit else None

    final = (
        d1 * w.get("semantic",   0.0) +
        d2 * w.get("skills",     0.0) +
        d3 * w.get("experience", 0.0) +
        d4 * w.get("education",  0.0) +
        d5 * w.get("keywords",   0.0)
    )
    if use_role_fit and d6 is not None:
        final += d6 * w.get("role_fit", 0.0)
    final *= 100

    scores: dict[str, float] = {
        "semantic":   round(d1 * 100, 1),
        "skills":     round(d2 * 100, 1),
        "experience": round(d3 * 100, 1),
        "education":  round(d4 * 100, 1),
        "keywords":   round(d5 * 100, 1),
    }
    if use_role_fit and d6 is not None:
        scores["role_fit"] = round(d6 * 100, 1)

    return {
        "final_score": round(final, 1),
        "scores":      scores,
    }


# ---------------------------------------------------------------------------
# Business rules — must-have skills + minimum experience floor
# ---------------------------------------------------------------------------

def calculate_score_with_rules(
    parsed_cv:         ParsedCV,
    parsed_jd:         ParsedJD,
    cv_embedding:      list[float],
    jd_embedding:      list[float],
    cv_raw_text:       str,
    weights:           dict[str, float] | None = None,
    cosine_min:        float = 0.20,
    cosine_max:        float = 0.80,
    use_role_fit:      bool  = False,
    enforce_must_have: bool  = True,
) -> dict:
    """
    Wraps calculate_score and applies hard-rule penalties:
      - Missing must-have skills (weight ≥ 3) with no category fallback:
          0.15 penalty each, cumulative cap 0.55.
      - cv_years < 0.8 × jd.min_experience_years:
          0.20 penalty.
      - Total cap: 0.70 (prevents crushing candidates to near-zero).

    A skill is only counted as "hard missing" if:
      - Not exact/fuzzy matched, AND
      - No same-category skills present (category_match < 0.3).
    This avoids penalizing candidates who have related skills in the same domain
    (e.g. PyTorch/TensorFlow covering "Machine Learning") while still factoring
    skill gaps into the D2 score dimension.
    """
    result = calculate_score(
        parsed_cv, parsed_jd, cv_embedding, jd_embedding, cv_raw_text,
        weights=weights, cosine_min=cosine_min, cosine_max=cosine_max,
        use_role_fit=use_role_fit,
    )

    penalty = 0.0
    reasons: list[str] = []

    if enforce_must_have:
        matcher = _skill_matcher
        cv_skills = {matcher.normalize_skill(s) for s in _collect_cv_skills(parsed_cv) if s}

        must_haves = [r for r in parsed_jd.required_skills if r.weight >= 3]
        hard_missing: list[str] = []
        for req in must_haves:
            jd_skill = matcher.normalize_skill(req.skill)
            if jd_skill in cv_skills:
                continue
            if any(matcher.fuzzy_match(jd_skill, cv_s) for cv_s in cv_skills):
                continue
            # Skip hard penalty only for specific skill-cluster categories where
            # having related tools genuinely covers the domain (e.g. pytorch+scikit-learn
            # covering "Machine Learning", or csharp+aspnet covering ".NET Core").
            # Broad categories like "language" are excluded — knowing Python does NOT
            # cover Java, even if they share the same category.
            cat = matcher._category_of(jd_skill)
            if (cat in matcher.PENALTY_SKIP_CATEGORIES
                    and matcher.category_match(cv_skills, jd_skill) >= 0.4):
                continue
            hard_missing.append(req.skill)

        if hard_missing:
            skill_penalty = min(0.15 * len(hard_missing), 0.55)
            penalty += skill_penalty
            reasons.append(f"missing must-have skills: {hard_missing}")

        if parsed_jd.min_experience_years:
            cv_years = parsed_cv.total_exp_months / 12.0
            min_required = 0.8 * parsed_jd.min_experience_years
            if cv_years < min_required:
                penalty += 0.20
                reasons.append(
                    f"insufficient experience: {cv_years:.1f}y < {min_required:.1f}y"
                )

    penalty = min(penalty, 0.70)
    result["final_score"]      = round(result["final_score"] * (1 - penalty), 1)
    result["penalty_applied"]  = round(penalty, 3)
    result["penalty_reasons"]  = reasons
    return result


def recalculate_final(scores: dict[str, float], weights: dict[str, float]) -> float:
    """
    Recalculate final score from dimension scores and new weights.
    Both input scores and final output score are in [0, 100].
    """
    total = 0.0
    for k, w in weights.items():
        total += scores.get(k, 0.0) * w
    return round(total, 1)

