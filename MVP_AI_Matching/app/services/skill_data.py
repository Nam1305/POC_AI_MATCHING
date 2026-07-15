"""
Bảng dữ liệu kỹ năng (skill taxonomy) — các bảng dữ liệu tĩnh, được duy trì
thủ công, mà SkillMatcher (trong scorer.py) dùng để so khớp kỹ năng.

File này được tách riêng khỏi scorer.py (nơi chứa logic so khớp) để:
  - Vốn từ vựng (vocabulary) kỹ năng có thể mở rộng dần mà không phải đụng
    vào code thuật toán
  - Các công cụ khác (ví dụ script generate_implies_llm.py) có thể import
    dữ liệu này với chi phí thấp, không cần kéo theo logic scoring

Các bảng dữ liệu:
  ALIASES                 ánh xạ từ biến thể cách viết → tên kỹ năng chuẩn
                          (canonical token), ví dụ "reactjs" → "react"
  CATEGORIES              tên kỹ năng chuẩn → nhóm lĩnh vực lớn (dùng để
                          chấm điểm "partial credit" khi cùng nhóm nhưng
                          không khớp chính xác)
  MANUAL_IMPLIES          các cạnh (edge) quan hệ "biết X thì chắc chắn biết
                          Y" mà đồ thị IMPLIES sinh tự động BẮT BUỘC phải
                          luôn chứa (đảm bảo không bị mất khi regenerate)
  IMPLIES                 đồ thị suy luận (implication graph) được sinh tự
                          động (re-export từ skill_implies.py)
  IMPLIES_ALL             đồ thị suy luận thực sự mà matcher sử dụng
                          = IMPLIES ∪ MANUAL_IMPLIES

File này là điểm import duy nhất cho toàn bộ dữ liệu kỹ năng. Đồ thị sinh
tự động (raw generated graph) thực sự nằm trong skill_implies.py — một file
do máy ghi ra (machine-written), bị scripts/generate_implies_llm.py GHI ĐÈ
TOÀN BỘ mỗi lần chạy lại — đó chính là lý do nó phải tách riêng khỏi file
này (file được duy trì thủ công). Ở đây, IMPLIES chỉ được re-export và gộp
(merge) lại, để mọi nơi khác trong code chỉ cần import từ skill_data, không
cần biết đến skill_implies.py.
"""

from __future__ import annotations

from app.services.skill_implies import IMPLIES  # generated graph — see generate_implies_llm.py


# ---------------------------------------------------------------------------
# ALIASES — variant spelling → canonical skill token
# ánh xạ biến thể cách viết (viết tắt, có version, có ký tự đặc biệt...)
# về một tên kỹ năng chuẩn duy nhất, để SkillMatcher.normalize_skill() so
# khớp được dù CV/JD viết khác nhau (vd "JS", "Javascript", "ES6+" đều → "javascript")
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
# Nhóm các kỹ năng chuẩn hóa vào từng lĩnh vực lớn. Dùng để chấm điểm
# "partial credit" (category_match trong scorer.py): nếu JD cần 1 kỹ năng
# CV không có chính xác, nhưng CV có nhiều kỹ năng khác cùng nhóm lĩnh vực
# thì vẫn được cộng một phần điểm (0.3–0.5) thay vì 0.
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



# ---------------------------------------------------------------------------
# MANUAL_IMPLIES — concept edges the generated IMPLIES graph must always contain
# Các cạnh "neo" (anchor edges) mà file skill_implies.py sinh tự động bằng
# LLM luôn phải chứa, và scorer.py sẽ gộp (merge) đè lên trên đồ thị sinh tự
# động: một thư viện cụ thể thì chắc chắn đảm bảo khả năng mà nó sinh ra để
# phục vụ (Chart.js → data visualization) hoặc giao thức nó bọc quanh
# (axios → REST). Được giữ riêng ở đây để mỗi lần regenerate skill_implies.py
# không bao giờ vô tình làm mất các cạnh quan trọng này.
# ---------------------------------------------------------------------------

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
# Đồ thị suy luận thực sự mà SkillMatcher sử dụng
# = đồ thị sinh tự động (IMPLIES) ∪ các cạnh neo thủ công (MANUAL_IMPLIES).
# Được dựng đúng 1 lần lúc import module; phép bao đóng bắc cầu (transitive
# closure — ví dụ nextjs → react → javascript) được áp dụng mỗi lần tra cứu,
# nằm trong SkillMatcher.implied_skills() ở scorer.py.
# ---------------------------------------------------------------------------

IMPLIES_ALL: dict[str, set[str]] = {k: set(v) for k, v in IMPLIES.items()}
for _src, _targets in MANUAL_IMPLIES.items():
    IMPLIES_ALL.setdefault(_src, set()).update(_targets)
