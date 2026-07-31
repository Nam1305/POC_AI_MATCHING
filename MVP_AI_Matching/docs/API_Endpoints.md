# API Endpoints

Ground truth extracted from the actual FastAPI code (`app/main.py`, `app/api/*.py`,
`app/schemas.py`). This file is the **request/response reference**;
`docs/Overview.md` covers the same endpoints from the architecture/flow angle and
explains *why* each field exists.

All routes below except `/health` are mounted under the `/ai` prefix.
Last verified against the code: 2026-07-31.

---

## `GET /health`

Liveness check.

**Request:** none.

**Response `200`:**
```json
{ "status": "ok" }
```

---

## `POST /ai/parse-jd`

Parse raw JD text into structured JSON + embedding vector.

**Request body** — accepts either `application/json` or `text/plain`:

```json
{ "jd_text": "Job Title: Junior .NET Backend Developer\n..." }
```
or send the raw JD text as the entire `text/plain` body.

The endpoint reads the raw request body itself: if it starts with `{` and parses
as JSON containing `jd_text`, that value is used; otherwise the whole body is
treated as `jd_text`.

**Response `200`:**
```json
{
  "parsed_jd": {
    "title": "Junior .NET Backend Developer",
    "responsibilities": "Own backend services for the internal CRM, working closely with the FE and QA teams.",
    "required_skills": [
      { "skill": "C#", "weight": 3, "alternatives": [] }
    ],
    "preferred_skills": ["Docker"],
    "nice_to_have_skills": ["Agile & Scrum"],
    "min_experience_years": 1,
    "education_degree": "bachelor",
    "work_location": {
      "city": "Ha Noi",
      "raw_address": "",
      "work_mode": "onsite",
      "lat": null,
      "lng": null
    }
  },
  "jd_embedding": [0.123, 0.456, "..."],
  "error": null
}
```

`error` is set (e.g. `"Embed failed: ..."`) when embedding fails; `jd_embedding`
is `null` in that case.

`education_degree` is one of `high_school`, `associate`, `bachelor`, `master`,
`phd`, `other`, or `null` (JD states no specific degree).
`work_location.work_mode` is one of `onsite`, `hybrid`, `remote` — defaults to
`onsite` when the JD gives no explicit signal.
`work_location.city` is constrained to exactly `"Ha Noi"`, `"Ho Chi Minh"`, or
`"Da Nang"`. `work_location.raw_address` holds only the street/district/
building portion (never repeats the city) — mirrors BE .NET's
`company_branch` table, which stores `address`/`city` as separate columns.
For geocoding, `parser.parse_jd` joins `raw_address + ", " + city` into one
query string (falling back to `city` alone when `raw_address` is empty).

`preferred_skills` and `nice_to_have_skills` are two separate tiers below
`required_skills` — mirrors BE .NET's `tags.preferred_skills` /
`tags.nice_to_have`. The numeric `skills` score (D2) is computed from ALL
THREE tiers combined: `required_skills` uses each skill's own `weight`
(1–3, LLM-assigned — skills sourced from the JD's "Required Skills:" tag
line are always 3), `preferred_skills` uses a flat weight of 2 per skill,
`nice_to_have_skills` uses a flat weight of 1 per skill
(`PREFERRED_SKILL_WEIGHT` / `NICE_TO_HAVE_SKILL_WEIGHT` in
`skill_matcher.py`). D2 = `Σ(weight × matched) / Σ(weight)` across all
matched/unmatched skills in all three tiers — a missing preferred/
nice-to-have skill still lowers the score, just less than a missing
required one. There is no de-duplication step across tiers in code; the
JD extraction prompt is responsible for ensuring a skill is only ever
placed in one tier.

Generic soft skills / meta-competencies ("teamwork", "problem solving",
"programming fundamentals", … — 44 entries in `schemas.py::GENERIC_NON_SKILLS`)
are stripped from **all three** tiers by a Pydantic model validator
(`ParsedJD._drop_generic_skills`) before the object is returned. They can never
match a CV skill list, so keeping them would produce a phantom missing
must-have for every candidate.

**Errors:**
- `400` — `"Request body is empty"`
- `400` — `"jd_text is empty"`

---

## `POST /ai/parse-cv`

Download CV file(s) from S3/R2 URL(s), extract text, parse into structured JSON,
and embed — processed concurrently for multiple URLs. Never uploads files
directly; only accepts URLs.

**Request body** — one of `cv_url` or `cv_urls` is required (max 50 URLs):

```json
{ "cv_url": "https://s3.amazonaws.com/bucket/cv.pdf" }
```
```json
{ "cv_urls": [
    "https://s3.amazonaws.com/bucket/cv1.pdf",
    "https://s3.amazonaws.com/bucket/cv2.pdf"
] }
```

**Response `200`:**
```json
{
  "results": [
    {
      "url": "https://s3.amazonaws.com/bucket/cv1.pdf",
      "cv_raw_text": "Nguyen Van A\n...",
      "parsed_cv": {
        "name": "Nguyen Van A",
        "summary": "",
        "skills": ["python", "fastapi"],
        "work_experience": [
          {
            "company": "ABC",
            "role": "Backend Developer",
            "start": "2020-01",
            "end": "present",
            "months": 66,
            "is_current": true,
            "tech_stack": ["FastAPI", "Redis"],
            "description": "..."
          }
        ],
        "education": [
          { "institution": "HUST", "degree": "bachelor", "degree_raw": "Bachelor", "major": "SE" }
        ],
        "projects": [
          { "name": "...", "tech_stack": ["FastAPI"], "description": "..." }
        ],
        "certifications": ["AWS Cloud Practitioner"],
        "languages": ["English - TOEIC 835"],
        "candidate_location": {
          "raw_address": "45 Le Loi, Quan 1, TP. Ho Chi Minh",
          "lat": 10.7757,
          "lng": 106.7004,
          "willing_to_relocate": null
        }
      },
      "cv_embedding": [0.456, "..."],
      "error": null
    }
  ]
}
```

`work_experience[].months` is computed by Python (`schemas.py::_diff_months`)
from `start`/`end` at validation time — never trust an LLM-provided value for
this field. For an entry with `"end": "present"`, `months` grows with the
current date, so the number above is illustrative, not fixed.

Per-URL failures never fail the whole request — that item's `error` is set
(e.g. `"HTTP 404 when downloading file"`, `"Network error: ..."`,
`"Unsupported file type: .xyz (only .pdf / .docx allowed)"`, `"No text
could be extracted from file"`, `"Parse/embed failed: ..."`) with
`cv_raw_text`, `parsed_cv`, `cv_embedding` left `null`; other URLs in the same
request are unaffected.

**Errors (whole-request, `422`):**
- `"cv_url or cv_urls is required"`
- `"Maximum 50 CVs per request"`
- `"Invalid URL (must start with http/https): {url}"`

---

## `POST /ai/score`

Compute the 5-dimension weighted match score plus a qualitative evaluation.

**Request body:**
```json
{
  "parsed_cv": { "...": "ParsedCV object, see /ai/parse-cv response" },
  "parsed_jd": { "...": "ParsedJD object, see /ai/parse-jd response" },
  "cv_embedding": [0.456, "..."],
  "jd_embedding": [0.123, "..."],
  "weights": {
    "semantic": 0.30,
    "skills": 0.35,
    "experience": 0.20,
    "education": 0.10,
    "location": 0.05
  },
  "include_narrative": false
}
```

- `weights` is optional; defaults to the values above. If provided, it must
  contain exactly the keys `semantic`, `skills`, `experience`, `education`,
  `location`, each in `[0, 1]`, summing to `1.0`.
- `include_narrative` is optional (default `false`); set `true` to also run
  the LLM narrative for the `evaluation` field.

**Response `200`:**
```json
{
  "final_score": 78.5,
  "scores": {
    "semantic": 82.0,
    "skills": 75.0,
    "experience": 80.0,
    "education": 100.0,
    "location": 60.0
  },
  "weights_used": {
    "semantic": 0.30,
    "skills": 0.35,
    "experience": 0.20,
    "education": 0.10,
    "location": 0.05
  },
  "evaluation": {
    "skill_details": [
      { "skill": "React", "status": "matched", "weight": 3 }
    ],
    "missing_must_have": [],
    "missing_preferred": ["Docker"],
    "missing_nice_to_have": ["Agile & Scrum"],
    "bonus_skills": ["GraphQL"],
    "skill_match_rate": 85.7,
    "experience_verdict": "sufficient",
    "experience_detail": "3.5 years vs. 2 years required",
    "education_verdict": "meets",
    "narrative": ""
  }
}
```

`skill_match_rate` is a **percentage (0–100)**, not a 0–1 fraction — it's
`matched_weight / total_weight * 100` from `evaluator.py`, using the exact
same 3-tier weighted formula as the `skills` score above (D2) — the two
numbers always agree.

`narrative` is only populated when `include_narrative: true`.

**Errors (`422`, pydantic weight validation):**
- `"weights must have exactly the keys [...], got [...]"`
- `"each weight must be between 0 and 1"`
- `"weights must sum to 1.0, got {total}"`

---

## `POST /ai/evaluate`

Qualitative CV-JD evaluation (skills/experience/education analysis +
narrative). No numeric score.

**Request body:**
```json
{
  "parsed_cv": { "...": "ParsedCV object" },
  "parsed_jd": { "...": "ParsedJD object" }
}
```

**Response `200`** — a `CVJobEvaluation` object (same shape as the `evaluation`
field of `/ai/score`, but always with `narrative` populated):
```json
{
  "skill_details": [
    { "skill": "React", "status": "matched", "weight": 3 }
  ],
  "missing_must_have": [],
  "missing_preferred": ["Docker"],
  "missing_nice_to_have": ["Agile & Scrum"],
  "bonus_skills": ["GraphQL"],
  "skill_match_rate": 85.7,
  "experience_verdict": "sufficient",
  "experience_detail": "3.5 years vs. 2 years required",
  "education_verdict": "meets",
  "narrative": "Ứng viên phù hợp tốt với vị trí..."
}
```

`skill_match_rate` is a **percentage (0–100)**, not a 0–1 fraction.

`skill_details[]` has one entry per JD skill requirement across all three
tiers (an OR-group is a single entry labelled `"A / B / C"`), with the tier's
weight in `weight`. `status` is one of `matched`, `matched_implied`,
`missing_must_have`, `missing_preferred`, `missing_nice_to_have`. A missing
skill is bucketed by tier + weight: `missing_must_have` = `required` tier with
`weight >= 3`; `missing_preferred` = `preferred` tier **or** `required` tier
with `weight < 3`; `missing_nice_to_have` = `nice_to_have` tier.

`bonus_skills` lists CV skills the JD does not ask for in any tier (compared on
canonical form, so `"React"` isn't a bonus when the JD asks for `"React.js"`),
capped at 8 entries.

`experience_verdict` is one of `sufficient` (CV years ≥ 80% of required),
`insufficient`, `over_qualified` (CV years ≥ 2× required), `not_required`
(JD sets no minimum).
`education_verdict` is one of `exceeds`, `meets`, `below`, `not_required`.

---

## Not implemented

`POST /ai/recalculate` and `POST /ai/search` appear in the original design (and
are listed as out-of-scope in `docs/Overview.md` → *Ngoài phạm vi bản hiện tại*).
Neither has a route or router file in `app/` — do not treat them as live
endpoints until they're actually built.
