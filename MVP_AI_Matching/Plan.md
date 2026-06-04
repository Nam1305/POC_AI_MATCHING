Complete Backend ↔ AI Flow
Flow 1 — HR tạo Job

[.NET API] [AI Service]
│
│ POST /ai/parse-jd
│ { "jd_text": "..." }
│ ─────────────────────────────────────────────→
│ Stage 1: LLM Extraction
│ Claude claude-sonnet-4-6 → parsed_jd JSON
│ Stage 2: Embedding
│ OpenAI text-embedding-3-small → float[1536]
│ ←─────────────────────────────────────────────
│ { parsed_jd, jd_embedding }
│
├─ INSERT jobs { title, description, parsed_jd, jd_embedding }
└─ INSERT scoring_configs { job_id, defaults: 30/35/20/10/5 }
Flow 2 — Ứng viên nộp CV (main flow, real-time)

[ReactJS] [.NET API] [AI Service]
│ │
│ POST /apply │
│ { job*id, │
│ cv_file } │
│──────────────→ │
│ INSERT application
│ status = "processing"
│ │
│ │ POST /ai/parse-cv
│ │ multipart: cv_file (binary)
│ │ ─────────────────────────────→
│ │ Stage 1: Document Processing
│ │ PyMuPDF smart layout extract
│ │ → quality score < 60? OCR fallback
│ │ → clean_text()
│ │ Stage 2: LLM Extraction
│ │ Claude → parsed_cv JSON
│ │ Stage 3: Embedding
│ │ OpenAI → cv_embedding float[1536]
│ │ ←─────────────────────────────
│ │ { cv_raw_text, parsed_cv, cv_embedding }
│ │
│ │ POST /ai/score
│ │ {
│ │ parsed_cv, ← vừa nhận
│ │ parsed_jd, ← lấy từ DB
│ │ cv_embedding, ← vừa nhận
│ │ jd_embedding, ← lấy từ DB
│ │ weights, ← lấy từ scoring_configs
│ │ cv_raw_text ← vừa nhận
│ │ }
│ │ ─────────────────────────────→
│ │ Stage 4: Scoring Engine
│ │ D1: cosine_sim(cv_vec, jd_vec)
│ │ D2: weighted skill match
│ │ D3: experience years ratio
│ │ D4: degree level map
│ │ D5: keyword overlap
│ │ → final = Σ(score_i × weight_i) × 100
│ │ ←─────────────────────────────
│ │ { final_score, scores:{...} }
│ │
│ UPDATE application
│ SET cv_raw_text, parsed_cv,
│ cv_embedding, score*\*,
│ final_score, status="done"
│ │
│ ←─────────────────│
│ { final_score: 78.5,
│ scores: { semantic:82, skills:75,
│ experience:80,
│ education:100, keywords:60 } }
Flow 3 — HR đổi weights (no LLM)

[.NET API] [AI Service]
│
│ Validate sum(weights) == 1.0
│ UPDATE scoring_configs
│ SELECT applications WHERE job_id = {id}
│ → chỉ lấy { id, score_semantic, score_skills,
│ score_experience, score_education, score_keywords }
│
│ POST /ai/recalculate
│ {
│ applications: [{ id, scores:{...} }, ...],
│ weights: { semantic:0.20, skills:0.45, ... }
│ }
│ ─────────────────────────────────────────────→
│ Pure math, no LLM:
│ final = Σ(score_i × weight_i)
│ ←─────────────────────────────────────────────
│ { results: [{ id, final_score }, ...] }
│
│ Batch UPDATE applications SET final_score = ...
│ Return new ranking (sorted DESC)
Flow 4 — HR NL Search

[.NET API] [AI Service]
│
│ Hard filter: job_id + status="done"
│ SELECT { id, cv_embedding, final_score, parsed_cv }
│
│ POST /ai/search
│ {
│ query: "React 3 năm, team lead",
│ applications: [
│ { id, cv_embedding, final_score, parsed_cv },
│ ... (toàn bộ CV của job, ~100 items)
│ ]
│ }
│ ─────────────────────────────────────────────→
│ Stage 1: Query Parsing (LLM)
│ Claude → structured filters JSON
│ Stage 2: Query Embedding
│ OpenAI → query_vector float[1536]
│ Stage 3: Vector Similarity
│ numpy cosine_sim(query_vec, cv_vec[i])
│ Stage 4: Structured Filter
│ Python filter trên parsed_cv JSON
│ Stage 5: Re-rank
│ combined = score×0.4 + sim×100×0.6
│ Stage 6: Match Reason (LLM)
│ Claude → explain top N results
│ ←─────────────────────────────────────────────
│ { query_parsed, results:[{ id, combined_score, match_reason }] }
│
│ Fetch candidate info theo ids
│ Return full result về ReactJS
RAG Pipeline Architecture

┌─────────────────────────────────────────────────────────────────┐
│ INDEXING PHASE │
│ (chạy khi CV/JD được submit) │
├─────────────────────────────────────────────────────────────────┤
│ │
│ PDF/DOCX file │
│ │ │
│ ▼ [STAGE 1 — Document Processing] │
│ PyMuPDF (fitz) │
│ ├─ extract_text_smart_layout() ← 1-col vs 2-col detection │
│ ├─ evaluate_extracted_text_quality() ← score 0-100 │
│ └─ quality < 60 → pytesseract OCR ← fallback cho scan PDF │
│ │ │
│ ▼ raw_text (clean) │
│ │ │
│ ▼ [STAGE 2 — Structured Extraction] │
│ Anthropic SDK → claude-sonnet-4-6 │
│ ├─ CV prompt → { skills[], work_experience[], education } │
│ └─ JD prompt → { required_skills[], min_exp, keywords[] } │
│ │ │
│ ▼ parsed JSON │
│ │ │
│ ▼ [STAGE 3 — Dense Embedding] │
│ OpenAI SDK → text-embedding-3-small │
│ ├─ input: full raw_text (không phải parsed JSON) │
│ └─ output: float[1536] │
│ │ │
│ ▼ (trả về .NET → lưu PostgreSQL) │
│ { raw_text, parsed_json, embedding[1536] } │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ SCORING PHASE │
│ (chạy ngay sau indexing) │
├─────────────────────────────────────────────────────────────────┤
│ │
│ [STAGE 4 — Multi-Dimension Scoring] │
│ numpy + pure Python │
│ │
│ D1 Semantic numpy.dot / norm cosine_sim(cv_vec, jd_vec) │
│ ────────────────────────────────────────── │
│ D2 Skills set intersection Σ(matched_weight)/Σ(total) │
│ ────────────────────────────────────────── │
│ D3 Experience arithmetic min(cv_years/jd_years, 1.0) │
│ ────────────────────────────────────────── │
│ D4 Education lookup table {PhD:4, Master:3, Bach:2} │
│ ────────────────────────────────────────── │
│ D5 Keywords string match matched / total_keywords │
│ │
│ final_score = Σ(Di × Wi) × 100 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ RETRIEVAL PHASE │
│ (chạy khi HR NL search) │
├─────────────────────────────────────────────────────────────────┤
│ │
│ NL query: "React 3 năm, team lead" │
│ │ │
│ ▼ [STAGE 5 — Query Understanding] │
│ claude-sonnet-4-6 (Anthropic SDK) │
│ → { required_skills:[{React, min_years:3}], │
│ soft_skills:["leadership"] } │
│ │ │
│ ▼ [STAGE 6 — Query Embedding] │
│ OpenAI text-embedding-3-small │
│ → query_vector float[1536] │
│ │ │
│ ▼ [STAGE 7 — Vector Retrieval] │
│ numpy │
│ cosine_sim(query_vec, cv_vec[i]) for i in all_applications │
│ → similarity_score per CV │
│ │ │
│ ▼ [STAGE 8 — Metadata Filtering] │
│ pure Python filter trên parsed_cv JSON │
│ ├─ skill "React" có trong cv.skills? → keep/drop │
│ └─ soft skill match trong descriptions? → boost score │
│ │ │
│ ▼ [STAGE 9 — Re-ranking] │
│ combined_score = final_score × 0.4 + similarity × 100 × 0.6 │
│ sort DESC → top N │
│ │ │
│ ▼ [STAGE 10 — Augmented Generation] │
│ claude-sonnet-4-6 │
│ input: query + top N parsed_cv │
│ → match_reason: "React 4 năm, dẫn team 5 người tại XYZ" │
└─────────────────────────────────────────────────────────────────┘
Tech Stack Summary per Stage
Stage Công việc Tech
1 PDF/DOCX → clean text PyMuPDF, pytesseract, python-docx
2 Text → structured JSON Anthropic SDK — claude-sonnet-4-6
3 Text → vector OpenAI SDK — text-embedding-3-small (1536-dim)
4 Scoring 5 dimensions numpy (cosine), pure Python (math)
5 NL query → filters Anthropic SDK — claude-sonnet-4-6
6 Query → vector OpenAI SDK — text-embedding-3-small
7 Vector similarity search numpy — cosine over in-memory list
8 Structured filter Pure Python — filter trên parsed_cv JSON
9 Re-ranking Pure Python — weighted formula
10 Match reason generation Anthropic SDK — claude-sonnet-4-6
