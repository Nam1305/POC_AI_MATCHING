"""
Static skill taxonomy — the hand-maintained data tables the SkillMatcher runs on.

Kept separate from scorer.py (the matching logic) so the vocabulary can grow
without touching algorithms, and so tools can import the data cheaply:

  ALIASES                 variant spelling → canonical token  (reactjs → react)
  CATEGORIES              canonical token → broad domain bucket (partial-credit)
  PENALTY_SKIP_CATEGORIES categories where same-domain coverage waives the hard
                          must-have penalty
  MANUAL_IMPLIES          concept edges the generated IMPLIES graph must always
                          contain
  IMPLIES                 the generated implication graph (re-exported)
  IMPLIES_ALL             the effective graph the matcher runs on
                          = IMPLIES ∪ MANUAL_IMPLIES

This module is the single import surface for all skill data. The raw generated
graph physically lives in skill_implies.py — a machine-written file that
scripts/generate_implies_llm.py OVERWRITES wholesale, which is exactly why it
stays a separate file from this hand-maintained one. Here it is only re-exported
and merged, so consumers import everything from skill_data.
"""

from __future__ import annotations

from app.services.skill_implies import IMPLIES  # generated graph — see generate_implies_llm.py


# ---------------------------------------------------------------------------
# ALIASES — variant spelling → canonical skill token
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# CATEGORIES — canonical token → broad domain bucket (drives partial credit)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# MANUAL_IMPLIES — concept edges the generated IMPLIES graph must always contain
# ---------------------------------------------------------------------------

# Anchor edges that the LLM-generated skill_implies.py is seeded with and that
# scorer.py merges on top of it: a concrete library guarantees the capability it
# exists to provide (Chart.js → data visualization) or the transport it wraps
# (axios → REST). Kept here so a regeneration can never silently drop them.
MANUAL_IMPLIES: dict[str, set[str]] = {
    "chartjs":    {"data_visualization", "javascript"},
    "d3js":       {"data_visualization", "javascript"},
    "recharts":   {"data_visualization", "react"},
    "highcharts": {"data_visualization", "javascript"},
    "plotly":     {"data_visualization"},
    "axios":      {"rest_api"},
}


# ---------------------------------------------------------------------------
# IMPLIES_ALL — effective implication graph the matcher runs on
# ---------------------------------------------------------------------------

# = generated graph (IMPLIES) ∪ hand-anchored concept edges (MANUAL_IMPLIES).
# Built once at import; the transitive closure is applied per-lookup in scorer.
IMPLIES_ALL: dict[str, set[str]] = {k: set(v) for k, v in IMPLIES.items()}
for _src, _targets in MANUAL_IMPLIES.items():
    IMPLIES_ALL.setdefault(_src, set()).update(_targets)
