"""Generate one-way skill implication data from Wikidata P277.

Flow:
1. Read canonical skills from SkillMatcher.ALIASES.
2. Use manually pinned QIDs as initial seed entities.
3. Query Wikidata P277 in batches.
4. Discover target QIDs automatically.
5. Read source type information through P31/P279.
6. Filter source categories that create semantic noise.
7. Keep only relations whose targets belong to app skill vocabulary.
8. Query canonical target QIDs in the next round.
9. Compute transitive closure.
10. Write all canonical skills to IMPLIES, including empty sets.

This script only generates static data.
It does not modify scorer behavior.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_PATH = (
    PROJECT_ROOT
    / "app"
    / "services"
    / "skill_implies.py"
)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

USER_AGENT = "MVP-AI-Matching/1.0 generate_implies.py"


# Round 1:
# Query all initial pinned QIDs.
#
# Round 2:
# Query newly discovered target QIDs
# if they belong to current canonical skill vocabulary.
MAX_ROUNDS = 2

MAX_RETRIES = 3

RETRY_DELAY_SECONDS = 3

# A source with more than this many distinct direct P277 targets is treated
# as polyglot/ambiguous and dropped entirely rather than partially trusted.
# IMPLIES grants FULL match credit, which is only justified when the base
# language is a guaranteed fact (react -> javascript). Libraries with many
# language bindings (spark -> java/python/r/scala/sql, xgboost ->
# java/python/ruby) don't have one certain base language — most real users
# only know ONE of those, so keeping all of them would produce false
# positives. Verified empirically: every legitimate single-ecosystem
# framework in this vocabulary has <=2 direct P277 targets.
MAX_DIRECT_TARGETS = 2


# ============================================================
# IMPORT PROJECT MODULE
# ============================================================

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.services.scorer import SkillMatcher  # noqa: E402


# ============================================================
# SKILL -> QID
#
# GIỮ NGUYÊN DICT SKILL_QIDS ĐÃ VERIFY CỦA BẠN Ở ĐÂY.
# ============================================================

SKILL_QIDS: dict[str, str | None] = {
    "agile": None,
    "airflow": "Q28915062",
    "angular": "Q28925578",
    "aspnet": "Q17513350",
    "aws": "Q456157",
    "azure": "Q725967",
    "ci_cd": None,
    "computer_vision": "Q844240",
    "csharp": "Q2370",
    "css": "Q46441",
    "dapper": "Q5221802",
    "data_analysis": "Q1988917",
    "data_preprocessing": None,
    "deep_learning": "Q197536",
    "django": "Q842014",
    "docker": "Q15206305",
    "dotnet": "Q21622213",
    "elasticsearch": "Q3050461",
    "entity framework": "Q851939",
    "express": "Q16878131",
    "fastapi": "Q101119404",
    "flask": "Q289281",
    "gcp": "Q17054505",
    "git": "Q186055",
    "github": "Q364",
    "gitlab": "Q16639197",
    "go": "Q37227",
    "gradle": "Q965596",
    "graphql": "Q25104949",
    "grpc": "Q26356541",
    "hibernate": "Q747866",
    "html": "Q8811",
    "java": "Q251",
    "javascript": "Q2005",
    "jenkins": "Q7491312",
    "junit": "Q847675",
    "keras": "Q28470421",
    "kubernetes": "Q22661306",
    "laravel": "Q13634357",
    "maven": "Q139941",
    "machine_learning": "Q2539",
    "micronaut": "Q110912899",
    "mongodb": "Q1165204",
    "mysql": "Q850",
    "nestjs": "Q107015664",
    "nextjs": "Q56062435",
    "nlp": "Q30642",
    "nodejs": "Q756100",
    "nosql": "Q82231",
    "nltk": "Q1635410",
    "nuget": "Q975870",
    "numpy": "Q197520",
    "oop": "Q79872",
    "opencv": "Q165277",
    "pandas": "Q15967387",
    "php": "Q59",
    "postgresql": "Q192490",
    "pytorch": "Q47509047",
    "python": "Q28865",
    "quarkus": "Q98139844",
    "rails": "Q190478",
    "react": "Q19399674",
    "redis": "Q2136322",
    "rest_api": None,
    "ruby": "Q161053",
    "rust": "Q575650",
    "scikit-learn": "Q1026367",
    "scrum": None,
    "spark": "Q7573619",
    "spacy": "Q28406945",
    "spring": "Q720314",
    "sql": "Q47607",
    "sqlserver": "Q215819",
    "tailwind": "Q102173844",
    "tensorflow": "Q21447895",
    "terraform": "Q28957072",
    "typescript": "Q978185",
    "vue": "Q24589705",
    "xgboost": "Q23793561",
}


# ============================================================
# SOURCE TYPE FILTERING
#
# Không blacklist từng relation:
#
# docker -> go
# mysql -> cpp
#
# Thay vào đó, loại theo category của source.
# ============================================================

BLOCKED_SOURCE_TYPE_TERMS: tuple[str, ...] = (
    # Database — "database" alone is too broad (matches "database abstraction
    # layer" e.g. Entity Framework, which is NOT a database). Use specific
    # phrases only, verified against real Wikidata P31/P279 labels.
    "database management system",
    "relational database management system",
    "document-oriented database",
    "key-value database",
    "nosql database",

    # Search infrastructure
    "search engine",

    # Container / infrastructure — verified real Wikidata labels (the earlier
    # guessed terms like "containerization software"/"container orchestration"
    # did not match actual labels and let docker/kubernetes/terraform leak
    # "go" through as a false implied relation).
    "container runtime",
    "container orchestrator",
    "container platform",
    "infrastructure automation software",
    "infrastructure provisioning tool",

    # Version control
    "version control system",
    "revision control system",

    # CI/CD infrastructure
    "continuous integration software",
    "continuous integration tool",
    "continuous delivery software",

    # Hosting / forge platforms — verified real Wikidata labels (GitLab's
    # actual P31/P279 chain uses "forge"/"internet hosting service", not the
    # earlier guessed "software forge"/"source code hosting service", so it
    # leaked through as a false "gitlab -> ruby" implied relation).
    "forge",
    "internet hosting service",
    "repository hosting service",
    "bug tracking system",
    "issue tracking system",
    "code hosting platform",
    "devops platform",

    # Cloud infrastructure
    "cloud computing platform",

    # OS
    "operating system",
)


# ============================================================
# SPECIAL LABEL NORMALIZATION
#
# Đây chỉ là normalization tên.
# Không phải map relation.
# ============================================================

SPECIAL_LABEL_NORMALIZATION: dict[str, str] = {
    "c#": "csharp",
    "c sharp": "csharp",
    "c++": "cpp",
    "react.js": "react",
    "reactjs": "react",
}


# ============================================================
# CANONICAL SKILLS
# ============================================================

def canonical_skills() -> set[str]:
    """Return canonical skill tokens from SkillMatcher.ALIASES."""

    return set(
        SkillMatcher.ALIASES.values()
    )


# ============================================================
# INITIAL QID -> CANONICAL
# ============================================================

def build_initial_qid_to_canonical(
    canonical: set[str],
) -> dict[str, str]:
    """Build QID -> canonical token mapping for pinned skills."""

    matcher = SkillMatcher()

    result: dict[str, str] = {}

    for skill, qid in SKILL_QIDS.items():

        if qid is None:
            continue

        normalized = matcher.normalize_skill(
            skill
        )

        if normalized in canonical:
            result[qid] = normalized
        elif skill in canonical:
            result[qid] = skill
        else:
            # Keep the configured name for logging,
            # but it will not enter final IMPLIES unless
            # it belongs to canonical vocabulary.
            result[qid] = skill

    return result


# ============================================================
# BASIC HELPERS
# ============================================================

def entity_id(uri: str) -> str:
    """Extract QID from a Wikidata entity URI."""

    return uri.rsplit("/", 1)[-1]


def binding_value(
    row: dict[str, object],
    field_name: str,
) -> str:
    """Safely read one SPARQL binding value."""

    field = row.get(
        field_name,
        {},
    )

    if not isinstance(field, dict):
        return ""

    return str(
        field.get(
            "value",
            "",
        )
    )


def is_qid(value: str) -> bool:
    """Return True when value looks like Q12345."""

    return bool(
        re.fullmatch(
            r"Q\d+",
            value.strip(),
            re.IGNORECASE,
        )
    )


def save_label(
    labels: dict[str, str],
    qid: str,
    label: str,
) -> None:
    """Save only useful human-readable labels."""

    clean_label = label.strip()

    if not clean_label:
        return

    # Prevent:
    #
    # Q15777 -> "Q15777"
    if is_qid(clean_label):
        return

    current_label = labels.get(qid)

    if (
        not current_label
        or is_qid(current_label)
    ):
        labels[qid] = clean_label


# ============================================================
# SOURCE TYPE HELPERS
# ============================================================

def parse_source_types(
    raw_types: str,
) -> set[str]:
    """Parse GROUP_CONCAT source type labels."""

    if not raw_types:
        return set()

    return {
        item.strip()
        for item in raw_types.split("|||")
        if item.strip()
    }


def blocked_source_reason(
    source_types: set[str],
) -> str | None:
    """Return the blocked type term if source should be filtered."""

    for source_type in source_types:

        normalized_type = (
            source_type
            .lower()
            .strip()
        )

        for blocked_term in BLOCKED_SOURCE_TYPE_TERMS:

            if blocked_term in normalized_type:
                return blocked_term

    return None


# ============================================================
# SPARQL QUERY
# ============================================================

def sparql_query(
    qids: list[str],
) -> str:
    """Build batch P277 query with source type metadata."""

    values = " ".join(
        f"wd:{qid}"
        for qid in qids
    )

    return f"""
SELECT
    ?item
    ?itemLabel
    ?value
    ?valueLabel
    (
        GROUP_CONCAT(
            DISTINCT ?sourceTypeLabel;
            separator="|||"
        )
        AS ?sourceTypes
    )
WHERE {{
    VALUES ?item {{
        {values}
    }}

    ?item wdt:P277 ?value .

    OPTIONAL {{
        ?item wdt:P31/wdt:P279* ?sourceType .

        ?sourceType rdfs:label ?sourceTypeLabel .

        FILTER(
            LANG(?sourceTypeLabel) = "en"
        )
    }}

    OPTIONAL {{
        ?item rdfs:label ?itemLabel .

        FILTER(
            LANG(?itemLabel) = "en"
        )
    }}

    OPTIONAL {{
        ?value rdfs:label ?valueLabel .

        FILTER(
            LANG(?valueLabel) = "en"
        )
    }}
}}
GROUP BY
    ?item
    ?itemLabel
    ?value
    ?valueLabel
""".strip()


# ============================================================
# FETCH WIKIDATA
# ============================================================

def fetch_p277(
    qids: list[str],
) -> list[dict[str, object]]:
    """Fetch P277 data from Wikidata with retry."""

    if not qids:
        return []

    query = sparql_query(qids)

    params = urllib.parse.urlencode(
        {
            "query": query,
            "format": "json",
        }
    ).encode()

    last_error: Exception | None = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        request = urllib.request.Request(
            SPARQL_ENDPOINT,
            data=params,
            headers={
                "Accept": (
                    "application/"
                    "sparql-results+json"
                ),
                "Content-Type": (
                    "application/"
                    "x-www-form-urlencoded"
                ),
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=90,
            ) as response:

                payload = json.loads(
                    response
                    .read()
                    .decode("utf-8")
                )

                return (
                    payload
                    .get("results", {})
                    .get("bindings", [])
                )

        except (
            urllib.error.URLError,
            TimeoutError,
        ) as exc:

            last_error = exc

            print(
                f"[Retry {attempt}/{MAX_RETRIES}] "
                f"Wikidata query failed: {exc}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(
                    RETRY_DELAY_SECONDS
                )

    raise RuntimeError(
        "Wikidata SPARQL query failed after "
        f"{MAX_RETRIES} attempts."
    ) from last_error


# ============================================================
# NORMALIZE LABEL
# ============================================================

def normalize_label(
    label: str,
) -> str | None:
    """Convert Wikidata label into normalized skill token."""

    if not label:
        return None

    key = (
        label
        .strip()
        .lower()
    )

    if not key:
        return None

    # Never convert:
    #
    # Q15777 -> q15777
    if is_qid(key):
        return None

    if key in SPECIAL_LABEL_NORMALIZATION:
        return SPECIAL_LABEL_NORMALIZATION[key]

    matcher = SkillMatcher()

    normalized = matcher.normalize_skill(
        key
    )

    if normalized:

        normalized = (
            normalized
            .strip()
            .lower()
        )

        if (
            normalized
            and not is_qid(normalized)
        ):
            return normalized

    fallback = re.sub(
        r"[^a-z0-9]+",
        "_",
        key,
    ).strip("_")

    if not fallback:
        return None

    if re.fullmatch(
        r"q\d+",
        fallback,
        re.IGNORECASE,
    ):
        return None

    return fallback


# ============================================================
# MULTI-ROUND DISCOVERY
# ============================================================

def discover_p277_graph(
    initial_qids: list[str],
    canonical: set[str],
    initial_qid_to_canonical: dict[str, str],
    max_rounds: int = MAX_ROUNDS,
) -> tuple[
    dict[str, set[str]],
    dict[str, str],
    int,
    dict[str, str],
]:
    """Discover and filter P277 graph."""

    qid_graph: dict[str, set[str]] = {}

    labels: dict[str, str] = {}

    queried_qids: set[str] = set()

    frontier: set[str] = set(
        initial_qids
    )

    raw_binding_count = 0

    # source QID -> blocked reason
    blocked_sources: dict[str, str] = {}

    for round_number in range(
        1,
        max_rounds + 1,
    ):

        current_batch = sorted(
            frontier - queried_qids
        )

        if not current_batch:

            print(
                f"\n[Round {round_number}] "
                "No new QIDs. Stop."
            )

            break

        print(
            f"\n[Round {round_number}] "
            f"Querying {len(current_batch)} QIDs..."
        )

        bindings = fetch_p277(
            current_batch
        )

        raw_binding_count += len(
            bindings
        )

        queried_qids.update(
            current_batch
        )

        next_frontier: set[str] = set()

        for row in bindings:

            source_uri = binding_value(
                row,
                "item",
            )

            target_uri = binding_value(
                row,
                "value",
            )

            if (
                not source_uri
                or not target_uri
            ):
                continue

            source_qid = entity_id(
                source_uri
            )

            target_qid = entity_id(
                target_uri
            )

            source_label = binding_value(
                row,
                "itemLabel",
            )

            target_label = binding_value(
                row,
                "valueLabel",
            )

            raw_source_types = binding_value(
                row,
                "sourceTypes",
            )

            source_types = parse_source_types(
                raw_source_types
            )

            save_label(
                labels,
                source_qid,
                source_label,
            )

            save_label(
                labels,
                target_qid,
                target_label,
            )

            # =================================================
            # FILTER SOURCE BY TYPE
            # =================================================

            block_reason = blocked_source_reason(
                source_types
            )

            if block_reason:

                blocked_sources[source_qid] = (
                    block_reason
                )

                continue

            # =================================================
            # RESOLVE TARGET TOKEN
            # =================================================

            target_token = (
                initial_qid_to_canonical.get(
                    target_qid
                )
            )

            if not target_token:

                target_token = normalize_label(
                    target_label
                )

            # =================================================
            # ONLY KEEP TARGETS IN CANONICAL VOCABULARY
            #
            # Prevent:
            #
            # react -> jsx
            # git -> tcl
            #
            # unless those tokens actually belong to ALIASES.
            # =================================================

            if (
                not target_token
                or target_token not in canonical
            ):
                continue

            # =================================================
            # KEEP DIRECT EDGE
            # =================================================

            qid_graph.setdefault(
                source_qid,
                set(),
            ).add(
                target_qid
            )

            # =================================================
            # NEXT ROUND
            # =================================================

            if target_qid not in queried_qids:

                next_frontier.add(
                    target_qid
                )

        print(
            f"[Round {round_number}] "
            f"Raw bindings: {len(bindings)}"
        )

        print(
            f"[Round {round_number}] "
            f"Next-round canonical QIDs: "
            f"{len(next_frontier)}"
        )

        frontier = next_frontier

    return (
        qid_graph,
        labels,
        raw_binding_count,
        blocked_sources,
    )


# ============================================================
# BUILD QID -> TOKEN
# ============================================================

def build_qid_to_token(
    labels: dict[str, str],
    initial_qid_to_canonical: dict[str, str],
) -> dict[str, str]:
    """Build QID -> skill token resolver."""

    qid_to_token = dict(
        initial_qid_to_canonical
    )

    for qid, label in labels.items():

        if qid in qid_to_token:
            continue

        token = normalize_label(
            label
        )

        if token:
            qid_to_token[qid] = token

    return qid_to_token


# ============================================================
# QID GRAPH -> SKILL GRAPH
# ============================================================

def qid_graph_to_skill_graph(
    qid_graph: dict[str, set[str]],
    qid_to_token: dict[str, str],
    canonical: set[str],
) -> dict[str, set[str]]:
    """Convert QID graph into canonical skill graph."""

    skill_graph: dict[str, set[str]] = {}

    for source_qid, target_qids in (
        qid_graph.items()
    ):

        source = qid_to_token.get(
            source_qid
        )

        if (
            not source
            or source not in canonical
        ):
            continue

        for target_qid in target_qids:

            target = qid_to_token.get(
                target_qid
            )

            if (
                not target
                or target not in canonical
            ):
                continue

            if source == target:
                continue

            skill_graph.setdefault(
                source,
                set(),
            ).add(
                target
            )

    return skill_graph


# ============================================================
# AMBIGUITY FILTER — drop polyglot sources
# ============================================================

def filter_ambiguous_sources(
    graph: dict[str, set[str]],
    max_targets: int = MAX_DIRECT_TARGETS,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Drop sources with too many distinct direct targets (polyglot
    libraries with no single certain base language). Returns
    (kept_graph, dropped_graph) for logging."""

    kept: dict[str, set[str]] = {}
    dropped: dict[str, set[str]] = {}

    for source, targets in graph.items():

        if len(targets) <= max_targets:
            kept[source] = targets
        else:
            dropped[source] = targets

    return kept, dropped


# ============================================================
# TRANSITIVE CLOSURE
# ============================================================

def transitive_closure(
    graph: dict[str, set[str]],
) -> dict[str, set[str]]:
    """Compute one-way transitive closure."""

    closed = {
        source: set(targets)
        for source, targets
        in graph.items()
    }

    changed = True

    while changed:

        changed = False

        for source, targets in list(
            closed.items()
        ):

            expanded = set(
                targets
            )

            for target in targets:

                expanded.update(
                    closed.get(
                        target,
                        set(),
                    )
                )

            expanded.discard(
                source
            )

            if expanded != targets:

                closed[source] = expanded

                changed = True

    return closed


# ============================================================
# ENSURE ALL CANONICAL SKILLS EXIST
# ============================================================

def complete_skill_graph(
    graph: dict[str, set[str]],
    canonical: set[str],
) -> dict[str, set[str]]:
    """Return every canonical skill, including empty relations."""

    complete: dict[str, set[str]] = {
        skill: set()
        for skill in canonical
    }

    for source, targets in graph.items():

        if source not in complete:
            continue

        complete[source].update(
            target
            for target in targets
            if (
                target in canonical
                and target != source
            )
        )

    return complete


# ============================================================
# LOGGING
# ============================================================

def print_direct_edges(
    graph: dict[str, set[str]],
) -> None:
    """Print accepted direct edges."""

    print(
        "\n========== ACCEPTED DIRECT EDGES =========="
    )

    if not graph:
        print("  None")
        return

    for source in sorted(graph):

        for target in sorted(
            graph[source]
        ):

            print(
                f"  {source} -> {target}"
            )


def print_blocked_sources(
    blocked_sources: dict[str, str],
    qid_to_token: dict[str, str],
) -> None:
    """Print filtered source technologies."""

    print(
        "\n========== BLOCKED SOURCES =========="
    )

    if not blocked_sources:
        print("  None")
        return

    for qid, reason in sorted(
        blocked_sources.items()
    ):

        source = qid_to_token.get(
            qid,
            qid,
        )

        print(
            f"  {source} "
            f"[reason: {reason}]"
        )


# ============================================================
# RENDER OUTPUT
# ============================================================

def render_python(
    implies: dict[str, set[str]],
) -> str:
    """Render deterministic Python output."""

    lines = [
        (
            "# Auto-generated by "
            "scripts/generate_implies.py "
            "- DO NOT EDIT BY HAND."
        ),
        (
            '# Source: Wikidata property P277 '
            '("programmed in"). '
            "Regenerate when needed."
        ),
        "",
        "IMPLIES: dict[str, set[str]] = {",
    ]

    for skill in sorted(
        implies
    ):

        targets = sorted(
            implies[skill]
        )

        if targets:

            target_text = ", ".join(
                f'"{target}"'
                for target in targets
            )

            lines.append(
                f'    "{skill}": '
                f'{{{target_text}}},'
            )

        else:

            # Important:
            #
            # {} is dict, not set.
            #
            # Empty set must be set().
            lines.append(
                f'    "{skill}": set(),'
            )

    lines.append("}")
    lines.append("")

    return "\n".join(
        lines
    )


# ============================================================
# GENERATE
# ============================================================

def generate() -> dict[str, set[str]]:
    """Generate final complete IMPLIES graph."""

    canonical = canonical_skills()

    initial_qid_to_canonical = (
        build_initial_qid_to_canonical(
            canonical
        )
    )

    # Query every pinned QID.
    initial_qids = sorted(
        {
            qid
            for qid in SKILL_QIDS.values()
            if qid is not None
        }
    )

    unmapped_skills = sorted(
        skill
        for skill in canonical
        if SKILL_QIDS.get(skill) is None
    )

    print(
        "========== INPUT =========="
    )

    print(
        f"Canonical skills: "
        f"{len(canonical)}"
    )

    print(
        f"Pinned QIDs queried: "
        f"{len(initial_qids)}"
    )

    print(
        f"Canonical skills without QID: "
        f"{len(unmapped_skills)}"
    )

    for skill in unmapped_skills:
        print(
            f"  - {skill}"
        )

    # ========================================================
    # DISCOVER
    # ========================================================

    (
        direct_qid_graph,
        labels,
        raw_binding_count,
        blocked_sources,
    ) = discover_p277_graph(
        initial_qids=initial_qids,
        canonical=canonical,
        initial_qid_to_canonical=(
            initial_qid_to_canonical
        ),
        max_rounds=MAX_ROUNDS,
    )

    if raw_binding_count == 0:

        raise RuntimeError(
            "Wikidata returned no P277 bindings. "
            "Output file was not overwritten."
        )

    # ========================================================
    # RESOLVE TOKENS
    # ========================================================

    qid_to_token = build_qid_to_token(
        labels=labels,
        initial_qid_to_canonical=(
            initial_qid_to_canonical
        ),
    )

    # ========================================================
    # DIRECT SKILL GRAPH
    # ========================================================

    direct_skill_graph = (
        qid_graph_to_skill_graph(
            qid_graph=direct_qid_graph,
            qid_to_token=qid_to_token,
            canonical=canonical,
        )
    )

    print_direct_edges(
        direct_skill_graph
    )

    print_blocked_sources(
        blocked_sources,
        qid_to_token,
    )

    # ========================================================
    # AMBIGUITY FILTER
    # ========================================================

    unambiguous_skill_graph, dropped_ambiguous = (
        filter_ambiguous_sources(
            direct_skill_graph
        )
    )

    print(
        "\n========== DROPPED (POLYGLOT / AMBIGUOUS) =========="
    )

    if not dropped_ambiguous:
        print("  None")
    else:
        for source in sorted(dropped_ambiguous):
            targets = ", ".join(sorted(dropped_ambiguous[source]))
            print(f"  {source} -> {{{targets}}}")

    # ========================================================
    # TRANSITIVE CLOSURE
    # ========================================================

    closed_skill_graph = (
        transitive_closure(
            unambiguous_skill_graph
        )
    )

    # ========================================================
    # ADD EMPTY SETS FOR ALL SKILLS
    # ========================================================

    final_implies = complete_skill_graph(
        graph=closed_skill_graph,
        canonical=canonical,
    )

    direct_relation_count = sum(
        len(targets)
        for targets
        in direct_skill_graph.values()
    )

    final_relation_count = sum(
        len(targets)
        for targets
        in final_implies.values()
    )

    empty_skill_count = sum(
        1
        for targets in final_implies.values()
        if not targets
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print(
        "\n========== SUMMARY =========="
    )

    print(
        f"Raw P277 bindings: "
        f"{raw_binding_count}"
    )

    print(
        f"Blocked source entities: "
        f"{len(blocked_sources)}"
    )

    print(
        f"Accepted direct relations: "
        f"{direct_relation_count}"
    )

    print(
        f"Final IMPLIES skills: "
        f"{len(final_implies)}"
    )

    print(
        f"Skills with empty relations: "
        f"{empty_skill_count}"
    )

    print(
        f"Final relations after closure: "
        f"{final_relation_count}"
    )

    return final_implies


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    """Generate and write skill_implies.py."""

    implies = generate()

    content = render_python(
        implies
    )

    OUTPUT_PATH.write_text(
        content,
        encoding="utf-8",
    )

    print(
        "\nWrote: "
        f"{OUTPUT_PATH.relative_to(PROJECT_ROOT)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )