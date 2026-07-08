# generate_implies.py — Generate skill implication data

Overview
--------
This script builds a one-way skill implication graph using Wikidata's P277 ("programmed in") property and the project's canonical skill vocabulary. It writes a deterministic Python module that maps each canonical skill token to a set of implied skills.

Location
--------
The script lives at `scripts/generate_implies.py` and writes its output to `app/services/skill_implies.py`.

What it does
------------
- Starts from a pinned set of Wikidata QIDs (see `SKILL_QIDS` in the script).
- Queries Wikidata P277 for technologies related to the pinned entities.
- Filters noisy source entities by type (databases, OS, cloud, etc.).
- Normalizes labels into the project's canonical skill tokens.
- Keeps only relations where the target belongs to the canonical vocabulary.
- Computes one-way transitive closure and emits a complete mapping (empty sets included).

Requirements
------------
- Python 3.8+ (the repository uses type annotations and modern stdlib APIs).
- Network access to `https://query.wikidata.org/sparql`.
- The repository installed as a local importable package (the script modifies `sys.path` to import `app.services.scorer.SkillMatcher`).
- No extra third-party packages are required by the script itself (it uses `urllib` and stdlib modules).

Configuration points
--------------------
- `SKILL_QIDS`: map of canonical skill tokens to optional Wikidata QIDs. Add or adjust pinned QIDs here.
- `MAX_ROUNDS`: number of discovery rounds (default 2).
- `MAX_RETRIES` / `RETRY_DELAY_SECONDS`: HTTP retry behavior for Wikidata queries.
- `OUTPUT_PATH`: where the generated `skill_implies.py` is written (default `app/services/skill_implies.py`).

Safety / Notes
--------------
- The script overwrites the file at `app/services/skill_implies.py`. Keep backups or run under version control.
- If Wikidata returns no results (e.g., rate-limited or network blocked), the script raises an error and does not overwrite the output.
- Adjust `USER_AGENT` if you need to comply with Wikidata API guidelines.

Usage
-----
From the project root (`MVP_AI_Matching`) run:

```
python scripts/generate_implies.py
```

Example: create a virtualenv, install requirements, then run:

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
python scripts/generate_implies.py
```

Output
------
After a successful run, `app/services/skill_implies.py` will contain an auto-generated `IMPLIES: dict[str, set[str]]` mapping. The header of the file notes the source and warns not to edit by hand.

Troubleshooting
---------------
- If you see the runtime error "Wikidata SPARQL query failed after ... attempts", ensure network access and that the endpoint is reachable.
- If relation coverage looks off, check `SKILL_QIDS` to ensure important canonical skills have pinned QIDs.
- Use `MAX_ROUNDS = 1` for a single-pass extraction during quick tests.

License / Attribution
---------------------
This script queries and uses public data from Wikidata. Follow Wikidata's terms of use when redistributing derived data.

If you want, I can also update the repository root README to reference this script. Let me know.