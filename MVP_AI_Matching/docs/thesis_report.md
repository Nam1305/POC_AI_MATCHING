# Tổng hợp Đồ án Tốt nghiệp — MVP AI Matching System

> **Project:** AI-powered CV/JD Matching Microservice
> **Stack:** Python FastAPI · LLM (Gemini/Claude/Groq) · pgvector · .NET Backend
> **Cập nhật:** 2026-08-05
>
> Tài liệu này được đối chiếu trực tiếp với source code trong `app/`. Mọi công
> thức, hằng số, tên model đều là **giá trị đang chạy thật**, không phải thiết
> kế dự kiến. Các cơ chế từng thiết kế nhưng chưa cài đặt được liệt kê riêng ở
> [mục 7](#7-phạm-vi-hiện-tại--hạn-chế).

---

## MỤC LỤC

1. [Kiến trúc hệ thống](#1-kiến-trúc-hệ-thống)
2. [Database Schema](#2-database-schema)
3. [Các Pipeline xử lý](#3-các-pipeline-xử-lý)
4. [Công thức toán học](#4-công-thức-toán-học)
5. [Cơ sở lý thuyết & Research Papers](#5-cơ-sở-lý-thuyết--research-papers)
6. [Kiểm thử & Đánh giá](#6-kiểm-thử--đánh-giá)
7. [Phạm vi hiện tại & Hạn chế](#7-phạm-vi-hiện-tại--hạn-chế)
8. [Gợi ý cấu trúc Chapter](#8-gợi-ý-cấu-trúc-chapter)

---

## 1. KIẾN TRÚC HỆ THỐNG

### 1.1 System Architecture — 4 Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                 │
│          Web App / Mobile  ─────  HR Dashboard                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP/REST
┌──────────────────────────────▼──────────────────────────────────────┐
│                    .NET BACKEND LAYER                               │
│   Business Logic · Auth · DB Read/Write · File Storage (S3/R2)     │
│   PostgreSQL + pgvector (resumes, jobs, applications)               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP (internal Docker network)
┌──────────────────────────────▼──────────────────────────────────────┐
│              PYTHON AI MICROSERVICE (Stateless)                     │
│                                                                     │
│  POST /ai/parse-jd  ──►  parser → geocode → embedder               │
│  POST /ai/parse-cv  ──►  pdf_extractor → parser → geocode → embed  │
│  POST /ai/score     ──►  scorer (5-dimension) ‖ evaluator          │
│  POST /ai/evaluate  ──►  evaluator (Python analysis + LLM narrative)│
│  GET  /health                                                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                   EXTERNAL PROVIDERS                                │
│   LLM      : Gemini 2.5 Flash | Claude | Groq Llama  (đổi qua .env) │
│   Embedding: gemini-embedding-001 (3072-dim)                        │
│   Geocode  : Nominatim (OpenStreetMap)  — free, no key             │
│   Routing  : OSRM public demo server    — free, no key             │
└─────────────────────────────────────────────────────────────────────┘
```

**Nguyên tắc thiết kế:**

- Python AI service là **stateless** — nhận input, trả output, không đọc/ghi DB,
  không có auth, không cache.
- .NET backend là nơi **duy nhất** tương tác với PostgreSQL.
- LLM provider đổi qua `.env` (`LLM_PROVIDER`) không cần sửa code. Embedding
  hiện chỉ hỗ trợ Gemini.
- **Mọi phép tính điểm là Python thuần** — không giao số học cho LLM.

### 1.2 Full System Flow

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLOW 1 — UPLOAD CV
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Candidate] POST /api/resumes (file.pdf)
    │
[.NET] Upload S3/R2 → presigned URL
    │
    ▼
[.NET] POST http://ai-service/ai/parse-cv { "cv_url": "https://..." }
    │
    ▼
[Python AI]
    ├─ Download file (httpx, retry 3× với backoff 1.5s/3s/4.5s)
    ├─ Stage 1: pdf_extractor.extract_text()  →  cv_raw_text
    │     PyMuPDF smart layout → quality score → OCR nếu < 60
    ├─ Stage 2: parser.parse_cv()  →  ParsedCV
    │     LLM extract (kèm is_resume: true/false, cùng 1 call)
    │     is_resume=false → bỏ qua completeness retry, trả sớm
    │     Ngược lại → completeness check → retry nếu thiếu
    │     Pydantic: Python tính months, lọc entry LLM bịa
    │     Nominatim geocode(raw_address) → candidate_location.{lat,lng}
    └─ Stage 3: embedder.embed(parsed_cv.build_embed_text())
          →  cv_embedding [3072 float]
    │
    return { results: [{ url, cv_raw_text, parsed_cv, cv_embedding, error }] }
    │
    ▼
[.NET] INSERT INTO resumes (cv_raw_text, parsed_cv JSONB, cv_embedding vector(3072))


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLOW 2 — CREATE JOB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[HR] POST /api/jobs { jd_text }
    │
    ▼
[Python AI] POST /ai/parse-jd
    ├─ Stage 2: parser.parse_jd()  →  ParsedJD
    │     LLM extract 3 tier skill (required + weight/OR-alternatives,
    │        preferred, nice_to_have), responsibilities,
    │        work_location, work_mode
    │     Pydantic: lọc soft-skill chung chung khỏi cả 3 tier
    │     Nominatim geocode(raw_address ?? city) → work_location.{lat,lng}
    └─ Stage 3: embedder.embed(parsed_jd.build_embed_text())
          →  jd_embedding [3072 float]
    │
[.NET] INSERT INTO jobs (parsed_jd JSONB, jd_embedding vector(3072))
       INSERT INTO scoring_configs (job_id, defaults 30/35/20/10/5)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLOW 3 — SCORE (AI Matching)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[.NET] SELECT parsed_cv, cv_embedding FROM resumes
       SELECT parsed_jd, jd_embedding FROM jobs
       SELECT weights FROM scoring_configs
    │
    ▼
[Python AI] POST /ai/score { parsed_cv, parsed_jd, cv_embedding,
                             jd_embedding, weights, include_narrative }
    │
    ├── asyncio.to_thread ──► scorer.calculate_score()   [pure Python, ~1ms]
    │      D1 Semantic   : normalize_cosine(cosine_sim(cv_emb, jd_emb))
    │      D2 Skills     : cascade 4 tầng, chấm nhị phân, trên cả 3 tier
    │      D3 Experience : (per-skill depth + cv_years/jd_min_years) / 2
    │      D4 Education  : min(cv_level / jd_level, 1.0)
    │      D5 Location   : OSRM driving-time trên lat/lng đã geocode
    │      final = Σ(Dᵢ × Wᵢ) × 100
    │
    └── song song ───────► evaluator.evaluate_cv_for_job()
           _analyze_skills / _analyze_experience / _analyze_education  [Python]
           _is_valid_cv  [Python — is_resume + emptiness check, tính SAU 3 phân
                          tích trên, nhưng luôn chạy TRƯỚC khi gọi LLM narrative]
           _llm_narrative  [chỉ khi include_narrative=true VÀ is_valid_cv=true;
                            ngược lại narrative = thông báo cố định, không gọi LLM]
    │
    return { final_score, scores{5}, weights_used, evaluation }
    │
[.NET] UPDATE applications SET final_score, scores JSONB, evaluation JSONB


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLOW 4 — HR XEM NHẬN XÉT CHI TIẾT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[HR] click 1 ứng viên
    │
[Python AI] POST /ai/evaluate { parsed_cv, parsed_jd }
    ├─ 3 phân tích Python (skills / experience / education)
    ├─ _is_valid_cv(parsed_cv) — is_resume=false hoặc CV rỗng toàn bộ?
    └─ is_valid_cv=true  → 1 LLM call → narrative tiếng Việt
       is_valid_cv=false → narrative = thông báo cố định, KHÔNG gọi LLM
    │
    return { skill_details[], missing_must_have[], missing_preferred[],
             missing_nice_to_have[], bonus_skills[], skill_match_rate,
             experience_verdict, experience_detail, education_verdict,
             is_valid_cv, narrative }
```

### 1.3 Vì sao tách AI service khỏi .NET

| Tiêu chí | Lý do |
| --- | --- |
| **Hệ sinh thái** | PyMuPDF, Tesseract, numpy, SDK của LLM đều mạnh nhất ở Python |
| **Scale độc lập** | Parse CV nặng CPU (OCR) và nặng I/O (LLM) — scale riêng khỏi web tier |
| **Stateless** | Không DB, không session → scale ngang tùy ý, restart không mất dữ liệu |
| **Ranh giới rõ** | Đổi model/provider AI không đụng tới business logic và schema DB |

---

## 2. DATABASE SCHEMA

> Schema thuộc phía .NET. AI service không đọc/ghi DB — phần này mô tả nơi
> **lưu trữ** output của AI service.

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│           resumes               │     │              jobs                │
├─────────────────────────────────┤     ├─────────────────────────────────┤
│ id            UUID  PK          │     │ id            UUID  PK          │
│ candidate_id  UUID              │     │ employer_id   UUID              │
│ cv_raw_text   TEXT              │     │ jd_text       TEXT              │
│ parsed_cv     JSONB             │     │ parsed_jd     JSONB             │
│ cv_embedding  vector(3072)      │     │ jd_embedding  vector(3072)      │
│ embed_model   VARCHAR(50)       │     │ embed_model   VARCHAR(50)       │
│ embed_version VARCHAR(20)       │     │ embed_version VARCHAR(20)       │
│ created_at    TIMESTAMPTZ       │     │ created_at    TIMESTAMPTZ       │
└───────────────┬─────────────────┘     └───────────────┬─────────────────┘
                │                                       │
                │           ┌───────────────────────────┤
                │           │                           │
                ▼           ▼                           ▼
┌───────────────────────────────────────────┐  ┌──────────────────────────┐
│              applications                  │  │     scoring_configs      │
├───────────────────────────────────────────┤  ├──────────────────────────┤
│ id            UUID  PK                    │  │ job_id      UUID  PK/FK  │
│ resume_id     UUID  FK → resumes          │  │ w_semantic  FLOAT  0.30  │
│ job_id        UUID  FK → jobs             │  │ w_skills    FLOAT  0.35  │
│ final_score   FLOAT                       │  │ w_experience FLOAT 0.20  │
│ scores        JSONB                       │  │ w_education FLOAT  0.10  │
│   { semantic, skills, experience,        │  │ w_location  FLOAT  0.05  │
│     education, location }                │  │ CHECK(sum = 1.0)         │
│ weights_used  JSONB                       │  └──────────────────────────┘
│ evaluation    JSONB                       │
│   { skill_details[], missing_must_have[],│
│     missing_preferred[],                 │
│     missing_nice_to_have[],              │
│     bonus_skills[], skill_match_rate,    │
│     experience_verdict, experience_detail│
│     education_verdict, is_valid_cv,      │
│     narrative }                          │
│ status        VARCHAR(20)                 │
│ scored_at     TIMESTAMPTZ                 │
└───────────────────────────────────────────┘
```

**SQL tạo bảng:**

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE resumes (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id  UUID,
    cv_raw_text   TEXT,
    parsed_cv     JSONB          NOT NULL,
    cv_embedding  vector(3072),                        -- NULL nếu embed lỗi
    embed_model   VARCHAR(50)    DEFAULT 'gemini-embedding-001',
    embed_version VARCHAR(20)    DEFAULT 'v2-no-skills',
    created_at    TIMESTAMPTZ    DEFAULT now()
);

CREATE TABLE jobs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employer_id   UUID,
    jd_text       TEXT,
    parsed_jd     JSONB          NOT NULL,
    jd_embedding  vector(3072),
    embed_model   VARCHAR(50)    DEFAULT 'gemini-embedding-001',
    embed_version VARCHAR(20)    DEFAULT 'v2-no-skills',
    created_at    TIMESTAMPTZ    DEFAULT now()
);

CREATE TABLE scoring_configs (
    job_id        UUID PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    w_semantic    FLOAT NOT NULL DEFAULT 0.30,
    w_skills      FLOAT NOT NULL DEFAULT 0.35,
    w_experience  FLOAT NOT NULL DEFAULT 0.20,
    w_education   FLOAT NOT NULL DEFAULT 0.10,
    w_location    FLOAT NOT NULL DEFAULT 0.05,
    CONSTRAINT weights_sum_to_one CHECK (
        abs(w_semantic + w_skills + w_experience + w_education + w_location - 1.0) < 1e-6
    )
);

CREATE TABLE applications (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id     UUID REFERENCES resumes(id) ON DELETE CASCADE,
    job_id        UUID REFERENCES jobs(id)    ON DELETE CASCADE,
    final_score   FLOAT,
    scores        JSONB,
    weights_used  JSONB,
    evaluation    JSONB,
    status        VARCHAR(20) DEFAULT 'processing',
    scored_at     TIMESTAMPTZ DEFAULT now()
);
```

**Ghi chú thiết kế:**

- **`vector(3072)`** — khớp với `gemini-embedding-001`. `cv_embedding` và
  `jd_embedding` **phải cùng model và cùng số chiều** thì cosine mới có nghĩa.
- **`embed_version`** — lưu `EMBED_TEXT_VERSION` (`"v2-no-skills"`). Vector được
  tính từ *shape text* nào thì phải so với vector tính từ **cùng shape đó**;
  đổi `build_embed_text()` mà quên bump version sẽ khiến hệ thống âm thầm so
  hai loại vector khác nhau.
- **`lat`/`lng` nằm trong JSONB**, không tách cột riêng — chúng được geocode
  **một lần tại parse-time** (giống embedding) và chỉ được đọc lại, không query.
- **Không có cột `penalty_*`** — hệ thống hiện **không áp hard-rule penalty**.
  `missing_must_have` được **báo cáo** trong `evaluation` để HR nhìn thấy, chứ
  không trừ điểm tự động.
- **`weights_used`** lưu bộ trọng số thực sự áp dụng cho lần chấm đó → điểm số
  cũ vẫn tái lập được sau khi HR đổi cấu hình.
- **Index pgvector** chỉ cần khi triển khai tìm kiếm vector quy mô lớn. Lưu ý
  kỹ thuật đáng nêu trong báo cáo: kiểu `vector` của pgvector **lưu** được tới
  16.000 chiều nhưng **index** (`ivfflat`, `hnsw`) chỉ hỗ trợ tối đa **2.000
  chiều** — vector 3072 chiều **không index trực tiếp được**. Ba phương án:
  (a) giữ nguyên như hiện tại — chấm điểm theo **cặp CV↔JD cụ thể**, không cần
  ANN index; (b) dùng kiểu `halfvec` (pgvector ≥ 0.7) — nửa độ chính xác, index
  được tới 4.000 chiều; (c) lưu thêm cột truncate 1536 chiều làm index tìm kiếm
  thô rồi re-rank bằng vector đầy đủ — khả thi vì `gemini-embedding-001` theo
  hướng Matryoshka nên **prefix của vector vẫn là embedding hợp lệ**.

---

## 3. CÁC PIPELINE XỬ LÝ

### 3.1 Stage 1 — Document Processing (`pdf_extractor.py`)

```
file bytes (tải từ S3/R2 URL)
    │
    ├─ .docx → python-docx: đọc paragraphs + table cells
    │
    └─ .pdf  → PyMuPDF đọc từng text block
         │
         ├─ Đếm block: left_count (center_x < 45% width)
         │             right_count (center_x > 55% width)
         │
         ├─ is_two_col = (left_count ≥ 2) AND (right_count ≥ 2)
         │
         ├─ 1 cột : đọc theo (y0, x0) tăng dần
         │
         └─ 2 cột : header (y0 < 16% height) → cột PHẢI → cột TRÁI
                    (giữ đúng reading order của CV dạng sidebar)
         │
         ▼
    Quality Score (0–100), điểm khởi đầu 100:
         - len(text) < 100 chars       → -60
         - word_count < 30             → -30
         - tỷ lệ ký tự "�" > 2%        → -20
         - avg word length < 2 hoặc > 15 → -15
         │
         ├─ score ≥ 60 → dùng text từ PyMuPDF
         └─ score < 60 → OCR fallback
                         rasterize 200 DPI → Tesseract (lang="eng+vie")
    │
    ▼
clean_text(): \x00 → space · gộp space/tab · gộp 3+ newline → 2 · strip
```

**Vì sao cần xử lý 2 cột:** CV dạng sidebar (cột trái = kỹ năng/liên hệ, cột
phải = kinh nghiệm) nếu đọc thuần theo tọa độ `y` sẽ **trộn lẫn hai cột** —
LLM nhận được văn bản đứt đoạn, trích xuất sai. Đọc cột phải trước vì đó
thường là nội dung chính (kinh nghiệm làm việc).

### 3.2 Stage 2 — LLM Parsing với Retry (`parser.py`, `llm_client.py`)

```
cv_text
    │
    ▼
LLM call — CV_EXTRACT_PROMPT (temperature=0)
    │   provider theo .env: gemini (response_format=json_object)
    │                     | anthropic (bóc code fence thủ công)
    │                     | groq (response_format=json_object)
    │   extract: is_resume (bool), name, summary, skills[], work_experience[],
    │            education[], projects[], certifications[], languages[],
    │            candidate_location
    │   is_resume: LLM tự đánh giá "đây có phải CV/hồ sơ ứng viên không"
    │              (false cho research paper, hóa đơn, hợp đồng...) — cùng
    │              1 lần gọi, không tốn thêm LLM call
    │   LLM chỉ trả date STRING ("YYYY-MM"), KHÔNG được tính months
    │
    ▼
JSON repair (llm_client._parse_llm_json):
    json.loads → strip trailing comma → json_repair.loads → raise
    │
    ▼
Pydantic validation (schemas.py):
    ├─ _normalize_degree   : "Bachelor of Software Eng." → bachelor
    │                        (khớp chuỗi con: phd/doctorate, master/msc/mba,
    │                         bachelor/bsc/beng, associate, high school/phổ thông)
    ├─ _set_current_and_months:
    │      is_current = end ∈ {present, nay, now, current}
    │      months     = _diff_months(start, end)   ← PYTHON tính
    ├─ _filter_empty_entries:
    │      giữ work entry khi có company, HOẶC role + (description hoặc start)
    │      → loại placeholder LLM bịa: {role:"Intern", company:"", start:""}
    └─ _normalize_certs    : dict {name/title} → string
    │
    ▼
is_resume == false ?
    │ YES → bỏ qua completeness check + retry (không có gì thật để "cứu" —
    │        tài liệu không phải CV), nhảy thẳng xuống return ParsedCV
    │ NO  ↓
Completeness check:
    work_experience == []  OR  skills == []  ?
         │ YES
         ▼
    asyncio.gather(                        ← chạy song song, không cộng dồn latency
        _retry_work_experience(cv_text),   ← prompt ngắn, chỉ hỏi work history
        _retry_skills(cv_text)             ← prompt ngắn, chỉ hỏi skills
    )
    Chỉ ghi đè nếu retry ra kết quả KHÁC RỖNG (không làm mất dữ liệu đã có)
    │
    ▼
Geocode (nếu có raw_address):
    asyncio.to_thread(Nominatim.geocode)
    ├─ thử "{address}, Vietnam"
    ├─ nếu trượt → thử "{segment cuối}, Vietnam"  (thường là tên thành phố)
    └─ lỗi/không thấy → (None, None), KHÔNG raise
    │
    ▼
ParsedCV hoàn chỉnh
```

**JD parsing** dùng `JD_EXTRACT_PROMPT` với 4 quy tắc đáng chú ý:

1. **OR-group:** "React.js, TypeScript, hoặc Vue.js" → **một** entry
   `{skill: "React.js", weight: 3, alternatives: ["TypeScript", "Vue.js"]}`,
   không tách thành 3 requirement độc lập.
2. **3 tier skill** — `required_skills` / `preferred_skills` /
   `nice_to_have_skills`, ánh xạ đúng 3 dòng tag mà .NET ghép vào `jd_text`
   (`Required Skills:` / `Preferred Skills:` / `Nice to Have Skills:`, mirror
   bảng `tags` bên BE). **Cả 3 tier đều tham gia D2** với trọng số giảm dần
   (xem [3.5](#35-d2--chi-tiết-pipeline-so-khớp-kỹ-năng-skill_matcherpy)) — đây
   là thay đổi so với thiết kế cũ, khi `preferred_skills` chỉ để hiển thị.
3. **Structured fields thắng prose + chống trùng tier.** `jd_text` là chuỗi
   ghép từ các trường DB cố định, nên prompt bắt LLM: copy **nguyên văn** skill
   từ 3 dòng tag vào đúng tier của chúng (skill trong dòng tag đã canonical sẵn,
   và luôn có `weight = 3` với tier required), chỉ khai thác thêm skill từ prose
   khi nó **chưa** xuất hiện ở bất kỳ dòng tag nào. Đây là **rào chắn duy nhất**
   chống một skill bị đếm ở 2 tier — **trong code không có bước dedup chéo tier**.
4. **Lọc non-skill:** danh sách chặn `GENERIC_NON_SKILLS` (44 mục: "teamwork",
   "problem solving", "programming fundamentals"...) được áp ở tầng Pydantic
   (`_drop_generic_skills`, quét **cả 3 tier**). Lý do: những mục này **không
   bao giờ khớp được** với CV, nên nếu giữ lại thì **mọi** ứng viên đều bị một
   "missing must-have" ảo và `skill_match_rate` bị kéo xuống một cách hệ thống.

**Vì sao Python tính `months` chứ không phải LLM:** LLM có thể lệch ±1–2 tháng
do hallucinate; số học thuần Python luôn chính xác và **tái lập được**.

### 3.3 Stage 3 — Embedding (`embedder.py`)

```
ParsedCV.build_embed_text()  /  ParsedJD.build_embed_text()
    │
    ▼
gemini-embedding-001  (gọi qua endpoint OpenAI-compatible của Google,
                       chạy trong run_in_executor để không chặn event loop)
    │
    ▼
vector [3072 float]
```

**Nội dung được embed — có chọn lọc:**

| | Đưa vào | **Cố ý loại bỏ** |
| --- | --- | --- |
| **CV** | `summary`; `role at company: description` (job mới nhất trước); `Project: name + description`; học vấn; certifications; languages | `skills[]`, mọi `work_experience[].tech_stack`, mọi `projects[].tech_stack` |
| **JD** | `title`; `responsibilities`; "minimum N years"; "Education: X or above" | `required_skills[]`, `preferred_skills[]`, `nice_to_have_skills[]` |

**Lý do (quan trọng cho phần bảo vệ):** so khớp kỹ năng là nhiệm vụ của D2. Nếu
token kỹ năng cũng nằm trong text được embed thì **cùng một tín hiệu được tính
hai lần** ở hai chiều điểm — trọng số hiệu dụng của "kỹ năng" thành 0.30 + 0.35
thay vì 0.35. Mô hình cộng có trọng số (SAW) yêu cầu các tiêu chí **độc lập ưu
tiên**; embed skill vào D1 phá vỡ giả định đó. Vì vậy D1 chỉ đo **narrative
fit** — vai trò, phạm vi trách nhiệm, bối cảnh nghiệp vụ.

Work experience được **sắp xếp job mới nhất trước** để embedding nghiêng về ngữ
cảnh gần đây thay vì các job cũ.

### 3.4 Stage 4 — 5-Dimension Scoring Engine (`scorer.py`)

```
┌──────────────────────────────────────────────────────────────┐
│  D1 Semantic (W = 0.30)                                      │
│  raw = cosine_sim(cv_embedding, jd_embedding)                │
│  D1  = clamp((raw - COSINE_MIN)/(COSINE_MAX - COSINE_MIN),0,1)│
│  Hiện tại: COSINE_MIN=0.0, COSINE_MAX=1.0 → không kéo giãn   │
│  Thiếu 1 trong 2 embedding → D1 = 0.5 (trung lập)            │
├──────────────────────────────────────────────────────────────┤
│  D2 Skills (W = 0.35)                                        │
│  Nguồn CV: skills[] + work_exp.tech_stack + proj.tech_stack  │
│            + languages + certifications (tách sub-token)     │
│  Nguồn JD: CẢ 3 tier (evaluate_tiers), trọng số wᵢ:          │
│    required_skills[i]  → req.weight = 3 luôn (LLM luôn gán 3)│
│    preferred_skills[i] → 2   (PREFERRED_SKILL_WEIGHT)        │
│    nice_to_have[i]     → 1   (NICE_TO_HAVE_SKILL_WEIGHT)     │
│  Mỗi required_skill là OR-group {skill} ∪ alternatives:      │
│    Layer 0  direct match (raw, lowercase)         → 1.0      │
│    Layer 1  canonical hóa 2 phía (skill_data)     → 1.0      │
│    Layer 2  entailment (skill_implies, đã đóng)   → 1.0      │
│    Layer 3  fuzzy SequenceMatcher ≥ 0.85          → 1.0      │
│    phụ      proficiency ordinal (JLPT/TOEIC/...)  → 1.0/0.0  │
│    không tầng nào thỏa                            → 0.0      │
│  D2 = Σ(wᵢ · mᵢ) / Σ(wᵢ)      wᵢ ∈ {1,2,3}, mᵢ ∈ {0,1}     │
│  JD trống ở CẢ 3 tier → D2 = 1.0                             │
├──────────────────────────────────────────────────────────────┤
│  D3 Experience (W = 0.20)                                    │
│  D3 = (S_skill + S_years) / 2   khi JD có required_skills    │
│    S_skill = Σ(wᵣ·min(Mᵣ/(12·jd_years),1)) / Σ(wᵣ)  — theo   │
│      TỪNG required_skill, Mᵣ = số tháng CV làm skill đó      │
│    S_years = min(cv_total_years / jd_min_years, 1.0)         │
│  JD không có required_skills → D3 = S_years một mình         │
│  cv_total_years tính bằng MERGE INTERVAL (job song song      │
│    không bị đếm 2 lần)                                       │
│  JD không yêu cầu số năm → D3 = 1.0                          │
│  S_years làm SÀN cho S_skill — tránh D3=0 chỉ vì CV lệch     │
│    đúng 1 tech stack dù vẫn nhiều năm kinh nghiệm cùng ngành │
├──────────────────────────────────────────────────────────────┤
│  D4 Education (W = 0.10)                                     │
│  D4 = min(cv_degree_level / jd_degree_level, 1.0)           │
│  high_school=1, associate=2, bachelor=3, master=4, phd=5,     │
│  other=1                                                     │
│  JD không yêu cầu bằng → 1.0 ; CV không có bằng → 0.5       │
├──────────────────────────────────────────────────────────────┤
│  D5 Location + Work Mode (W = 0.05)                          │
│  JD remote → 1.0 ; CV willing_to_relocate → 1.0             │
│  thiếu lat/lng → 0.5 ; OSRM lỗi 2 lần → 0.5                 │
│  else: t = OSRM duration (phút)                              │
│        T_max = 45 (onsite) / 75 (hybrid)                     │
│        D5 = round(max(0, 1 - t/T_max), 3)                    │
└──────────────────────────────────────────────────────────────┘
                    │
                    ▼
            final = Σ(Dᵢ × Wᵢ) × 100      (làm tròn 1 chữ số thập phân)
            scores[i] = round(Dᵢ × 100, 1)
```

**Quy tắc xuyên suốt — "thiếu dữ liệu → 0.5, không phạt":** ứng viên không bị
trừ điểm vì hệ thống không trích xuất/geocode được thông tin. Áp dụng cho D1
(thiếu embedding), D4 (CV không ghi bằng cấp), D5 (thiếu tọa độ hoặc OSRM lỗi).
Ngược lại, khi **JD không yêu cầu** thì chiều đó = **1.0** (không có yêu cầu thì
không thể không đạt).

### 3.5 D2 — Chi tiết pipeline so khớp kỹ năng (`skill_matcher.py`)

Đây là thành phần có hàm lượng thuật toán cao nhất của hệ thống.

```
              ┌─────────────────────────────────────────┐
              │  build_cv_context(cv)  — chạy 1 LẦN     │
              │  cho cả JD, tránh lặp canonical hóa     │
              ├─────────────────────────────────────────┤
              │  raw           : skill thô đã lowercase │
              │  canonical     : đã canonical hóa       │
              │  canonical_src : canonical → skill gốc  │
              │  implied       : union mọi skill kéo theo│
              │  implied_src   : implied → skill gốc    │
              └────────────────┬────────────────────────┘
                               │
   ┌───────────────────────────▼────────────────────────────┐
   │  evaluate_tiers(jd, ctx) — duyệt CẢ 3 tier skill        │
   │  required  → evaluate_group()  (OR-group aware)         │
   │              = max theo (_LAYER_RANK, credit) trên      │
   │                toàn bộ {skill} ∪ alternatives           │
   │  preferred / nice_to_have → evaluate_name() (string phẳng)│
   │  Trả TierResult(label, weight, tier, match) — nguồn DUY  │
   │  NHẤT cho cả scorer.score_skills lẫn evaluator          │
   └───────────────────────────┬────────────────────────────┘
                               │
                  evaluate_name(jd_skill, ctx)
                               │
      ┌────────────────────────┼────────────────────────┐
      ▼                        ▼                        ▼
  Layer 0                   Layer 1                 Layer 2
  n ∈ ctx.raw ?          resolve_canonical(n)    canon ∈ ctx.implied ?
  exact, rẻ nhất          ∈ ctx.canonical ?      "biết Django ⟹ Python"
  rank 5                  rank 4                 rank 3
      │                        │                        │
      └────────────────────────┼────────────────────────┘
                               ▼
                      Layer 3 — fuzzy ≥ 0.85
                      (BỎ QUA nếu n là token trình độ ngôn ngữ)
                      rank 2
                               │
                               ▼
                  Tầng phụ — proficiency ordinal
                  cùng framework + cv_rank ≥ jd_rank
                  rank 1  →  matched / missing (verdict dứt điểm)
                               │
                               ▼
                          missing (rank 0)
```

**Chuẩn hóa format (`to_stackoverflow_format`)** — bắc cầu giữa output LLM
(Title Case, có space) và định dạng tag Stack Overflow (lowercase, space →
hyphen). Sinh **6 biến thể** theo thứ tự ưu tiên, dừng ở biến thể **đầu tiên**
tìm thấy trong `skill_data.json`:

```
"ASP.NET Core" → ["asp.net core", "asp.net-core", "asp.netcore",
                  "aspnet core", "aspnet-core", "aspnetcore"]
"Node.js"      → ["node.js", "node.js", "node.js", "nodejs", ...]  (dedup giữ thứ tự)
```

**Dữ liệu tĩnh:**

| File | Quy mô | Nguồn | Vai trò |
| --- | --- | --- | --- |
| `skill_data.json` | **9.524 entry** (3.988 canonical + 5.536 synonym) | Stack Exchange API: `/tags` + `/tags/{tags}/synonyms`, + bổ sung thủ công theo domain | Layer 1 |
| `skill_implies.json` | **1.505 key / 1.787 cạnh** (sau khi đóng bắc cầu) | Viết tay + `close_implies.py` | Layer 2 |

Trong `skill_data.json`, `value = null` nghĩa là **chính key đó đã là canonical**
(không phải "bỏ qua") — chi tiết dễ hiểu nhầm khi đọc dữ liệu.

**Pipeline dựng dữ liệu (offline, chạy tay, commit output):**

```
crawl_so_tags.py                → so_raw_data.json   (phân trang toàn bộ tag, loại collective tag)
build_skill_data.py             → skill_data.json    (batch 20 tag/request → map synonym → canonical)
add_misc_skills.py              → bổ sung thủ công các skill thiếu
add_qa_skills.py                → bổ sung nhóm QA/testing
add_ai_python_skills.py         → bổ sung hệ sinh thái AI/Python (package ⟹ Python)
add_devops_support_qa_skills.py → bổ sung DevOps / IT support / QA
close_implies.py                → skill_implies.json (đóng bắc cầu — CHẠY CUỐI CÙNG)
```

Các script `add_*.py` đều **idempotent** (chạy lại không nhân đôi dữ liệu) và
chỉ thêm cạnh entailment **bảo thủ** (package → framework/ngôn ngữ trực tiếp của
nó). Bắt buộc chạy `close_implies.py` sau cùng, nếu không test bất biến nhóm L
sẽ fail.

**Bao đóng bắc cầu (`close_implies.py`):**

```python
def transitive_closure(graph):
    closed = {k: set(v) for k, v in graph.items()}
    changed = True
    while changed:                          # lặp tới điểm bất động
        changed = False
        for node, targets in closed.items():
            expanded = set(targets)
            for t in list(targets):
                expanded |= closed.get(t, set())
            expanded.discard(node)          # không cho X → X
            if expanded != targets:
                closed[node] = expanded
                changed = True
    return closed
```

`nestjs → typescript → javascript` ⟹ sau khi đóng, `nestjs` liệt kê **cả**
`javascript`. Nhờ vậy Layer 2 chỉ cần **một lần tra hash O(1)** lúc chấm điểm,
không phải duyệt đồ thị.

Số cạnh sau khi đóng (1.787) chỉ nhỉnh hơn số key (1.505) vì phần lớn quy tắc là
**một bậc** (package ⟹ ngôn ngữ), chuỗi bắc cầu dài ≥ 3 khá hiếm — đồ thị rất
**nông và thưa**.

**Tầng phụ — trình độ ngôn ngữ:**

| Framework | Regex | Rank |
| --- | --- | --- |
| JLPT | `\bjlpt\s*n\s*([1-5])\b` | `6 - n` (N1 cao nhất — **thứ tự nghịch**) |
| HSK | `\bhsk\s*([1-9])\b` | `n` |
| TOPIK | `\btopik\s*([1-6])\b` | `n` |
| IELTS | `\bielts\s*([0-9](\.[05])?)\b` | điểm |
| TOEIC | `\btoeic\s*([0-9]{2,3})\b` | điểm |
| TOEFL | `\btoefl(\s*ibt)?\s*([0-9]{2,3})\b` | điểm |
| CEFR | `\b([abc][12])\b` | A1=1 … C2=6 |

Chuỗi chứng chỉ được **tách sub-token** qua `_CREDENTIAL_SPLIT_RE`
(`[-–—:,/()]+`): `"Japanese - JLPT N3"` → `{"japanese - jlpt n3", "japanese",
"jlpt n3"}`.

Chỉ so **trong cùng framework**. So khớp cho verdict **dứt điểm**: CV có chứng
chỉ cùng framework nhưng **thấp hơn** yêu cầu → `missing` ngay, không rơi xuống
tầng khác (đã biết chắc là không đạt).

### 3.6 Stage 5 — Qualitative Evaluation (`evaluator.py`)

```
_analyze_skills(cv, jd)          [Python, tái dùng SkillMatcher.evaluate_tiers]
    ├─ với MỖI skill của cả 3 tier (required OR-group aware):
    │     matched / matched_implied                  → skill_details
    │     missing & tier=required & weight ≥ 3       → missing_must_have
    │     missing & tier=preferred, HOẶC
    │             tier=required & weight < 3         → missing_preferred
    │     missing & tier=nice_to_have                → missing_nice_to_have
    ├─ bonus_skills: skill CV có mà JD không đòi ở BẤT KỲ tier nào (so trên
    │     dạng canonical, tối đa 8) — "React" không bị coi là bonus khi JD
    │     đòi "React.js"
    └─ skill_match_rate = matched_weight / total_weight × 100
          ← CÙNG evaluate_tiers với scorer.score_skills, nên tỷ lệ hiển thị
            cho HR luôn khớp đúng điểm D2 dùng để xếp hạng

_analyze_experience(cv, jd)      [Python]
    not_required   : JD không yêu cầu
    over_qualified : cv_years ≥ 2 × required
    sufficient     : cv_years ≥ 0.8 × required
    insufficient   : còn lại  (kèm "thiếu X năm")

_analyze_education(cv, jd)       [Python]
    not_required | exceeds | meets | below

_is_valid_cv(cv)                 [Python — tính SAU 3 phân tích trên, TRƯỚC _llm_narrative]
    false nếu cv.is_resume=false (LLM tự đánh giá lúc parse — Stage 2),
    HOẶC name/skills/work_experience/education/projects đều rỗng
    (fallback cho ParsedCV cũ, parse trước khi field is_resume tồn tại)

_llm_narrative(...)              [LLM 1 call, temperature=0.55 — CHỈ khi is_valid_cv=true]
    Input: TOÀN BỘ số liệu do Python tính sẵn + 1 đoạn ví dụ few-shot văn phong
    Output: 1 đoạn ~5-8 câu tiếng Việt cho HR (độ dài co giãn theo dữ liệu thực tế)
    KHÔNG bullet, KHÔNG tiêu đề, KHÔNG khuyến nghị hành động
```

**Vì sao không có trường `recommendation`:** nếu LLM tự gán nhãn
"strong_fit/reject" thì nhãn đó có thể **mâu thuẫn với `final_score`** mà hệ
thống đã tính — hai nguồn kết luận khác nhau trên cùng một ứng viên. Narrative
chỉ **mô tả**; quyết định thuộc về HR dựa trên điểm số. Đây cũng là yêu cầu
"human-in-the-loop" đối với hệ thống AI rủi ro cao trong tuyển dụng.

**Vì sao mọi con số do Python tính trước rồi mới đưa vào prompt:** LLM chỉ làm
việc nó giỏi (diễn đạt tự nhiên), không làm việc nó dở (số học). Điều này loại
bỏ hoàn toàn khả năng narrative nói "khớp 85%" trong khi `skill_match_rate`
thực tế là 71.4%.

**Vì sao có bước `_is_valid_cv` riêng trước `_llm_narrative`:** phát hiện thực
tế — upload một PDF **không phải CV** (ví dụ một research paper) khiến
`parse_cv()` trả về `ParsedCV` gần như rỗng một cách **đúng đắn** (LLM không
hallucinate dữ liệu), nhưng `_NARRATIVE_PROMPT` (bản đầu tiên) khi đó vẫn yêu
cầu LLM viết đủ 10 câu nhận xét "chuyên nghiệp như người thật viết cho người
thật" quanh toàn placeholder (`"Ứng viên"`, `"Chưa xác định"`, 0.0 năm kinh
nghiệm) — LLM tuân
thủ hướng dẫn output nên tạo ra một đoạn văn trôi chảy nhưng vô nghĩa, đọc rất
"không tự nhiên" vì đang mô tả một ứng viên không hề tồn tại. `_is_valid_cv`
chặn trước khi gọi LLM: `false` khi `cv.is_resume=false` (tín hiệu do chính
LLM trả về **trong cùng lần gọi trích xuất** ở Stage 2, không tốn thêm LLM
call — xem `parser.CV_EXTRACT_PROMPT`), hoặc khi mọi trường nội dung
(`name`/`skills`/`work_experience`/`education`/`projects`) đều rỗng — điều
kiện "rỗng toàn bộ" cố ý tránh nhầm với một CV fresher thật (fresher thật vẫn
có tên và/hoặc học vấn, chỉ thiếu `work_experience`). Khi không hợp lệ,
`narrative` là một thông báo cố định thay vì gọi LLM — vừa tránh đánh giá bịa
đặt, vừa tiết kiệm 1 LLM call cho case này.

**Vì sao `_NARRATIVE_PROMPT` được viết lại (không chỉ riêng case không phải
CV):** ngay cả với một CV hợp lệ, bản prompt đầu tiên vẫn cho ra văn phong
gượng — nguyên nhân là nó ép LLM phải "điểm danh" đủ 8 mục nội dung theo
đúng thứ tự cố định, trong một khối lượng cố định (10 câu), không kèm ví dụ
minh hoạ cho "giọng văn tự nhiên" mà chỉ mô tả bằng tính từ trừu tượng. Kết
quả: câu văn rơi vào khuôn mẫu liệt kê tuần tự ("Về kỹ năng kỹ thuật... Về
kinh nghiệm... Về học vấn...") và luôn mở đầu bằng cụm sáo rỗng ("Dựa trên
hồ sơ...", "Nhìn chung, ứng viên..."), đọc như một bài luận được lấp đầy
theo khuôn, không giống ghi chú của một recruiter thật. Bản sửa (temperature
0.4 → 0.55, max_tokens 1200 → 800) thay đổi 3 điểm: (1) thêm **1 đoạn ví dụ
few-shot** minh hoạ đúng giọng văn mong muốn — đòn bẩy hiệu quả nhất để LLM
bắt đúng phong cách, hiệu quả hơn nhiều so với mô tả bằng tính từ; (2) nới độ
dài từ "đúng 10 câu" xuống "khoảng 5-8 câu, không cố nhồi cho đủ" và cho phép
bỏ qua mục dữ liệu không có gì đáng nói, thay vì buộc đề cập đủ mọi mục kể cả
khi không quan trọng; (3) liệt kê tường minh các cụm mở đầu cần tránh. Đây là
một ví dụ cho luận điểm rộng hơn của prompt engineering: **few-shot cụ thể
kiểm soát văn phong tốt hơn instruction trừu tượng**, và **ép cấu trúc cứng
trên một tác vụ mang tính tổng hợp (synthesis) sẽ tạo ra output máy móc**,
dù bản thân LLM hoàn toàn có khả năng viết tự nhiên nếu được yêu cầu đúng
cách.

---

## 4. CÔNG THỨC TOÁN HỌC

### 4.1 Cosine Similarity

$$\text{cosine\_sim}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \cdot \|\mathbf{v}\|} = \frac{\sum_{i=1}^{n} u_i v_i}{\sqrt{\sum_{i=1}^{n} u_i^2} \cdot \sqrt{\sum_{i=1}^{n} v_i^2}}$$

- Miền giá trị: $[-1, 1]$; với text embedding thực tế thường $\in [0, 1]$.
- Đo **góc** giữa hai vector trong không gian $n = 3072$ chiều, **bất biến với
  độ dài** → CV 3 trang và JD 15 dòng vẫn so sánh được.
- Nếu mẫu số bằng 0 (vector rỗng) → trả 0.0 thay vì chia cho 0.

**Quan hệ với khoảng cách Euclid:** với vector đã chuẩn hóa L2,
$\|\mathbf{u} - \mathbf{v}\|^2 = 2(1 - \cos\theta)$ — hai độ đo cho **cùng thứ
tự xếp hạng**. Đây là câu trả lời cho phản biện *"sao không dùng Euclid?"*.

### 4.2 Cosine Normalization

$$D_1 = \max\!\left(0,\ \min\!\left(\frac{r - r_{\min}}{r_{\max} - r_{\min}},\ 1\right)\right)$$

**Cấu hình đang chạy:** $r_{\min} = 0.0$, $r_{\max} = 1.0$ (env `COSINE_MIN` /
`COSINE_MAX`) → phép biến đổi là **đồng nhất**, cosine thô được dùng trực tiếp.

**Cơ sở lý thuyết của việc kéo giãn:** embedding của transformer có tính
**anisotropy** — các vector tập trung trong một hình nón hẹp, nên cosine giữa
hai văn bản bất kỳ hiếm khi tiến gần 0. Nếu đo được rằng cặp CV/JD thực tế chỉ
rơi vào khoảng $[0.2, 0.8]$ thì D1 chỉ dùng 60% thang điểm; kéo giãn khoảng đó
về $[0,1]$ giúp tận dụng toàn bộ thang.

**Lưu ý về tính chất:** phép kéo giãn là **affine đơn điệu** → **không đổi thứ
hạng nếu chỉ xét riêng D1**, nhưng **có đổi thứ hạng của `final_score`** vì nó
thay đổi độ lớn đóng góp của D1 tương đối với D2–D5.

### 4.3 Skill Score (D2)

$$D_2 = \frac{\sum_{i=1}^{|S_{JD}|} w_i \cdot m_i}{\sum_{i=1}^{|S_{JD}|} w_i}, \qquad w_i \in \{1,2,3\}, \quad m_i \in \{0, 1\}$$

**Chấm nhị phân** — mỗi requirement hoặc thỏa (full trọng số) hoặc thiếu (0).
Không có partial credit.

$S_{JD}$ là **hợp của cả 3 tier** skill mà JD nêu, với $w_i$ quy đổi theo tier:

$$
w_i =
\begin{cases}
3 & \text{skill} \in \texttt{required\_skills} \\
2 & \text{skill} \in \texttt{preferred\_skills} \\
1 & \text{skill} \in \texttt{nice\_to\_have\_skills}
\end{cases}
$$

Ý nghĩa của thiết kế này: **thứ bậc ưu tiên của nhà tuyển dụng được mã hóa thành
trọng số**, thay vì thành ranh giới cứng "tính điểm / không tính điểm". Thiếu một
skill `nice_to_have` vẫn kéo D2 xuống, nhưng chỉ bằng $1/3$ so với thiếu một
must-have. $S_{JD} = \varnothing$ (JD trống ở cả 3 tier) → $D_2 = 1.0$.

`RequiredSkill.weight` là một trường số nguyên (schema cho phép mọi giá trị,
scorer cộng dồn `wᵢ` tuỳ ý), nhưng **prompt buộc LLM luôn gán `weight = 3`**
cho mọi entry trong `required_skills` — 3 tier (required/preferred/
nice_to_have) chính là 3 mức ưu tiên, `weight` không dùng để phân độ mịn hơn
bên trong `required_skills` nữa (tránh nhập nhằng "required weight=1" với
"preferred"). `required_skills` vẫn là tier duy nhất có OR-group
(`alternatives`); 2 tier còn lại là list string phẳng, dùng hằng số trọng số
cho cả tier (`PREFERRED_SKILL_WEIGHT = 2`, `NICE_TO_HAVE_SKILL_WEIGHT = 1`).

$m_i$ được xác định bởi cascade, requirement dừng ở **tầng sớm nhất** thỏa nó:

| Tầng | Điều kiện | rank | $m_i$ |
| --- | --- | --- | --- |
| Layer 0 | `jd_skill.lower() ∈ cv_raw_skills` | 5 | 1 |
| Layer 1 | `resolve_canonical(jd) ∈ cv_canonical` | 4 | 1 |
| Layer 2 | `resolve_canonical(jd) ∈ cv_implied` | 3 | 1 |
| Layer 3 | `max SequenceMatcher.ratio ≥ 0.85` | 2 | 1 |
| Proficiency | cùng framework ∧ `cv_rank ≥ jd_rank` | 1 | 1 |
| Proficiency | cùng framework ∧ `cv_rank < jd_rank` | 1 | 0 |
| — | không tầng nào thỏa | 0 | 0 |

**OR-group:** một requirement gồm $\{skill\} \cup alternatives$ được thỏa bởi
**bất kỳ** phương án nào:

$$m_i = \max_{a \in \text{group}_i} m(a)$$

Về hình thức, D2 là một **hội của các tuyển có trọng số**, được làm mềm thành
độ phủ thay vì AND cứng:

$$D_2 = \text{weighted-coverage}\left(\bigwedge_i \bigvee_{a \in \text{group}_i} a\right)$$

**Bản chất của độ đo:** đây là **weighted recall (độ phủ có trọng số) trên tập
yêu cầu của JD**, **không phải Jaccard**:

| Độ đo | Công thức | Vì sao không dùng |
| --- | --- | --- |
| Jaccard | $\dfrac{\|A \cap B\|}{\|A \cup B\|}$ | Đối xứng → **phạt** ứng viên biết nhiều kỹ năng ngoài JD |
| Dice | $\dfrac{2\|A \cap B\|}{\|A\| + \|B\|}$ | Vẫn đối xứng |
| Overlap coefficient | $\dfrac{\|A \cap B\|}{\min(\|A\|,\|B\|)}$ | Gần nhất nhưng không có trọng số |
| **Đang dùng** | $\dfrac{\sum w_i m_i}{\sum w_i}$ | Đúng ngữ nghĩa: JD là tập yêu cầu **cần được phủ**; kỹ năng dư không phải lỗi |

Hệ quả cần nêu rõ: D2 **không phạt over-qualification** và **không đo
precision**. Kỹ năng dư được xử lý riêng ở `bonus_skills` (chỉ hiển thị).

### 4.4 Fuzzy String Similarity (Ratcliff/Obershelp)

$$\text{ratio}(a, b) = \frac{2M}{|a| + |b|}$$

với $M$ = tổng độ dài các khối khớp tìm được đệ quy (Gestalt pattern matching,
`difflib.SequenceMatcher`). **Không phải Levenshtein.**

Ngưỡng: $\text{ratio} \geq 0.85$.

**Số liệu thực đo:**

| Cặp | ratio | Kết quả |
| --- | --- | --- |
| `postgresql` / `postgres` | 0.889 | ✅ khớp đúng |
| `nodejs` / `node.js` | 0.923 | ✅ khớp đúng |
| `angular` / `angularjs` | 0.875 | ⚠️ **khớp nhầm** (2 framework khác nhau) |
| `sql` / `mysql` | 0.750 | ✅ đúng khi không khớp |
| `java` / `javascript` | 0.571 | ✅ đúng khi không khớp |
| `n3` / `n4` | 0.500 | đã chặn riêng bằng tầng proficiency |

Layer 3 nằm **cuối** cascade vì nó vừa đắt hơn ($O(|S_{JD}| \times |S_{CV}|)$
phép so chuỗi) vừa lỏng hơn 3 tầng chính xác phía trên. Đây là mô hình
**cascade ưu tiên precision**: quy tắc chính xác chạy trước, quy tắc xấp xỉ chỉ
chạy khi các quy tắc trên đã trượt.

Layer 3 **bị vô hiệu hóa** cho token trình độ ngôn ngữ: `"N4"` và `"N3"` giống
nhau về ký tự nhưng **khác nhau về chất** — phải để tầng proficiency so theo
thứ bậc.

### 4.5 Bao đóng bắc cầu của đồ thị Entailment (D2 Layer 2)

Quan hệ $\Rightarrow$ ("biết X thì biết Y") là quan hệ **thứ tự bộ phận**,
**phản đối xứng** (Django $\Rightarrow$ Python nhưng Python $\nRightarrow$
Django). Đồ thị là **DAG**.

Bao đóng bắc cầu $R^+$ là nghiệm nhỏ nhất của:

$$R^+ = R \cup \{(x, z) \mid \exists y: (x,y) \in R^+ \land (y,z) \in R^+\}$$

Cài đặt bằng **lặp tới điểm bất động**: toán tử mở rộng là **đơn điệu** trên
dàn hữu hạn các tập con → hội tụ sau hữu hạn bước (định lý điểm bất động
Kleene). Với đồ thị thưa 1.505 đỉnh / 1.787 cạnh, cách này rẻ hơn Floyd–Warshall
$O(V^3)$.

**Đánh đổi không gian ↔ thời gian:** closure được **vật chất hóa offline** và
commit vào repo, đổi lấy tra cứu **O(1)** lúc chấm điểm thay vì duyệt đồ thị
mỗi lần.

### 4.6 Experience Score (D3)

**Công thức hiện tại trong code** (`score_experience` —
[scorer.py:167-191](../app/services/scorer.py#L167-L191)). D3 là **trung bình
cộng đều** của 2 tỷ lệ độc lập — độ sâu theo từng required_skill và tỷ lệ số
năm kinh nghiệm thô — để tránh D3 sập về 0 chỉ vì CV lệch đúng 1 tech stack cụ
thể trong khi vẫn có nhiều năm kinh nghiệm cùng ngành (xem ví dụ cuối mục):

$$
D_3 =
\begin{cases}
1.0 & Y_{JD} = 0 \quad \text{(JD không yêu cầu số năm)} \\[4pt]
\dfrac{S_{skill} + S_{years}}{2} & R \neq \emptyset \text{ và } \sum_{r \in R} w_r > 0 \\[6pt]
S_{years} & \text{ngược lại (JD không có required\_skills)}
\end{cases}
$$

**$S_{skill}$ — độ sâu theo từng required_skill** (`_skill_experience_ratio` —
[scorer.py:133-164](../app/services/scorer.py#L133-L164)):

$$\rho_r = \min\!\left(\frac{M_r}{12\,Y_{JD}},\ 1.0\right), \qquad S_{skill} = \frac{\sum_{r \in R} w_r\,\rho_r}{\sum_{r \in R} w_r}$$

trong đó $R$ = tập required_skills của JD (mỗi phần tử 1 OR-group), $w_r$ =
trọng số requirement $r$ (như D2), $M_r$ = tổng số tháng (đã gộp khoảng chồng
lấn) của các job trong CV có `tech_stack` khớp OR-group $r$ (dùng lại
`SkillMatcher.evaluate_name`, layer0-3, xem §4.5). Requirement không job nào
chứng minh được → $\rho_r = 0$ — kể cả khi skill đó có mặt rời rạc trong
`cv.skills` (không gắn job/thời lượng cụ thể thì không có gì để đo độ sâu).

**$S_{years}$ — tỉ lệ số năm thô** (công thức D3 gốc trước `a070201`, nay vừa
là fallback khi JD không có required_skills, vừa là thành phần thứ 2 của
blend ở trên):

$$S_{years} = \min\!\left(\frac{Y_{CV}}{Y_{JD}},\ 1.0\right), \qquad Y_{CV} = \frac{1}{12}\left|\bigcup_{j \in \text{jobs}} [\text{start}_j, \text{end}_j]\right|$$

Các job **chồng lấn** (ví dụ freelance chạy song song với full-time) chỉ được
tính **một lần**. Thuật toán: sắp xếp theo `start`, gộp khoảng khi
$s_{k+1} \leq e_k$ — $O(n \log n)$.

**Không có modifier** relevance/recency/over-qualification ngoài $S_{skill}$/
$S_{years}$ ở trên. Lý do ban đầu (khi D3 còn thuần $S_{years}$): độ liên quan
của kinh nghiệm với vị trí đã được D1 (narrative fit) và D2 (kỹ năng) đo —
nếu D3 đo lại thì cùng một tín hiệu bị đếm ba lần. `a070201` nới lý do này
một phần bằng $S_{skill}$ (đo độ liên quan THEO SKILL), nhưng $S_{skill}$
thuần lại tạo ra hệ quả mới — xem ví dụ dưới — nên D3 quay lại pha trộn với
$S_{years}$ làm sàn điểm.

**Vì sao cần blend thay vì $D_3 = S_{skill}$ thuần:** JD yêu cầu .NET, tối
thiểu 3 năm. Ứng viên A có 7 năm kinh nghiệm Java (không có .NET); ứng viên B
chỉ có 1 năm .NET.

| Ứng viên | $S_{skill}$ | $S_{years}$ | $D_3 = S_{skill}$ (trước) | $D_3 = (S_{skill}+S_{years})/2$ (nay) |
| --- | --- | --- | --- | --- |
| A — Java 7 năm, không .NET | 0.000 | 1.000 | 0.000 | **0.500** |
| B — .NET 1 năm | 0.333 | 0.333 | 0.333 | 0.333 |

Với $D_3 = S_{skill}$ thuần, ứng viên đã 7 năm kinh nghiệm dev (A) bị chấm
**thấp hơn** ứng viên mới 1 năm (B) — vô lý vì cả hai đều "sai stack yêu cầu",
chỉ khác mức độ liên quan ngành. Blend 50/50 dùng $S_{years}$ làm sàn, đưa A
lên 0.500 > 0.333 của B, khớp trực giác "7 năm kinh nghiệm dev vẫn nên được
đánh giá cao hơn 1 năm kinh nghiệm đúng stack". Đánh đổi: blend không phân
biệt được "sai đúng 1 stack nhưng cùng ngành" (case A) với "lệch hẳn lĩnh
vực" (vd 7 năm Marketing) — cả 2 đều có $S_{skill}=0$ nên cùng nhận sàn
$S_{years}/2$; D2 (skill match) vẫn là tầng chính chịu trách nhiệm phân biệt
2 case này qua điểm skill overlap.

Xem test minh họa: `test_score_experience_seasoned_wrong_stack_beats_junior_right_stack`
trong [tests/test_scorer.py](../tests/test_scorer.py).

### 4.7 Tính Months từ Date Strings

$$\text{months}(s, e) = (Y_e - Y_s) \times 12 + (M_e - M_s)$$

- `parse_month` chấp nhận `"YYYY-MM"`, `"YYYY/MM"`, `"YYYY.MM"`, hoặc chỉ năm
  (`"2019"` → `2019-01`).
- `"present" | "now" | "nay" | "current"` → tháng hiện tại.
- Ngày không đọc được → `None` → fallback về tháng hiện tại.
- Nếu $e < s$ thì đặt $e = s$ (chống dữ liệu lỗi cho ra số âm).

**Vì sao Python tính thay vì LLM:** LLM có thể sai ±1–2 tháng do hallucinate;
số học Python luôn chính xác và **tái lập được** giữa các lần chạy.

### 4.8 Education Score (D4)

$$D_4 = \min\!\left(\frac{L_{CV}}{L_{JD}},\ 1.0\right)$$

| Degree | $L$ |
| --- | --- |
| high_school | 1 |
| associate | 2 |
| bachelor | 3 |
| master | 4 |
| phd | 5 |
| other | 1 |

- $L_{CV} = \max$ trên toàn bộ `education[]` của CV.
- JD không yêu cầu bằng cấp ($L_{JD} = 0$) → $D_4 = 1.0$.
- CV không có thông tin bằng cấp ($L_{CV} = 0$) → $D_4 = 0.5$ (trung lập).
- Bằng cấp **cao hơn** yêu cầu không được cộng thêm (chặn trần ở 1.0) — học vấn
  là **ngưỡng lọc**, không phải yếu tố phân biệt.

**Ghi chú về đo lường:** $L$ là thang **thứ tự** nhưng được dùng như thang **tỉ
lệ** trong phép chia. Đây là giả định đơn giản hóa có ý thức: "cử nhân / thạc sĩ
= 0.75" không có ý nghĩa đo lường nghiêm ngặt, nhưng cho ra thứ tự đúng và một
độ phạt trơn tru khi thiếu bằng.

### 4.9 Location + Work-Mode Score (D5)

**Geocoding (Nominatim) chạy 1 lần ở parse-time**, giống hệt cách `embedding`
được tính 1 lần — không tính lại mỗi lần chấm:

$$(\text{lat}, \text{lng}) = \text{Nominatim.geocode}(\text{raw\_address})$$

**Routing (OSRM) chạy ở score-time**, vì route phụ thuộc **cặp** CV↔JD cụ thể:

$$
D_5 =
\begin{cases}
1.0 & \text{JD.work\_mode} = \text{remote} \\
1.0 & \text{CV.willing\_to\_relocate} = \text{true} \\
0.5 & \text{CV không có } \texttt{raw\_address} \text{, cùng } \texttt{city} \text{ với JD} \\
0.0 & \text{CV không có } \texttt{raw\_address} \text{, khác } \texttt{city} \text{ (hoặc CV không có city)} \\
0.5 & \text{có } \texttt{raw\_address} \text{ nhưng thiếu lat/lng ở 1 trong 2 phía} \\
0.5 & \text{OSRM thất bại 2 lần (retry 1 lần sau 0.5s)} \\
\text{round}(S_{\text{loc}},\ 3) & \text{ngược lại}
\end{cases}
$$

$$S_{\text{loc}} = \max\!\left(0,\ 1 - \frac{t}{T_{\max}}\right), \qquad T_{\max} = \begin{cases} 45 \text{ phút} & \text{onsite} \\ 75 \text{ phút} & \text{hybrid} \end{cases}$$

với $t$ = driving duration (phút) từ `OSRM route.duration`.

Thứ tự kiểm tra trong code (`scorer.py::score_location`): remote → relocate →
**CV thiếu `raw_address`** (so `city` thô, trả sớm 0.5/0.0, KHÔNG gọi OSRM) →
thiếu lat/lng → route. Nhánh `raw_address` là bổ sung sau này so với thiết kế
D5 ban đầu — `CandidateLocation` có thêm field `city` (enum "Ha Noi"/"Ho Chi
Minh"/"Da Nang", chuẩn hóa qua validator) để so nhanh khi không đủ dữ liệu
geocode chi tiết.

**Vì sao không dùng haversine (đường chim bay) làm fallback:** đường chim bay
không phản ánh thực tế giao thông đô thị (sông, đường một chiều, tắc đường) —
một ước lượng sai lệch còn tệ hơn một điểm trung lập trung thực. Hàm fallback
đã được **gỡ bỏ hoàn toàn** khỏi `location_service.py`.

### 4.10 Final Weighted Score

$$\text{final} = \left(\sum_{i=1}^{5} D_i \cdot W_i\right) \times 100, \qquad \sum_{i=1}^{5} W_i = 1$$

| Dimension | $W_i$ | Lý do |
| --- | --- | --- |
| $W_1$ Semantic | 0.30 | Narrative fit tổng thể — vai trò, phạm vi, bối cảnh |
| $W_2$ Skills | 0.35 | Yếu tố quyết định nhất trong tuyển dụng IT |
| $W_3$ Experience | 0.20 | Số năm kinh nghiệm |
| $W_4$ Education | 0.10 | Thường là ngưỡng lọc, không phải yếu tố phân biệt |
| $W_5$ Location | 0.05 | Tín hiệu phụ — thời gian di chuyển |
| **Tổng** | **1.00** | |

**Ràng buộc kỹ thuật:**
- `config.py::_check_default_weights_sum_to_one` — service **không khởi động
  được** nếu default weights trong `.env` không tổng bằng 1.0 (fail fast).
- `score.py::_validate_weights` — override từ HR phải có **đúng 5 key**, mỗi giá
  trị $\in [0,1]$, tổng $= 1.0$ (sai → HTTP 422).
- Response trả `weights_used` để audit.

**Cơ sở lý thuyết:** đây là mô hình **Simple Additive Weighting (SAW/WSM)** của
MADM (Hwang & Yoon, 1981). Điều kiện áp dụng — mọi tiêu chí cùng thang $[0,1]$,
cùng chiều (càng cao càng tốt), và **độc lập ưu tiên** — chính là lý do
`build_embed_text()` loại skills khỏi D1 (xem [3.3](#33-stage-3--embedding-embedderpy)).

### 4.11 Skill Match Rate (evaluator, không phải điểm số)

$$\text{skill\_match\_rate} = \frac{\sum_i w_i \cdot m_i}{\sum_i w_i} \times 100$$

Cùng công thức **và cùng nguồn dữ liệu** với D2 (`SkillMatcher.evaluate_tiers`),
chỉ khác ở dạng phần trăm — dùng cho **hiển thị và narrative**. Không tham gia
`final_score` (D2 đã tham gia rồi).

Vì hai bên gọi chung một hàm nên luôn có $\text{skill\_match\_rate} = 100 \cdot D_2$
— không thể xảy ra tình trạng UI báo "khớp 85%" trong khi điểm `skills` dùng để
xếp hạng lại là một con số khác.

---

## 5. CƠ SỞ LÝ THUYẾT & RESEARCH PAPERS

> Danh mục đầy đủ 40 tài liệu tham khảo kèm link đã xác minh và bản đồ
> component → paper: xem **[`research_papers.md`](research_papers.md)**.
> Mục này chỉ tóm tắt **những gì cần nắm chắc để bảo vệ trước hội đồng**.

### 5.1 Nhóm lý thuyết theo thành phần

| Thành phần | Lý thuyết cốt lõi | Nguồn chính |
| --- | --- | --- |
| Kiến trúc D1–D5 | MADM / Simple Additive Weighting; điều kiện độc lập ưu tiên | Hwang & Yoon (1981); Saaty AHP (1980) |
| D1 — embedding | Bi-encoder Siamese, precompute vector; anisotropy của embedding; Matryoshka | Reimers & Gurevych (2019); Ethayarajh (2019); Kusupati et al. (2022) |
| D1 — cosine | Vector space model; quan hệ cosine ↔ Euclid trên vector chuẩn hóa | Gomaa & Fahmy (2013) |
| D2 — Layer 1 | Entity resolution / canonicalization; synonym ring | Naumann & Herschel (2010); ESCO; O\*NET |
| D2 — Layer 2 | Subsumption / entailment; DAG; bao đóng bắc cầu; forward-chaining materialization | Warshall (1962); RDFS; WordNet |
| D2 — Layer 3 | Gestalt pattern matching (Ratcliff/Obershelp); precision–recall của ngưỡng | Ratcliff & Metzener (1988) |
| D2 — proficiency | Thang đo của Stevens: phép nào hợp lệ trên thang thứ tự | Stevens (1946); CEFR |
| Stage 1 | Document layout analysis; OCR pipeline | Zhong et al. PubLayNet (2019); Smith Tesseract (2007) |
| Stage 2 | LLM-based information extraction; structured prompting | Wei et al. CoT (2022); LLM-IE Survey (2024) |
| Toàn hệ | Person-Job Fit; talent analytics | Zhu et al. (2018); Qin et al. (2023) |
| Đạo đức/pháp lý | AI rủi ro cao trong tuyển dụng; quyết định tự động; bias của embedding | EU AI Act (2024/1689); GDPR Art. 22; Bolukbasi et al. (2016) |
| Đánh giá | nDCG cho xếp hạng; kappa cho độ tin cậy nhãn | Järvelin & Kekäläinen (2002); Cohen (1960) |

### 5.2 Bốn luận điểm trung tâm cần thuộc

**(1) Vì sao phải hybrid — embedding một mình không đủ.**
Embedding đo ngữ nghĩa văn bản, **không đo giá trị số học**:
`embed("5 years") ≈ embed("3 years")` với cosine ~0.98. Nó cũng không nhạy với
phủ định và không biểu diễn được ràng buộc cứng. Do đó D2–D5 (symbolic, tất
định) **bắt buộc** phải tồn tại bên cạnh D1 (dense, học sâu). Hai loại lỗi của
hai hướng này bổ sung cho nhau: dense bắc cầu qua **lexical gap**
("Backend Developer" ≈ "Server-side Engineer"), symbolic giữ **precision** mà
dense làm nhòe.

**(2) Vì sao D1 loại skills khỏi text embed.**
Mô hình cộng có trọng số đòi hỏi các tiêu chí độc lập ưu tiên. Nếu token kỹ năng
nằm trong cả D1 lẫn D2 thì trọng số hiệu dụng của "kỹ năng" là 0.65 chứ không
phải 0.35 — hệ thống nói một đằng làm một nẻo. `EMBED_TEXT_VERSION` ghi nhận
quyết định này ở tầng code.

**(3) Vì sao D2 chấm nhị phân thay vì partial credit.**
Bản trước dùng 3 mức (1.0 exact / 0.9 fuzzy / 0.3–0.5 cùng nhóm). Ba lý do thay
đổi: (a) các hệ số 0.9 và 0.3–0.5 **không có cơ sở hiệu chỉnh** — chọn tùy ý,
không đo được; (b) không giải thích được cho HR ("được 0.4 điểm cho Vue vì biết
React" là câu không bảo vệ được); (c) nhị phân + entailment tường minh chuyển
tri thức từ **hệ số ma thuật** sang **quy tắc kiểm toán được** — mỗi điểm truy
vết được về đúng kỹ năng nào trong CV đã thỏa (`matched_layer` + `matched_via`).

**(4) Vì sao 70% trọng số nằm ở các chiều tất định.**
Tuyển dụng là lĩnh vực **rủi ro cao** theo EU AI Act (Annex III), và GDPR Điều
22 cho phép cá nhân từ chối quyết định hoàn toàn tự động. Kiến trúc để D1 —
chiều duy nhất không giải thích được và duy nhất có nguy cơ kế thừa thiên lệch
từ dữ liệu huấn luyện — chỉ chiếm 0.30, còn 0.70 nằm ở các quy tắc tất định,
kiểm toán được. Đây là **lựa chọn thiết kế có cơ sở**, không phải hạn chế kỹ
thuật.

### 5.3 Các điểm yếu đã nhận diện (nên chủ động nêu)

| Điểm yếu | Bản chất | Hướng xử lý |
| --- | --- | --- |
| `angular` / `angularjs` khớp nhầm ở Layer 3 (ratio 0.875) | Đánh đổi precision–recall của ngưỡng cứng | Chặn Layer 3 khi cả hai phía đều resolve ra canonical hợp lệ nhưng khác nhau |
| 1.505 quy tắc implies viết tay | Knowledge acquisition bottleneck — có soundness, không có completeness | Bootstrap từ co-occurrence tag trên Stack Overflow |
| Embedding đối xứng cho bài toán bất đối xứng (CV dài ↔ JD ngắn) | Model kiểu STS không tối ưu cho retrieval | Dùng `task_type` `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` của API Gemini |
| Thang thứ tự dùng như thang tỉ lệ ($L$, $w$) | Giả định đơn giản hóa về đo lường | Nêu rõ giả định; nếu cần chặt hơn thì rút trọng số bằng AHP |
| Heuristic 2 cột dùng ngưỡng cứng 45%/55% | Không xử lý được layout 3 cột / bất đối xứng | Model layout detection có huấn luyện (hướng của PubLayNet) |
| D2 không đo precision (không phạt skill dư) | Chủ ý — độ đo bất đối xứng | `bonus_skills` báo cáo riêng cho HR |
| Chưa có gold set gán nhãn bởi HR | Chưa đo được nDCG end-to-end | Xem [mục 6](#6-kiểm-thử--đánh-giá) |

---

## 6. KIỂM THỬ & ĐÁNH GIÁ

### 6.1 Bộ test hiện có

**200 test, không cần LLM và không cần mạng** — assert trên dữ liệu tĩnh
`skill_data.json` + `skill_implies.json` (riêng `test_parser.py` monkeypatch
`call_llm_json` để test logic xung quanh output LLM mà không gọi LLM thật):

| File | Số test | Phạm vi |
| --- | --- | --- |
| `tests/test_d2_skills.py` | 103 | D2 end-to-end, nhóm A–L (xem dưới) |
| `tests/test_skill_matcher.py` | 45 | Từng tầng của cascade, chuẩn hóa format, proficiency |
| `tests/test_scorer.py` | 34 | D1–D5 riêng lẻ + `calculate_score` tổng hợp |
| `tests/test_evaluator.py` | 10 | Phân loại skill theo 3 tier, verdict experience/education, `_is_valid_cv` + narrative bị bỏ qua khi không phải CV |
| `tests/test_parser.py` | 8 | Pydantic validation, tính months, coerce 3 tier skill, `is_resume` mặc định + bỏ qua retry khi không phải CV |
| **Tổng** | **200** | Chạy trong ~1s, hoàn toàn offline |

**Phân nhóm `test_d2_skills.py`:**

| Nhóm | Nội dung |
| --- | --- |
| A | Chuẩn hóa format + `resolve_canonical` + fallback khi skill lạ |
| B | Layer 0 — direct match, case-insensitive, từ tech_stack và projects |
| C | Layer 1 — identity cross-format; canonical khác nhau **không** được khớp |
| D | Layer 2 — entailment khớp đúng chiều và **không rò rỉ chiều ngược** |
| E | Proficiency — so ordinal, tách sub-token, chọn chứng chỉ cao nhất |
| F | OR-group — thỏa bởi primary hoặc alternative; nhãn hiển thị |
| G | Ưu tiên tầng — layer0 > layer1 > layer2; `matched_via` trỏ đúng skill CV |
| H | Scoring — full match, weighted partial, nhị phân (chỉ 0 hoặc 1), ảnh hưởng của weight |
| I | Evaluator — phân loại status theo tier, preferred kéo `skill_match_rate` xuống, bonus loại trừ skill JD đã đòi |
| J | Nhóm QA/testing — entailment và synonym riêng của domain |
| K | Biên — CV rỗng, tên skill rỗng, trùng lặp, ký tự đặc biệt, matcher stateless |
| L | **Bất biến dữ liệu** — implies đã đóng bắc cầu, key/value đều canonical; + hồ sơ composite thực tế |

Nhóm **L** đáng chú ý về mặt phương pháp: đây là **property-based invariant
test trên chính dữ liệu tri thức**, không phải test logic. Nó bảo đảm rằng nếu
ai đó sửa `skill_implies.json` bằng tay mà quên chạy `close_implies.py` thì CI
sẽ **fail ngay**, thay vì để hệ thống âm thầm bỏ sót suy luận bắc cầu.

> **⚠️ Trạng thái hiện tại: 196 pass / 4 fail** (`pytest tests/ -q`). Hai nhóm
> nguyên nhân khác nhau, không liên quan tới thay đổi `is_resume`/`_is_valid_cv`
> ở mục 3.6:
>
> | Test | Kỳ vọng cũ | Hành vi hiện tại | Nguyên nhân |
> | --- | --- | --- | --- |
> | `test_scorer.py::test_score_skills_typo_no_longer_fuzzy_matched` | `"pythonn"` **không** khớp `"Python"` → D2 = 0.0 | Khớp ở Layer 3 (ratio 0.923) → D2 = 1.0 | Layer 3 fuzzy được thêm lại sau khi test này được viết |
> | `test_d2_skills.py::test_J9_ui_ux_compound_term` | `xfail(strict=True)`: `"UI/UX testing"` không khớp | Đã khớp qua Layer 3 → **XPASS** | Hạn chế mà test giả định đã được khắc phục |
> | `test_scorer.py::test_score_location_close_onsite_full_score` | Kỳ vọng D5 = 1.0 khi CV/JD gần nhau | D5 = **0.0** | `CandidateLocation` dựng trong test không có `raw_address` → rơi vào nhánh mới `if not cv_loc.raw_address: return 0.5/0.0 theo city` ([xem 4.9](#49-location--work-mode-score-d5)), route OSRM không còn được gọi tới |
> | `test_scorer.py::test_score_location_route_failure_after_retry_returns_neutral` | Kỳ vọng D5 = 0.5 khi OSRM lỗi 2 lần | D5 = **0.0** | Cùng nguyên nhân — thiếu `raw_address` khiến hàm return sớm trước khi chạm nhánh retry OSRM |
>
> Hai test đầu là **test cũ chưa cập nhật theo Layer 3 fuzzy** (như phân tích
> gốc). Hai test sau là **test chưa cập nhật theo nhánh `raw_address`/`city` mới
> trong `score_location()`** (mục 3.2/4.9) — bản thân nhánh này đúng ý đồ thiết
> kế, chỉ có fixture test chưa set `raw_address`. Cần xử lý trước khi bảo vệ:
> (1) viết lại 2 test fuzzy theo hành vi hiện tại; (2) set `raw_address` trong
> fixture của 2 test location, hoặc viết thêm test riêng cho nhánh
> "không có `raw_address`". Đây là ví dụ tốt cho báo cáo về việc **test bám sát
> thay đổi thiết kế** — nhưng để suite đỏ khi hội đồng chạy `pytest` thì là
> điểm trừ.

### 6.2 Chỉ số đánh giá đề xuất (chưa thực hiện)

Bộ test hiện tại là **unit-level validation** — chứng minh từng tầng hoạt động
đúng đặc tả. Để đánh giá **chất lượng xếp hạng end-to-end** cần:

| Chỉ số | Đo cái gì | Cách làm |
| --- | --- | --- |
| **nDCG@10** | Chất lượng xếp hạng so với nhãn nhiều mức của HR | HR chấm 1–5 cho N ứng viên trên M job; so ranking hệ thống vs ranking HR |
| **Precision@k / Recall@k** | Tỷ lệ ứng viên phù hợp trong top-k | Nhãn nhị phân "đáng phỏng vấn" |
| **Spearman ρ / Kendall τ** | Tương quan thứ hạng tổng thể | Trên toàn bộ danh sách, không chỉ top-k |
| **Cohen's kappa** | Độ tin cậy của chính gold set | ≥ 2 HR chấm cùng tập; kappa thấp ⇒ nhãn không dùng làm chuẩn được |
| **Ablation study** | Đóng góp của từng chiều | Chạy lại với $W_i = 0$ cho từng $i$, so nDCG |
| **Precision/Recall của D2** | Chất lượng riêng của skill matching | Gold set "skill này CV có hay không", so với output `evaluate_all_skills` |

**Ablation study là thí nghiệm đáng giá nhất** cho báo cáo: nó trả lời trực tiếp
câu hỏi *"mỗi chiều đóng góp bao nhiêu, có chiều nào thừa không?"* — và cũng là
cách kiểm chứng thực nghiệm cho bộ trọng số 30/35/20/10/5.

### 6.3 Hiệu năng

| Thành phần | Chi phí | Ghi chú |
| --- | --- | --- |
| `calculate_score` | ~1ms | Pure Python + numpy, không I/O |
| `parse-cv` | ~5–10s | LLM 1–3 call + geocode + embed |
| `parse-jd` | ~3–5s | LLM 1 call + geocode + embed |
| `evaluate` (narrative) | ~3–5s | LLM 1 call |
| OCR fallback | +2–5s/trang | Chỉ khi quality score < 60 |
| Batch parse-cv | song song | `asyncio.gather`, tối đa 50 URL/request |

Mọi lời gọi SDK đồng bộ đều được đẩy sang thread executor
(`run_in_executor` / `asyncio.to_thread`) để không chặn event loop FastAPI.
Trong `/ai/score`, phần chấm điểm và phần evaluator chạy **song song**.

---

## 7. PHẠM VI HIỆN TẠI & HẠN CHẾ

### 7.1 Đã cài đặt

✅ 4 endpoint: `parse-jd`, `parse-cv`, `score`, `evaluate` (+ `/health`)
✅ Trích xuất PDF/DOCX với nhận diện 2 cột + OCR fallback
✅ LLM parsing đa provider + retry theo tính đầy đủ + JSON repair
✅ Embedding 3072 chiều, text embed có chọn lọc (loại skills)
✅ Scoring 5 chiều + trọng số HR chỉnh được per-job
✅ D2 cascade 4 tầng + tầng proficiency + dữ liệu tri thức 9.524/1.505
✅ D2 tính trên **cả 3 tier** skill (required / preferred / nice_to_have)
✅ D5 geocode parse-time + routing score-time
✅ Evaluation định tính + narrative tiếng Việt
✅ Document-type validation (`is_resume` + `_is_valid_cv`) — chặn narrative
   bịa đặt khi tài liệu tải lên không phải CV (xem 3.6)
✅ 200 test không phụ thuộc mạng (196 pass / 4 test cũ cần cập nhật — xem 6.1)

### 7.2 Chưa cài đặt (từng có trong thiết kế)

| Tính năng | Trạng thái | Ghi chú |
| --- | --- | --- |
| `POST /ai/recalculate` | Chưa có | .NET tự tính được: tổ hợp tuyến tính trên 5 điểm đã lưu |
| `POST /ai/search` — NL search | Chưa có | Cần: LLM parse query → embed → cosine → filter → re-rank → LLM explain |
| Hard-rule penalties | Chưa có | `missing_must_have` chỉ được **báo cáo**, không trừ điểm |
| D3 modifiers (relevance/recency/over-qual) | Chưa có | D3 hiện chỉ là tỷ lệ số năm |
| Work-mode multiplier $M$ cho D5 | Chưa có | `score_location()` chưa nhân hệ số tương thích work-mode |
| pgvector ANN index | Chưa có | 3072 chiều vượt giới hạn index của pgvector — xem [mục 2](#2-database-schema) |

### 7.3 Đã gỡ bỏ có chủ đích

| Cơ chế cũ | Thay bằng | Lý do |
| --- | --- | --- |
| Category partial credit (0.3–0.5×) | Cascade 4 tầng, nhị phân | Hệ số không hiệu chỉnh được, không giải thích được cho HR |
| Fuzzy partial credit (0.9×) | Fuzzy = full credit ở Layer 3 | Điểm bộ phận làm mờ ranh giới "có/không có kỹ năng" |
| D5 Keywords (string match trên raw text) | D5 Location + Work Mode | Keyword trùng tín hiệu với D1/D2 |
| Haversine fallback cho D5 | Điểm trung lập 0.5 | Đường chim bay không phản ánh giao thông đô thị |
| Upload multipart cho `/parse-cv` | Nhận URL S3/R2 | Tách lưu trữ file khỏi AI service; hỗ trợ batch |
| `preferred_skills` chỉ để hiển thị (không tính điểm) | Tính vào D2 với trọng số 2 (và `nice_to_have` = 1) | Ranh giới cứng "tính / không tính" làm mất thông tin thứ bậc mà nhà tuyển dụng đã nêu rõ; trọng số biểu diễn đúng hơn |

---

## 8. GỢI Ý CẤU TRÚC CHAPTER

```
CHƯƠNG 1 — Giới thiệu
  1.1 Đặt vấn đề (sàng lọc CV thủ công: tốn thời gian, thiếu nhất quán)
  1.2 Mục tiêu đề tài
  1.3 Phạm vi và giới hạn        → Mục 7

CHƯƠNG 2 — Cơ sở lý thuyết
  2.1 Bài toán Person-Job Fit
      → Zhu et al. 2018; Qin et al. 2023
  2.2 Large Language Models và Structured Extraction
      → Chain-of-Thought; LLM-based IE vs NER
  2.3 Dense Embeddings và Semantic Similarity
      → Bi-encoder vs cross-encoder; cosine; anisotropy
      → Công thức 4.1, 4.2
  2.4 Multi-Attribute Decision Making
      → SAW/WSM; điều kiện độc lập ưu tiên; AHP
      → Công thức 4.10
  2.5 Skill Ontology và Entity Resolution
      → ESCO/O*NET vs Stack Overflow tags; synonym ring
  2.6 Đồ thị tri thức và Bao đóng bắc cầu
      → DAG; subsumption; Warshall; fixpoint iteration
      → Công thức 4.5
  2.7 Fuzzy String Matching
      → Ratcliff/Obershelp vs Levenshtein
      → Công thức 4.4
  2.8 Thang đo và phép toán hợp lệ
      → Stevens; thang thứ tự trong D2-proficiency và D4
  2.9 AI có trách nhiệm trong tuyển dụng
      → EU AI Act; GDPR Art. 22; bias của embedding

CHƯƠNG 3 — Phân tích & Thiết kế hệ thống
  3.1 Kiến trúc tổng thể           → Mục 1.1
  3.2 Luồng nghiệp vụ              → Mục 1.2
  3.3 Thiết kế Database            → Mục 2
  3.4 Thiết kế API                 → Overview.md (API Contract)
  3.5 Stateless microservice pattern

CHƯƠNG 4 — Cài đặt hệ thống
  4.1 Stage 1: Document Processing → Mục 3.1
  4.2 Stage 2: LLM Parsing + Retry → Mục 3.2
  4.3 Stage 3: Embedding có chọn lọc → Mục 3.3
  4.4 Scoring Engine D1–D5         → Mục 3.4 + toàn bộ Mục 4
  4.5 Skill Matching 4 tầng        → Mục 3.5 (chương trọng tâm)
  4.6 Xây dựng dữ liệu tri thức    → crawl → build → close
  4.7 Qualitative Evaluation       → Mục 3.6

CHƯƠNG 5 — Kiểm thử & Đánh giá
  5.1 Chiến lược kiểm thử          → Mục 6.1
  5.2 Bất biến dữ liệu tri thức    → nhóm L
  5.3 Đánh giá xếp hạng            → Mục 6.2 (nDCG, ablation)
  5.4 Hiệu năng                    → Mục 6.3

CHƯƠNG 6 — Kết luận & Hướng phát triển
  6.1 Kết quả đạt được             → Mục 7.1
  6.2 Hạn chế                      → Mục 5.3 + 7.2
  6.3 Hướng phát triển
      - NL search (Stage 5–10)
      - task_type bất đối xứng cho embedding
      - Bootstrap luật entailment từ dữ liệu
      - Adaptive weights từ feedback của HR
      - Fine-tune embedding với hard-negative mining
```

---

*Tài liệu đối chiếu trực tiếp với source code `app/` — cập nhật 2026-08-05*
