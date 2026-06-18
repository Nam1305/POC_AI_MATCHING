# AI Matching System — High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               CLIENT LAYER                                      │
│                                                                                 │
│        ┌─────────────────────────┐        ┌──────────────────────────┐         │
│        │     HR / Recruiter      │        │        Candidate          │         │
│        │      (React UI)         │        │     (Web / Mobile)        │         │
│        └───────────┬─────────────┘        └──────────┬───────────────┘         │
└────────────────────│──────────────────────────────────│────────────────────────┘
                     │ Manage jobs / Search              │ Submit application
                     ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         .NET BACKEND API                                        │
│               (Auth · Business Logic · Orchestration)                           │
│                                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │ POST          │  │ POST          │  │ PUT           │  │ POST          │   │
│  │ /api/jobs     │  │ /api/         │  │ /scoring-     │  │ /api/search   │   │
│  │ (create JD)   │  │ applications  │  │ config        │  │ (find CVs)    │   │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘   │
└──────────│──────────────────│──────────────────│──────────────────│───────────┘
           │                  │                  │                  │
           │      HTTP (Docker internal network) │                  │
           ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                   PYTHON FASTAPI — AI MICROSERVICE (Stateless)                  │
│                                                                                 │
│  ┌────────────────────────────── REST Endpoints ─────────────────────────────┐  │
│  │                                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐ │  │
│  │  │ /ai/parse-jd│  │ /ai/parse-cv│  │/ai/score │  │/ai/recal-│  │/ai/  │ │  │
│  │  │             │  │             │  │          │  │ culate   │  │search│ │  │
│  │  │ Text →      │  │ File URL →  │  │5-Dim     │  │Re-apply  │  │NL    │ │  │
│  │  │ Struct JD   │  │ Struct CV   │  │Scoring   │  │Weights   │  │Query │ │  │
│  │  └──────┬──────┘  └──────┬──────┘  └────┬─────┘  └────┬─────┘  └──┬───┘ │  │
│  └─────────│────────────────│──────────────│──────────────│────────────│─────┘  │
│            │                │              │              │            │        │
│  ┌─────────▼────────────────▼──────── Service Layer ─────▼────────────▼──────┐  │
│  │                                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  ┌────────────────┐   │  │
│  │  │pdf_extractor│  │   parser    │  │  embedder  │  │    scorer      │   │  │
│  │  │─────────────│  │─────────────│  │────────────│  │────────────────│   │  │
│  │  │ PyMuPDF     │  │ LLM Extract │  │Dense Vector│  │Semantic   30%  │   │  │
│  │  │ Tesseract   │──▶ Raw → JSON  │──▶float[1536] │  │Skills     35%  │   │  │
│  │  │ python-docx │  │             │  │float[384]  │  │Experience 20%  │   │  │
│  │  └─────────────┘  └─────────────┘  └────────────┘  │Education  10%  │   │  │
│  │                                                      │Keywords    5%  │   │  │
│  │  ┌─────────────────────────────┐                    └────────────────┘   │  │
│  │  │         nl_search           │                                          │  │
│  │  │─────────────────────────────│                                          │  │
│  │  │ Parse Query → Embed →       │                                          │  │
│  │  │ Vector Search → Re-rank →   │                                          │  │
│  │  │ LLM Explain                 │                                          │  │
│  │  └─────────────────────────────┘                                          │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
               ┌────────────────┴─────────────────┐
               ▼                                   ▼
┌──────────────────────────┐        ┌──────────────────────────────┐
│     LLM PROVIDERS        │        │      EMBEDDING PROVIDERS     │
│                          │        │                              │
│  ┌────────────────────┐  │        │  ┌────────────────────────┐  │
│  │  Anthropic Claude  │  │        │  │  OpenAI                │  │
│  │  sonnet-4-6        │  │        │  │  text-embedding-3-small│  │
│  │  ✅ Production      │  │        │  │  1536-dim              │  │
│  └────────────────────┘  │        │  │  ✅ Production          │  │
│                          │        │  └────────────────────────┘  │
│  ┌────────────────────┐  │        │                              │
│  │  Groq · Llama 3.1  │  │        │  ┌────────────────────────┐  │
│  │  8B Instant        │  │        │  │  SentenceTransformer   │  │
│  │  🆓 Dev / Free      │  │        │  │  all-MiniLM-L6-v2      │  │
│  └────────────────────┘  │        │  │  384-dim               │  │
│                          │        │  │  🆓 Local / Free        │  │
└──────────────────────────┘        │  └────────────────────────┘  │
                                    └──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                               DATA LAYER                                        │
│                                                                                 │
│   ┌─────────────────────────────────────┐   ┌───────────────────────────────┐  │
│   │            Database                 │   │       Cloud Storage           │  │
│   │─────────────────────────────────────│   │───────────────────────────────│  │
│   │  jobs         (parsed_jd, embedding)│   │  S3 / Cloudflare R2           │  │
│   │  applications (parsed_cv, scores)   │   │  PDF · DOCX files             │  │
│   │  scoring_configs (weights per job)  │   │                               │  │
│   └─────────────────────────────────────┘   └───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Scoring Engine — 5 Dimensions

```
  CV Embedding ──┐
                 ├──▶  D1 Semantic    (30%)  cosine_sim(CV_emb, JD_emb)
  JD Embedding ──┘

  Parsed CV ─────┐
                 ├──▶  D2 Skills      (35%)  Exact + Fuzzy + Category match
                 ├──▶  D3 Experience  (20%)  Ratio + Relevance + Recency
                 ├──▶  D4 Education   (10%)  Degree level comparison
  Parsed JD ─────┴──▶  D5 Keywords    ( 5%)  Substring match in raw text

                            │
                            ▼
              ┌─────────────────────────┐
              │      Final Score        │
              │   Σ(Dᵢ × Wᵢ) × 100     │
              │       0 – 100           │
              │  (Weights tunable by HR)│
              └─────────────────────────┘
```

---

## Flow Summary

| Flow           | Trigger                  | LLM?   | Output                             |
|----------------|--------------------------|--------|------------------------------------|
| **Parse JD**   | HR tạo job mới           | ✅     | `parsed_jd` + `jd_embedding`       |
| **Parse CV**   | Candidate nộp hồ sơ      | ✅     | `parsed_cv` + `cv_embedding`       |
| **Score**      | Sau khi parse xong       | ❌     | `final_score` + 5 dimension scores |
| **Recalculate**| HR điều chỉnh weights    | ❌     | Batch `final_score` mới            |
| **NL Search**  | HR tìm kiếm tự nhiên     | ✅ ×2  | Ranked results + match reasons     |
