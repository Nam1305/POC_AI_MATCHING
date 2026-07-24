# API Endpoints

Ground truth extracted from the actual FastAPI code (`app/main.py`, `app/api/*.py`,
`app/schemas.py`), not from `docs/Overview.md` (which contains stale/aspirational
examples — see the note at the bottom of this file).

All routes below except `/health` are mounted under the `/ai` prefix.

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
    "required_skills": [
      { "skill": "C#", "weight": 3, "alternatives": [] }
    ],
    "preferred_skills": ["Docker"],
    "min_experience_years": 1,
    "education_degree": "bachelor",
    "keywords": ["backend", ".net"],
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

Per-URL failures never fail the whole request — that item's `error` is set
(e.g. `"HTTP 404 when downloading file"`, `"Network error: ..."`, `"No text
could be extracted from file"`, `"Parse/embed failed: ..."`) with
`cv_raw_text`, `parsed_cv`, `cv_embedding` left `null`; other URLs in the same
request are unaffected.

**Errors (whole-request, `422`):** neither `cv_url` nor `cv_urls` given, more
than 50 URLs, or any URL not starting with `http://`/`https://`.

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
    "bonus_skills": ["GraphQL"],
    "skill_match_rate": 0.85,
    "experience_verdict": "sufficient",
    "experience_detail": "3.5 years vs. 2 years required",
    "education_verdict": "meets",
    "narrative": ""
  }
}
```

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
  "bonus_skills": ["GraphQL"],
  "skill_match_rate": 0.85,
  "experience_verdict": "sufficient",
  "experience_detail": "3.5 years vs. 2 years required",
  "education_verdict": "meets",
  "narrative": "Ứng viên phù hợp tốt với vị trí..."
}
```

`skill_details[].status` is one of `matched`, `matched_implied`,
`missing_must_have`, `missing_preferred`.
`experience_verdict` is one of `sufficient`, `insufficient`,
`over_qualified`, `not_required`.
`education_verdict` is one of `exceeds`, `meets`, `below`, `not_required`.

---

## Not implemented

`docs/Overview.md` also describes `POST /ai/recalculate` and `POST /ai/search`.
Neither has a route or router file in `app/` — do not treat them as live
endpoints until they're actually built.
