"""Add current DevOps, IT support/help desk, and QA/testing skills.

The migration is idempotent. It adds only conservative implication edges,
such as an implementation tool to its direct practice or framework.

Run from the repository root:
    python3 app/data/add_devops_support_qa_skills.py
    python3 app/data/close_implies.py
"""

from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path(__file__).parent
SKILL_DATA_FILE = DATA_DIR / "skill_data.json"
IMPLIES_FILE = DATA_DIR / "skill_implies.json"

CANONICAL_SKILLS: set[str] = {
    # DevOps, platform engineering, and observability.
    "argocd",
    "ci-cd",
    "cloud-engineering",
    "containerization",
    "devsecops",
    "fluxcd",
    "github-actions",
    "gitops",
    "gitlab-ci",
    "gcp",
    "infrastructure-as-code",
    "linkerd",
    "loki",
    "monitoring",
    "new-relic",
    "network-management",
    "observability",
    "opentelemetry",
    "opentofu",
    "packer",
    "platform-engineering",
    "tekton",
    "tempo",
    "terraform-cloud",
    "trivy",
    "vault",
    "vulnerability-management",
    # IT support, help desk, endpoint management, and ITSM.
    "anydesk",
    "asset-management",
    "change-management",
    "dhcp",
    "endpoint-management",
    "freshservice",
    "help-desk",
    "incident-management",
    "intune",
    "itil",
    "itil-4",
    "itsm",
    "jamf",
    "jira-service-management",
    "knowledge-base",
    "microsoft-entra-id",
    "problem-management",
    "remote-support",
    "service-desk",
    "sla",
    "snyk",
    "teamviewer",
    "ticket-management",
    "zendesk",
    # QA, test engineering, and current automation tooling.
    "accessibility-testing",
    "behave",
    "browserstack",
    "burp-suite",
    "chaos-testing",
    "contract-testing",
    "cross-browser-testing",
    "detox",
    "exploratory-testing",
    "insomnia",
    "maestro",
    "newman",
    "owasp-zap",
    "pact",
    "qa-engineer",
    "regression-testing",
    "robot-framework",
    "saucelabs",
    "sdet",
    "security-testing",
    "smoke-testing",
    "test-case-management",
    "test-management",
    "test-planning",
    "visual-regression-testing",
}

ALIASES: dict[str, str] = {
    "argo-cd": "argocd",
    "azure-ad": "microsoft-entra-id",
    "azure-devops": "devops",
    "ci/cd": "ci-cd",
    "continuous-integration": "ci-cd",
    "dev-sec-ops": "devsecops",
    "end-to-end-testing": "e2e-testing",
    "e2e": "e2e-testing",
    "github-action": "github-actions",
    "github-workflows": "github-actions",
    "gitlab-cicd": "gitlab-ci",
    "google-cloud-platform": "gcp",
    "grafana-loki": "loki",
    "helpdesk": "help-desk",
    "incident-response": "incident-management",
    "infrastructure-as-code-iac": "infrastructure-as-code",
    "it-help-desk": "it-helpdesk",
    "it-service-management": "itsm",
    "itil4": "itil-4",
    "jamf-pro": "jamf",
    "jenkins": "jenkins-ci",
    "jira-service-desk": "jira-service-management",
    "new-relic-observability": "new-relic",
    "office-365": "microsoft-365",
    "open-telemetry": "opentelemetry",
    "open-tofu": "opentofu",
    "qa-engineering": "qa-engineer",
    "robotframework": "robot-framework",
    "sauce-labs": "saucelabs",
    "sre": "sre",
    "test-automation": "automation-testing",
    "test-rail": "test-management",
    "testautomation": "automation-testing",
    "web-accessibility-testing": "accessibility-testing",
    "zap": "owasp-zap",
}

IMPLIES: dict[str, list[str]] = {
    # DevOps and platform engineering.
    "argocd": ["kubernetes", "gitops"],
    "ci-cd": ["devops"],
    "containerization": ["docker"],
    "datadog": ["observability"],
    "devsecops": ["devops"],
    "fluxcd": ["kubernetes", "gitops"],
    "github-actions": ["github", "ci-cd"],
    "gitlab-ci": ["gitlab", "ci-cd"],
    "kubernetes-helm": ["kubernetes"],
    "infrastructure-as-code": ["devops"],
    "jenkins-ci": ["ci-cd"],
    "linkerd": ["kubernetes"],
    "loki": ["observability", "logging"],
    "new-relic": ["observability"],
    "observability": ["monitoring"],
    "opentelemetry": ["observability"],
    "opentofu": ["terraform"],
    "prometheus": ["monitoring"],
    "grafana": ["monitoring"],
    "tekton": ["kubernetes", "ci-cd"],
    "tempo": ["observability"],
    "terraform": ["infrastructure-as-code"],
    "trivy": ["devsecops", "vulnerability-management"],
    "snyk": ["devsecops", "vulnerability-management"],
    # IT support and IT service management.
    "anydesk": ["remote-support"],
    "change-management": ["itsm"],
    "dhcp": ["network-management"],
    "endpoint-management": ["mdm"],
    "freshservice": ["itsm"],
    "help-desk": ["it-helpdesk", "it-support"],
    "incident-management": ["itsm"],
    "intune": ["mdm", "microsoft-365"],
    "it-helpdesk": ["it-support"],
    "itil": ["itsm"],
    "itil-4": ["itil"],
    "jamf": ["mdm"],
    "jira-service-management": ["itsm", "jira"],
    "problem-management": ["itsm"],
    "remote-support": ["remote-desktop"],
    "service-desk": ["it-helpdesk", "itsm"],
    "teamviewer": ["remote-support"],
    "ticket-management": ["it-helpdesk"],
    "zendesk": ["ticket-management"],
    # QA and testing practices/tools.
    "accessibility-testing": ["testing"],
    "allure": ["testing"],
    "appium": ["automation-testing"],
    "behave": ["python", "bdd"],
    "browserstack": ["cross-browser-testing"],
    "burp-suite": ["security-testing"],
    "chaos-testing": ["testing"],
    "contract-testing": ["testing"],
    "cross-browser-testing": ["testing"],
    "cucumber": ["bdd"],
    "detox": ["automation-testing", "mobile-testing"],
    "exploratory-testing": ["testing"],
    "insomnia": ["api-testing"],
    "karate": ["api-testing"],
    "maestro": ["automation-testing", "mobile-testing"],
    "manual-testing": ["testing"],
    "newman": ["api-testing", "postman"],
    "owasp-zap": ["security-testing"],
    "pact": ["contract-testing"],
    "qa-engineer": ["qa", "testing"],
    "regression-testing": ["testing"],
    "robot-framework": ["python", "automation-testing"],
    "saucelabs": ["cross-browser-testing"],
    "sdet": ["automation-testing", "testing"],
    "selenium-webdriver": ["automation-testing"],
    "smoke-testing": ["testing"],
    "test-case-management": ["test-management"],
    "test-case-design": ["testing"],
    "test-management": ["testing"],
    "test-planning": ["testing"],
    "testcontainers": ["docker"],
    "visual-regression-testing": ["testing"],
}


def is_canonical(skill_data: dict[str, str | None], name: str) -> bool:
    return name in skill_data and skill_data[name] in (None, name)


def main() -> int:
    skill_data: dict[str, str | None] = json.loads(
        SKILL_DATA_FILE.read_text(encoding="utf-8")
    )
    implies: dict[str, list[str]] = json.loads(
        IMPLIES_FILE.read_text(encoding="utf-8")
    )

    added_canonical = added_aliases = added_edges = added_equivalences = 0
    errors: list[str] = []
    existing_canonical_aliases: list[tuple[str, str]] = []

    for name in sorted(CANONICAL_SKILLS):
        if name not in skill_data:
            skill_data[name] = None
            added_canonical += 1
        elif not is_canonical(skill_data, name):
            errors.append(f"{name!r} exists but is not canonical: {skill_data[name]!r}")

    for alias, canonical in ALIASES.items():
        if not is_canonical(skill_data, canonical):
            errors.append(f"alias target {canonical!r} is not canonical")
        elif alias not in skill_data:
            skill_data[alias] = canonical
            added_aliases += 1
        elif alias != canonical and is_canonical(skill_data, alias):
            # Keep old Stack Overflow canonicals, but make their equivalence
            # explicit so they inherit the modern skill's implications.
            existing_canonical_aliases.append((alias, canonical))

    for source, targets in IMPLIES.items():
        if not is_canonical(skill_data, source):
            errors.append(f"implies source {source!r} is not canonical")
            continue
        for target in targets:
            if not is_canonical(skill_data, target):
                errors.append(f"implies target {target!r} is not canonical")

    if errors:
        print("Data invariant errors; no files written:")
        for error in errors:
            print(f"  {error}")
        return 1

    for source, targets in IMPLIES.items():
        current = implies.setdefault(source, [])
        for target in targets:
            if target not in current:
                current.append(target)
                added_edges += 1

    for old_canonical, canonical in existing_canonical_aliases:
        current = implies.setdefault(old_canonical, [])
        if canonical not in current:
            current.append(canonical)
            added_equivalences += 1

    SKILL_DATA_FILE.write_text(
        json.dumps(skill_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    IMPLIES_FILE.write_text(
        json.dumps(implies, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "Added "
        f"{added_canonical} canonical skills, {added_aliases} aliases, "
        f"{added_edges} implication edges, and {added_equivalences} "
        "canonical-equivalence edges."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
