"""
Thực nghiệm đo ĐỘ PHỦ (coverage) của 2 file dữ liệu tĩnh làm nền cho D2 Skill
Scoring: `app/data/skill_data.json` (Layer 1 — canonical hóa) và
`app/data/skill_implies.json` (Layer 2 — entailment). Hai file này quyết định
Layer 1/2 có bắt được skill hay không TRƯỚC KHI rơi xuống Layer 3 (fuzzy, đắt
và lỏng hơn) — độ phủ thấp ở đây nghĩa là hệ thống phải dựa nhiều hơn vào fuzzy
match hoặc bỏ sót hẳn, ảnh hưởng trực tiếp tới D2.

Gồm 2 phần độc lập, 1000 test case MỖI phần (2000 tổng), trả lời 2 câu hỏi
khác nhau:

  PHẦN A — Độ phủ của skill_data.json (Layer 1).
    Câu hỏi: "Với các tên kỹ năng THỰC TẾ như LLM parser sẽ trích ra từ
    CV/JD (Title Case, có dấu chấm/khoảng trắng, viết tắt phổ biến — KHÔNG
    phải định dạng Stack Overflow tag mà skill_data.json dùng làm key), bao
    nhiêu % được `resolve_canonical()` nhận diện thành công?"
    Phương pháp: ~330 tên kỹ năng ĐỘC LẬP với file, viết tay từ tri thức miền,
    phủ rộng ~35 nhóm công nghệ phổ biến trong CV/JD thật (ngôn ngữ, frontend,
    backend, mobile, database, cloud/devops, dịch vụ AWS/Azure/GCP cụ thể,
    BI/ERP, embedded/IoT, blockchain, data/ML, testing, tool, khái niệm quy
    trình...), sau đó BÙ thêm bằng biến thể định dạng (space<->dash, bỏ dấu
    chấm, đổi kiểu viết hoa...) của chính các mục đã có — mỗi biến thể vẫn là
    1 cách viết THẬT mà các CV/JD khác nhau có thể tạo ra cho cùng 1 kỹ năng —
    để đạt đúng 1000 (xem `_pad_to_target()`). Với mỗi tên, chạy qua đúng cơ
    chế tra cứu của `to_stackoverflow_format()` + tra `SKILL_DATA` (KHÔNG gọi
    lại `resolve_canonical()` như hộp đen — tách được 3 kết quả: khớp qua
    synonym, khớp qua key tự-canonical (value=null), và KHÔNG tìm thấy).

  PHẦN B — Độ phủ của skill_implies.json (Layer 2).
    Câu hỏi: "Với các quan hệ kéo-theo (entailment) đã biết rộng rãi trong
    giới lập trình (ví dụ 'biết Django thì biết Python'), bao nhiêu % thực
    sự có trong skill_implies.json để Layer 2 tự động suy ra?"
    Phương pháp: ~185 cặp (skill con, skill cha kỳ vọng) từ tri thức miền —
    framework kéo theo ngôn ngữ nền, dịch vụ cloud cụ thể kéo theo platform
    (AWS/Azure/GCP), tool kéo theo platform nền — KHÔNG phải suy ngược từ nội
    dung file (nếu suy ngược thì đương nhiên 100%, vô nghĩa), sau đó BÙ thêm
    bằng biến thể định dạng của phía CON (giữ nguyên cha + quan hệ) để đạt
    đúng 1000 (xem `_pad_pairs_to_target()`). Với mỗi cặp: canonical hóa cả 2
    phía qua skill_data.json rồi tra SKILL_IMPLIES[child] có chứa parent
    không (dữ liệu đã flatten bắc cầu sẵn nên không cần duyệt graph).

Cả 2 phần đều là recall (độ phủ) của tri thức miền so với dữ liệu tĩnh, KHÔNG
phải test correctness của thuật toán skill_matcher.py (đã có
d2_layer3_threshold_experiment.py cho Layer 3). Một test case "MISS" ở đây
không phải lỗi code — nó cho biết CHÍNH XÁC lỗ hổng nào trong dữ liệu tri thức
cần bổ sung (qua `app/data/add_*_skills.py`).

Chạy: python scripts/d2_kb_coverage_experiment.py
Output: docs/d2_kb_coverage_experiment.md, docs/d2_kb_coverage_experiment.xlsx
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from _xlsx_writer import write_xlsx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.skill_matcher import (  # noqa: E402
    SKILL_DATA,
    SKILL_IMPLIES,
    resolve_canonical,
    to_stackoverflow_format,
)

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
REPORT_PATH = DOCS_DIR / "d2_kb_coverage_experiment.md"
XLSX_PATH = DOCS_DIR / "d2_kb_coverage_experiment.xlsx"


# ===========================================================================
# PHẦN A — Corpus độ phủ skill_data.json (Layer 1)
# Tên kỹ năng viết theo phong cách output LLM thật (Title Case, dấu chấm,
# viết tắt phổ biến) — KHÔNG viết theo định dạng key của skill_data.json, để
# phép thử phản ánh đúng khoảng cách giữa "LLM trích ra" và "key có sẵn".
# ===========================================================================

_SKILL_DATA_CORPUS_BASE: list[tuple[str, str]] = [
    # -- Ngôn ngữ lập trình (25) ------------------------------------------------
    *[(s, "Ngôn ngữ") for s in [
        "Python", "Java", "JavaScript", "TypeScript", "C#", "C++", "C", "Go",
        "Golang", "Rust", "Kotlin", "Swift", "PHP", "Ruby", "Scala", "Perl",
        "R Programming", "MATLAB", "Dart", "Elixir", "Erlang", "Haskell",
        "Objective-C", "Visual Basic", "F#",
    ]],
    # -- Frontend web (24) -------------------------------------------------------
    *[(s, "Frontend") for s in [
        "HTML5", "CSS3", "React", "React.js", "ReactJS", "Vue.js", "VueJS",
        "Angular", "AngularJS", "Svelte", "jQuery", "Next.js", "NextJS",
        "Nuxt.js", "Redux", "Redux Toolkit", "MobX", "Webpack", "Vite",
        "Babel", "Sass", "Tailwind CSS", "Bootstrap", "Material UI",
    ]],
    # -- Backend / Node (10) ------------------------------------------------------
    *[(s, "Backend Node") for s in [
        "Node.js", "NodeJS", "Express.js", "ExpressJS", "NestJS", "Fastify",
        "Koa", "GraphQL", "Apollo Client", "Socket.IO",
    ]],
    # -- Python framework/lib (20) ------------------------------------------------
    *[(s, "Python stack") for s in [
        "Django", "Flask", "FastAPI", "Pandas", "NumPy", "SciPy",
        "Scikit-learn", "TensorFlow", "PyTorch", "Keras", "OpenCV",
        "Matplotlib", "Seaborn", "Celery", "SQLAlchemy", "Pydantic",
        "Streamlit", "Scrapy", "BeautifulSoup", "Jupyter Notebook",
    ]],
    # -- Java ecosystem (15) -------------------------------------------------------
    *[(s, "Java stack") for s in [
        "Spring", "Spring Boot", "Spring MVC", "Spring Security", "Hibernate",
        "Maven", "Gradle", "JUnit", "Kotlin Coroutines", "JSP", "Servlets",
        "JPA", "Struts", "Grails", "Tomcat",
    ]],
    # -- .NET ecosystem (15) --------------------------------------------------------
    *[(s, ".NET stack") for s in [
        ".NET", ".NET Core", "ASP.NET", "ASP.NET Core", "ASP.NET MVC",
        "Entity Framework", "Entity Framework Core", "LINQ", "WPF",
        "WinForms", "Xamarin", "Xamarin.Forms", "Blazor", "WCF", "NHibernate",
    ]],
    # -- PHP / Ruby (8) ---------------------------------------------------------------
    *[(s, "PHP/Ruby") for s in [
        "Laravel", "Symfony", "CodeIgniter", "CakePHP", "WordPress",
        "Composer", "Ruby on Rails", "RSpec",
    ]],
    # -- Mobile (15) -------------------------------------------------------------------
    *[(s, "Mobile") for s in [
        "Android", "iOS", "Flutter", "React Native", "SwiftUI",
        "Android Studio", "Cocoa Touch", "Objective-C", "Jetpack Compose",
        "Ionic Framework", "Cordova", "Xamarin.Android", "Xamarin.iOS",
        "Kivy", "Unity",
    ]],
    # -- Database (20) -----------------------------------------------------------------
    *[(s, "Database") for s in [
        "MySQL", "PostgreSQL", "MongoDB", "Redis", "SQLite", "SQL Server",
        "Oracle Database", "Elasticsearch", "Cassandra", "DynamoDB",
        "Firebase", "MariaDB", "Neo4j", "InfluxDB", "CouchDB", "Snowflake",
        "BigQuery", "Supabase", "T-SQL", "PL/SQL",
    ]],
    # -- Cloud & DevOps (25) --------------------------------------------------------------
    *[(s, "Cloud/DevOps") for s in [
        "AWS", "Amazon Web Services", "Azure", "Microsoft Azure",
        "Google Cloud Platform", "GCP", "Docker", "Kubernetes",
        "Docker Compose", "Terraform", "Ansible", "Jenkins", "GitLab CI",
        "GitHub Actions", "CircleCI", "Travis CI", "Nginx", "Apache",
        "Linux", "Bash", "Shell Scripting", "Prometheus", "Grafana",
        "Kubernetes Helm", "Vagrant",
    ]],
    # -- Data / ML / AI (22) ----------------------------------------------------------------
    *[(s, "Data/ML/AI") for s in [
        "Machine Learning", "Deep Learning", "Natural Language Processing",
        "Computer Vision", "Data Analysis", "Data Visualization",
        "Neural Networks", "Power BI", "Tableau", "Excel", "Airflow",
        "Kafka", "Apache Spark", "Hadoop", "OpenAI", "ChatGPT", "LLM",
        "LangChain", "Hugging Face", "Prompt Engineering", "Vector Database",
        "RAG",
    ]],
    # -- Testing/QA (14) --------------------------------------------------------------------
    *[(s, "Testing/QA") for s in [
        "Selenium", "Cypress", "Jest", "Mocha", "PyTest", "Postman",
        "TestNG", "Cucumber", "Appium", "Robot Framework", "Unit Testing",
        "Integration Testing", "Automation Testing", "Performance Testing",
    ]],
    # -- Tool & version control (12) -----------------------------------------------------------
    *[(s, "Tool/VCS") for s in [
        "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Confluence",
        "Figma", "Adobe XD", "Photoshop", "Visual Studio Code", "npm",
        "Yarn",
    ]],
    # -- Khái niệm / quy trình (16) -----------------------------------------------------------
    *[(s, "Khái niệm/Process") for s in [
        "Object-Oriented Programming", "Design Patterns", "Data Structures",
        "Algorithms", "Agile", "Scrum", "CI/CD", "TDD", "Microservices",
        "REST API", "RESTful API", "SOAP", "gRPC", "WebSocket", "OAuth2",
        "JWT",
    ]],
    # -- Game / mới nổi --------------------------------------------------------------------
    *[(s, "Game/Emerging") for s in [
        "Unreal Engine", "Blockchain", "Solidity", "IoT", "WebGL",
        "Three.js", "Prisma", "tRPC", "Zustand", "WebAssembly", "Deno",
        "Bun", "Web3", "Edge Computing",
    ]],
    # -- Networking / Security ---------------------------------------------------------------
    *[(s, "Network/Security") for s in [
        "TCP/IP", "HTTP", "HTTPS", "SSL", "TLS", "OAuth", "SAML", "LDAP",
        "Active Directory", "Firewall", "VPN", "Penetration Testing",
        "OWASP", "Encryption", "Single Sign-On", "Two-Factor Authentication",
    ]],
    # -- CMS / Ecommerce -----------------------------------------------------------------------
    *[(s, "CMS/Ecommerce") for s in [
        "Shopify", "Magento", "WooCommerce", "Drupal", "Joomla", "Wix",
        "Webflow", "Elementor",
    ]],
    # -- Monitoring / Observability ------------------------------------------------------------
    *[(s, "Monitoring") for s in [
        "Datadog", "New Relic", "Splunk", "ELK Stack", "Nagios", "Zabbix",
        "Sentry", "PagerDuty", "Kibana", "Logstash",
    ]],
    # -- Message Queue ---------------------------------------------------------------------------
    *[(s, "Message Queue") for s in [
        "RabbitMQ", "ActiveMQ", "ZeroMQ", "Apache Kafka", "Amazon SQS",
        "Message Queue",
    ]],
    # -- Design / Project management tools --------------------------------------------------------
    *[(s, "Design/PM") for s in [
        "Sketch", "InVision", "Zeplin", "Canva", "Trello", "Asana",
        "Monday.com", "Notion", "Miro", "Slack",
    ]],
    # -- Hệ điều hành ------------------------------------------------------------------------------
    *[(s, "OS") for s in [
        "Windows", "macOS", "Ubuntu", "CentOS", "Windows Server",
        "Red Hat Linux",
    ]],
    # -- Cloud hosting/CDN ----------------------------------------------------------------------------
    *[(s, "Cloud hosting") for s in [
        "Heroku", "Vercel", "Netlify", "DigitalOcean", "Linode",
        "Cloudflare", "CDN", "Serverless",
    ]],
    # -- Data warehousing --------------------------------------------------------------------------------
    *[(s, "Data warehouse") for s in [
        "Data Warehouse", "Data Lake", "Redshift", "Databricks", "dbt",
        "Delta Lake",
    ]],
    # -- Build tool / testing bổ sung -------------------------------------------------------------------------
    *[(s, "Build/Testing bổ sung") for s in [
        "ESLint", "Prettier", "pnpm", "ts-node", "SWC", "Playwright",
        "Enzyme", "Vitest", "Storybook",
    ]],
    # -- Quy trình / soft skill trong JD (bổ sung) --------------------------------------------------------------
    *[(s, "Quy trình/khác") for s in [
        "Kanban", "Waterfall", "Code Review", "Pair Programming",
        "Continuous Integration", "Continuous Deployment", "Load Balancing",
        "Caching", "Fault Tolerance", "High Availability", "Scalability",
        "System Design", "API Gateway", "Rate Limiting", "Feature Flags",
        "Chaos Engineering",
    ]],
    # -- AWS service (dịch vụ cụ thể, thường gặp trong JD cloud) -------------------------------------------------
    *[(s, "AWS services") for s in [
        "Amazon EC2", "Amazon S3", "Amazon RDS", "AWS Lambda", "Amazon SQS",
        "Amazon SNS", "Amazon CloudFront", "Amazon Route 53", "AWS IAM",
        "Amazon ECS", "Amazon EKS", "AWS Fargate", "Amazon CloudWatch",
        "AWS CodePipeline", "AWS CodeBuild", "AWS CodeDeploy",
        "Amazon Kinesis", "AWS Glue", "Amazon Athena", "Amazon SageMaker",
        "AWS Elastic Beanstalk", "Amazon API Gateway", "AWS Step Functions",
        "AWS Secrets Manager", "AWS KMS", "Amazon VPC", "Amazon Aurora",
        "Amazon ElastiCache", "Amazon Neptune", "Amazon DocumentDB",
        "AWS AppSync", "AWS Amplify", "Amazon Cognito", "AWS CloudTrail",
        "AWS Systems Manager", "Amazon EMR",
    ]],
    # -- Azure service (dịch vụ cụ thể) --------------------------------------------------------------------------
    *[(s, "Azure services") for s in [
        "Azure SQL Database", "Azure Cosmos DB", "Azure Kubernetes Service",
        "Azure Blob Storage", "Azure Active Directory", "Azure App Service",
        "Azure Data Factory", "Azure Synapse Analytics", "Azure Monitor",
        "Azure Logic Apps", "Azure Service Bus", "Azure Event Hub",
        "Azure Key Vault", "Azure Container Instances", "Azure Data Lake",
        "Azure Databricks", "Azure Virtual Machines", "Azure DevOps Pipelines",
        "Azure API Management", "Azure Functions App", "Azure Front Door",
        "Azure Cognitive Services", "Azure Machine Learning",
        "Azure Resource Manager", "Azure DNS", "Azure CDN",
        "Azure Application Insights", "Azure Service Fabric",
        "Azure Batch", "Azure Notification Hubs",
    ]],
    # -- GCP service (dịch vụ cụ thể) ----------------------------------------------------------------------------
    *[(s, "GCP services") for s in [
        "Cloud Run", "Cloud Functions", "Cloud Storage", "Compute Engine",
        "Cloud SQL", "Firestore", "Pub/Sub", "Cloud Dataflow",
        "Cloud Dataproc", "Vertex AI", "GKE", "Cloud Build", "Cloud CDN",
        "Cloud Spanner", "Cloud Bigtable", "Cloud Pub/Sub",
        "Cloud IAM", "Cloud Load Balancing", "Cloud Monitoring",
        "Cloud Logging", "Cloud Armor", "Cloud Endpoints",
        "Anthos", "App Engine", "Cloud Composer", "Cloud Data Fusion",
        "Cloud Natural Language API", "Cloud Vision API",
        "Cloud Text-to-Speech", "Firebase Hosting",
    ]],
    # -- BI / Analytics / ERP/CRM --------------------------------------------------------------------------------
    *[(s, "BI/ERP/CRM") for s in [
        "SAP", "SAP ABAP", "SAP HANA", "SAP FICO", "SAP MM", "Salesforce",
        "Salesforce Apex", "Salesforce Lightning", "Microsoft Dynamics 365",
        "Oracle NetSuite", "Odoo", "Zoho CRM", "HubSpot", "Looker",
        "Qlik Sense", "Sisense", "Domo", "Metabase", "Google Data Studio",
        "SSRS", "SSIS", "SSAS", "Alteryx", "KNIME",
    ]],
    # -- Embedded / IoT -------------------------------------------------------------------------------------------
    *[(s, "Embedded/IoT") for s in [
        "Arduino", "Raspberry Pi", "Embedded C", "RTOS", "FreeRTOS",
        "Microcontroller Programming", "ESP32", "STM32", "MQTT",
        "Zigbee", "LoRaWAN", "PLC Programming", "SCADA", "Modbus",
    ]],
    # -- Blockchain / Web3 mở rộng --------------------------------------------------------------------------------
    *[(s, "Blockchain") for s in [
        "Ethereum", "Smart Contract", "Hyperledger Fabric", "Truffle",
        "Hardhat", "Web3.js", "Ethers.js", "MetaMask", "NFT", "DeFi",
        "IPFS",
    ]],
    # -- AR/VR / Graphics -----------------------------------------------------------------------------------------
    *[(s, "AR/VR/Graphics") for s in [
        "ARKit", "ARCore", "OpenGL", "DirectX", "Vulkan", "Blender",
        "Maya", "3ds Max", "Godot Engine", "WebXR",
    ]],
    # -- Networking / giao thức ------------------------------------------------------------------------------------
    *[(s, "Networking protocol") for s in [
        "DNS", "DHCP", "FTP", "SFTP", "SMTP", "IMAP", "POP3", "SNMP",
        "VoIP", "SIP Protocol", "BGP", "OSPF", "IPsec", "MPLS",
    ]],
    # -- Ngôn ngữ / công cụ hiếm gặp hơn (bổ sung độ đa dạng) ------------------------------------------------------
    *[(s, "Ngôn ngữ/tool hiếm") for s in [
        "COBOL", "Ada", "Prolog", "Scheme", "Common Lisp", "Racket",
        "OCaml", "Nim Lang", "Zig Lang", "Crystal Lang", "D Language",
        "Pascal", "Smalltalk", "Tcl", "AWK", "Sed", "PowerShell Core",
        "Visual Basic .NET", "Apex Language", "Vimscript",
    ]],
    # -- Python bổ sung (thư viện phổ biến chưa liệt kê) -----------------------------------------------------------
    *[(s, "Python stack bổ sung") for s in [
        "Pyramid", "Bottle", "Tornado Web", "aiohttp", "httpx", "Requests",
        "XGBoost", "LightGBM", "CatBoost", "JAX", "Pillow", "spaCy",
        "NLTK", "Gensim", "Transformers", "Alembic", "Marshmallow",
        "Click", "Typer", "PyYAML", "Django REST Framework",
        "Django Channels", "Dash", "Gradio", "Poetry", "Black Formatter",
        "Flake8", "Mypy", "Numba", "Dask", "Ray", "Luigi", "Prefect",
        "Great Expectations",
    ]],
    # -- JS/TS bổ sung (thư viện phổ biến chưa liệt kê) --------------------------------------------------------------
    *[(s, "JS/TS stack bổ sung") for s in [
        "Zod", "Yup", "Lodash", "Day.js", "date-fns", "Axios",
        "React Query", "TanStack Query", "SWR", "Recoil", "Jotai",
        "Framer Motion", "GSAP", "D3.js", "Chart.js", "Highcharts",
        "ApexCharts", "Puppeteer", "Turborepo", "Nx Monorepo", "Lerna",
        "Rollup.js", "Parcel Bundler", "esbuild", "Astro", "Remix",
        "SolidJS", "Qwik", "Alpine.js", "Preact",
    ]],
    # -- Testing/QA bổ sung ------------------------------------------------------------------------------------------
    *[(s, "Testing/QA bổ sung") for s in [
        "WebdriverIO", "Karate DSL", "Gatling", "JMeter", "LoadRunner",
        "SoapUI", "Katalon Studio", "Testcontainers", "Mockito",
        "Chai.js", "Sinon.js", "Supertest", "Locust", "k6",
    ]],
]

TARGET_A = 1000  # số test case Phần A theo yêu cầu — xem _pad_to_target()
TARGET_B = 1000  # số test case Phần B theo yêu cầu — xem _pad_pairs_to_target()

# Biến thể định dạng dùng để "bù" corpus lên đủ cỡ mẫu tròn khi danh sách kỹ
# năng/quan hệ độc lập-với-file (viết tay ở trên) chưa đủ số lượng mục tiêu.
#
# CHỈ dùng biến đổi KHÔNG PHÁ HỦY thông tin mà to_stackoverflow_format() cần —
# nếu tự ý xóa dấu cách/dấu gạch/dấu chấm TRƯỚC khi đưa vào lookup, ta vô tình
# tước mất chính các biến thể mà to_stackoverflow_format() vốn tự sinh ra từ
# input CÓ dấu cách (ví dụ "React Native" bị pad thành "ReactNative" sẽ KHÔNG
# còn cách nào phục hồi lại "react-native" — trong khi input gốc có dấu cách
# thì to_stackoverflow_format() tự thử cả 2 biến thể). Test case pad vì vậy
# phải là 1 trong 2 loại: (a) SUBSET của các biến thể to_stackoverflow_format()
# đã tự thử (hyphen hóa, bỏ dấu chấm, đổi hoa/thường — an toàn, không hạ độ
# phủ so với bản gốc), hoặc (b) 1 kiểu viết THẬT nhưng chưa được cascade hỗ
# trợ (dấu underscore) — được phép MISS thật, đó là phát hiện hợp lệ, không
# phải lỗi phương pháp.
_FORMAT_VARIANTS = [
    lambda s: s.replace(" ", "-"),                      # (a) subset — SO-tag hyphen style
    lambda s: s.replace(".", ""),                        # (a) subset — bỏ dấu chấm
    lambda s: s.replace("-", " "),                        # (a) an toàn — khôi phục dấu cách cho mục có sẵn dấu gạch
    lambda s: s.upper(),                                  # (a) an toàn — tra cứu không phân biệt hoa/thường
    lambda s: s.lower(),                                  # (a) an toàn — tra cứu không phân biệt hoa/thường
    lambda s: s.title(),                                  # (a) an toàn — tra cứu không phân biệt hoa/thường
    lambda s: s.swapcase(),                               # (a) an toàn — tra cứu không phân biệt hoa/thường
    lambda s: s.replace(" ", "-").upper(),                # (a) subset + case, vẫn an toàn
    lambda s: s.replace(" ", "-").lower(),                # (a) subset + case, vẫn an toàn
    lambda s: s.replace(" ", "_"),                        # (b) kiểu viết thật, có thể MISS hợp lệ
]


def _pad_to_target(base: list[tuple[str, str]], target: int,
                    pad_category: str, seed: int = 42) -> list[tuple[str, str]]:
    """Nếu base ngắn hơn target, sinh thêm test case bằng cách viết lại các
    mục đã có theo 1 trong các _FORMAT_VARIANTS. Duyệt TOÀN BỘ tổ hợp (mục,
    biến thể) rồi XÁO TRỘN có seed cố định trước khi lấy — nếu duyệt tuần tự
    theo thứ tự khai báo, khi target-base < len(base) ta sẽ dừng lại giữa
    biến thể ĐẦU TIÊN áp cho vài trăm mục đầu danh sách, không bao giờ chạm
    tới các biến thể còn lại (ví dụ bỏ-dấu-chấm — quan trọng cho các mục dạng
    "Node.js"/"Vue.js") — làm mẫu pad lệch có hệ thống theo thứ tự khai báo
    thay vì đại diện cho toàn bộ base. Xáo trộn khử thiên lệch đó. Bỏ qua biến
    thể trùng bản gốc hoặc trùng 1 mục đã có. Nếu base đã >= target thì cắt
    đúng target."""
    import random
    combos = [(raw, vf) for raw, _cat in base for vf in _FORMAT_VARIANTS]
    random.Random(seed).shuffle(combos)
    out = list(base)
    seen = {raw for raw, _ in base}
    for raw, variant_fn in combos:
        if len(out) >= target:
            break
        candidate = variant_fn(raw)
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append((candidate, pad_category))
    return out[:target]


SKILL_DATA_CORPUS: list[tuple[str, str]] = _pad_to_target(
    _SKILL_DATA_CORPUS_BASE, TARGET_A, "Biến thể định dạng (bổ sung tới 1000)")


# ===========================================================================
# PHẦN B — Corpus độ phủ skill_implies.json (Layer 2): (con, cha kỳ vọng)
# Nhãn "cha kỳ vọng" đến từ tri thức miền phổ biến (framework/tool phụ thuộc
# vào ngôn ngữ/platform nền), KHÔNG suy ngược từ nội dung file.
# ===========================================================================

_IMPLIES_CORPUS_BASE: list[tuple[str, str, str]] = [
    # -- Python framework/lib -> Python (hoặc thư viện nền) (20) -------------------
    ("Django", "Python", "Python framework"),
    ("Flask", "Python", "Python framework"),
    ("FastAPI", "Python", "Python framework"),
    ("Pandas", "Python", "Python library"),
    ("NumPy", "Python", "Python library"),
    ("SciPy", "Python", "Python library"),
    ("Matplotlib", "Python", "Python library"),
    ("Scikit-learn", "Python", "Python library"),
    ("PyTorch", "Python", "Python library"),
    ("TensorFlow", "Python", "Python library"),
    ("Keras", "TensorFlow", "Keras chạy trên TensorFlow backend"),
    ("Celery", "Python", "Python library"),
    ("PySpark", "Python", "Python API của Spark"),
    ("PySpark", "Apache Spark", "Python API của Spark"),
    ("SQLAlchemy", "Python", "Python ORM"),
    ("Streamlit", "Python", "Python framework"),
    ("Scrapy", "Python", "Python framework"),
    ("BeautifulSoup", "Python", "Python library"),
    ("Jinja2", "Python", "Python template engine"),
    ("PyTest", "Python", "Python test framework"),
    # -- JS/TS ecosystem (26) -------------------------------------------------------
    ("React", "JavaScript", "JS library"),
    ("Vue.js", "JavaScript", "JS framework"),
    ("Angular", "TypeScript", "Angular viết bằng/yêu cầu TypeScript"),
    ("Angular", "JavaScript", "Angular chạy trên JavaScript runtime"),
    ("Next.js", "React", "Next.js là meta-framework của React"),
    ("Next.js", "JavaScript", "Next.js chạy trên JavaScript"),
    ("Nuxt.js", "Vue.js", "Nuxt.js là meta-framework của Vue"),
    ("Express", "Node.js", "Express chạy trên Node.js"),
    ("Express", "JavaScript", "Express chạy trên JavaScript"),
    ("NestJS", "TypeScript", "NestJS viết bằng TypeScript"),
    ("NestJS", "Node.js", "NestJS chạy trên Node.js"),
    ("Redux", "JavaScript", "State library cho JS"),
    ("Redux Toolkit", "Redux", "Redux Toolkit là bộ công cụ chính thức của Redux"),
    ("jQuery", "JavaScript", "JS library"),
    ("TypeScript", "JavaScript", "TypeScript biên dịch ra JavaScript"),
    ("Node.js", "JavaScript", "Node.js chạy JavaScript phía server"),
    ("Svelte", "JavaScript", "JS framework"),
    ("Gatsby", "React", "Gatsby là static site generator dựa trên React"),
    ("React Native", "React", "React Native dựa trên React"),
    ("React Native", "JavaScript", "React Native viết bằng JavaScript"),
    ("Vuex", "Vue.js", "Vuex là state management của Vue"),
    ("Material UI", "React", "Material UI là component library cho React"),
    ("Styled Components", "React", "Styled Components dùng cho React"),
    ("Ember.js", "JavaScript", "JS framework"),
    ("Backbone.js", "JavaScript", "JS framework"),
    ("Vite", "JavaScript", "Build tool cho JS"),
    # -- Java ecosystem (10) -----------------------------------------------------------
    ("Spring Boot", "Spring", "Spring Boot là module của Spring"),
    ("Spring Boot", "Java", "Spring Boot chạy trên Java"),
    ("Spring MVC", "Spring", "Spring MVC là module của Spring"),
    ("Spring Security", "Spring", "Spring Security là module của Spring"),
    ("Hibernate", "Java", "Hibernate là ORM cho Java"),
    ("Maven", "Java", "Maven là build tool cho Java"),
    ("JUnit", "Java", "JUnit là test framework cho Java"),
    ("Kotlin", "Java", "Kotlin chạy trên JVM, tương tác với Java"),
    ("Kotlin Coroutines", "Kotlin", "Coroutines là tính năng của Kotlin"),
    ("Grails", "Java", "Grails chạy trên JVM"),
    # -- .NET ecosystem (12) -----------------------------------------------------------
    ("ASP.NET Core", "ASP.NET", "ASP.NET Core là thế hệ mới của ASP.NET"),
    ("ASP.NET Core", "C#", "ASP.NET Core viết bằng C#"),
    ("ASP.NET MVC", "ASP.NET", "ASP.NET MVC là module của ASP.NET"),
    ("Entity Framework", "C#", "EF là ORM cho .NET/C#"),
    ("Entity Framework Core", "Entity Framework", "EF Core là thế hệ mới của EF"),
    ("WPF", "C#", "WPF là UI framework của .NET/C#"),
    ("WinForms", "C#", "WinForms là UI framework của .NET/C#"),
    ("Xamarin", "C#", "Xamarin viết bằng C#"),
    ("Xamarin.Forms", "Xamarin", "Xamarin.Forms là module của Xamarin"),
    ("Blazor", "C#", "Blazor viết bằng C#"),
    ("Blazor WebAssembly", "Blazor", "Blazor WASM là chế độ chạy của Blazor"),
    ("LINQ", "C#", "LINQ là tính năng ngôn ngữ của C#/.NET"),
    # -- PHP / Ruby (6) -----------------------------------------------------------------
    ("Laravel", "PHP", "Laravel là framework PHP"),
    ("Symfony", "PHP", "Symfony là framework PHP"),
    ("CodeIgniter", "PHP", "CodeIgniter là framework PHP"),
    ("WordPress", "PHP", "WordPress viết bằng PHP"),
    ("Ruby on Rails", "Ruby", "Rails là framework của Ruby"),
    ("RSpec", "Ruby", "RSpec là test framework của Ruby"),
    # -- Mobile (6) ---------------------------------------------------------------------
    ("Flutter", "Dart", "Flutter viết bằng Dart"),
    ("SwiftUI", "Swift", "SwiftUI là UI framework của Swift"),
    ("Xamarin.Android", "Xamarin", "Xamarin.Android là module của Xamarin"),
    ("Xamarin.iOS", "Xamarin", "Xamarin.iOS là module của Xamarin"),
    ("Cocoa Touch", "Objective-C", "Cocoa Touch gắn với Objective-C/iOS"),
    ("Jetpack Compose", "Android", "Jetpack Compose là UI toolkit của Android"),
    # -- Cloud/DevOps (10) ----------------------------------------------------------------
    ("Kubernetes", "Docker", "K8s thường điều phối container Docker"),
    ("Docker Compose", "Docker", "Docker Compose là tính năng của Docker"),
    ("Kubernetes Helm", "Kubernetes", "Helm là package manager của Kubernetes"),
    ("Spark Streaming", "Apache Spark", "Spark Streaming là module của Spark"),
    ("Kibana", "Elasticsearch", "Kibana dùng để visualize dữ liệu Elasticsearch"),
    ("Logstash", "Elasticsearch", "Logstash thuộc ELK stack cùng Elasticsearch"),
    ("GitHub", "Git", "GitHub là dịch vụ hosting cho Git"),
    ("GitLab", "Git", "GitLab là dịch vụ hosting cho Git"),
    ("Terraform Provider AWS", "Terraform", "Provider là module mở rộng của Terraform"),
    ("Kubectl", "Kubernetes", "kubectl là CLI điều khiển Kubernetes"),
    # -- DB driver -> DB (5) ----------------------------------------------------------------
    ("psycopg2", "PostgreSQL", "psycopg2 là driver Python cho PostgreSQL"),
    ("PyMongo", "MongoDB", "PyMongo là driver Python cho MongoDB"),
    ("PyMySQL", "MySQL", "PyMySQL là driver Python cho MySQL"),
    ("cx_Oracle", "Oracle Database", "cx_Oracle là driver Python cho Oracle"),
    ("JDBC", "Java", "JDBC là API kết nối DB của Java"),
    # -- Hiện đại / chưa chắc có (9) ----------------------------------------------------------
    ("Prisma", "Node.js", "Prisma là ORM phổ biến cho Node.js/TypeScript"),
    ("tRPC", "TypeScript", "tRPC dựa trên type-safety của TypeScript"),
    ("Chakra UI", "React", "Chakra UI là component library cho React"),
    ("Redux Saga", "Redux", "Redux Saga là middleware của Redux"),
    ("Redux Thunk", "Redux", "Redux Thunk là middleware của Redux"),
    ("Apollo Client", "GraphQL", "Apollo Client là client cho GraphQL"),
    ("Apollo Server", "Node.js", "Apollo Server chạy trên Node.js"),
    ("Zustand", "React", "Zustand là state library phổ biến cho React"),
    ("LangChain", "Python", "LangChain thường dùng qua Python SDK"),
    # -- JS/Node bổ sung (12) -----------------------------------------------------------------
    ("ESLint", "JavaScript", "ESLint là linter cho JavaScript"),
    ("Prettier", "JavaScript", "Prettier là formatter cho JavaScript"),
    ("Yarn", "Node.js", "Yarn là package manager của Node.js"),
    ("npm", "Node.js", "npm là package manager mặc định của Node.js"),
    ("Sequelize.js", "Node.js", "Sequelize là ORM cho Node.js"),
    ("Mongoose", "Node.js", "Mongoose là ODM cho Node.js"),
    ("Passport.js", "Node.js", "Passport là middleware auth của Node.js"),
    ("Socket.IO", "Node.js", "Socket.IO thường chạy trên Node.js server"),
    ("React Router", "React", "React Router là routing library của React"),
    ("React Hook Form", "React", "React Hook Form là form library của React"),
    ("Formik", "React", "Formik là form library của React"),
    ("Angular Material", "Angular", "Angular Material là component library của Angular"),
    # -- CMS/Ecommerce (4) --------------------------------------------------------------------
    ("WooCommerce", "WordPress", "WooCommerce là plugin ecommerce của WordPress"),
    ("Elementor", "WordPress", "Elementor là page builder plugin của WordPress"),
    ("Drupal", "PHP", "Drupal là CMS viết bằng PHP"),
    ("Magento", "PHP", "Magento là nền tảng ecommerce viết bằng PHP"),
    # -- Data / warehouse (4) -----------------------------------------------------------------
    ("dbt", "SQL", "dbt biên dịch transformation thành SQL"),
    ("Databricks", "Apache Spark", "Databricks là nền tảng quản lý Spark"),
    ("Redshift", "AWS", "Redshift là data warehouse dịch vụ của AWS"),
    ("BigQuery", "Google Cloud Platform", "BigQuery là data warehouse dịch vụ của GCP"),
    # -- Cloud/DevOps bổ sung (7) -------------------------------------------------------------
    ("Istio", "Kubernetes", "Istio là service mesh chạy trên Kubernetes"),
    ("ArgoCD", "Kubernetes", "ArgoCD là công cụ GitOps triển khai lên Kubernetes"),
    ("AWS Lambda", "AWS", "Lambda là dịch vụ serverless của AWS"),
    ("Azure Functions", "Azure", "Azure Functions là dịch vụ serverless của Azure"),
    ("Google Cloud Functions", "Google Cloud Platform", "Cloud Functions là dịch vụ serverless của GCP"),
    ("CloudFormation", "AWS", "CloudFormation là IaC dịch vụ của AWS"),
    ("Azure DevOps", "Azure", "Azure DevOps là bộ công cụ CI/CD của Azure"),
    # -- Testing bổ sung (3) ------------------------------------------------------------------
    ("Playwright", "JavaScript", "Playwright là test framework cho JavaScript"),
    ("Jest", "JavaScript", "Jest là test framework cho JavaScript"),
    ("Enzyme", "React", "Enzyme là test utility cho React"),
    # -- iOS/Swift bổ sung (2) ----------------------------------------------------------------
    ("Core Data", "Swift", "Core Data là framework persistence của Apple dùng với Swift"),
    ("Combine", "Swift", "Combine là framework reactive của Apple dùng với Swift"),
    # -- Bổ sung khác để phủ rộng hơn (14) -----------------------------------------------------
    ("Vitest", "JavaScript", "Vitest là test framework cho JavaScript/Vite"),
    ("Storybook", "JavaScript", "Storybook là công cụ dựng UI component cho JavaScript"),
    ("Vercel", "Next.js", "Vercel là nền tảng deploy chính thức của Next.js"),
    ("Elasticsearch", "Java", "Elasticsearch viết bằng Java"),
    ("Cassandra", "Java", "Cassandra viết bằng Java"),
    ("Kafka Streams", "Apache Kafka", "Kafka Streams là thư viện xử lý stream của Kafka"),
    ("Micronaut", "Java", "Micronaut là framework Java"),
    ("Quarkus", "Java", "Quarkus là framework Java"),
    ("Dropwizard", "Java", "Dropwizard là framework Java"),
    ("Ktor", "Kotlin", "Ktor là framework web viết bằng Kotlin"),
    ("Retrofit", "Java", "Retrofit là HTTP client cho Java/Android"),
    ("OkHttp", "Java", "OkHttp là HTTP client cho Java/Android"),
    ("Room", "Android", "Room là thư viện persistence của Android"),
    ("ViewModel", "Android", "ViewModel là thành phần kiến trúc của Android"),
    # -- AWS services -> AWS (30) ---------------------------------------------------------------
    ("Amazon EC2", "AWS", "EC2 là dịch vụ compute của AWS"),
    ("Amazon S3", "AWS", "S3 là dịch vụ storage của AWS"),
    ("Amazon RDS", "AWS", "RDS là dịch vụ database của AWS"),
    ("Amazon SQS", "AWS", "SQS là dịch vụ message queue của AWS"),
    ("Amazon SNS", "AWS", "SNS là dịch vụ notification của AWS"),
    ("Amazon CloudFront", "AWS", "CloudFront là dịch vụ CDN của AWS"),
    ("Amazon Route 53", "AWS", "Route 53 là dịch vụ DNS của AWS"),
    ("AWS IAM", "AWS", "IAM là dịch vụ quản lý quyền của AWS"),
    ("Amazon ECS", "AWS", "ECS là dịch vụ container orchestration của AWS"),
    ("Amazon EKS", "AWS", "EKS là dịch vụ Kubernetes quản lý của AWS"),
    ("Amazon EKS", "Kubernetes", "EKS là Kubernetes quản lý của AWS"),
    ("AWS Fargate", "AWS", "Fargate là dịch vụ serverless container của AWS"),
    ("Amazon CloudWatch", "AWS", "CloudWatch là dịch vụ monitoring của AWS"),
    ("AWS CodePipeline", "AWS", "CodePipeline là dịch vụ CI/CD của AWS"),
    ("AWS CodeBuild", "AWS", "CodeBuild là dịch vụ build của AWS"),
    ("AWS CodeDeploy", "AWS", "CodeDeploy là dịch vụ deploy của AWS"),
    ("Amazon Kinesis", "AWS", "Kinesis là dịch vụ streaming của AWS"),
    ("AWS Glue", "AWS", "Glue là dịch vụ ETL của AWS"),
    ("Amazon Athena", "AWS", "Athena là dịch vụ query serverless của AWS"),
    ("Amazon SageMaker", "AWS", "SageMaker là dịch vụ ML của AWS"),
    ("AWS Elastic Beanstalk", "AWS", "Elastic Beanstalk là PaaS của AWS"),
    ("Amazon API Gateway", "AWS", "API Gateway là dịch vụ quản lý API của AWS"),
    ("AWS Step Functions", "AWS", "Step Functions là dịch vụ workflow của AWS"),
    ("AWS Secrets Manager", "AWS", "Secrets Manager là dịch vụ quản lý secret của AWS"),
    ("AWS KMS", "AWS", "KMS là dịch vụ quản lý key mã hóa của AWS"),
    ("Amazon VPC", "AWS", "VPC là dịch vụ mạng ảo của AWS"),
    ("Amazon Aurora", "AWS", "Aurora là dịch vụ database của AWS"),
    ("Amazon ElastiCache", "AWS", "ElastiCache là dịch vụ cache của AWS"),
    ("Amazon Cognito", "AWS", "Cognito là dịch vụ authentication của AWS"),
    ("Amazon EMR", "AWS", "EMR là dịch vụ big data của AWS"),
    # -- Azure services -> Azure (25) ---------------------------------------------------------------
    ("Azure SQL Database", "Azure", "Azure SQL Database là dịch vụ database của Azure"),
    ("Azure Cosmos DB", "Azure", "Cosmos DB là dịch vụ NoSQL của Azure"),
    ("Azure Kubernetes Service", "Azure", "AKS là dịch vụ Kubernetes quản lý của Azure"),
    ("Azure Kubernetes Service", "Kubernetes", "AKS là Kubernetes quản lý của Azure"),
    ("Azure Blob Storage", "Azure", "Blob Storage là dịch vụ lưu trữ của Azure"),
    ("Azure Active Directory", "Azure", "Azure AD là dịch vụ định danh của Azure"),
    ("Azure App Service", "Azure", "App Service là PaaS của Azure"),
    ("Azure Data Factory", "Azure", "Data Factory là dịch vụ ETL của Azure"),
    ("Azure Synapse Analytics", "Azure", "Synapse Analytics là data warehouse của Azure"),
    ("Azure Monitor", "Azure", "Azure Monitor là dịch vụ monitoring của Azure"),
    ("Azure Logic Apps", "Azure", "Logic Apps là dịch vụ workflow của Azure"),
    ("Azure Service Bus", "Azure", "Service Bus là dịch vụ message queue của Azure"),
    ("Azure Key Vault", "Azure", "Key Vault là dịch vụ quản lý secret của Azure"),
    ("Azure Data Lake", "Azure", "Data Lake là dịch vụ lưu trữ big data của Azure"),
    ("Azure Databricks", "Azure", "Azure Databricks tích hợp Spark trên Azure"),
    ("Azure Databricks", "Apache Spark", "Azure Databricks chạy trên nền Spark"),
    ("Azure Virtual Machines", "Azure", "VM là dịch vụ compute của Azure"),
    ("Azure API Management", "Azure", "API Management là dịch vụ quản lý API của Azure"),
    ("Azure Cognitive Services", "Azure", "Cognitive Services là dịch vụ AI của Azure"),
    ("Azure Machine Learning", "Azure", "Azure ML là dịch vụ ML của Azure"),
    ("Azure DNS", "Azure", "Azure DNS là dịch vụ DNS của Azure"),
    ("Azure CDN", "Azure", "Azure CDN là dịch vụ CDN của Azure"),
    ("Azure Application Insights", "Azure", "Application Insights là dịch vụ APM của Azure"),
    ("Azure Service Fabric", "Azure", "Service Fabric là nền tảng microservices của Azure"),
    ("Azure Notification Hubs", "Azure", "Notification Hubs là dịch vụ push notification của Azure"),
    # -- GCP services -> GCP (20) ---------------------------------------------------------------
    ("Cloud Run", "Google Cloud Platform", "Cloud Run là dịch vụ serverless container của GCP"),
    ("Cloud Functions", "Google Cloud Platform", "Cloud Functions là dịch vụ serverless của GCP"),
    ("Cloud Storage", "Google Cloud Platform", "Cloud Storage là dịch vụ lưu trữ của GCP"),
    ("Compute Engine", "Google Cloud Platform", "Compute Engine là dịch vụ compute của GCP"),
    ("Cloud SQL", "Google Cloud Platform", "Cloud SQL là dịch vụ database của GCP"),
    ("Firestore", "Google Cloud Platform", "Firestore là dịch vụ NoSQL của GCP"),
    ("Pub/Sub", "Google Cloud Platform", "Pub/Sub là dịch vụ messaging của GCP"),
    ("Cloud Dataflow", "Google Cloud Platform", "Dataflow là dịch vụ xử lý dữ liệu của GCP"),
    ("Cloud Dataproc", "Google Cloud Platform", "Dataproc là dịch vụ Spark/Hadoop quản lý của GCP"),
    ("Cloud Dataproc", "Apache Spark", "Dataproc chạy Spark/Hadoop quản lý"),
    ("Vertex AI", "Google Cloud Platform", "Vertex AI là dịch vụ ML của GCP"),
    ("GKE", "Google Cloud Platform", "GKE là dịch vụ Kubernetes quản lý của GCP"),
    ("GKE", "Kubernetes", "GKE là Kubernetes quản lý của GCP"),
    ("Cloud Build", "Google Cloud Platform", "Cloud Build là dịch vụ CI/CD của GCP"),
    ("Cloud Spanner", "Google Cloud Platform", "Cloud Spanner là dịch vụ database phân tán của GCP"),
    ("Cloud Bigtable", "Google Cloud Platform", "Bigtable là dịch vụ NoSQL của GCP"),
    ("Cloud IAM", "Google Cloud Platform", "Cloud IAM là dịch vụ quản lý quyền của GCP"),
    ("Cloud Monitoring", "Google Cloud Platform", "Cloud Monitoring là dịch vụ monitoring của GCP"),
    ("App Engine", "Google Cloud Platform", "App Engine là PaaS của GCP"),
    ("Cloud Composer", "Google Cloud Platform", "Cloud Composer là dịch vụ Airflow quản lý của GCP"),
    ("Cloud Composer", "Airflow", "Cloud Composer là Airflow quản lý trên GCP"),
    # -- BI/ERP/CRM (12) ---------------------------------------------------------------
    ("SAP ABAP", "SAP", "ABAP là ngôn ngữ lập trình của SAP"),
    ("SAP HANA", "SAP", "HANA là database platform của SAP"),
    ("SAP FICO", "SAP", "FICO là module tài chính của SAP"),
    ("SAP MM", "SAP", "MM là module quản lý vật tư của SAP"),
    ("Salesforce Apex", "Salesforce", "Apex là ngôn ngữ lập trình của Salesforce"),
    ("Salesforce Lightning", "Salesforce", "Lightning là framework UI của Salesforce"),
    ("SSRS", "SQL Server", "SSRS là công cụ reporting của SQL Server"),
    ("SSIS", "SQL Server", "SSIS là công cụ ETL của SQL Server"),
    ("SSAS", "SQL Server", "SSAS là công cụ phân tích của SQL Server"),
    ("Looker", "SQL", "Looker dùng LookML dựa trên SQL"),
    ("Google Data Studio", "Google Cloud Platform", "Data Studio tích hợp hệ sinh thái GCP"),
    ("Firebase Hosting", "Firebase", "Firebase Hosting là dịch vụ của Firebase"),
    # -- Embedded/IoT (6) ---------------------------------------------------------------
    ("FreeRTOS", "Embedded C", "FreeRTOS thường viết bằng Embedded C"),
    ("ESP32", "Embedded C", "Lập trình ESP32 thường dùng Embedded C"),
    ("STM32", "Embedded C", "Lập trình STM32 thường dùng Embedded C"),
    ("Arduino", "C++", "Arduino sketch dựa trên C++"),
    ("MQTT", "IoT", "MQTT là giao thức truyền thông phổ biến trong IoT"),
    ("Raspberry Pi", "Linux", "Raspberry Pi thường chạy hệ điều hành Linux"),
    # -- Blockchain (5) ---------------------------------------------------------------
    ("Smart Contract", "Solidity", "Smart contract trên Ethereum thường viết bằng Solidity"),
    ("Truffle", "Solidity", "Truffle là framework phát triển Solidity"),
    ("Hardhat", "Solidity", "Hardhat là framework phát triển Solidity"),
    ("Web3.js", "JavaScript", "Web3.js là thư viện JavaScript"),
    ("Ethers.js", "JavaScript", "Ethers.js là thư viện JavaScript"),
    # -- AR/VR/Graphics (4) ---------------------------------------------------------------
    ("ARKit", "Swift", "ARKit thường dùng qua Swift trên iOS"),
    ("ARCore", "Android", "ARCore thường dùng trên nền tảng Android"),
    ("Godot Engine", "GDScript", "Godot Engine dùng ngôn ngữ script riêng GDScript"),
    ("WebXR", "JavaScript", "WebXR là API JavaScript cho AR/VR trên web"),
    # -- Python bổ sung -> Python (16) ---------------------------------------------------------------
    ("Pyramid", "Python", "Python framework"),
    ("Bottle", "Python", "Python framework"),
    ("Tornado Web", "Python", "Python framework"),
    ("aiohttp", "Python", "Python library"),
    ("XGBoost", "Python", "Python library phổ biến qua API Python"),
    ("LightGBM", "Python", "Python library phổ biến qua API Python"),
    ("JAX", "Python", "Python library"),
    ("Pillow", "Python", "Python library"),
    ("spaCy", "Python", "Python library"),
    ("NLTK", "Python", "Python library"),
    ("Gensim", "Python", "Python library"),
    ("Transformers", "Python", "Hugging Face Transformers là Python library"),
    ("Django REST Framework", "Django", "DRF là extension của Django"),
    ("Django Channels", "Django", "Channels là extension của Django"),
    ("Dash", "Python", "Dash là Python framework cho dashboard"),
    ("Gradio", "Python", "Gradio là Python library"),
    # -- JS/TS bổ sung (14) ---------------------------------------------------------------
    ("React Query", "React", "React Query là data-fetching library của React"),
    ("TanStack Query", "React", "TanStack Query là data-fetching library của React"),
    ("SWR", "React", "SWR là data-fetching library của React"),
    ("Recoil", "React", "Recoil là state library của React"),
    ("Jotai", "React", "Jotai là state library của React"),
    ("Framer Motion", "React", "Framer Motion là animation library của React"),
    ("D3.js", "JavaScript", "D3.js là thư viện visualization của JavaScript"),
    ("Turborepo", "JavaScript", "Turborepo là monorepo tool cho hệ sinh thái JS"),
    ("Nx Monorepo", "JavaScript", "Nx là monorepo tool cho hệ sinh thái JS"),
    ("Astro", "JavaScript", "Astro là framework JavaScript"),
    ("Remix", "React", "Remix là meta-framework của React"),
    ("SolidJS", "JavaScript", "SolidJS là framework JavaScript"),
    ("Qwik", "JavaScript", "Qwik là framework JavaScript"),
    ("Preact", "React", "Preact là bản thay thế nhẹ của React"),
    # -- Testing/QA bổ sung (8) ---------------------------------------------------------------
    ("WebdriverIO", "JavaScript", "WebdriverIO là test framework cho JavaScript"),
    ("Testcontainers", "Docker", "Testcontainers chạy test bằng container Docker"),
    ("Mockito", "Java", "Mockito là mocking framework cho Java"),
    ("Chai.js", "JavaScript", "Chai là assertion library cho JavaScript"),
    ("Sinon.js", "JavaScript", "Sinon là mocking library cho JavaScript"),
    ("Supertest", "Node.js", "Supertest dùng để test HTTP server Node.js"),
    ("k6", "JavaScript", "k6 dùng script JavaScript để load test"),
    ("JMeter", "Java", "JMeter viết bằng Java"),
]


def _pad_pairs_to_target(base: list[tuple[str, str, str]], target: int,
                          seed: int = 43) -> list[tuple[str, str, str]]:
    """Tương tự _pad_to_target() nhưng cho cặp (con, cha, ghi chú): chỉ biến
    đổi format của SKILL CON (cha và quan hệ giữ nguyên, vì quan hệ kéo theo
    không đổi theo cách viết) — mô phỏng cùng 1 quan hệ được viết dưới nhiều
    hình thức khác nhau trong các CV/JD khác nhau. Cũng xáo trộn tổ hợp
    (cặp, biến thể) trước khi lấy — cùng lý do khử thiên lệch thứ tự đã nêu ở
    _pad_to_target()."""
    import random
    combos = [(child, parent, note, vf) for child, parent, note in base for vf in _FORMAT_VARIANTS]
    random.Random(seed).shuffle(combos)
    out = list(base)
    seen = {c for c, _, _ in base}
    for child, parent, note, variant_fn in combos:
        if len(out) >= target:
            break
        candidate = variant_fn(child)
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append((candidate, parent, f"{note} (biến thể định dạng của '{child}')"))
    return out[:target]


IMPLIES_CORPUS: list[tuple[str, str, str]] = _pad_pairs_to_target(_IMPLIES_CORPUS_BASE, TARGET_B)


# ===========================================================================
# PHẦN A — Logic đo độ phủ Layer 1
# ===========================================================================

@dataclass
class CoverageRow:
    raw: str
    category: str
    found: bool
    kind: str          # "self_canonical" | "synonym" | "not_found"
    matched_key: str
    canonical: str


def check_skill_data_lookup(raw: str) -> CoverageRow:
    """Lặp lại CHÍNH XÁC cơ chế tra cứu của resolve_canonical() nhưng tách rõ
    3 kết quả (thay vì chỉ trả 1 chuỗi) để đo được độ phủ thật, không lẫn với
    trường hợp 'không tìm thấy nhưng tình cờ trùng canonical'."""
    for variant in to_stackoverflow_format(raw):
        if variant in SKILL_DATA:
            value = SKILL_DATA[variant]
            if value is None:
                return CoverageRow(raw, "", True, "self_canonical", variant, variant)
            return CoverageRow(raw, "", True, "synonym", variant, value)
    fallback = raw.strip().lower()
    return CoverageRow(raw, "", False, "not_found", "", fallback)


def run_skill_data_coverage() -> list[CoverageRow]:
    rows = []
    for raw, category in SKILL_DATA_CORPUS:
        r = check_skill_data_lookup(raw)
        rows.append(CoverageRow(raw, category, r.found, r.kind, r.matched_key, r.canonical))
    return rows


# ===========================================================================
# PHẦN B — Logic đo độ phủ Layer 2
# ===========================================================================

@dataclass
class ImpliesRow:
    child: str
    parent: str
    note: str
    child_canon: str
    parent_canon: str
    found: bool


def check_implies(child: str, parent: str, note: str) -> ImpliesRow:
    child_canon = resolve_canonical(child)
    parent_canon = resolve_canonical(parent)
    implied = SKILL_IMPLIES.get(child_canon, [])
    return ImpliesRow(child, parent, note, child_canon, parent_canon, parent_canon in implied)


def run_implies_coverage() -> list[ImpliesRow]:
    return [check_implies(c, p, n) for c, p, n in IMPLIES_CORPUS]


# ===========================================================================
# Rendering
# ===========================================================================

_KIND_LABEL = {
    "self_canonical": "✅ self-canonical",
    "synonym": "✅ synonym",
    "not_found": "❌ KHÔNG tìm thấy",
}


def render_category_summary(rows: list[CoverageRow]) -> str:
    cats: dict[str, list[CoverageRow]] = {}
    for r in rows:
        cats.setdefault(r.category, []).append(r)
    lines = ["| Nhóm | Số case | Tìm thấy | Độ phủ |", "| --- | --- | --- | --- |"]
    for cat, rs in cats.items():
        found = sum(1 for r in rs if r.found)
        lines.append(f"| {cat} | {len(rs)} | {found} | {found/len(rs)*100:.1f}% |")
    return "\n".join(lines)


def render_skill_data_table(rows: list[CoverageRow]) -> str:
    lines = ["| Nhóm | Tên kỹ năng (đầu vào) | Kết quả tra cứu | Key khớp | Canonical |",
             "| --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r.category} | `{r.raw}` | {_KIND_LABEL[r.kind]} | "
                      f"{f'`{r.matched_key}`' if r.matched_key else '—'} | `{r.canonical}` |")
    return "\n".join(lines)


def render_implies_table(rows: list[ImpliesRow]) -> str:
    lines = ["| Con | Cha kỳ vọng | Lý do | Con (canonical) | Cha (canonical) | Có trong skill_implies.json? |",
             "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        mark = "✅ CÓ" if r.found else "❌ KHÔNG"
        lines.append(f"| `{r.child}` | `{r.parent}` | {r.note} | `{r.child_canon}` | "
                      f"`{r.parent_canon}` | {mark} |")
    return "\n".join(lines)


def skill_data_sheet_rows(rows: list[CoverageRow]) -> list[list]:
    out = [["Category", "Raw input", "Found", "Kind", "Matched key", "Canonical"]]
    for r in rows:
        out.append([r.category, r.raw, "TRUE" if r.found else "FALSE", r.kind, r.matched_key, r.canonical])
    return out


def implies_sheet_rows(rows: list[ImpliesRow]) -> list[list]:
    out = [["Child", "Expected parent", "Note", "Child canonical", "Parent canonical", "Found"]]
    for r in rows:
        out.append([r.child, r.parent, r.note, r.child_canon, r.parent_canon, "TRUE" if r.found else "FALSE"])
    return out


def summary_sheet_rows(a_rows: list[CoverageRow], b_rows: list[ImpliesRow]) -> list[list]:
    a_found = sum(1 for r in a_rows if r.found)
    a_self = sum(1 for r in a_rows if r.kind == "self_canonical")
    a_syn = sum(1 for r in a_rows if r.kind == "synonym")
    b_found = sum(1 for r in b_rows if r.found)
    return [
        ["Metric", "Value"],
        ["PHAN A - skill_data.json (Layer 1)", ""],
        ["Tong test case", len(a_rows)],
        ["Tim thay (found)", a_found],
        ["  - qua self-canonical key", a_self],
        ["  - qua synonym", a_syn],
        ["Khong tim thay", len(a_rows) - a_found],
        ["Do phu", round(a_found / len(a_rows), 4)],
        [],
        ["PHAN B - skill_implies.json (Layer 2)", ""],
        ["Tong test case", len(b_rows)],
        ["Tim thay (found)", b_found],
        ["Khong tim thay", len(b_rows) - b_found],
        ["Do phu", round(b_found / len(b_rows), 4)],
        [],
        ["TONG", ""],
        ["Tong test case (A+B)", len(a_rows) + len(b_rows)],
    ]


def main() -> None:
    a_rows = run_skill_data_coverage()
    b_rows = run_implies_coverage()

    a_found = sum(1 for r in a_rows if r.found)
    a_self = sum(1 for r in a_rows if r.kind == "self_canonical")
    a_syn = sum(1 for r in a_rows if r.kind == "synonym")
    a_miss = [r for r in a_rows if not r.found]

    b_found = sum(1 for r in b_rows if r.found)
    b_miss = [r for r in b_rows if not r.found]

    total_cases = len(a_rows) + len(b_rows)
    n_categories = len({r.category for r in a_rows if r.category != "Biến thể định dạng (bổ sung tới 1000)"})
    n_base_a = len(_SKILL_DATA_CORPUS_BASE)
    n_pad_a = len(a_rows) - n_base_a
    n_base_b = len(_IMPLIES_CORPUS_BASE)
    n_pad_b = len(b_rows) - n_base_b

    # Nhóm tên dịch vụ cloud CỤ THỂ (Amazon EC2, Azure Cosmos DB, Cloud Run...)
    # kéo trung bình Phần A xuống rất mạnh (0-3%) vì Stack Overflow tag taxonomy
    # — nguồn của skill_data.json — chỉ tag NỀN TẢNG chung (aws/azure/gcp), không
    # tag riêng từng SKU dịch vụ. Tách ra để kết luận không gộp lẫn 2 hiện tượng
    # khác nhau: "công nghệ thường gặp" (độ phủ thật cao) và "tên dịch vụ cloud
    # cụ thể" (độ phủ thật thấp, do bản chất nguồn dữ liệu chứ không phải lỗi).
    _CLOUD_SKU_CATS = {"AWS services", "Azure services", "GCP services"}
    cloud_rows = [r for r in a_rows if r.category in _CLOUD_SKU_CATS]
    general_rows = [r for r in a_rows if r.category not in _CLOUD_SKU_CATS
                     and r.category != "Biến thể định dạng (bổ sung tới 1000)"]
    cloud_found = sum(1 for r in cloud_rows if r.found)
    general_found = sum(1 for r in general_rows if r.found)

    report = f"""# Thực nghiệm: độ phủ của skill_data.json và skill_implies.json (D2)

Sinh tự động bởi `scripts/d2_kb_coverage_experiment.py`. Đối tượng đo: 2 file
dữ liệu tĩnh làm nền cho Layer 1/2 của D2 Skill Scoring —
[`app/data/skill_data.json`](../app/data/skill_data.json) ({len(SKILL_DATA)}
entries) và [`app/data/skill_implies.json`](../app/data/skill_implies.json)
({len(SKILL_IMPLIES)} entries), xem đặc tả pipeline ở
[`app/services/skill_matcher.py`](../app/services/skill_matcher.py) và
[`docs/thesis_report.md` mục 3.5](thesis_report.md#35-d2--chi-tiết-pipeline-so-khớp-kỹ-năng-skill_matcherpy).

**Tổng cộng {total_cases} test case** ({len(a_rows)} cho Phần A, {len(b_rows)}
cho Phần B), xây từ tri thức miền (domain knowledge) **độc lập với nội dung 2
file** — nếu suy ngược test case từ chính file thì độ phủ đương nhiên đạt
100%, không đo được gì. Một test case MISS ở đây **không phải lỗi thuật
toán** (đã kiểm chứng riêng ở `d2_layer3_threshold_experiment.py`) — nó chỉ ra
đúng khoảng trống dữ liệu cần bổ sung qua `app/data/add_*_skills.py`.

## PHẦN A — Độ phủ của skill_data.json (Layer 1 — canonical hóa)

**Câu hỏi:** với tên kỹ năng viết theo phong cách output LLM thật (Title
Case, dấu chấm, viết tắt phổ biến — không phải định dạng key SO-tag của
skill_data.json), bao nhiêu % được nhận diện?

**Phương pháp:** {n_base_a} tên kỹ năng viết tay từ tri thức miền, phủ
{n_categories} nhóm công nghệ thường gặp trong CV/JD thật (ngôn ngữ, frontend,
backend, mobile, database, cloud/devops, dịch vụ AWS/Azure/GCP cụ thể,
BI/ERP/CRM, embedded/IoT, blockchain, data/ML/AI, testing, tool, khái niệm quy
trình...), cộng thêm {n_pad_a} test case **biến thể định dạng** của chính các
mục đã có (space↔dash, bỏ dấu chấm, đổi kiểu viết hoa, space↔underscore — xem
`_pad_to_target()`) để đạt đúng cỡ mẫu tròn {len(a_rows)}; mỗi biến thể vẫn là
1 cách viết thật một CV/JD khác có thể tạo ra cho cùng 1 kỹ năng, nên đây vẫn
là phép thử hợp lệ (độ mạnh của `to_stackoverflow_format()` trước biến thiên
định dạng), không phải số liệu đệm vô nghĩa. Với mỗi tên, lặp lại đúng cơ chế
tra cứu `to_stackoverflow_format()` + tra `SKILL_DATA`, tách 3 kết quả: khớp
qua **key tự-canonical** (value=null — chính key đã là tên chuẩn), khớp qua
**synonym** (value≠null — key trỏ sang 1 canonical khác), hoặc **không tìm
thấy** ở bất kỳ biến thể định dạng nào.

### A.1 Độ phủ theo nhóm công nghệ

{render_category_summary(a_rows)}

### A.2 Tổng hợp

| Chỉ số | Giá trị |
| --- | --- |
| Tổng test case | {len(a_rows)} |
| Tìm thấy | {a_found} ({a_found/len(a_rows)*100:.1f}%) |
| — qua key tự-canonical (value=null) | {a_self} |
| — qua synonym (value≠null) | {a_syn} |
| Không tìm thấy | {len(a_miss)} ({len(a_miss)/len(a_rows)*100:.1f}%) |
| **Độ phủ skill_data.json** | **{a_found/len(a_rows)*100:.1f}%** |

### A.3 Danh sách MISS (không tìm thấy ở bất kỳ biến thể nào)

{chr(10).join(f"- `{r.raw}` ({r.category})" for r in a_miss) or "- (không có — độ phủ 100%)"}

### A.4 Toàn bộ {len(a_rows)} test case

<details>
<summary>Xem đầy đủ (bấm để mở)</summary>

{render_skill_data_table(a_rows)}

</details>

## PHẦN B — Độ phủ của skill_implies.json (Layer 2 — entailment)

**Câu hỏi:** với các quan hệ "biết X thì biết Y" đã biết rộng rãi trong giới
lập trình (framework kéo theo ngôn ngữ/thư viện nền), bao nhiêu % thực sự có
trong skill_implies.json để Layer 2 tự động suy ra, thay vì phải dựa vào JD
liệt kê tường minh cả framework lẫn ngôn ngữ nền?

**Phương pháp:** {n_base_b} cặp (skill con, skill cha kỳ vọng) viết tay từ tri
thức miền, phủ Python/JS-TS/Java/.NET/PHP-Ruby/Mobile/dịch vụ AWS-Azure-GCP cụ
thể/BI-ERP/Embedded-IoT/Blockchain/DB driver và một nhóm thư viện hiện đại
(Prisma, tRPC, Zustand...) mà độ phủ **không chắc chắn trước**, cộng thêm
{n_pad_b} test case **biến thể định dạng của phía CON** (cha và quan hệ giữ
nguyên — xem `_pad_pairs_to_target()`) để đạt đúng cỡ mẫu tròn {len(b_rows)}.
Với mỗi cặp: canonical hóa cả 2 phía qua skill_data.json (Layer 1), rồi tra
`SKILL_IMPLIES[con_canonical]` có chứa `cha_canonical` không.

### B.1 Tổng hợp

| Chỉ số | Giá trị |
| --- | --- |
| Tổng test case | {len(b_rows)} |
| Có trong skill_implies.json | {b_found} ({b_found/len(b_rows)*100:.1f}%) |
| KHÔNG có | {len(b_miss)} ({len(b_miss)/len(b_rows)*100:.1f}%) |
| **Độ phủ skill_implies.json** | **{b_found/len(b_rows)*100:.1f}%** |

### B.2 Danh sách MISS (quan hệ kỳ vọng nhưng chưa có trong file)

{chr(10).join(f"- `{r.child}` → `{r.parent}` ({r.note}) — canonical: `{r.child_canon}` → `{r.parent_canon}`" for r in b_miss) or "- (không có — độ phủ 100%)"}

### B.3 Toàn bộ {len(b_rows)} test case

<details>
<summary>Xem đầy đủ (bấm để mở)</summary>

{render_implies_table(b_rows)}

</details>

## Kết luận

| | Kết quả |
| --- | --- |
| Độ phủ skill_data.json (Phần A, {len(a_rows)} case) | **{a_found}/{len(a_rows)} = {a_found/len(a_rows)*100:.1f}%** |
| Độ phủ skill_implies.json (Phần B, {len(b_rows)} case) | **{b_found}/{len(b_rows)} = {b_found/len(b_rows)*100:.1f}%** |

Độ phủ tổng {a_found/len(a_rows)*100:.1f}% của Phần A che giấu 1 khác biệt lớn
giữa 2 loại kỹ năng — tách theo A.1 để không kết luận nhầm:

| Nhóm | Case | Tìm thấy | Độ phủ |
| --- | --- | --- | --- |
| Công nghệ chung (ngôn ngữ, framework, DB, tool, khái niệm...) | {len(general_rows)} | {general_found} | **{general_found/len(general_rows)*100:.1f}%** |
| Tên dịch vụ cloud CỤ THỂ (Amazon EC2, Azure Cosmos DB, Cloud Run...) | {len(cloud_rows)} | {cloud_found} | **{cloud_found/len(cloud_rows)*100:.1f}%** |

Với **công nghệ chung** — loại kỹ năng chiếm đa số trên CV/JD thật —
skill_data.json đạt độ phủ {"cao" if general_found/len(general_rows) >= 0.85 else "khá"}
({general_found/len(general_rows)*100:.1f}%); phần lớn MISS (xem A.3) rơi vào
công nghệ quá mới hoặc tên gọi hiếm gặp mà nguồn dữ liệu gốc (Stack Overflow
tags, xem `app/data/crawl_so_tags.py`) chưa kịp cập nhật. Ngược lại, độ phủ
gần như **bằng 0** với **tên dịch vụ cloud cụ thể** — đây KHÔNG phải lỗ hổng
bất ngờ mà là hệ quả tất yếu của nguồn dữ liệu: Stack Overflow tag hóa theo
NỀN TẢNG chung (`aws`, `azure`, `gcp` đều đã có trong skill_data.json), không
tag riêng từng SKU dịch vụ (`amazon-ec2`, `azure-cosmosdb`...). Hệ quả thực tế
cho D2: nếu JD ghi cụ thể "Amazon EC2" thay vì "AWS", CV chỉ ghi "AWS" chung
chung sẽ KHÔNG được Layer 1 nhận diện khớp — phải rơi xuống Layer 3 (fuzzy)
hoặc bị tính là thiếu, dù về bản chất ứng viên có kỹ năng liên quan.

skill_implies.json có độ phủ thấp hơn skill_data.json — đúng như kỳ vọng, vì
đây là quan hệ **kéo theo giữa 2 skill** (tổ hợp) thay vì **định danh 1 skill**
(đơn), nên không gian cần phủ lớn hơn nhiều bậc; các MISS ở B.2 (ví dụ
{", ".join(f'`{r.child}` → `{r.parent}`' for r in b_miss[:5])}...) là ứng
viên trực tiếp để bổ sung vào `skill_implies.json` qua các script
`app/data/add_*_skills.py`, vì thiếu quan hệ kéo theo ở Layer 2 khiến JD phải
liệt kê tường minh cả framework lẫn ngôn ngữ nền thì CV mới được chấm đủ điểm
D2 — nếu JD chỉ ghi "Prisma" mà CV chỉ ghi "Node.js" (không ghi "Prisma"), hệ
thống matched đúng; nhưng chiều ngược lại (JD ghi "Node.js", CV chỉ ghi
"Prisma") sẽ MISS nếu quan hệ kéo theo chưa có trong file.

**Hạn chế của thực nghiệm này:** corpus của cả 2 phần do người viết tổng hợp
từ tri thức miền cá nhân, không phải khảo sát tần suất xuất hiện thực tế trên
CV/JD của hệ thống (ngoài phạm vi thu thập được của đồ án) — độ phủ đo được ở
đây là ước lượng có căn cứ domain, không phải số liệu production. Nếu có log
`evaluate_all_skills()` thực tế, cách đo chính xác hơn là thống kê trực tiếp
tỷ lệ `matched_layer="missing"` trên yêu cầu JD thật.

---
*Tái tạo báo cáo này: `python scripts/d2_kb_coverage_experiment.py`*
"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    write_xlsx(XLSX_PATH, {
        "Summary": summary_sheet_rows(a_rows, b_rows),
        "A - skill_data coverage": skill_data_sheet_rows(a_rows),
        "B - skill_implies coverage": implies_sheet_rows(b_rows),
    })

    print(f"Đã ghi báo cáo vào {REPORT_PATH}")
    print(f"Đã ghi Excel vào {XLSX_PATH}")
    print(f"Tổng test case: {total_cases} (A={len(a_rows)}, B={len(b_rows)})")
    print(f"PHẦN A — skill_data.json: {a_found}/{len(a_rows)} = {a_found/len(a_rows)*100:.1f}%")
    print(f"PHẦN B — skill_implies.json: {b_found}/{len(b_rows)} = {b_found/len(b_rows)*100:.1f}%")


if __name__ == "__main__":
    main()
