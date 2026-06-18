# AI Service — Request Flow

3 endpoints, stateless, no DB.

---

## Flow 1 — HR tạo Job

```
POST /ai/parse-jd
{ "jd_text": "..." }
      │
      ▼  [LLM] JD text → ParsedJD JSON
      ▼  [Embed] JD text → float[3072]
      │
{ parsed_jd, jd_embedding }
```

---

## Flow 2 — Ứng viên nộp CV + Score

```
POST /ai/parse-cv
{ "cv_url": "https://s3/.../cv.pdf" }
      │
      ▼  Download file from S3/R2 URL
      ▼  [PyMuPDF] smart layout extract → raw_text
           └── quality < 60 → OCR fallback (pytesseract)
      ▼  [LLM] raw_text → ParsedCV JSON
      ▼  [Embed] parsed text → float[3072]
      │
{ cv_raw_text, parsed_cv, cv_embedding }

      │
      ▼

POST /ai/score
{ parsed_cv, parsed_jd, cv_embedding, jd_embedding }
      │
      ▼  Pure Python — zero LLM (~1ms)
         D1 Semantic    cosine_sim(cv_vec, jd_vec)
         D2 Skills      weighted overlap + alias/fuzzy/category
         D3 Experience  cv_years / jd_min_years + recency modifier
         D4 Education   degree level lookup
         D5 Keywords    substring / word-boundary match
         final = Σ(Di × Wi) × 100
      │
{ final_score, scores: { semantic, skills, experience, education, keywords } }
```

**Latency:** ~5–10 s total (LLM parse + embed dominate; score step is <1 ms)

---

## Flow 3 — HR điều chỉnh weights

Không cần gọi AI Service. Tính lại trực tiếp từ dimension scores đã lưu:

```
final_score = score_semantic   × w_semantic
            + score_skills     × w_skills
            + score_experience × w_experience
            + score_education  × w_education
            + score_keywords   × w_keywords
```

---

## API Contract

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

---

## Scoring Weights (default)

| Dimension  | Weight | Method                                  |
|------------|--------|-----------------------------------------|
| Semantic   | 0.30   | cosine_sim(cv_embedding, jd_embedding)  |
| Skills     | 0.35   | weighted overlap + alias/fuzzy/category |
| Experience | 0.20   | cv_years / jd_min_years + modifiers     |
| Education  | 0.10   | degree level ratio                      |
| Keywords   | 0.05   | substring / word-boundary match         |

---

## LLM Calls per Flow

| Flow            | LLM calls | Embed calls |
|-----------------|-----------|-------------|
| Parse JD        | 1         | 1           |
| Parse CV        | 1         | 1           |
| Score           | 0         | 0           |
| Weight change   | 0         | 0           |

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
│   └── score.py             # POST /ai/score  (pure Python scorer)
│
└── services/
    ├── pdf_extractor.py     # PyMuPDF smart layout + OCR fallback
    ├── parser.py            # LLM: JD/CV text → structured JSON
    ├── embedder.py          # Embed: text → float[N]
    ├── scorer.py            # 5-dimension scoring engine
    └── llm_client.py        # unified LLM call (Anthropic / Groq / Gemini)
```
