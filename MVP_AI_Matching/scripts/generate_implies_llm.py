"""Generate the skill-implication graph (IMPLIES) with an LLM — option B.

Semantics of an edge  X -> Y :
    "Anyone who can legitimately claim X on their CV necessarily has working
     knowledge of Y."  A one-way logical guarantee, NOT 'often used together'.

Why LLM instead of Wikidata P277: P277 ("programmed in") only expresses
framework -> language and misses the edges that actually matter for matching —
framework -> framework (nextjs -> react), superset -> base (typescript ->
javascript), library -> capability (chartjs -> data_visualization), and
specialization -> general concept (deep_learning -> machine_learning). An LLM
encodes the real "guarantees knowledge of" relation directly.

This is an OFFLINE one-shot generator: run manually, eyeball the diff it prints,
commit the frozen output. Match-time scoring stays pure-Python (no LLM calls).

    python scripts/generate_implies_llm.py            # generate + write
    python scripts/generate_implies_llm.py --dry-run  # print graph + diff only
    python scripts/generate_implies_llm.py --workers 4

Provider/model come from .env (LLM_PROVIDER), same as the rest of the app.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings                              # noqa: E402
from app.services.llm_client import call_llm_json_sync       # noqa: E402
from app.services.scorer import SkillMatcher                 # noqa: E402
from app.services.skill_data import MANUAL_IMPLIES           # noqa: E402
from app.services.skill_implies import IMPLIES as OLD_IMPLIES  # noqa: E402  (diff baseline)

OUTPUT_PATH = PROJECT_ROOT / "app" / "services" / "skill_implies.py"

# Hand-verified edges that MUST appear regardless of LLM variance. Sourced from
# skill_data.MANUAL_IMPLIES so anchors have a single source of truth. The LLM
# output is unioned on top of these.
SEED_EDGES: dict[str, set[str]] = {k: set(v) for k, v in MANUAL_IMPLIES.items()}

# Human guardrail: edges the LLM reliably over-generates but that are NOT strict
# guarantees. A pure visualization tool/skill does not make someone a data
# analyst; visualization/preprocessing/analysis are sibling activities, not
# implications. Removed AFTER the LLM union, BEFORE transitive closure.
DENY_EDGES: set[tuple[str, str]] = {
    ("chartjs", "data_analysis"),
    ("d3js", "data_analysis"),
    ("highcharts", "data_analysis"),
    ("recharts", "data_analysis"),
    ("plotly", "data_analysis"),
    ("data_visualization", "data_analysis"),
    ("data_preprocessing", "data_analysis"),
    ("responsive_web_design", "ui_design"),
}


PROMPT_TEMPLATE = """You are building a one-way skill-implication graph for a CV/JD matching engine.
An edge grants FULL skill-match credit, so a wrong edge is worse than a missing one.

TARGET SKILL: "{source}"

Return the skills from the VOCABULARY that are STRICTLY GUARANTEED by "{source}".

THE TEST — apply to every candidate Y, one at a time:
    "Could a competent practitioner of {source} plausibly exist who has NEVER used Y?"
    If such a person could exist  -> EXCLUDE Y.
    Only if it is IMPOSSIBLE to use {source} at all without Y -> INCLUDE Y.

INCLUDE ONLY these four kinds of edge:
1. the language {source} is fundamentally authored in and cannot be used without
       react -> javascript ; django -> python ; typescript -> javascript
2. the parent framework {source} directly extends and cannot run without
       nextjs -> react ; nestjs -> express ; express -> nodejs ; kubernetes -> docker
3. the capability whose very definition {source} IS an implementation of
       chartjs -> data_visualization ; d3js -> data_visualization
4. the strictly broader concept that {source} is a named sub-type of
       deep_learning -> machine_learning

EXCLUDE (a practitioner could exist without Y — do NOT include):
- sibling / alternative tools           mysql does NOT imply postgresql ; react does NOT imply vue
- adjacent skills in the same workflow  chartjs does NOT imply data_analysis ; django does NOT imply mysql
- a language a TOOL is written in but USERS never touch
                                        elasticsearch does NOT imply java ; jenkins does NOT imply java
- markup/styling a framework renders but does not require you to author
                                        react does NOT imply css or html
- general paradigms unless {source} literally IS that paradigm
                                        python does NOT imply oop ; numpy does NOT imply oop
- the reverse direction                 javascript does NOT imply react ; machine_learning does NOT imply deep_learning

Precision over recall: when unsure, EXCLUDE. Most skills guarantee 0-2 others; many guarantee none.

Return ONLY JSON, no prose: {{"implies": ["token", ...]}}
Use EXACT tokens copied from the VOCABULARY. Empty list if nothing is strictly guaranteed.

VOCABULARY:
{vocab}
"""


def canonical_vocab() -> list[str]:
    return sorted(set(SkillMatcher.ALIASES.values()))


def propose_edges(source: str, vocab: list[str], vocab_set: set[str]) -> set[str]:
    """One LLM call: which vocab tokens does `source` guarantee?"""
    # Give every candidate except the source itself.
    candidates = [t for t in vocab if t != source]
    prompt = PROMPT_TEMPLATE.format(source=source, vocab=json.dumps(candidates))
    try:
        raw = call_llm_json_sync(prompt, "")
    except Exception as exc:  # noqa: BLE001 — keep going, seeds still apply
        print(f"  [warn] {source}: LLM call failed ({exc})", file=sys.stderr)
        return set()
    items = raw.get("implies", []) if isinstance(raw, dict) else []
    return {t for t in items if isinstance(t, str) and t in vocab_set and t != source}


def transitive_closure(graph: dict[str, set[str]]) -> dict[str, set[str]]:
    """One-way transitive closure (nextjs -> react -> javascript => nextjs -> javascript)."""
    closed = {s: set(t) for s, t in graph.items()}
    changed = True
    while changed:
        changed = False
        for src, targets in list(closed.items()):
            expanded = set(targets)
            for t in targets:
                expanded |= closed.get(t, set())
            expanded.discard(src)
            if expanded != targets:
                closed[src] = expanded
                changed = True
    return closed


def render_python(implies: dict[str, set[str]]) -> str:
    provider = settings.llm_provider
    model = {"gemini": settings.gemini_model,
             "anthropic": settings.anthropic_model,
             "groq": settings.groq_model}.get(provider, provider)
    today = datetime.date.today().isoformat()
    lines = [
        "# Auto-generated by scripts/generate_implies_llm.py - DO NOT EDIT BY HAND.",
        f"# Source: LLM ({provider} / {model}), one-way 'guarantees knowledge of' relation.",
        f"# Generated: {today}. Regenerate: python scripts/generate_implies_llm.py",
        "",
        "IMPLIES: dict[str, set[str]] = {",
    ]
    for skill in sorted(implies):
        targets = sorted(implies[skill])
        if targets:
            body = ", ".join(f'"{t}"' for t in targets)
            lines.append(f'    "{skill}": {{{body}}},')
        else:
            lines.append(f'    "{skill}": set(),')
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def print_diff(old: dict[str, set[str]], new: dict[str, set[str]]) -> None:
    print("\n========== DIFF vs current skill_implies.py ==========")
    keys = sorted(set(old) | set(new))
    any_change = False
    for k in keys:
        o, n = old.get(k, set()), new.get(k, set())
        added, removed = n - o, o - n
        if added or removed:
            any_change = True
            parts = []
            if added:
                parts.append("+{" + ", ".join(sorted(added)) + "}")
            if removed:
                parts.append("-{" + ", ".join(sorted(removed)) + "}")
            print(f"  {k}: {' '.join(parts)}")
    if not any_change:
        print("  (identical)")


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM-generate the IMPLIES graph")
    ap.add_argument("--dry-run", action="store_true", help="print graph + diff, do not write")
    ap.add_argument("--workers", type=int, default=8, help="parallel LLM calls (default 8)")
    args = ap.parse_args()

    vocab = canonical_vocab()
    vocab_set = set(vocab)
    print(f"Provider: {settings.llm_provider} | vocab: {len(vocab)} skills | workers: {args.workers}")

    # Direct edges = seed anchors ∪ LLM proposals.
    direct: dict[str, set[str]] = {s: set(SEED_EDGES.get(s, set())) for s in vocab}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(propose_edges, s, vocab, vocab_set): s for s in vocab}
        done = 0
        for fut in as_completed(futures):
            src = futures[fut]
            direct[src] |= fut.result()
            done += 1
            if done % 10 == 0 or done == len(vocab):
                print(f"  ...{done}/{len(vocab)} skills")

    # Apply human guardrail before closure so denied edges can't sneak back via
    # a transitive path.
    for src, tgt in DENY_EDGES:
        direct.get(src, set()).discard(tgt)

    final = transitive_closure(direct)
    # Guarantee every vocab token is present (even with an empty set).
    for s in vocab:
        final.setdefault(s, set())

    edge_count = sum(len(v) for v in final.values())
    nonempty = sum(1 for v in final.values() if v)
    print(f"\nEdges (after closure): {edge_count} across {nonempty} skills")

    print_diff(OLD_IMPLIES, final)

    if args.dry_run:
        print("\n[dry-run] not writing.")
        return 0

    OUTPUT_PATH.write_text(render_python(final), encoding="utf-8")
    print(f"\nWrote: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
