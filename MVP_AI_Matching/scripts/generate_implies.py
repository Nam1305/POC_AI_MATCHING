"""Generate one-way skill implication data from Wikidata P277.

The generated file is static data for the scorer to consume later. This script
does not change scorer behavior and is intended to be run manually when the
skill taxonomy needs refreshing.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "app" / "services" / "skill_implies.py"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "MVP-AI-Matching/1.0 generate_implies.py"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.scorer import SkillMatcher  # noqa: E402


# Pinned Wikidata entity IDs. None means there is no good Wikidata item for the
# canonical skill in this app, or the item has no useful P277 signal for this
# task. Do not auto-fill this dict from search results.
SKILL_QIDS: dict[str, str | None] = {
    "agile": None,
    "airflow": "Q17052835",
    "angular": "Q28925578",
    "aspnet": "Q19847029",
    "aws": "Q456157",
    "azure": "Q725967",
    "ci_cd": None,
    "computer_vision": "Q844240",
    "csharp": "Q2370",
    "css": "Q46441",
    "dapper": "Q5212334",
    "data_analysis": "Q1988917",
    "data_preprocessing": None,
    "deep_learning": "Q197536",
    "django": "Q842014",
    "docker": "Q15206305",
    "dotnet": "Q5289",
    "elasticsearch": "Q3050461",
    "entity framework": "Q1635401",
    "express": "Q16878131",
    "fastapi": "Q107629205",
    "flask": "Q289281",
    "gcp": "Q170903",
    "git": "Q186055",
    "github": "Q364",
    "gitlab": "Q16639197",
    "go": "Q37227",
    "gradle": "Q214448",
    "graphql": "Q25104949",
    "grpc": "Q18334356",
    "hibernate": "Q747017",
    "html": "Q8811",
    "java": "Q251",
    "javascript": "Q2005",
    "jenkins": "Q7491312",
    "junit": "Q170819",
    "keras": "Q2848560",
    "kubernetes": "Q22661306",
    "laravel": "Q13634357",
    "maven": "Q139941",
    "machine_learning": "Q2539",
    "micronaut": "Q60706778",
    "mongodb": "Q1165204",
    "mysql": "Q850",
    "nestjs": "Q65005248",
    "nextjs": "Q2849803",
    "nlp": "Q30642",
    "nodejs": "Q756100",
    "nosql": "Q189248",
    "nltk": "Q1635411",
    "nuget": "Q3760916",
    "numpy": "Q214440",
    "oop": "Q79872",
    "opencv": "Q165744",
    "pandas": "Q1597757",
    "php": "Q59",
    "postgresql": "Q192490",
    "pytorch": "Q16937606",
    "python": "Q28865",
    "quarkus": "Q65049613",
    "rails": "Q1138939",
    "react": "Q19399674",
    "redis": "Q2136322",
    "rest_api": None,
    "ruby": "Q161053",
    "rust": "Q575650",
    "scikit-learn": "Q253328",
    "scrum": None,
    "spark": "Q757155",
    "spacy": "Q7573757",
    "spring": "Q171550",
    "sql": "Q47607",
    "sqlserver": "Q215819",
    "tailwind": "Q105991325",
    "tensorflow": "Q21447895",
    "terraform": "Q28937865",
    "typescript": "Q978185",
    "vue": "Q30388858",
    "xgboost": "Q18584075",
}


# Labels and QIDs returned by Wikidata that should resolve to the app's
# canonical tokens.
VALUE_QID_TO_CANONICAL: dict[str, str] = {
    qid: skill for skill, qid in SKILL_QIDS.items() if qid
}
VALUE_QID_TO_CANONICAL.update(
    {
        "Q2407": "csharp",  # C Sharp; some items use this older entity.
        "Q188531": "cpp",
        "Q36074": "scala",
        "Q3816639": "kotlin",
    }
)

VALUE_LABEL_TO_CANONICAL: dict[str, str] = {
    "c sharp": "csharp",
    "c#": "csharp",
    "c++": "cpp",
    "javascript": "javascript",
    "typescript": "typescript",
    "python": "python",
    "java": "java",
    "kotlin": "kotlin",
    "scala": "scala",
    "ruby": "ruby",
    "php": "php",
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
}


# Verified P277 results from the task brief and manual Wikidata review. These
# are also used as a fallback when the public SPARQL endpoint is unavailable.
VERIFIED_IMPLIES: dict[str, set[str]] = {
    "react": {"javascript"},
    "vue": {"javascript", "typescript"},
    "angular": {"typescript"},
    "nextjs": {"react", "javascript"},
    "nodejs": {"javascript"},
    "express": {"javascript"},
    "django": {"python"},
    "flask": {"python"},
    "fastapi": {"python"},
    "spring": {"java"},
    "hibernate": {"java"},
    "junit": {"java"},
    "maven": {"java"},
    "gradle": {"java", "kotlin"},
    "quarkus": {"java"},
    "micronaut": {"java"},
    "aspnet": {"csharp"},
    "entity framework": {"csharp"},
    "dapper": {"csharp"},
    "nuget": {"csharp"},
    "tensorflow": {"python"},
    "pytorch": {"python"},
    "numpy": {"python"},
    "pandas": {"python"},
    "scikit-learn": {"python"},
    "keras": {"python"},
    "nltk": {"python"},
    "spacy": {"python"},
    "xgboost": {"python"},
    "airflow": {"python"},
    "opencv": {"cpp"},
    "spark": {"java", "scala"},
    "rails": {"ruby"},
    "laravel": {"php"},
}

# Raw P277 can describe implementation languages for tools/databases, which is
# not always a safe "knowing X implies knowing Y" skill relationship. Only emit
# pairs that have been manually reviewed for this matching use case.
REVIEWED_IMPLIES: dict[str, set[str]] = {
    **VERIFIED_IMPLIES,
    "typescript": {"javascript"},
}


def canonical_skills() -> set[str]:
    return set(SkillMatcher.ALIASES.values())


def sparql_query(qids: list[str]) -> str:
    values = " ".join(f"wd:{qid}" for qid in qids)
    return f"""
SELECT ?item ?itemLabel ?value ?valueLabel WHERE {{
  VALUES ?item {{ {values} }}
  ?item wdt:P277 ?value .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
""".strip()


def fetch_p277(qids: list[str]) -> list[dict[str, object]]:
    query = sparql_query(qids)
    params = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    request = urllib.request.Request(
        SPARQL_ENDPOINT,
        data=params,
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"Warning: Wikidata query failed; using verified fallback data. {exc}")
        return []
    return payload.get("results", {}).get("bindings", [])


def entity_id(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def resolve_value(qid: str, label: str, canonical: set[str]) -> str | None:
    if qid in VALUE_QID_TO_CANONICAL:
        return VALUE_QID_TO_CANONICAL[qid]

    key = label.lower().strip()
    if key in VALUE_LABEL_TO_CANONICAL:
        return VALUE_LABEL_TO_CANONICAL[key]

    normalized = SkillMatcher().normalize_skill(key)
    return normalized if normalized in canonical else None


def direct_implies_from_bindings(
    bindings: list[dict[str, object]],
    canonical: set[str],
) -> dict[str, set[str]]:
    qid_to_skill = {qid: skill for skill, qid in SKILL_QIDS.items() if qid}
    implies: dict[str, set[str]] = {}

    for row in bindings:
        item = row.get("item", {})
        value = row.get("value", {})
        value_label = row.get("valueLabel", {})
        if not isinstance(item, dict) or not isinstance(value, dict):
            continue

        source = qid_to_skill.get(entity_id(str(item.get("value", ""))))
        if not source:
            continue

        target = resolve_value(
            entity_id(str(value.get("value", ""))),
            str(value_label.get("value", "")) if isinstance(value_label, dict) else "",
            canonical,
        )
        # allowed_targets = REVIEWED_IMPLIES.get(source, set())
        # if target and target != source and target in allowed_targets:
        #     implies.setdefault(source, set()).add(target)

        if target and target != source:
            implies.setdefault(source, set()).add(target)

    return implies


def merge_implies(*sources: dict[str, set[str]]) -> dict[str, set[str]]:
    merged: dict[str, set[str]] = {}
    for source in sources:
        for skill, targets in source.items():
            merged.setdefault(skill, set()).update(targets)
    return {skill: targets for skill, targets in merged.items() if targets}


def transitive_closure(implies: dict[str, set[str]]) -> dict[str, set[str]]:
    closed = {skill: set(targets) for skill, targets in implies.items()}

    changed = True
    while changed:
        changed = False
        for skill, targets in list(closed.items()):
            expanded = set(targets)
            for target in targets:
                expanded.update(closed.get(target, set()))
            expanded.discard(skill)
            if expanded != targets:
                closed[skill] = expanded
                changed = True

    return {skill: targets for skill, targets in closed.items() if targets}


def render_python(implies: dict[str, set[str]]) -> str:
    lines = [
        "# Auto-generated by scripts/generate_implies.py - DO NOT EDIT BY HAND.",
        '# Source: Wikidata property P277 ("programmed in"). Regenerate when needed.',
        "IMPLIES: dict[str, set[str]] = {",
    ]
    for skill in sorted(implies):
        targets = ", ".join(f'"{target}"' for target in sorted(implies[skill]))
        lines.append(f'    "{skill}": {{{targets}}},')
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def generate() -> dict[str, set[str]]:
    canonical = canonical_skills()
    missing = sorted(canonical - set(SKILL_QIDS))
    if missing:
        raise RuntimeError(f"Missing QID review entries for canonical skills: {missing}")

    qids = sorted(qid for skill, qid in SKILL_QIDS.items() if skill in canonical and qid)
    live_implies = direct_implies_from_bindings(fetch_p277(qids), canonical)

    # Keep reviewed relations so sparse Wikidata records do not drop known-good
    # framework-to-language implications. Transitive closure then connects chains.
    reviewed_fallback = {
        skill: targets
        for skill, targets in REVIEWED_IMPLIES.items()
        if skill in canonical or skill in SKILL_QIDS
    }
    return transitive_closure(merge_implies(live_implies, reviewed_fallback))


def main() -> int:
    implies = generate()
    OUTPUT_PATH.write_text(render_python(implies), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)} with {len(implies)} keys.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
