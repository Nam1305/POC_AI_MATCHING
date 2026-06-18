# AI Service — Request Flow

3 endpoints, stateless, no DB.

```
.NET Backend ──HTTP──▶ Python FastAPI AI Service
```

---

## Flow 1 — HR tạo Job

```
[.NET]
  │
  │  POST /ai/parse-jd
  │  { "jd_text": "..." }
  │ ──────────────────────────────────────▶
  │                                   [LLM] Claude → ParsedJD JSON
  │                                   [Embed] gemini-embedding-001 → float[3072]
  │ ◀──────────────────────────────────────
  │  { parsed_jd, jd_embedding }
  │
  ├─ INSERT jobs { title, parsed_jd, jd_embedding }
  └─ INSERT scoring_configs { defaults: 30/35/20/10/5 }
```

---

## Flow 2 — Ứng viên nộp CV

```
[ReactJS]       [.NET]                              [AI Service]
    │               │
    │  POST /apply  │
    │  { job_id,    │
    │    cv_file }  │
    │─────────────▶ │
    │          INSERT application
    │          status = "processing"
    │               │
    │               │  POST /ai/parse-cv
    │               │  { "cv_url": "https://s3/.../cv.pdf" }
    │               │ ─────────────────────────────────────▶
    │               │                              Download file from URL
    │               │                              [PDF] PyMuPDF smart layout → raw_text
    │               │                              [LLM] Claude → ParsedCV JSON
    │               │                              [Embed] gemini-embedding-001 → float[3072]
    │               │ ◀─────────────────────────────────────
    │               │  { cv_raw_text, parsed_cv, cv_embedding }
    │               │
    │               │  POST /ai/score
    │               │  { parsed_cv, parsed_jd,
    │               │    cv_embedding, jd_embedding }
    │               │ ─────────────────────────────────────▶
    │               │                              Pure Python (no LLM, ~1ms):
    │               │                              D1 Semantic   cosine_sim(cv_vec, jd_vec)
    │               │                              D2 Skills     weighted overlap + fuzzy
    │               │                              D3 Experience cv_years / jd_min_years
    │               │                              D4 Education  degree level lookup
    │               │                              D5 Keywords   substring / word-boundary
    │               │                              final = Σ(Di × Wi) × 100
    │               │ ◀─────────────────────────────────────
    │               │  { final_score, scores: {semantic, skills,
    │               │                          experience, education, keywords} }
    │               │
    │          UPDATE application
    │          SET parsed_cv, cv_embedding,
    │              scores, final_score, status="done"
    │ ◀─────────────│
    │  { final_score: 78.5,
    │    scores: { semantic:82, skills:75,
    │              experience:80, education:100, keywords:60 } }
```

**Latency:** ~5–10 s total (Claude parse + embed dominate; score is <1 ms)

---

## Flow 3 — HR điều chỉnh weights

Không cần gọi AI Service. .NET tự tính:

```
[.NET]
  │
  │  PUT /api/jobs/{id}/scoring-config
  │  { semantic:0.20, skills:0.45, experience:0.20, education:0.10, keywords:0.05 }
  │
  ├─ Validate sum == 1.0
  ├─ UPDATE scoring_configs
  ├─ SELECT applications WHERE job_id = {id}
  │    → { id, score_semantic, score_skills, score_experience,
  │         score_education, score_keywords }
  │
  │  Recalculate in .NET:
  │  final_score = score_semantic × w_semantic
  │              + score_skills   × w_skills
  │              + ...
  │
  └─ Batch UPDATE applications SET final_score = ...
     Return new ranking sorted DESC
```

---

## Flow 4 — HR NL Search

```
[.NET]
  │
  │  Hard filter: job_id + status="done"
  │  SELECT { id, cv_embedding, final_score, parsed_cv }
  │
  │  POST /ai/search
  │  { query: "React 3 năm, team lead",
  │    applications: [{ id, cv_embedding, final_score, parsed_cv }, ...],
  │    top_n_reasons: 5 }
  │ ─────────────────────────────────────▶
  │                              [LLM] Claude → structured filters JSON
  │                              [Embed] gemini-embedding-001 → query_vec
  │                              [numpy] cosine_sim(query_vec, cv_vec[i]) for all
  │                              [Python] metadata filter on parsed_cv JSON
  │                              Re-rank: combined = final_score×0.4 + sim×100×0.6
  │                              [LLM] Claude → match_reason for top N
  │ ◀─────────────────────────────────────
  │  { results: [{ id, similarity_score, combined_score, match_reason }] }
  │
  │  Fetch candidate info by ids → return to ReactJS
```

---

## API Contract Summary

### POST /ai/parse-jd
```json
Request:  { "jd_text": "string" }
Response: { "parsed_jd": {...}, "jd_embedding": [float, ...], "error": null }
```

### POST /ai/parse-cv
```json
Request:  { "cv_url": "https://..." }
          { "cv_urls": ["https://...", ...] }   // up to 10 concurrent

Response: {
  "results": [{
    "url": "...",
    "cv_raw_text": "string",
    "parsed_cv": {...},
    "cv_embedding": [float, ...],
    "error": null
  }]
}
```

### POST /ai/score
```json
Request: {
  "parsed_cv":    {...},
  "parsed_jd":    {...},
  "cv_embedding": [float, ...],
  "jd_embedding": [float, ...]
}

Response: {
  "final_score": 78.5,
  "scores": {
    "semantic":   82.0,
    "skills":     75.0,
    "experience": 80.0,
    "education":  100.0,
    "keywords":   60.0
  }
}
```

### POST /ai/search
```json
Request: {
  "query": "React 3 năm, có kinh nghiệm team lead",
  "applications": [
    { "id": "uuid-1", "cv_embedding": [...], "final_score": 78.5, "parsed_cv": {...} }
  ],
  "top_n_reasons": 5
}

Response: {
  "results": [
    { "id": "uuid-1", "similarity_score": 0.87, "combined_score": 82.1,
      "match_reason": "React 4 năm, dẫn nhóm 5 người tại XYZ" }
  ]
}
```

---

## Scoring Weights (default)

| Dimension | Weight | Method                                   |
|-----------|--------|------------------------------------------|
| Semantic  | 0.30   | cosine_sim(cv_embedding, jd_embedding)   |
| Skills    | 0.35   | weighted overlap + alias/fuzzy/category  |
| Experience| 0.20   | cv_years / jd_min_years + modifiers      |
| Education | 0.10   | degree level ratio                       |
| Keywords  | 0.05   | substring / word-boundary match          |

HR điều chỉnh weights qua PUT /api/jobs/{id}/scoring-config trên .NET (không cần gọi AI Service).

---

## Project Structure

```
app/
├── main.py                  # FastAPI app, router mounts
├── config.py                # .env: LLM provider, embed provider, weights
├── schemas.py               # ParsedCV, ParsedJD, shared Pydantic models
│
├── api/
│   ├── parse.py             # POST /ai/parse-jd, POST /ai/parse-cv
│   ├── score.py             # POST /ai/score  (pure Python scorer)
│   └── search.py            # POST /ai/search (NL search)
│
└── services/
    ├── pdf_extractor.py     # PyMuPDF smart layout + OCR fallback
    ├── parser.py            # LLM: JD/CV text → structured JSON
    ├── embedder.py          # Embed: text → float[N]
    ├── scorer.py            # 5-dimension scoring engine
    ├── nl_search.py         # query embed → cosine → re-rank → LLM reason
    └── llm_client.py        # unified LLM call (Anthropic / Groq / Gemini)
```

## LLM Calls per Flow

| Flow            | LLM calls | Embed calls |
|-----------------|-----------|-------------|
| Parse JD        | 1         | 1           |
| Parse CV        | 1         | 1           |
| Score           | 0         | 0           |
| Weight change   | 0         | 0           |
| NL Search       | 1 (parse) + 1 (reasons) | 1 |
