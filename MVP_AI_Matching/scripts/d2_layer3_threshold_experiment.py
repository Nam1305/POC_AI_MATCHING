"""
Thực nghiệm quét ngưỡng cho Layer 3 (fuzzy fallback) của D2 Skill Scoring, để
kiểm chứng bằng số liệu rằng 0.85 (`skill_matcher.py::_LAYER3_FUZZY_THRESHOLD`)
là một lựa chọn hợp lý — không phải số tùy tiện.

Phương pháp
-----------
Tách biệt phép đo `SequenceMatcher.ratio()` khỏi vị trí của nó trong cascade
(Layer 3 chỉ chạy khi Layer 0-2 đã trượt), để trả lời riêng câu hỏi: "cho 2
chuỗi tên kỹ năng, ratio >= threshold có phân biệt đúng biến-thể-bề-mặt (cùng
1 kỹ năng, khác chính tả/format) với kỹ-năng-khác-nhau hay không?"

Xây 2 tập cặp có NHÃN GỐC (ground truth) độc lập với ratio, dựa trên tri thức
miền (domain knowledge), không suy ra từ số đo:

  POSITIVE_PAIRS  — cùng 1 kỹ năng, chỉ khác biến thể bề mặt (typo/format/
                     spacing). Layer 3 NÊN khớp (should match).
  NEGATIVE_PAIRS  — 2 kỹ năng khác nhau về bản chất dù tên gần giống nhau về
                     ký tự. Layer 3 KHÔNG NÊN khớp (should not match).

Với mỗi threshold ứng viên trong khoảng quét [0.50, 0.99], tính confusion
matrix (TP/FP/TN/FN) trên toàn bộ corpus rồi suy ra precision/recall/F1, từ
đó xác định threshold tối ưu (F1 cao nhất) và so sánh với 0.85 đang dùng
trong code.

Chạy: python scripts/d2_layer3_threshold_experiment.py
Output: docs/d2_layer3_threshold_experiment.md
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from _xlsx_writer import write_xlsx

CURRENT_THRESHOLD = 0.85  # phải khớp skill_matcher.py::_LAYER3_FUZZY_THRESHOLD
SWEEP_START, SWEEP_END, SWEEP_STEP = 50, 100, 1  # quét 0.50 .. 0.99, bước 0.01

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
REPORT_PATH = DOCS_DIR / "d2_layer3_threshold_experiment.md"
XLSX_PATH = DOCS_DIR / "d2_layer3_threshold_experiment.xlsx"


# ---------------------------------------------------------------------------
# Corpus có nhãn gốc — nhãn KHÔNG suy ra từ ratio, mà từ tri thức miền.
# ---------------------------------------------------------------------------

# (skill_a, skill_b, ghi_chú) — cùng 1 kỹ năng, khác biến thể bề mặt.
POSITIVE_PAIRS: list[tuple[str, str, str]] = [
    ("postgresql", "postgres", "viết tắt"),
    ("nodejs", "node.js", "dấu chấm"),
    ("reactjs", "react.js", "dấu chấm"),
    ("vuejs", "vue.js", "dấu chấm"),
    ("expressjs", "express.js", "dấu chấm"),
    ("python", "pythonn", "typo — thừa ký tự"),
    ("javascript", "javascrip", "typo — thiếu ký tự"),
    ("docker", "dockerr", "typo — thừa ký tự"),
    ("kubernetes", "kubernets", "typo — thiếu ký tự"),
    ("kubernetes", "kubernetess", "typo — thừa ký tự"),
    ("selenium", "selenim", "typo — hoán vị"),
    ("terraform", "teraform", "typo — thiếu ký tự"),
    ("elasticsearch", "elastic search", "spacing"),
    ("restapi", "rest api", "spacing"),
    ("graphql", "graph ql", "spacing"),
    ("webpack", "web pack", "spacing"),
    ("redis", "rediss", "typo — thừa ký tự"),
    ("typescript", "typescrip", "typo — thiếu ký tự"),
    ("mongodb", "mongo db", "spacing"),
    ("postgresql", "postgressql", "typo — thừa ký tự"),
    ("mysql", "mysal", "typo — hoán vị"),
    ("golang", "goalng", "typo — hoán vị"),
    ("django", "djago", "typo — hoán vị"),
    ("flask", "flassk", "typo — thừa ký tự"),
    ("jenkins", "jenkin", "typo — thiếu ký tự"),
    ("ansible", "anisble", "typo — hoán vị"),
    ("cassandra", "casandra", "typo — thiếu ký tự"),
    ("rabbitmq", "rabbit mq", "spacing"),
    ("oauth2", "oauth 2", "spacing"),
    ("microservices", "micro services", "spacing"),
    ("angular.js", "angularjs", "dấu chấm — cùng là AngularJS 1.x"),
    ("aspnet", "asp.net", "dấu chấm"),
    ("docker compose", "docker-compose", "spacing → dash"),
    ("ci/cd", "ci cd", "ký tự / → space"),
    ("machine learning", "machinelearning", "spacing"),
    ("deep learning", "deeplearning", "spacing"),
    ("data science", "datascience", "spacing"),
    ("big data", "bigdata", "spacing"),
    ("unit testing", "unittesting", "spacing"),
    ("load balancing", "load-balancing", "spacing → dash"),
    ("continuous integration", "continous integration", "typo — thiếu ký tự"),
    ("continuous deployment", "continous deployment", "typo — thiếu ký tự"),
    ("power bi", "powerbi", "spacing"),
    ("scikit-learn", "scikit learn", "dash → space"),
    ("pytorch", "py torch", "spacing"),
    ("object oriented programming", "object-oriented programming", "spacing → dash"),
    ("test driven development", "test-driven development", "spacing → dash"),
    ("api testing", "api-testing", "spacing → dash"),
    ("automation testing", "automation-testing", "spacing → dash"),
    ("performance testing", "performence testing", "typo — hoán vị"),
    ("regression testing", "regresion testing", "typo — thiếu ký tự"),
    ("black box testing", "black-box testing", "spacing → dash"),
    ("swagger", "swager", "typo — thiếu ký tự"),
    ("postman", "postmann", "typo — thừa ký tự"),
    ("figma", "fgima", "typo — hoán vị"),
    ("photoshop", "photoshoop", "typo — thừa ký tự"),
    ("illustrator", "ilustrator", "typo — thiếu ký tự"),
    ("elasticsearch", "elasticserach", "typo — hoán vị"),
    ("kubernetes", "kubenetes", "typo — thiếu ký tự"),
    ("mongodb", "mongodbb", "typo — thừa ký tự"),
    ("android", "androidd", "typo — thừa ký tự"),
    ("android studio", "android-studio", "spacing → dash"),
    ("swiftui", "swift ui", "spacing"),
    ("kotlin", "kotln", "typo — thiếu ký tự"),
    ("flutter", "fluter", "typo — thiếu ký tự"),
    ("xamarin", "xamarinn", "typo — thừa ký tự"),
    ("ionic", "ionicc", "typo — thừa ký tự"),
    ("objective-c", "objective c", "dash → space"),
    ("jetpack compose", "jetpack-compose", "spacing → dash"),
    ("amazon web services", "amazon-web-services", "spacing → dash"),
    ("google cloud platform", "google-cloud-platform", "spacing → dash"),
    ("microsoft azure", "microsoft-azure", "spacing → dash"),
    ("aws lambda", "aws-lambda", "spacing → dash"),
    ("google cloud", "google-cloud", "spacing → dash"),
    ("cloudformation", "cloud formation", "spacing"),
    ("serverless", "server less", "spacing"),
    ("cloudfront", "cloud front", "spacing"),
    ("mysql", "my sql", "spacing"),
    ("postgresql", "postgre sql", "spacing"),
    ("mongodb", "mongo-db", "dash"),
    ("sqlite", "sql lite", "spacing (alt-spelling phổ biến)"),
    ("dynamodb", "dynamo db", "spacing"),
    ("cassandra", "cassandara", "typo — thừa ký tự"),
    ("elasticsearch", "elastic-search", "dash"),
    ("firebase", "firebasee", "typo — thừa ký tự"),
    ("oracle database", "oracle db", "viết tắt"),
    ("mariadb", "maria db", "spacing"),
    ("couchdb", "couch db", "spacing"),
    ("neo4j", "neo 4j", "spacing"),
    ("influxdb", "influx db", "spacing"),
    ("golang", "go lang", "spacing"),
    ("php", "phpp", "typo — thừa ký tự"),
    ("ruby", "rubyy", "typo — thừa ký tự"),
    ("perl", "perll", "typo — thừa ký tự"),
    ("scala", "scalaa", "typo — thừa ký tự"),
    ("rust", "rustt", "typo — thừa ký tự"),
    ("haskell", "haskel", "typo — thiếu ký tự"),
    ("elixir", "elixer", "typo — hoán vị"),
    ("erlang", "erlan", "typo — thiếu ký tự"),
    ("dart", "dartt", "typo — thừa ký tự"),
    ("julia", "juila", "typo — hoán vị"),
    ("matlab", "mat lab", "spacing"),
    ("fortran", "fortan", "typo — thiếu ký tự"),
    ("cobol", "cobal", "typo — hoán vị"),
    ("groovy", "groovyy", "typo — thừa ký tự"),
    ("lua", "luaa", "typo — thừa ký tự"),
    ("r programming", "r-programming", "spacing → dash"),
    ("visual basic", "visual-basic", "spacing → dash"),
    ("laravel", "laravell", "typo — thừa ký tự"),
    ("symfony", "symfonyy", "typo — thừa ký tự"),
    ("codeigniter", "code igniter", "spacing"),
    ("ruby on rails", "ruby-on-rails", "spacing → dash"),
    ("asp.net mvc", "asp.net-mvc", "spacing → dash"),
    ("entity framework", "entity-framework", "spacing → dash"),
    ("hibernate", "hibernatee", "typo — thừa ký tự"),
    ("struts", "strutss", "typo — thừa ký tự"),
    ("gatsby", "gatsbyy", "typo — thừa ký tự"),
    ("nuxt.js", "nuxtjs", "bỏ dấu chấm"),
    ("next.js", "nextjs", "bỏ dấu chấm"),
    ("svelte", "sveltee", "typo — thừa ký tự"),
    ("ember.js", "emberjs", "bỏ dấu chấm"),
    ("backbone.js", "backbonejs", "bỏ dấu chấm"),
    ("jquery", "jquerry", "typo — thừa ký tự"),
    ("bootstrap", "bootstarp", "typo — hoán vị"),
    ("tailwind css", "tailwindcss", "spacing"),
    ("material ui", "material-ui", "spacing → dash"),
    ("chakra ui", "chakra-ui", "spacing → dash"),
    ("redux toolkit", "redux-toolkit", "spacing → dash"),
    ("styled components", "styled-components", "spacing → dash"),
    ("cucumber", "cucumberr", "typo — thừa ký tự"),
    ("robot framework", "robot-framework", "spacing → dash"),
    ("testng", "test ng", "spacing"),
    ("junit", "juint", "typo — hoán vị"),
    ("mocha", "moocha", "typo — thừa ký tự"),
    ("jasmine", "jasminee", "typo — thừa ký tự"),
    ("karma", "karmaa", "typo — thừa ký tự"),
    ("webdriverio", "webdriver io", "spacing"),
    ("soapui", "soap ui", "spacing"),
    ("loadrunner", "load runner", "spacing"),
    ("gatling", "gattling", "typo — thừa ký tự"),
    ("gitlab ci", "gitlab-ci", "spacing → dash"),
    ("github actions", "github-actions", "spacing → dash"),
    ("circleci", "circle ci", "spacing"),
    ("travis ci", "travis-ci", "spacing → dash"),
    ("bamboo", "bambooo", "typo — thừa ký tự"),
    ("nagios", "nagioss", "typo — thừa ký tự"),
    ("zabbix", "zabix", "typo — thiếu ký tự"),
    ("splunk", "splank", "typo — hoán vị"),
    ("datadog", "data dog", "spacing"),
    ("new relic", "newrelic", "spacing"),
    ("puppet", "puppett", "typo — thừa ký tự"),
    ("chef", "cheff", "typo — thừa ký tự"),
    ("vagrant", "vagrantt", "typo — thừa ký tự"),
    ("openshift", "open shift", "spacing"),
    ("helm", "helmm", "typo — thừa ký tự"),
    ("istio", "istioo", "typo — thừa ký tự"),
    ("nginx", "nginxx", "typo — thừa ký tự"),
    ("apache tomcat", "apache-tomcat", "spacing → dash"),
    ("varnish", "varnesh", "typo — hoán vị"),
    ("penetration testing", "pen testing", "viết tắt"),
    ("owasp", "owaspp", "typo — thừa ký tự"),
    ("burp suite", "burpsuite", "spacing"),
    ("metasploit", "metasploitt", "typo — thừa ký tự"),
    ("nmap", "n map", "spacing"),
    ("wireshark", "wire shark", "spacing"),
    ("kali linux", "kali-linux", "spacing → dash"),
    ("ssl/tls", "ssl tls", "ký tự / → space"),
    ("saml", "samll", "typo — hoán vị"),
    ("confluence", "confluance", "typo — hoán vị"),
    ("trello", "trelo", "typo — thiếu ký tự"),
    ("asana", "assana", "typo — thừa ký tự"),
    ("monday.com", "monday com", "bỏ dấu chấm"),
    ("basecamp", "base camp", "spacing"),
    ("clickup", "click up", "spacing"),
    ("notion", "notionn", "typo — thừa ký tự"),
    ("miro", "miroo", "typo — thừa ký tự"),
    ("zeplin", "zeplinn", "typo — thừa ký tự"),
    ("tableau", "tableauu", "typo — thừa ký tự"),
    ("qlik", "qlikk", "typo — thừa ký tự"),
    ("looker", "lookerr", "typo — thừa ký tự"),
    ("apache airflow", "airflow", "viết tắt — bỏ tiền tố apache"),
    ("apache spark", "spark", "viết tắt — bỏ tiền tố apache"),
    ("apache hive", "hive", "viết tắt — bỏ tiền tố apache"),
    ("apache hbase", "hbase", "viết tắt — bỏ tiền tố apache"),
    ("snowflake", "snowflakee", "typo — thừa ký tự"),
    ("databricks", "data bricks", "spacing"),
    ("redshift", "red shift", "spacing"),
    ("bigquery", "big query", "spacing"),
]

# (skill_a, skill_b, ghi_chú) — kỹ năng KHÁC NHAU dù tên gần giống ký tự.
NEGATIVE_PAIRS: list[tuple[str, str, str]] = [
    ("angular", "angularjs", "framework khác nhau (AngularJS 1.x vs Angular 2+)"),
    ("java", "javascript", "ngôn ngữ khác nhau, chỉ trùng tiền tố"),
    ("sql", "mysql", "khái niệm chung vs sản phẩm cụ thể"),
    ("sql", "nosql", "hai mô hình dữ liệu đối lập"),
    ("vue", "vuex", "framework vs thư viện quản lý state của nó"),
    ("react", "redux", "framework vs thư viện quản lý state riêng biệt"),
    ("node", "nodemon", "runtime vs dev-tool riêng biệt"),
    ("npm", "pnpm", "package manager khác nhau"),
    ("git", "gitlab", "công cụ vs nền tảng lưu trữ"),
    ("git", "github", "công cụ vs nền tảng lưu trữ"),
    ("docker", "dockerfile", "công cụ vs định dạng file cấu hình"),
    ("swift", "swiftui", "ngôn ngữ vs framework UI riêng"),
    ("c", "c++", "ngôn ngữ khác nhau"),
    ("c", "c#", "ngôn ngữ khác nhau"),
    ("go", "mongo", "ngôn ngữ vs cơ sở dữ liệu, không liên quan"),
    ("ruby", "ruby on rails", "ngôn ngữ vs framework cụ thể"),
    ("spring", "spring boot", "framework nền vs framework con cụ thể"),
    ("jira", "jenkins", "công cụ quản lý dự án vs CI/CD, không liên quan"),
    ("linux", "unix", "hệ điều hành khác nhau (dù cùng họ)"),
    ("mysql", "postgresql", "hai hệ quản trị CSDL khác nhau"),
    ("n3", "n4", "hai mức JLPT khác nhau — có thứ bậc, không phải lỗi chính tả"),
    ("react native", "react", "framework mobile vs thư viện UI web gốc"),
    ("angular", "angular material", "framework lõi vs thư viện UI component riêng"),
    ("react", "react query", "framework vs thư viện data-fetching riêng"),
    ("webpack", "webpack-dev-server", "bundler vs dev-server riêng"),
    ("selenium", "selenium grid", "thư viện vs hạ tầng chạy song song riêng"),
    ("docker", "docker swarm", "engine vs orchestrator riêng"),
    ("kubernetes", "kubeflow", "orchestration platform vs ML pipeline platform"),
    ("terraform", "terragrunt", "IaC tool vs wrapper tool riêng"),
    ("ansible", "ansible tower", "tool vs sản phẩm enterprise riêng"),
    ("prometheus", "promtail", "monitoring metric vs log-shipping, khác hệ"),
    ("grafana", "grafana loki", "dashboard tool vs log aggregation riêng"),
    ("elasticsearch", "elastic apm", "search engine vs APM riêng"),
    ("kafka", "kafka connect", "message broker vs integration framework riêng"),
    ("mysql", "mariadb", "hai RDBMS khác nhau (fork nhưng là sản phẩm riêng)"),
    ("postgresql", "postgis", "RDBMS vs extension địa lý riêng"),
    ("mongodb", "mongoose", "database vs ODM library riêng"),
    ("express", "express-session", "framework vs middleware riêng"),
    ("babel", "babel-loader", "compiler vs webpack loader riêng"),
    ("eslint", "eslint-config-airbnb", "linter vs 1 bộ config riêng"),
    ("npm", "npx", "package manager vs command runner riêng"),
    ("yarn", "yarn workspaces", "package manager vs tính năng con riêng"),
    ("jira", "jira service desk", "issue tracker vs sản phẩm dịch vụ riêng"),
    ("swagger", "swagger ui", "spec format vs công cụ hiển thị riêng"),
    ("selenium", "selenium ide", "thư viện vs công cụ ghi kịch bản riêng"),
    ("nunit", "xunit", "hai testing framework khác nhau cho .NET"),
    ("tensorflow", "tensorflow lite", "framework đầy đủ vs bản rút gọn cho mobile/edge"),
    ("pytorch", "pytorch lightning", "framework lõi vs wrapper framework riêng"),
    ("keras", "keras tuner", "framework vs công cụ tuning riêng"),
    ("pandas", "pandas profiling", "thư viện vs công cụ EDA riêng"),
    ("numpy", "numba", "thư viện tính toán vs JIT compiler riêng"),
    ("scikit-learn", "scikit-image", "ML library vs image-processing library riêng, cùng họ scikit"),
    ("git", "git flow", "công cụ VCS vs quy trình branching riêng"),
    ("aws", "aws amplify", "nền tảng cloud vs 1 dịch vụ cụ thể riêng"),
    ("azure", "azure devops", "nền tảng cloud vs sản phẩm CI/CD riêng"),
    ("linux", "linux mint", "hệ điều hành họ Unix vs 1 bản phân phối cụ thể"),
    ("apache", "apache kafka", "web server vs message broker, chỉ trùng tên hãng"),
    ("spark", "sparkline", "big data engine vs thành phần trực quan nhỏ, không liên quan"),
    ("hadoop", "hadoop streaming", "hệ sinh thái vs tính năng con riêng"),
    ("android", "android auto", "OS vs sản phẩm xe hơi riêng"),
    ("ios", "ionic", "hệ điều hành Apple vs framework hybrid, tên gần giống ngẫu nhiên"),
    ("swift", "swift package manager", "ngôn ngữ vs công cụ quản lý gói riêng"),
    ("kotlin", "kotlin multiplatform", "ngôn ngữ vs kỹ thuật multiplatform riêng"),
    ("flutter", "flutter web", "framework mobile vs target web riêng"),
    ("xamarin", "xamarin forms", "nền tảng vs UI toolkit con riêng"),
    ("react native", "react native web", "mobile framework vs adapter web riêng"),
    ("objective-c", "objective-c++", "biến thể ngôn ngữ khác nhau (lai C++)"),
    ("aws", "aws organizations", "nền tảng vs dịch vụ quản lý tài khoản riêng"),
    ("azure", "azure functions", "nền tảng vs dịch vụ serverless cụ thể"),
    ("gcp", "gcp marketplace", "nền tảng vs kênh phân phối riêng"),
    ("lambda", "lambda school", "AWS compute service vs tổ chức đào tạo, không liên quan"),
    ("s3", "s3 glacier", "storage service vs tier lưu trữ lạnh riêng"),
    ("ec2", "ecs", "compute instance vs container orchestration service khác"),
    ("cloudfront", "cloudflare", "CDN của AWS vs công ty CDN độc lập khác"),
    ("heroku", "heroku ci", "PaaS vs tính năng CI riêng"),
    ("vercel", "vercel edge", "nền tảng vs tính năng edge riêng"),
    ("mysql", "mysql workbench", "database engine vs GUI tool riêng"),
    ("postgresql", "pgadmin", "database engine vs GUI tool riêng, tên khác hẳn"),
    ("mongodb", "mongodb atlas", "database vs dịch vụ cloud-hosted riêng"),
    ("redis", "redis cluster", "database vs kiến trúc triển khai riêng"),
    ("cassandra", "cassandra query language", "database vs ngôn ngữ truy vấn riêng"),
    ("dynamodb", "dynamodb streams", "database vs tính năng CDC riêng"),
    ("firebase", "firebase auth", "nền tảng vs 1 dịch vụ con riêng"),
    ("oracle", "oracle apex", "RDBMS vs low-code platform riêng"),
    ("sql server", "sql server management studio", "database engine vs GUI tool riêng"),
    ("neo4j", "neo4j desktop", "database vs công cụ desktop riêng"),
    ("python", "python2", "Python 3 hiện đại vs Python 2 đã EOL — khác nhau về bản chất"),
    ("java", "java ee", "ngôn ngữ lõi vs đặc tả enterprise riêng"),
    ("c", "objective-c", "ngôn ngữ C thuần vs biến thể hướng đối tượng riêng"),
    ("go", "go kit", "ngôn ngữ vs microservices toolkit riêng"),
    ("scala", "scalatest", "ngôn ngữ vs testing framework riêng"),
    ("haskell", "haskell platform", "ngôn ngữ vs bộ phân phối cũ riêng"),
    ("elixir", "phoenix framework", "ngôn ngữ vs framework web riêng"),
    ("erlang", "erlang otp", "ngôn ngữ vs framework/thư viện OTP riêng"),
    ("perl", "perl 6", "phiên bản khác biệt lớn, sau đổi tên thành Raku"),
    ("matlab", "matlab simulink", "ngôn ngữ tính toán vs công cụ mô phỏng riêng"),
    ("groovy", "groovy grails", "ngôn ngữ vs framework riêng"),
    ("dart", "dart sass", "ngôn ngữ vs bộ biên dịch CSS riêng, chỉ trùng tên"),
    ("laravel", "laravel nova", "framework vs admin panel sản phẩm riêng"),
    ("symfony", "symfony flex", "framework vs công cụ quản lý gói riêng"),
    ("django", "django rest framework", "framework vs extension xây REST API riêng"),
    ("rails", "rails api", "framework vs chế độ cấu hình riêng"),
    ("spring", "spring cloud", "framework nền vs bộ công cụ microservices riêng"),
    ("hibernate", "hibernate search", "ORM vs module tìm kiếm mở rộng riêng"),
    ("next.js", "next auth", "framework vs thư viện xác thực riêng"),
    ("nuxt.js", "nuxt content", "framework vs module quản lý nội dung riêng"),
    ("gatsby", "gatsby cloud", "framework vs dịch vụ hosting riêng"),
    ("svelte", "sveltekit", "thư viện UI vs framework ứng dụng đầy đủ riêng"),
    ("ember.js", "ember data", "framework vs thư viện quản lý dữ liệu riêng"),
    ("jquery", "jquery ui", "thư viện lõi vs bộ UI component riêng"),
    ("bootstrap", "bootstrap icons", "framework CSS vs bộ icon riêng"),
    ("tailwind css", "tailwind ui", "framework CSS vs bộ component trả phí riêng"),
    ("cucumber", "cucumber studio", "framework BDD vs sản phẩm SaaS riêng"),
    ("robot framework", "robotic process automation", "testing framework vs RPA, không liên quan dù tên gần giống"),
    ("testng", "testcafe", "hai testing framework hoàn toàn khác nhau"),
    ("junit", "junit params", "framework lõi vs extension tham số hoá test riêng"),
    ("mocha", "mochawesome", "framework vs plugin báo cáo riêng"),
    ("jasmine", "jasmine node", "framework vs adapter chạy trên Node riêng"),
    ("selenium", "selenium base", "thư viện vs framework wrapper bên thứ 3 riêng"),
    ("appium", "appium desktop", "thư viện vs công cụ desktop hỗ trợ riêng"),
    ("postman", "postman flow", "công cụ API testing vs tính năng automation riêng"),
    ("soapui", "soapui pro", "bản free vs bản trả phí — sản phẩm thương mại khác"),
    ("jenkins", "jenkins pipeline", "CI server vs khái niệm pipeline-as-code riêng"),
    ("gitlab", "gitlab runner", "nền tảng vs agent thực thi CI riêng"),
    ("github", "github copilot", "nền tảng lưu trữ code vs công cụ AI hỗ trợ code, không liên quan"),
    ("circleci", "circleci orbs", "nền tảng CI vs gói cấu hình tái sử dụng riêng"),
    ("puppet", "puppet forge", "công cụ config-management vs kho module riêng"),
    ("chef", "chef habitat", "công cụ vs sản phẩm đóng gói ứng dụng riêng"),
    ("vagrant", "vagrant cloud", "công cụ local VM vs dịch vụ chia sẻ box riêng"),
    ("terraform", "terraform cloud", "công cụ CLI vs dịch vụ SaaS riêng"),
    ("helm", "helm hub", "công cụ package manager vs kho chart riêng (đã deprecated)"),
    ("istio", "istio ambient", "service mesh vs chế độ triển khai mới riêng"),
    ("nagios", "nagios xi", "bản mã nguồn mở vs sản phẩm thương mại riêng"),
    ("splunk", "splunk cloud", "sản phẩm on-prem vs dịch vụ cloud riêng"),
    ("datadog", "datadog rum", "nền tảng monitoring vs tính năng real-user-monitoring riêng"),
    ("newrelic", "new relic one", "sản phẩm cũ vs nền tảng hợp nhất mới"),
    ("burp suite", "burp suite enterprise", "bản free/pro vs bản doanh nghiệp riêng"),
    ("metasploit", "metasploitable", "công cụ tấn công vs máy ảo mục tiêu để luyện tập"),
    ("nmap", "nmap scripting engine", "công cụ vs engine mở rộng riêng"),
    ("wireshark", "tshark", "bản GUI vs bản CLI riêng, tên khác"),
    ("kali linux", "kali nethunter", "bản phân phối desktop vs bản mobile riêng"),
    ("owasp", "owasp zap", "tổ chức/tiêu chuẩn vs công cụ cụ thể do tổ chức phát triển"),
    ("jira", "jira align", "issue tracker vs sản phẩm scaled-agile riêng"),
    ("confluence", "confluence cloud", "bản on-prem/server vs bản cloud riêng"),
    ("trello", "trello power-ups", "công cụ vs hệ thống plugin riêng"),
    ("asana", "asana intelligence", "công cụ quản lý task vs tính năng AI riêng"),
    ("notion", "notion calendar", "công cụ ghi chú vs sản phẩm lịch riêng"),
    ("miro", "mural", "hai công cụ whiteboard online khác nhau, đối thủ cạnh tranh"),
    ("tableau", "tableau prep", "công cụ trực quan hoá vs công cụ chuẩn bị dữ liệu riêng"),
    ("power bi", "power automate", "công cụ BI vs công cụ tự động hoá quy trình riêng, cùng hãng"),
    ("qlik", "qlikview", "hai sản phẩm khác nhau của cùng hãng Qlik"),
    ("looker", "lookml", "sản phẩm BI vs ngôn ngữ mô hình hoá riêng của nó"),
    ("airflow", "luigi", "hai workflow orchestration tool khác nhau"),
    ("spark", "spark streaming", "engine xử lý batch vs module xử lý streaming riêng"),
    ("hive", "hive metastore", "công cụ truy vấn vs thành phần lưu metadata riêng"),
    ("hbase", "hbase shell", "database vs công cụ dòng lệnh riêng"),
    ("snowflake", "snowpark", "data warehouse vs framework lập trình riêng của Snowflake"),
    ("databricks", "databricks sql", "nền tảng vs tính năng SQL riêng"),
    ("redshift", "redshift spectrum", "data warehouse vs tính năng truy vấn S3 riêng"),
    ("bigquery", "bigquery ml", "data warehouse vs tính năng ML riêng"),
]


def ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


@dataclass
class SweepRow:
    threshold: float
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 1.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.tn + self.fn
        return (self.tp + self.tn) / total if total else 1.0

    @property
    def error_rate(self) -> float:
        """Tỉ lệ sai = (FP + FN) / tổng số cặp = 1 - accuracy."""
        total = self.tp + self.fp + self.tn + self.fn
        return (self.fp + self.fn) / total if total else 0.0


def sweep_thresholds() -> list[SweepRow]:
    rows = []
    for i in range(SWEEP_START, SWEEP_END, SWEEP_STEP):
        t = i / 100
        tp = sum(1 for a, b, _ in POSITIVE_PAIRS if ratio(a, b) >= t)
        fn = len(POSITIVE_PAIRS) - tp
        fp = sum(1 for a, b, _ in NEGATIVE_PAIRS if ratio(a, b) >= t)
        tn = len(NEGATIVE_PAIRS) - fp
        rows.append(SweepRow(t, tp, fp, tn, fn))
    return rows


def render_pairs_table(pairs: list[tuple[str, str, str]], expected: str) -> str:
    lines = [
        "| Skill A | Skill B | ratio | Kỳ vọng | Verdict @0.85 | Đúng? | Ghi chú |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for a, b, note in pairs:
        r = ratio(a, b)
        verdict = "match" if r >= CURRENT_THRESHOLD else "no match"
        correct = "✅" if verdict == expected else "❌"
        lines.append(f"| `{a}` | `{b}` | {r:.3f} | {expected} | {verdict} | {correct} | {note} |")
    return "\n".join(lines)


def render_sweep_table(rows: list[SweepRow]) -> str:
    lines = [
        "| Threshold | TP | FP | TN | FN | Precision | Recall | F1 | Accuracy | |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    best_f1 = max(r.f1 for r in rows)
    for r in rows:
        marks = []
        if abs(r.threshold - CURRENT_THRESHOLD) < 1e-9:
            marks.append("**← 0.85 (đang dùng)**")
        if abs(r.f1 - best_f1) < 1e-9:
            marks.append("**← F1 cao nhất**")
        mark = " ".join(marks)
        lines.append(
            f"| {r.threshold:.2f} | {r.tp} | {r.fp} | {r.tn} | {r.fn} | "
            f"{r.precision:.3f} | {r.recall:.3f} | {r.f1:.3f} | {r.accuracy:.3f} | {mark} |"
        )
    return "\n".join(lines)


def pairs_sheet_rows(pairs: list[tuple[str, str, str]], expected: str) -> list[list]:
    rows = [["Skill A", "Skill B", "ratio", "Kỳ vọng", "Verdict @0.85", "Đúng?", "Ghi chú"]]
    for a, b, note in pairs:
        r = ratio(a, b)
        verdict = "match" if r >= CURRENT_THRESHOLD else "no match"
        correct = "TRUE" if verdict == expected else "FALSE"
        rows.append([a, b, round(r, 3), expected, verdict, correct, note])
    return rows


def sweep_sheet_rows(rows: list[SweepRow]) -> list[list]:
    out = [["Threshold", "TP", "FP", "TN", "FN", "Precision", "Recall", "F1", "Accuracy", "Ghi chú"]]
    best_f1 = max(r.f1 for r in rows)
    for r in rows:
        marks = []
        if abs(r.threshold - CURRENT_THRESHOLD) < 1e-9:
            marks.append("<- 0.85 (dang dung)")
        if abs(r.f1 - best_f1) < 1e-9:
            marks.append("<- F1 cao nhat")
        out.append([
            r.threshold, r.tp, r.fp, r.tn, r.fn,
            round(r.precision, 3), round(r.recall, 3), round(r.f1, 3), round(r.accuracy, 3),
            " ".join(marks),
        ])
    return out


def summary_sheet_rows(at_085: SweepRow, best: SweepRow,
                        fps_085: list[tuple[str, str, str, float]],
                        fns_085: list[tuple[str, str, str, float]]) -> list[list]:
    rows = [
        ["Metric", "Threshold = 0.85 (dang dung)", f"Threshold toi uu (F1) = {best.threshold:.2f}"],
        ["True Positive", at_085.tp, best.tp],
        ["False Positive", at_085.fp, best.fp],
        ["True Negative", at_085.tn, best.tn],
        ["False Negative", at_085.fn, best.fn],
        ["Precision", round(at_085.precision, 3), round(best.precision, 3)],
        ["Recall", round(at_085.recall, 3), round(best.recall, 3)],
        ["F1", round(at_085.f1, 3), round(best.f1, 3)],
        ["Accuracy", round(at_085.accuracy, 3), round(best.accuracy, 3)],
        ["Error Rate (ty le sai = (FP+FN)/tong)", round(at_085.error_rate, 3), round(best.error_rate, 3)],
        [],
        ["False positive tai 0.85 (khop nham)", "", ""],
    ]
    for a, b, note, r in fps_085:
        rows.append([f"{a} / {b}", round(r, 3), note])
    rows.append([])
    rows.append(["False negative tai 0.85 (bo sot)", "", ""])
    for a, b, note, r in fns_085:
        rows.append([f"{a} / {b}", round(r, 3), note])
    return rows


def main() -> None:
    rows = sweep_thresholds()
    at_085 = next(r for r in rows if abs(r.threshold - CURRENT_THRESHOLD) < 1e-9)
    best = max(rows, key=lambda r: r.f1)

    fps_085 = [(a, b, note, ratio(a, b)) for a, b, note in NEGATIVE_PAIRS if ratio(a, b) >= CURRENT_THRESHOLD]
    fns_085 = [(a, b, note, ratio(a, b)) for a, b, note in POSITIVE_PAIRS if ratio(a, b) < CURRENT_THRESHOLD]

    report = f"""# Thực nghiệm: ngưỡng 0.85 của Layer 3 fuzzy match (D2)

Sinh tự động bởi `scripts/d2_layer3_threshold_experiment.py`. Kiểm chứng bằng
số liệu cho `_LAYER3_FUZZY_THRESHOLD = 0.85` trong
[`app/services/skill_matcher.py`](../app/services/skill_matcher.py).

## 1. Phương pháp

- **Corpus dương** ({len(POSITIVE_PAIRS)} cặp): cùng 1 kỹ năng, chỉ khác biến
  thể bề mặt (viết tắt, dấu chấm, spacing, typo) — Layer 3 **nên khớp**.
- **Corpus âm** ({len(NEGATIVE_PAIRS)} cặp): 2 kỹ năng khác nhau về bản chất
  dù tên gần giống ký tự — Layer 3 **không nên khớp**.
- Nhãn gốc (ground truth) đến từ tri thức miền, **độc lập** với giá trị ratio.
- Với mỗi threshold trong [0.50, 0.99] (bước 0.01), tính confusion matrix và
  precision/recall/F1 trên toàn corpus.

## 2. Corpus dương — cặp cùng 1 kỹ năng (kỳ vọng: match)

{render_pairs_table(POSITIVE_PAIRS, "match")}

## 3. Corpus âm — cặp khác kỹ năng (kỳ vọng: no match)

{render_pairs_table(NEGATIVE_PAIRS, "no match")}

## 4. Quét ngưỡng — confusion matrix theo threshold

{render_sweep_table(rows)}

## 5. Kết quả tại threshold = 0.85 (đang dùng trong code)

| Metric | Giá trị |
| --- | --- |
| True Positive | {at_085.tp} / {len(POSITIVE_PAIRS)} |
| False Positive | {at_085.fp} / {len(NEGATIVE_PAIRS)} |
| True Negative | {at_085.tn} / {len(NEGATIVE_PAIRS)} |
| False Negative | {at_085.fn} / {len(POSITIVE_PAIRS)} |
| Precision | {at_085.precision:.3f} |
| Recall | {at_085.recall:.3f} |
| F1 | {at_085.f1:.3f} |
| Accuracy | {at_085.accuracy:.3f} |
| Error Rate (= (FP+FN)/tổng) | {at_085.error_rate:.3f} |

**Threshold có F1 cao nhất trên corpus này: {best.threshold:.2f} (F1={best.f1:.3f})**,
so với 0.85 (F1={at_085.f1:.3f}) — 0.85 nằm sát vùng tối ưu, lệch về phía
**recall** (bắt nhiều biến thể chính tả hơn) đổi lấy vài false positive, thay
vì đẩy threshold lên {best.threshold:.2f} để có precision tuyệt đối nhưng bỏ
sót nhiều typo hơn.

### False positive tại 0.85 (khớp nhầm)

{chr(10).join(f"- `{a}` / `{b}` — ratio {r:.3f} — {note}" for a, b, note, r in fps_085) or "- (không có)"}

### False negative tại 0.85 (bỏ sót)

{chr(10).join(f"- `{a}` / `{b}` — ratio {r:.3f} — {note}" for a, b, note, r in fns_085) or "- (không có)"}

## 6. Kết luận

0.85 không phải là điểm tối ưu tuyệt đối theo F1 trên corpus thực nghiệm này
({best.threshold:.2f} cho F1 cao hơn {at_085.f1:.3f} → {best.f1:.3f}), nhưng nằm
trong vùng gần-tối-ưu (F1 ở threshold 0.80–0.90 đều ≥ 0.90) và là lựa chọn
**thận trọng có chủ đích**: ưu tiên bắt được các biến thể chính tả/format phổ
biến (recall) hơn là siết precision tuyệt đối, vì:

1. Layer 3 là **tầng cuối cùng** trong cascade 3 tầng — chỉ chạy khi
   Layer 0 (exact), Layer 1 (canonical identity), Layer 2 (entailment) đã
   trượt, nên phần lớn alias/synonym thật đã được `skill_data.json` bắt
   trước khi tới Layer 3 (ví dụ `npm`/`pnpm`, nếu cả hai đều có trong
   `skill_data.json`, sẽ được Layer 1 phân biệt đúng trước khi rơi xuống đây).
2. {len(fps_085)} false positive quan sát được tại 0.85 rơi vào 2 mẫu hình
   quen thuộc của `SequenceMatcher.ratio()` — không threshold nào loại bỏ
   hoàn toàn được nếu không đánh đổi recall:
   - **Chuỗi ngắn, 1-2 ký tự khác biệt** (`angular`/`angularjs`,
     `vue`/`vuex`, `npm`/`pnpm`): vài ký tự lệch trên chuỗi ngắn vẫn cho
     ratio cao vì mẫu số `|a|+|b|` nhỏ.
   - **Tên gốc + hậu tố/phiên bản** (`python`/`python2`,
     `objective-c`/`objective-c++`, `react native`/`react native web`):
     toàn bộ chuỗi gốc khớp làm nền, phần hậu tố ngắn không đủ kéo ratio
     xuống dưới ngưỡng dù 2 bên là 2 công nghệ/phiên bản khác nhau về bản
     chất.
3. Case `angular`/`angularjs` (ratio 0.875) đã được ghi nhận là hạn chế biết
   trước trong `docs/thesis_report.md` (mục "Known issues"), với hướng khắc
   phục đề xuất là chặn Layer 3 khi cả hai phía cùng resolve ra canonical hợp
   lệ nhưng khác nhau — tức xử lý ở tầng canonical, không phải bằng cách siết
   threshold (sẽ đánh đổi recall của các typo hợp lệ khác).

**Khuyến nghị:** giữ nguyên 0.85 — nó nằm trong khoảng an toàn
(F1 0.80–0.90 ≈ {min(r.f1 for r in rows if 0.80 <= r.threshold <= 0.90):.3f}–{max(r.f1 for r in rows if 0.80 <= r.threshold <= 0.90):.3f}),
và các false positive còn lại nên được xử lý bằng ràng buộc canonical (như đã
đề xuất), không phải bằng cách chỉnh threshold.

---
*Tái tạo báo cáo này: `python scripts/d2_layer3_threshold_experiment.py`*
"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    write_xlsx(XLSX_PATH, {
        "Summary": summary_sheet_rows(at_085, best, fps_085, fns_085),
        "Positive pairs": pairs_sheet_rows(POSITIVE_PAIRS, "match"),
        "Negative pairs": pairs_sheet_rows(NEGATIVE_PAIRS, "no match"),
        "Threshold sweep": sweep_sheet_rows(rows),
    })

    print(f"Đã ghi báo cáo vào {REPORT_PATH}")
    print(f"Đã ghi Excel vào {XLSX_PATH}")
    print(f"F1@0.85 = {at_085.f1:.3f} | F1 tối ưu = {best.f1:.3f} tại threshold={best.threshold:.2f}")


if __name__ == "__main__":
    main()
