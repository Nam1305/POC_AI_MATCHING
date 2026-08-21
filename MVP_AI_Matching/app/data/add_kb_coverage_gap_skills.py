"""Add skills/aliases/implies edges found missing by
scripts/d2_kb_coverage_experiment.py (~1000 test case/phần, xem
docs/d2_kb_coverage_experiment.md).

Nguồn dữ liệu: MISS list ở A.3 (skill_data.json — 208 miss trên 617 test case
viết tay, KHÔNG tính các case bù bằng biến thể định dạng) và B.2
(skill_implies.json — 168 miss trên 291 cặp viết tay). Mỗi entry dưới đây đã
được kiểm tra thủ công với skill_data.json HIỆN TẠI trước khi xếp loại:
  - ALIASES: tên gọi khác của 1 canonical ĐÃ CÓ SẴN (ví dụ "R Programming"
    chỉ là cách viết khác của "r" vốn đã canonical — không phải khái niệm
    mới, chỉ thiếu cầu nối định dạng).
  - CANONICAL_SKILLS: khái niệm THỰC SỰ chưa có trong skill_data.json, phần
    lớn là (a) tên dịch vụ cloud cụ thể (Amazon EC2, Azure Cosmos DB, Cloud
    Run...) — Stack Overflow chỉ tag nền tảng chung (aws/azure/gcp), không
    tag từng SKU, và (b) thư viện/công cụ hiện đại ra đời sau khi nguồn SO
    tag gốc được crawl.
  - IMPLIES: phần lớn effort thực sự nằm ở đây — rất nhiều khái niệm ở vế
    "con" ĐÃ canonical sẵn trong skill_data.json (ví dụ eslint, prettier,
    yarn, prisma, esp32, arduino, smart-contracts...), nhưng thiếu cạnh kéo
    theo sang nền tảng/ngôn ngữ nền trong skill_implies.json.

Chạy TAY, 1 lần, commit output. Sau đó PHẢI chạy `python app/data/close_implies.py`
để đóng bắc cầu (ví dụ để "azure-databricks" kéo theo cả "azure" LẪN mọi thứ
"apache-spark" đã kéo theo).

    python app/data/add_kb_coverage_gap_skills.py [--dry-run]
    python app/data/close_implies.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
SKILL_DATA_FILE = DATA_DIR / "skill_data.json"
IMPLIES_FILE = DATA_DIR / "skill_implies.json"


# ---------------------------------------------------------------------------
# ALIASES — tên gọi khác của 1 canonical ĐÃ CÓ SẴN trong skill_data.json.
# ---------------------------------------------------------------------------

ALIASES: dict[str, str] = {
    "r-programming": "r",
    "amazon-web-services": "aws",
    "microsoft-azure": "azure",
    "object-oriented-programming": "oop",
    "natural-language-processing": "nlp",
    "neural-networks": "neural-network",
    "apex-language": "apex",
    "salesforce-apex": "apex",
    "amazon-sqs": "sqs",
    "sip-protocol": "sip",
    "d-language": "d",
    "powershell-core": "powershell",
    "visual-basic-net": "vb.net",
    "tornado-web": "tornado",
    "pyyaml": "yaml",
    "karate-dsl": "karate",
    "plc-programming": "plc",
    # Bí danh nội bộ giữa 2 canonical MỚI thêm ở dưới (2 tên khác nhau cùng 1
    # dịch vụ, xuất hiện dưới 2 cách gọi khác nhau trong corpus thực nghiệm).
    "azure-functions-app": "azure-functions",
    "cloud-functions": "google-cloud-functions",
}


# ---------------------------------------------------------------------------
# CANONICAL_SKILLS — khái niệm chưa có trong skill_data.json.
# ---------------------------------------------------------------------------

CANONICAL_SKILLS: set[str] = {
    # Khái niệm/tool chung còn thiếu.
    "fastify", "dynamodb", "bigquery", "circleci", "chatgpt", "yarn",
    "web3", "edge-computing", "penetration-testing",
    "two-factor-authentication", "wix", "webflow", "pagerduty", "zeromq",
    "digitalocean", "linode", "data-lake", "redshift", "ts-node", "swc",
    "code-review", "pair-programming", "continuous-deployment",
    "fault-tolerance", "system-design", "feature-flags",
    "chaos-engineering",
    # BI / ERP / CRM.
    "sap-abap", "sap-hana", "sap-fico", "sap-mm", "oracle-netsuite",
    "zoho-crm", "hubspot", "looker", "qlik-sense", "sisense", "domo",
    "metabase", "google-data-studio", "alteryx", "knime",
    # Embedded / IoT còn thiếu (esp32/stm32/arduino/mqtt... đã canonical sẵn).
    "microcontroller-programming", "zigbee", "lorawan", "scada",
    # Blockchain còn thiếu (solidity/ethereum/smart-contracts đã canonical sẵn).
    "metamask", "nft", "defi", "ipfs",
    # AR/VR/Graphics còn thiếu.
    "3ds-max", "webxr",
    # Networking protocol còn thiếu.
    "pop3", "bgp", "ospf", "ipsec", "mpls",
    # Ngôn ngữ hiếm còn thiếu (d/vb.net/powershell/apex đã canonical -> alias).
    "nim", "crystal-lang",
    # Python — thư viện/tool chưa có (tornado/mypy/ruff/poetry đã canonical sẵn).
    "httpx", "spacy", "nltk", "gensim", "alembic", "marshmallow", "typer",
    "dash", "gradio", "black", "flake8", "luigi",
    # JS/TS — thư viện/tool chưa có.
    "zod", "yup", "dayjs", "date-fns", "swr", "recoil", "jotai",
    "framer-motion", "turborepo", "nx-monorepo", "lerna", "parcel-bundler",
    "esbuild", "solidjs", "qwik", "preact",
    # Testing còn thiếu (karate/webdriverio/mockito/k6/jmeter đã canonical sẵn).
    "katalon-studio", "chai.js", "sinon.js", "supertest",
    # Cloud service tổng quát còn thiếu (aws/azure/gcp/kubernetes đã canonical sẵn).
    "cloudformation", "aws-lambda", "azure-functions",
    "google-cloud-functions", "chakra-ui",
    # AWS — dịch vụ cụ thể (SO chỉ tag "aws" chung, không tag từng SKU).
    "amazon-ec2", "amazon-s3", "amazon-rds", "amazon-sns",
    "amazon-cloudfront", "amazon-route-53", "aws-iam", "amazon-ecs",
    "amazon-eks", "aws-fargate", "amazon-cloudwatch", "aws-codepipeline",
    "aws-codebuild", "aws-codedeploy", "amazon-kinesis", "aws-glue",
    "amazon-athena", "amazon-sagemaker", "aws-elastic-beanstalk",
    "amazon-api-gateway", "aws-step-functions", "aws-secrets-manager",
    "aws-kms", "amazon-vpc", "amazon-aurora", "amazon-elasticache",
    "amazon-cognito", "amazon-emr",
    # Azure — dịch vụ cụ thể.
    "azure-sql-database", "azure-cosmos-db", "azure-kubernetes-service",
    "azure-blob-storage", "azure-active-directory", "azure-app-service",
    "azure-data-factory", "azure-synapse-analytics", "azure-monitor",
    "azure-logic-apps", "azure-service-bus", "azure-key-vault",
    "azure-data-lake", "azure-databricks", "azure-virtual-machines",
    "azure-api-management", "azure-cognitive-services",
    "azure-machine-learning", "azure-dns", "azure-cdn",
    "azure-application-insights", "azure-service-fabric",
    "azure-notification-hubs",
    # GCP — dịch vụ cụ thể.
    "cloud-run", "cloud-storage", "compute-engine", "cloud-sql",
    "firestore", "pub-sub", "cloud-dataflow", "cloud-dataproc",
    "vertex-ai", "gke", "cloud-build", "cloud-spanner", "cloud-bigtable",
    "cloud-iam", "cloud-monitoring", "app-engine", "cloud-composer",
}


# ---------------------------------------------------------------------------
# IMPLIES — cạnh kéo theo còn thiếu. Phần lớn vế "con" đã canonical sẵn
# trong skill_data.json; script chỉ bổ sung cạnh trong skill_implies.json.
# ---------------------------------------------------------------------------

IMPLIES: dict[str, list[str]] = {
    # Đã canonical sẵn, chỉ thiếu cạnh kéo theo.
    "cocoa-touch": ["objective-c"],
    "android-jetpack-compose": ["android"],
    "cx-oracle": ["oracle-database"],
    "jdbc": ["java"],
    "prisma": ["node.js"],
    "chakra-ui": ["reactjs"],
    "eslint": ["javascript"],
    "prettier": ["javascript"],
    "yarn": ["node.js"],
    "npm": ["node.js"],
    "sequelize.js": ["node.js"],
    "mongoose": ["node.js"],
    "passport.js": ["node.js"],
    "socket.io": ["node.js"],
    "formik": ["reactjs"],
    "woocommerce": ["wordpress"],
    "elementor": ["wordpress"],
    "drupal": ["php"],
    "magento": ["php"],
    "dbt": ["sql"],
    "databricks": ["apache-spark"],
    "istio": ["kubernetes"],
    "azure-devops": ["azure"],
    "enzyme": ["reactjs"],
    "core-data": ["swift"],
    "combine": ["swift"],
    "storybook": ["javascript"],
    "vercel": ["next.js"],
    "elasticsearch": ["java"],
    "cassandra": ["java"],
    "ktor": ["kotlin"],
    "retrofit": ["java"],
    "okhttp": ["java"],
    "android-room": ["android"],
    "viewmodel": ["android"],
    "esp32": ["embedded-c"],
    "stm32": ["embedded-c"],
    "freertos": ["embedded-c"],
    "arduino": ["c++"],
    "mqtt": ["iot"],
    "raspberry-pi": ["linux"],
    "smart-contracts": ["solidity"],
    "truffle": ["solidity"],
    "hardhat": ["solidity"],
    "arkit": ["swift"],
    "arcore": ["android"],
    "godot": ["gdscript"],  # "godot-engine" là alias có sẵn của canonical "godot"
    "webxr": ["javascript"],
    "pyramid": ["python"],
    "bottle": ["python"],
    "tornado": ["python"],
    "aiohttp": ["python"],
    "spacy": ["python"],
    "nltk": ["python"],
    "gensim": ["python"],
    "dash": ["python"],
    "gradio": ["python"],
    "tanstack-query": ["reactjs"],
    "webdriverio": ["javascript"],
    "mockito": ["java"],
    "k6": ["javascript"],
    "jmeter": ["java"],
    "looker": ["sql"],
    "sqs": ["aws"],
    # Canonical mới thêm ở trên (CANONICAL_SKILLS) -> nền tảng/ngôn ngữ nền.
    "cloudformation": ["aws"],
    "aws-lambda": ["aws"],
    "azure-functions": ["azure"],
    "google-cloud-functions": ["gcp"],
    "redshift": ["aws"],
    "bigquery": ["gcp"],
    "google-data-studio": ["gcp"],
    "black": ["python"],
    "flake8": ["python"],
    "luigi": ["python"],
    "httpx": ["python"],
    "alembic": ["python"],
    "marshmallow": ["python"],
    "typer": ["python"],
    "zod": ["typescript"],
    "yup": ["javascript"],
    "dayjs": ["javascript"],
    "date-fns": ["javascript"],
    "swr": ["reactjs"],
    "recoil": ["reactjs"],
    "jotai": ["reactjs"],
    "framer-motion": ["reactjs"],
    "turborepo": ["javascript"],
    "nx-monorepo": ["javascript"],
    "lerna": ["javascript"],
    "parcel-bundler": ["javascript"],
    "esbuild": ["javascript"],
    "solidjs": ["javascript"],
    "qwik": ["javascript"],
    "preact": ["reactjs"],
    "chai.js": ["javascript"],
    "sinon.js": ["javascript"],
    "supertest": ["node.js"],
    "chatgpt": ["openai"],
    # AWS — dịch vụ cụ thể -> aws (+ kubernetes cho EKS/Fargate liên quan).
    "amazon-ec2": ["aws"],
    "amazon-s3": ["aws"],
    "amazon-rds": ["aws"],
    "amazon-sns": ["aws"],
    "amazon-cloudfront": ["aws"],
    "amazon-route-53": ["aws"],
    "aws-iam": ["aws"],
    "amazon-ecs": ["aws"],
    "amazon-eks": ["aws", "kubernetes"],
    "aws-fargate": ["aws"],
    "amazon-cloudwatch": ["aws"],
    "aws-codepipeline": ["aws"],
    "aws-codebuild": ["aws"],
    "aws-codedeploy": ["aws"],
    "amazon-kinesis": ["aws"],
    "aws-glue": ["aws"],
    "amazon-athena": ["aws"],
    "amazon-sagemaker": ["aws"],
    "aws-elastic-beanstalk": ["aws"],
    "amazon-api-gateway": ["aws"],
    "aws-step-functions": ["aws"],
    "aws-secrets-manager": ["aws"],
    "aws-kms": ["aws"],
    "amazon-vpc": ["aws"],
    "amazon-aurora": ["aws"],
    "amazon-elasticache": ["aws"],
    "amazon-cognito": ["aws"],
    "amazon-emr": ["aws"],
    # Azure — dịch vụ cụ thể -> azure (+ kubernetes/apache-spark khi liên quan).
    "azure-sql-database": ["azure"],
    "azure-cosmos-db": ["azure"],
    "azure-kubernetes-service": ["azure", "kubernetes"],
    "azure-blob-storage": ["azure"],
    "azure-active-directory": ["azure"],
    "azure-app-service": ["azure"],
    "azure-data-factory": ["azure"],
    "azure-synapse-analytics": ["azure"],
    "azure-monitor": ["azure"],
    "azure-logic-apps": ["azure"],
    "azure-service-bus": ["azure"],
    "azure-key-vault": ["azure"],
    "azure-data-lake": ["azure"],
    "azure-databricks": ["azure", "apache-spark"],
    "azure-virtual-machines": ["azure"],
    "azure-api-management": ["azure"],
    "azure-cognitive-services": ["azure"],
    "azure-machine-learning": ["azure"],
    "azure-dns": ["azure"],
    "azure-cdn": ["azure"],
    "azure-application-insights": ["azure"],
    "azure-service-fabric": ["azure"],
    "azure-notification-hubs": ["azure"],
    # GCP — dịch vụ cụ thể -> gcp (+ kubernetes/apache-spark/airflow khi liên quan).
    "cloud-run": ["gcp"],
    "cloud-storage": ["gcp"],
    "compute-engine": ["gcp"],
    "cloud-sql": ["gcp"],
    "firestore": ["gcp"],
    "pub-sub": ["gcp"],
    "cloud-dataflow": ["gcp"],
    "cloud-dataproc": ["gcp", "apache-spark"],
    "vertex-ai": ["gcp"],
    "gke": ["gcp", "kubernetes"],
    "cloud-build": ["gcp"],
    "cloud-spanner": ["gcp"],
    "cloud-bigtable": ["gcp"],
    "cloud-iam": ["gcp"],
    "cloud-monitoring": ["gcp"],
    "app-engine": ["gcp"],
    "cloud-composer": ["gcp", "airflow"],
    # BI/ERP/CRM -> nền tảng chung.
    "sap-abap": ["sap"],
    "sap-hana": ["sap"],
    "sap-fico": ["sap"],
    "sap-mm": ["sap"],
}


def is_canonical(skill_data: dict[str, str | None], name: str) -> bool:
    return name in skill_data and skill_data[name] in (None, name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    skill_data: dict[str, str | None] = json.loads(SKILL_DATA_FILE.read_text(encoding="utf-8"))
    implies: dict[str, list[str]] = json.loads(IMPLIES_FILE.read_text(encoding="utf-8"))

    added_canonical = added_aliases = added_edges = 0
    errors: list[str] = []

    for name in sorted(CANONICAL_SKILLS):
        if name not in skill_data:
            skill_data[name] = None
            added_canonical += 1
        elif not is_canonical(skill_data, name):
            errors.append(f"{name!r} exists but is not canonical: {skill_data[name]!r}")

    for alias, canonical in ALIASES.items():
        if not is_canonical(skill_data, canonical):
            errors.append(f"alias target {canonical!r} (from {alias!r}) is not canonical")
        elif alias not in skill_data:
            skill_data[alias] = canonical
            added_aliases += 1
        elif skill_data[alias] != canonical and not (alias == canonical):
            errors.append(
                f"alias {alias!r} already exists with different value {skill_data[alias]!r} "
                f"(wanted -> {canonical!r})"
            )

    for source, targets in IMPLIES.items():
        if not is_canonical(skill_data, source):
            errors.append(f"implies source {source!r} is not canonical")
            continue
        for target in targets:
            if not is_canonical(skill_data, target):
                errors.append(f"implies target {target!r} (from {source!r}) is not canonical")

    if errors:
        print(f"Data invariant errors ({len(errors)}); no files written:")
        for error in errors:
            print(f"  {error}")
        return 1

    for source, targets in IMPLIES.items():
        current = implies.setdefault(source, [])
        for target in targets:
            if target not in current:
                current.append(target)
                added_edges += 1

    print(
        f"Thêm: {added_canonical} canonical, {added_aliases} alias, "
        f"{added_edges} implies-edge"
    )

    if args.dry_run:
        print("[dry-run] không ghi.")
        return 0

    SKILL_DATA_FILE.write_text(json.dumps(skill_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    IMPLIES_FILE.write_text(json.dumps(implies, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Đã ghi. NHỚ chạy: python app/data/close_implies.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
