# AI CV-JD Matching — System Overview

## Kiến trúc tổng thể

```
ReactJS  ──→  .NET API  ──→  PostgreSQL
                  ↕ internal HTTP (Docker network)
            Python FastAPI AI Service
            (stateless: nhận input → xử lý → trả output)
```

**Nguyên tắc:**

- AI service **không có DB, không có auth** — chỉ xử lý AI
- **.NET là source of truth** — sở hữu toàn bộ business logic, auth, PostgreSQL
- **ReactJS chỉ giao tiếp với .NET** — không gọi AI service trực tiếp
- Deploy **Docker Compose** cùng server, giao tiếp qua internal network

---

## Nghiệp vụ 2 Side

### Side 1 — Ứng viên nộp CV

```
1. Ứng viên vào trang chi tiết Job → xem JD

2. Nhấn "Nộp đơn" → upload file CV (PDF hoặc DOCX)

3. ReactJS → POST /api/applications { job_id, cv_file }

4. .NET xử lý:
   a. Xác thực JWT token → candidate_id
   b. Lưu application record, status = "processing"
   c. Lấy job.parsed_jd + job.jd_embedding + scoring_config từ DB
   d. Gọi AI Service (2 lần):
      → POST /ai/parse-cv { cv_file }
      ← { cv_raw_text, parsed_cv, cv_embedding }

      → POST /ai/score { parsed_cv, parsed_jd, cv_embedding, jd_embedding, weights, cv_raw_text }
      ← { final_score, scores: { semantic, skills, experience, education, keywords } }
   e. UPDATE application: lưu tất cả kết quả, status = "done"
   f. Return về ReactJS: { final_score, scores }

5. ReactJS hiển thị kết quả ngay:
   ┌─────────────────────────────────┐
   │  Điểm phù hợp của bạn: 78.5/100 │
   │  Semantic similarity  ████░  82% │
   │  Skills match         ███░░  75% │
   │  Experience           ████░  80% │
   │  Education            █████ 100% │
   │  Keywords             ███░░  60% │
   └─────────────────────────────────┘
```

**Thời gian xử lý:** ~5–10s (Claude parse + OpenAI embed là chủ yếu)

---

### Side 2 — HR quản lý ứng viên

#### 2a. Tạo Job mới

```
1. HR nhập JD text → POST /api/jobs { title, jd_text }

2. .NET:
   → POST /ai/parse-jd { jd_text }
   ← { parsed_jd, jd_embedding }
   → INSERT jobs + INSERT scoring_configs (default weights)
```

#### 2b. Xem ranking top ứng viên

```
1. HR vào /jobs/{id}/candidates

2. .NET: SELECT applications ORDER BY final_score DESC LIMIT 10

3. ReactJS hiển thị bảng:
   ┌────┬──────────────┬────────┬────────┬────────┬────────┬─────────┐
   │ #  │ Ứng viên     │ Tổng   │ Skills │ Exp    │ Edu    │Semantic │
   ├────┼──────────────┼────────┼────────┼────────┼────────┼─────────┤
   │ 1  │ Nguyen Van A │  85.2  │  90%   │  80%   │ 100%   │  82%    │
   │ 2  │ Tran Thi B   │  78.5  │  75%   │  85%   │ 100%   │  76%    │
   └────┴──────────────┴────────┴────────┴────────┴────────┴─────────┘
```

#### 2c. Điều chỉnh weights

```
1. HR kéo 5 sliders (tổng phải = 100%) → PUT /api/jobs/{id}/scoring-config

2. .NET:
   a. Validate sum == 100%
   b. UPDATE scoring_configs
   c. Fetch tất cả applications (chỉ cần 5 dimension scores, không cần text/embedding)
   → POST /ai/recalculate { applications:[{id, scores},...], weights }
   ← { results: [{ id, final_score }, ...] }
   d. Batch UPDATE final_score → return new ranking

   → Không gọi LLM, chỉ tính toán thuần túy
```

#### 2d. Tìm kiếm bằng ngôn ngữ tự nhiên

```
1. HR gõ: "Tìm ứng viên React 3 năm, có kinh nghiệm team lead"

2. .NET:
   a. Hard filter: job_id + status="done"
   b. Fetch { id, cv_embedding, final_score, parsed_cv } của tất cả CV
   → POST /ai/search { query, applications:[...] }
   ← { query_parsed, results:[{ id, combined_score, match_reason }] }
   c. Fetch candidate info theo ids → return

3. ReactJS hiển thị kết quả với lý do match:
   ┌─────────────────────────────────────────┐
   │ Nguyen Van A — 82.1 pts                  │
   │ ✓ React: 4 năm kinh nghiệm              │
   │ ✓ Team lead: dẫn nhóm 5 người tại XYZ  │
   └─────────────────────────────────────────┘
```

**Lưu ý về filter:** Không áp `final_score > threshold` làm default — NL search có mục đích tìm "hidden gems" mà ranking thông thường bỏ sót. Chỉ filter `job_id` + `status=done`. HR có thể thêm filter tùy chọn trên UI.

---

## Complete Backend ↔ AI Flow

### Flow 1 — HR tạo Job

```
[.NET API]                              [AI Service]
    │
    │  POST /ai/parse-jd
    │  { "jd_text": "..." }
    │ ─────────────────────────────────────────────→
    │                                        Stage 1: LLM Extraction
    │                                        Claude claude-sonnet-4-6 → parsed_jd JSON
    │                                        Stage 2: Embedding
    │                                        OpenAI text-embedding-3-small → float[1536]
    │ ←─────────────────────────────────────────────
    │  { parsed_jd, jd_embedding }
    │
    ├─ INSERT jobs { title, description, parsed_jd, jd_embedding }
    └─ INSERT scoring_configs { job_id, defaults: 30/35/20/10/5 }
```

---

### Flow 2 — Ứng viên nộp CV

```
[ReactJS]          [.NET API]                         [AI Service]
    │                   │
    │  POST /apply       │
    │  { job_id,         │
    │    cv_file }       │
    │──────────────→     │
    │               INSERT application
    │               status = "processing"
    │                   │
    │                   │  POST /ai/parse-cv
    │                   │  multipart: cv_file (binary)
    │                   │ ─────────────────────────────→
    │                   │                        Stage 1: Document Processing
    │                   │                        PyMuPDF smart layout extract
    │                   │                        → quality score < 60? OCR fallback
    │                   │                        → clean_text()
    │                   │                        Stage 2: LLM Extraction
    │                   │                        Claude → parsed_cv JSON
    │                   │                        Stage 3: Embedding
    │                   │                        OpenAI → cv_embedding float[1536]
    │                   │ ←─────────────────────────────
    │                   │  { cv_raw_text, parsed_cv, cv_embedding }
    │                   │
    │                   │  POST /ai/score
    │                   │  {
    │                   │    parsed_cv,            ← vừa nhận
    │                   │    parsed_jd,            ← lấy từ DB
    │                   │    cv_embedding,         ← vừa nhận
    │                   │    jd_embedding,         ← lấy từ DB
    │                   │    weights,              ← lấy từ scoring_configs
    │                   │    cv_raw_text           ← vừa nhận
    │                   │  }
    │                   │ ─────────────────────────────→
    │                   │                        Stage 4: Scoring Engine
    │                   │                        D1: cosine_sim(cv_vec, jd_vec)
    │                   │                        D2: weighted skill match
    │                   │                        D3: experience years ratio
    │                   │                        D4: degree level map
    │                   │                        D5: keyword overlap
    │                   │                        → final = Σ(score_i × weight_i) × 100
    │                   │ ←─────────────────────────────
    │                   │  { final_score, scores:{...} }
    │                   │
    │               UPDATE application
    │               SET cv_raw_text, parsed_cv,
    │                   cv_embedding, score_*,
    │                   final_score, status="done"
    │                   │
    │ ←─────────────────│
    │  { final_score: 78.5,
    │    scores: { semantic:82, skills:75,
    │              experience:80,
    │              education:100, keywords:60 } }
```

---

### Flow 3 — HR đổi weights (no LLM)

```
[.NET API]                              [AI Service]
    │
    │  Validate sum(weights) == 1.0
    │  UPDATE scoring_configs
    │  SELECT applications WHERE job_id = {id}
    │    → chỉ lấy { id, score_semantic, score_skills,
    │                   score_experience, score_education, score_keywords }
    │
    │  POST /ai/recalculate
    │  {
    │    applications: [{ id, scores:{...} }, ...],
    │    weights: { semantic:0.20, skills:0.45, ... }
    │  }
    │ ─────────────────────────────────────────────→
    │                                        Pure math, no LLM:
    │                                        final = Σ(score_i × weight_i)
    │ ←─────────────────────────────────────────────
    │  { results: [{ id, final_score }, ...] }
    │
    │  Batch UPDATE applications SET final_score = ...
    │  Return new ranking (sorted DESC)
```

---

### Flow 4 — HR NL Search

```
[.NET API]                              [AI Service]
    │
    │  Hard filter: job_id + status="done"
    │  SELECT { id, cv_embedding, final_score, parsed_cv }
    │
    │  POST /ai/search
    │  {
    │    query: "React 3 năm, team lead",
    │    applications: [
    │      { id, cv_embedding, final_score, parsed_cv },
    │      ...
    │    ]
    │  }
    │ ─────────────────────────────────────────────→
    │                                        Stage 5: Query Parsing (LLM)
    │                                        Claude → structured filters JSON
    │                                        Stage 6: Query Embedding
    │                                        OpenAI → query_vector float[1536]
    │                                        Stage 7: Vector Similarity
    │                                        numpy cosine_sim(query_vec, cv_vec[i])
    │                                        Stage 8: Structured Filter
    │                                        Python filter trên parsed_cv JSON
    │                                        Stage 9: Re-rank
    │                                        combined = score×0.4 + sim×100×0.6
    │                                        Stage 10: Match Reason (LLM)
    │                                        Claude → explain top N results
    │ ←─────────────────────────────────────────────
    │  { query_parsed, results:[{ id, combined_score, match_reason }] }
    │
    │  Fetch candidate info theo ids
    │  Return full result về ReactJS
```

---

## RAG Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     INDEXING PHASE                               │
│              (chạy khi CV/JD được submit)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PDF/DOCX file                                                    │
│      │                                                            │
│      ▼  [STAGE 1 — Document Processing]                          │
│  PyMuPDF (fitz)                                                   │
│  ├─ extract_text_smart_layout()   ← 1-col vs 2-col detection     │
│  ├─ evaluate_extracted_text_quality()  ← score 0–100            │
│  └─ quality < 60 → pytesseract OCR  ← fallback cho scan PDF     │
│      │                                                            │
│      ▼  raw_text (clean)                                         │
│      │                                                            │
│      ▼  [STAGE 2 — Structured Extraction]                        │
│  Anthropic SDK → claude-sonnet-4-6                               │
│  ├─ CV prompt  → { skills[], work_experience[], education }      │
│  └─ JD prompt  → { required_skills[], min_exp, keywords[] }     │
│      │                                                            │
│      ▼  parsed JSON                                              │
│      │                                                            │
│      ▼  [STAGE 3 — Dense Embedding]                              │
│  OpenAI SDK → text-embedding-3-small                             │
│  ├─ input: full raw_text (không phải parsed JSON)                │
│  └─ output: float[1536]                                          │
│      │                                                            │
│      ▼  (trả về .NET → lưu PostgreSQL)                          │
│  { raw_text, parsed_json, embedding[1536] }                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     SCORING PHASE                                │
│              (chạy ngay sau indexing)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [STAGE 4 — Multi-Dimension Scoring]                             │
│  numpy + pure Python                                              │
│                                                                   │
│  D1 Semantic    numpy cosine_sim   cosine_sim(cv_vec, jd_vec)   │
│                 ─────────────────────────────────────────────    │
│  D2 Skills      set intersection   Σ(matched_weight)/Σ(total)  │
│                 ─────────────────────────────────────────────    │
│  D3 Experience  arithmetic         min(cv_years/jd_years, 1.0) │
│                 ─────────────────────────────────────────────    │
│  D4 Education   lookup table       {PhD:4, Master:3, Bach:2}   │
│                 ─────────────────────────────────────────────    │
│  D5 Keywords    string match       matched / total_keywords     │
│                                                                   │
│  final_score = Σ(Di × Wi) × 100                                 │
│                                                                   │
│  Default weights:                                                 │
│  semantic=0.30 | skills=0.35 | exp=0.20 | edu=0.10 | kw=0.05   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     RETRIEVAL PHASE                              │
│              (chạy khi HR NL search)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  NL query: "React 3 năm, team lead"                              │
│      │                                                            │
│      ▼  [STAGE 5 — Query Understanding]                          │
│  claude-sonnet-4-6 (Anthropic SDK)                               │
│  → { required_skills:[{React, min_years:3}],                    │
│      soft_skills:["leadership"] }                                │
│      │                                                            │
│      ▼  [STAGE 6 — Query Embedding]                              │
│  OpenAI text-embedding-3-small                                    │
│  → query_vector float[1536]                                      │
│      │                                                            │
│      ▼  [STAGE 7 — Vector Retrieval]                             │
│  numpy                                                            │
│  cosine_sim(query_vec, cv_vec[i]) for all applications          │
│  → similarity_score per CV                                       │
│      │                                                            │
│      ▼  [STAGE 8 — Metadata Filtering]                           │
│  pure Python filter trên parsed_cv JSON                          │
│  ├─ skill có trong cv.skills? → keep/drop                        │
│  └─ soft skill match trong descriptions? → boost                 │
│      │                                                            │
│      ▼  [STAGE 9 — Re-ranking]                                   │
│  combined_score = final_score × 0.4 + similarity × 100 × 0.6   │
│  sort DESC → top N                                               │
│      │                                                            │
│      ▼  [STAGE 10 — Augmented Generation]                        │
│  claude-sonnet-4-6                                               │
│  input: query + top N parsed_cv                                  │
│  → match_reason per candidate                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Contract (AI Service ↔ .NET)

### POST /ai/parse-jd

```json
Request:  { "jd_text": "string" }

Response: {
  "parsed_jd": {
    "required_skills": [{ "skill": "Python", "level": "mid", "weight": 2 }],
    "preferred_skills": [{ "skill": "Docker" }],
    "min_experience_years": 2,
    "education": { "degree": "Bachelor", "major": "Computer Science" },
    "responsibilities": ["..."],
    "keywords": ["FastAPI", "PostgreSQL", "Docker"]
  },
  "embedding": [0.123, ...]
}
```

### POST /ai/parse-cv

```
Request:  multipart/form-data — cv_file: binary (PDF hoặc DOCX)

Response: {
  "cv_raw_text": "string",
  "parsed_cv": {
    "skills": ["Python", "FastAPI", "Docker"],
    "work_experience": [
      { "company": "ABC", "role": "Backend Dev", "months": 18, "description": "..." }
    ],
    "education": { "degree": "Bachelor", "major": "SE", "gpa": 3.6 },
    "certifications": ["AWS Cloud Practitioner"],
    "projects": [{ "name": "...", "tech_stack": ["FastAPI", "Redis"], "description": "..." }]
  },
  "embedding": [0.456, ...]
}
```

### POST /ai/score

```json
Request: {
  "parsed_cv": { ... },
  "parsed_jd": { ... },
  "cv_embedding": [0.456, ...],
  "jd_embedding": [0.123, ...],
  "weights": { "semantic": 0.30, "skills": 0.35, "experience": 0.20, "education": 0.10, "keywords": 0.05 },
  "cv_raw_text": "string"
}

Response: {
  "final_score": 78.5,
  "scores": {
    "semantic": 82.0,
    "skills": 75.0,
    "experience": 80.0,
    "education": 100.0,
    "keywords": 60.0
  }
}
```

### POST /ai/recalculate

```json
Request: {
  "applications": [
    { "id": "uuid-1", "scores": { "semantic": 82.0, "skills": 75.0, "experience": 80.0, "education": 100.0, "keywords": 60.0 } }
  ],
  "weights": { "semantic": 0.20, "skills": 0.45, "experience": 0.20, "education": 0.10, "keywords": 0.05 }
}

Response: {
  "results": [
    { "id": "uuid-1", "final_score": 81.4 }
  ]
}
```

### POST /ai/search

```json
Request: {
  "query": "Tìm ứng viên React 3 năm, có kinh nghiệm team lead",
  "applications": [
    { "id": "uuid-1", "cv_embedding": [0.456, ...], "final_score": 78.5, "parsed_cv": { ... } }
  ]
}

Response: {
  "query_parsed": {
    "required_skills": [{ "skill": "React", "min_years": 3 }],
    "soft_skills": ["team lead", "leadership"]
  },
  "results": [
    {
      "id": "uuid-1",
      "similarity_score": 0.87,
      "combined_score": 82.1,
      "match_reason": "React 4 năm kinh nghiệm, từng dẫn nhóm 5 người tại XYZ"
    }
  ]
}
```

---

## Tại sao cần Structured Extraction thay vì Chunk + Embed

Embedding model đo **ngữ nghĩa văn bản**, không hiểu **giá trị số học**:

```
embed("5 years experience") ≈ embed("3 years experience")   # cosine ~0.98
embed("2 years") ≈ embed("10 years")                         # similarity cao
```

→ Cosine similarity không nói được "5 năm > 3 năm yêu cầu".

| Dimension     | Cần gì                             | Có từ embedding không?            |
| ------------- | ---------------------------------- | --------------------------------- |
| D1 Semantic   | Chủ đề CV ↔ JD có khớp không       | Được                              |
| D2 Skills     | Đúng skills nào có mặt             | Không — cần structured list       |
| D3 Experience | Tổng số năm làm việc               | Không — cần tính số               |
| D4 Education  | Degree level (Bach < Master < PhD) | Không — cần lookup                |
| D5 Keywords   | Keyword xuất hiện trong text       | Không cần embedding, string match |

**3 thứ .NET lưu sau mỗi CV:**

1. `cv_raw_text` — hiển thị + D5 keyword
2. `parsed_cv` JSON — D2, D3, D4 + NL search filter
3. `cv_embedding` float[1536] — D1 semantic + NL search similarity

---

## Tech Stack Summary

| Stage | Công việc              | Tech                                                 |
| ----- | ---------------------- | ---------------------------------------------------- |
| 1     | PDF/DOCX → clean text  | `PyMuPDF (fitz)`, `pytesseract`, `python-docx`       |
| 2     | Text → structured JSON | `Anthropic SDK` — `claude-sonnet-4-6`                |
| 3     | Text → vector          | `OpenAI SDK` — `text-embedding-3-small` (1536-dim)   |
| 4     | Scoring 5 dimensions   | `numpy` (cosine), pure Python (math)                 |
| 5     | NL query → filters     | `Anthropic SDK` — `claude-sonnet-4-6`                |
| 6     | Query → vector         | `OpenAI SDK` — `text-embedding-3-small`              |
| 7     | Vector similarity      | `numpy` — cosine over in-memory list                 |
| 8     | Structured filter      | Pure Python — filter trên `parsed_cv` JSON           |
| 9     | Re-ranking             | Pure Python — `final_score×0.4 + similarity×100×0.6` |
| 10    | Match reason           | `Anthropic SDK` — `claude-sonnet-4-6`                |

## Project Structure (AI Service)

```
d:\AIMatchingCV\
├── app/
│   ├── main.py                  # FastAPI app, mount routers
│   ├── config.py                # API keys (Anthropic, OpenAI)
│   │
│   ├── api/
│   │   ├── parse.py             # POST /ai/parse-jd, POST /ai/parse-cv
│   │   ├── score.py             # POST /ai/score
│   │   ├── recalculate.py       # POST /ai/recalculate
│   │   └── search.py            # POST /ai/search
│   │
│   └── services/
│       ├── pdf_extractor.py     # PyMuPDF smart layout + OCR fallback
│       ├── parser.py            # Claude: JD/CV text → structured JSON
│       ├── embedder.py          # OpenAI: text → float[1536]
│       ├── scorer.py            # 5-dimension scoring engine
│       └── nl_search.py         # query embed → cosine sim → re-rank
│
├── POC_CV_Matching/             # Notebooks + 8 CV PDF mẫu
├── requirements.txt
├── .env
├── Dockerfile
└── docker-compose.yml
```

## Dependencies

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
pymupdf                    # PDF extraction — smart layout 2-column
pytesseract                # OCR fallback cho scan PDF
pillow                     # image processing cho OCR
python-docx                # DOCX extraction
anthropic>=0.28.0          # Claude API
openai>=1.30.0             # text-embedding-3-small
numpy                      # cosine similarity
pydantic-settings          # config từ .env
python-multipart           # file upload
```
