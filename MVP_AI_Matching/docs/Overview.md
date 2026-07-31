# AI CV-JD Matching — System Overview

> Tài liệu này mô tả **đúng những gì đang có trong code** (`app/`). Mọi công
> thức, tên model, tên endpoint đều đối chiếu trực tiếp với source.
> Cập nhật: 2026-07-31

---

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

## 4 Endpoint hiện có

| Endpoint | LLM? | Mô tả |
| --- | --- | --- |
| `POST /ai/parse-jd` | ✅ 1 call | JD text → `ParsedJD` + `jd_embedding` (+ geocode) |
| `POST /ai/parse-cv` | ✅ 1–3 call | URL file CV → `cv_raw_text` + `ParsedCV` + `cv_embedding` (+ geocode) |
| `POST /ai/score` | ⬜ / ✅ tùy chọn | 5 chiều điểm + evaluation (narrative chỉ khi `include_narrative=true`) |
| `POST /ai/evaluate` | ✅ 1 call | Nhận xét định tính bằng tiếng Việt cho HR |
| `GET /health` | — | Health check |

> **Chưa có trong code:** `/ai/recalculate` và `/ai/search` (NL search). Xem
> mục [Ngoài phạm vi bản hiện tại](#ngoài-phạm-vi-bản-hiện-tại).

---

## Nghiệp vụ 2 Side

### Side 1 — Ứng viên nộp CV

```
1. Ứng viên vào trang chi tiết Job → xem JD

2. Nhấn "Nộp đơn" → upload file CV (PDF hoặc DOCX)

3. ReactJS → POST /api/applications { job_id, cv_file }

4. .NET xử lý:
   a. Xác thực JWT token → candidate_id
   b. Upload file lên S3/R2 → nhận presigned URL
   c. Lưu application record, status = "processing"
   d. Lấy parsed_jd + jd_embedding + scoring_config từ DB
   e. Gọi AI Service (2 lần):
      → POST /ai/parse-cv { cv_url }
      ← { results: [{ cv_raw_text, parsed_cv, cv_embedding }] }

      → POST /ai/score { parsed_cv, parsed_jd, cv_embedding, jd_embedding, weights }
      ← { final_score, scores{5}, weights_used, evaluation }
   f. UPDATE application: lưu tất cả kết quả, status = "done"
   g. Return về ReactJS

5. ReactJS hiển thị kết quả ngay:
   ┌─────────────────────────────────┐
   │  Điểm phù hợp của bạn: 78.5/100 │
   │  Semantic similarity  ████░  82% │
   │  Skills match         ███░░  75% │
   │  Experience           ████░  80% │
   │  Education            █████ 100% │
   │  Location             ███░░  60% │
   └─────────────────────────────────┘
```

**Thời gian xử lý:** ~5–10s (LLM parse + embedding là chủ yếu; chấm điểm ~1ms)

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
1. HR kéo 5 sliders (tổng phải = 1.0) → PUT /api/jobs/{id}/scoring-config

2. .NET:
   a. Validate sum == 1.0
   b. UPDATE scoring_configs
   c. Gọi lại POST /ai/score cho từng application với weights mới
      (AI service hiện chưa có endpoint recalculate riêng)

   → Hoặc .NET tự tính lại: final = Σ(scoreᵢ/100 × wᵢ) × 100
     vì 5 điểm thành phần đã được lưu sẵn trong DB, phép tính là
     số học thuần túy, không cần gọi AI service.
```

#### 2d. Xem nhận xét chi tiết 1 ứng viên

```
1. HR bấm vào 1 ứng viên trong bảng ranking

2. .NET:
   → POST /ai/evaluate { parsed_cv, parsed_jd }
   ← { skill_details[], missing_must_have[], missing_preferred[],
       missing_nice_to_have[], bonus_skills[], skill_match_rate,
       experience_verdict, experience_detail, education_verdict,
       narrative }

3. ReactJS hiển thị:
   ┌──────────────────────────────────────────────────┐
   │ Nguyen Van A — 82.1 điểm                          │
   │ Kỹ năng khớp: 85.7%                               │
   │ ✓ React   ✓ TypeScript   ✓ Node.js (suy ra)      │
   │ ✗ Thiếu bắt buộc: Kubernetes                      │
   │ + Bonus: GraphQL, Redis                           │
   │                                                    │
   │ "Ứng viên có nền tảng frontend vững, 3 năm..."   │
   └──────────────────────────────────────────────────┘
```

> `/ai/score` cũng trả về khối `evaluation` này (không có `narrative` trừ khi
> truyền `include_narrative=true`), nên .NET có thể lấy phần structured ngay
> ở bước chấm điểm và chỉ gọi `/ai/evaluate` khi HR thực sự mở chi tiết.

---

## Complete Backend ↔ AI Flow

### Flow 1 — HR tạo Job

```
[.NET API]                              [AI Service]
    │
    │  POST /ai/parse-jd
    │  { "jd_text": "..." }        (hoặc text/plain: raw JD)
    │ ─────────────────────────────────────────────→
    │                                        Stage 2: LLM Extraction
    │                                        gemini-2.5-flash → parsed_jd JSON
    │                                        (temperature=0, response_format=json_object)
    │                                        Geocode: Nominatim(raw_address ?? city)
    │                                        → work_location.{lat,lng}
    │                                        Stage 3: Embedding
    │                                        gemini-embedding-001 → float[3072]
    │                                        (input = parsed_jd.build_embed_text())
    │ ←─────────────────────────────────────────────
    │  { parsed_jd, jd_embedding, error }
    │
    ├─ INSERT jobs { title, description, parsed_jd, jd_embedding }
    └─ INSERT scoring_configs { job_id, defaults: 30/35/20/10/5 }
```

`jd_embedding` là `null` kèm `error != null` nếu bước embedding lỗi — parse
vẫn thành công. `/ai/score` coi thiếu embedding là **điểm trung lập 0.5** cho
D1, không phải lỗi.

---

### Flow 2 — Ứng viên nộp CV

```
[ReactJS]          [.NET API]                         [AI Service]
    │                   │
    │  POST /apply       │
    │  { job_id,         │
    │    cv_file }       │
    │──────────────→     │
    │               Upload S3/R2 → presigned URL
    │               INSERT application, status = "processing"
    │                   │
    │                   │  POST /ai/parse-cv
    │                   │  { "cv_url": "https://s3.../cv.pdf" }
    │                   │ ─────────────────────────────→
    │                   │                        Download file (retry 3×)
    │                   │                        Stage 1: Document Processing
    │                   │                        PyMuPDF smart layout extract
    │                   │                        → quality score < 60? OCR fallback
    │                   │                        → clean_text()
    │                   │                        Stage 2: LLM Extraction
    │                   │                        gemini-2.5-flash → parsed_cv JSON
    │                   │                        → completeness check → retry nếu thiếu
    │                   │                        Geocode: Nominatim(raw_address)
    │                   │                        → candidate_location.{lat,lng}
    │                   │                        Stage 3: Embedding
    │                   │                        gemini-embedding-001 → float[3072]
    │                   │ ←─────────────────────────────
    │                   │  { results: [{ url, cv_raw_text, parsed_cv,
    │                   │               cv_embedding, error }] }
    │                   │
    │                   │  POST /ai/score
    │                   │  {
    │                   │    parsed_cv,            ← vừa nhận
    │                   │    parsed_jd,            ← lấy từ DB
    │                   │    cv_embedding,         ← vừa nhận
    │                   │    jd_embedding,         ← lấy từ DB
    │                   │    weights,              ← lấy từ scoring_configs (optional)
    │                   │    include_narrative: false
    │                   │  }
    │                   │ ─────────────────────────────→
    │                   │                        Stage 4: Scoring Engine (pure Python)
    │                   │                        D1: normalize_cosine(cosine_sim(cv, jd))
    │                   │                        D2: 4-layer skill match (nhị phân)
    │                   │                        D3: min(cv_years / jd_years, 1.0)
    │                   │                        D4: min(cv_level / jd_level, 1.0)
    │                   │                        D5: OSRM driving-time (lat/lng đã geocode)
    │                   │                        → final = Σ(Dᵢ × Wᵢ) × 100
    │                   │                        ‖ song song: evaluator (Python analysis)
    │                   │ ←─────────────────────────────
    │                   │  { final_score, scores{5}, weights_used, evaluation }
    │                   │
    │               UPDATE application
    │               SET cv_raw_text, parsed_cv, cv_embedding,
    │                   final_score, scores JSONB, evaluation JSONB,
    │                   status = "done"
    │                   │
    │ ←─────────────────│
    │  { final_score: 78.5,
    │    scores: { semantic:82, skills:75,
    │              experience:80,
    │              education:100, location:60 } }
```

**Batch:** `/ai/parse-cv` nhận `cv_urls: [...]` (tối đa 50 URL) và xử lý
**đồng thời** bằng `asyncio.gather`. Lỗi ở 1 CV chỉ set `error` cho đúng phần
tử đó, các CV khác không bị ảnh hưởng (per-item error tolerance).

---

### Flow 3 — HR đổi weights

```
[.NET API]
    │
    │  Validate sum(weights) == 1.0
    │  UPDATE scoring_configs
    │  SELECT applications WHERE job_id = {id}
    │    → { id, scores: { semantic, skills, experience, education, location } }
    │
    │  Tính lại tại chỗ (không cần AI service):
    │    final = Σ(scoreᵢ / 100 × wᵢ) × 100
    │
    │  Batch UPDATE applications SET final_score = ...
    │  Return new ranking (sorted DESC)
```

5 điểm thành phần đã nằm sẵn trong DB, phép tính lại là **tổ hợp tuyến tính
thuần túy** — không cần LLM, không cần embedding, không cần round-trip sang
AI service. Nếu muốn giữ mọi logic chấm điểm ở một chỗ thì gọi lại `/ai/score`
với `weights` mới.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     INDEXING PHASE                               │
│              (chạy khi CV/JD được submit)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PDF/DOCX file (tải từ S3/R2 URL)                                │
│      │                                                            │
│      ▼  [STAGE 1 — Document Processing]  pdf_extractor.py        │
│  PyMuPDF (fitz)                                                   │
│  ├─ extract_text_smart_layout()   ← 1-col vs 2-col detection     │
│  ├─ evaluate_extracted_text_quality()  ← score 0–100            │
│  ├─ quality < 60 → pytesseract OCR (200 DPI, eng+vie)           │
│  └─ clean_text()                                                 │
│      │                                                            │
│      ▼  raw_text (clean)                                         │
│      │                                                            │
│      ▼  [STAGE 2 — Structured Extraction]  parser.py             │
│  LLM provider theo .env (gemini | anthropic | groq), temp=0       │
│  ├─ CV prompt  → { skills[], work_experience[], education[],     │
│  │                 projects[], certifications[], languages[],     │
│  │                 candidate_location }                           │
│  ├─ completeness check → retry prompt nếu skills/work_exp rỗng   │
│  ├─ JD prompt  → { title, responsibilities, required_skills[],   │
│  │                 preferred_skills[], nice_to_have_skills[],     │
│  │                 min_experience_years, education_degree,        │
│  │                 work_location }                                │
│  └─ Geocode (Nominatim) → lat/lng   ← 1 lần, giống embedding     │
│      │                                                            │
│      ▼  parsed JSON (Pydantic validated)                         │
│      │   ├─ months tính bằng Python, KHÔNG hỏi LLM               │
│      │   ├─ _filter_empty_entries: loại entry LLM bịa            │
│      │   └─ _drop_generic_skills: loại "teamwork", "problem      │
│      │      solving"... khỏi cả 3 tier skill của JD               │
│      │                                                            │
│      ▼  [STAGE 3 — Dense Embedding]  embedder.py                 │
│  gemini-embedding-001 (qua OpenAI-compatible endpoint)            │
│  ├─ input: build_embed_text()  ← KHÔNG phải raw_text             │
│  │          (narrative-fit: bỏ skills[] và tech_stack[])          │
│  └─ output: float[3072]                                           │
│      │                                                            │
│      ▼  (trả về .NET → lưu PostgreSQL)                          │
│  { cv_raw_text, parsed_json, embedding[3072] }                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     SCORING PHASE                                │
│              (chạy ngay sau indexing)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [STAGE 4 — Multi-Dimension Scoring]  scorer.py                  │
│  numpy + pure Python, KHÔNG gọi LLM                              │
│                                                                   │
│  D1 Semantic    numpy cosine     normalize_cosine(cos(cv, jd))   │
│                 ─────────────────────────────────────────────    │
│  D2 Skills      4-layer cascade  Σ(wᵢ·mᵢ)/Σ(wᵢ),  mᵢ ∈ {0,1}   │
│                 (trên CẢ 3 tier: required / preferred / n-t-h)   │
│                 ─────────────────────────────────────────────    │
│  D3 Experience  arithmetic       min(cv_years/jd_years, 1.0)    │
│                 ─────────────────────────────────────────────    │
│  D4 Education   lookup table     min(cv_level/jd_level, 1.0)    │
│                 ─────────────────────────────────────────────    │
│  D5 Location    OSRM route       max(0, 1 - t/T_max)             │
│                                                                   │
│  final_score = Σ(Dᵢ × Wᵢ) × 100                                 │
│                                                                   │
│  Default weights:                                                 │
│  semantic=0.30 | skills=0.35 | exp=0.20 | edu=0.10 | loc=0.05  │
│                                                                   │
│  Quy tắc "thiếu dữ liệu → 0.5" (neutral, không phạt):           │
│    D1 thiếu embedding · D4 CV không có bằng cấp                  │
│    D5 thiếu lat/lng hoặc OSRM lỗi 2 lần                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     EVALUATION PHASE                             │
│              (song song với scoring, hoặc gọi riêng)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [STAGE 5 — Qualitative Evaluation]  evaluator.py                │
│  ├─ _analyze_skills()      Python — tái dùng SkillMatcher        │
│  │    → skill_details[], missing_must_have[], missing_preferred[],│
│  │      missing_nice_to_have[], bonus_skills[], skill_match_rate  │
│  │      (cùng evaluate_tiers với D2 → rate luôn khớp điểm skills) │
│  ├─ _analyze_experience()  Python — verdict 4 mức                │
│  │    not_required | over_qualified | sufficient | insufficient  │
│  ├─ _analyze_education()   Python — verdict 4 mức                │
│  │    not_required | exceeds | meets | below                     │
│  └─ _llm_narrative()       LLM 1 call — đoạn văn tiếng Việt      │
│       Mọi CON SỐ do Python tính trước; LLM chỉ "viết văn"        │
│       KHÔNG có recommendation (interview/reject) — HR tự quyết   │
└─────────────────────────────────────────────────────────────────┘
```

---

## D1 — Semantic (chi tiết)

```python
# scorer.py
cosine_sim(v1, v2) = dot(v1, v2) / (‖v1‖ · ‖v2‖)
normalize_cosine(r) = clamp((r - COSINE_MIN) / (COSINE_MAX - COSINE_MIN), 0, 1)
```

**Cấu hình hiện tại:** `COSINE_MIN = 0.0`, `COSINE_MAX = 1.0` → **không kéo
giãn**, cosine thô được dùng trực tiếp. Hai hằng số này đọc từ `.env`, có thể
chỉnh sang `0.2 / 0.8` nếu muốn kéo giãn thang điểm (xem `app/config.py`).

**Text được embed KHÔNG phải raw text**, mà là `build_embed_text()`:

| | Đưa vào embedding | Loại khỏi embedding |
| --- | --- | --- |
| **CV** | `summary`, `role at company: description` (job mới nhất trước), `Project: name + description`, học vấn, certifications, languages | `skills[]`, mọi `tech_stack[]` |
| **JD** | `title`, `responsibilities`, min experience, degree yêu cầu | `required_skills[]`, `preferred_skills[]`, `nice_to_have_skills[]` |

**Lý do loại skills khỏi D1:** so khớp kỹ năng là việc của D2. Nếu embed cả
token kỹ năng thì cùng một tín hiệu bị tính **hai lần** trên hai chiều điểm
(0.30 + 0.35 thực chất dồn 0.65 vào kỹ năng), vi phạm giả định **độc lập giữa
các tiêu chí** của mô hình cộng có trọng số. D1 vì vậy chỉ đo **narrative fit**:
vai trò, phạm vi trách nhiệm, bối cảnh nghiệp vụ.

Hằng số `EMBED_TEXT_VERSION = "v2-no-skills"` (`schemas.py`) đánh dấu phiên bản
nội dung được embed — **bump khi `build_embed_text()` đổi**, để vector tính từ
shape cũ không bị so sánh nhầm với vector tính từ shape mới.

---

## D2 — Skills (chi tiết)

$$D_2 = \frac{\sum_i w_i \cdot m_i}{\sum_i w_i}, \quad w_i \in \{1,2,3\}, \quad m_i \in \{0, 1\}$$

Chấm **nhị phân**: mỗi requirement hoặc thỏa (full trọng số) hoặc thiếu (0).
Không còn partial credit fuzzy/category như bản trước.

Mỗi requirement là một **OR-group** — `{skill} ∪ alternatives`, thỏa 1 phương án
là đủ (JD ghi "React, Vue hoặc Angular" → 1 entry, không tách thành 3).

### 3 tier skill của JD đều tính điểm

`SkillMatcher.evaluate_tiers()` duyệt **cả 3 danh sách** skill của JD và quy đổi
mỗi skill về một trọng số $w_i$:

| Tier JD | Trọng số $w_i$ | Nguồn trọng số |
| --- | --- | --- |
| `required_skills[]` | `req.weight` ∈ {1, 2, 3} | LLM gán; skill lấy từ dòng tag "Required Skills:" luôn = 3 |
| `preferred_skills[]` | **2** (cố định) | `PREFERRED_SKILL_WEIGHT` — list string phẳng, không có weight riêng |
| `nice_to_have_skills[]` | **1** (cố định) | `NICE_TO_HAVE_SKILL_WEIGHT` |

Thiếu 1 skill preferred/nice-to-have **vẫn kéo D2 xuống**, chỉ nhẹ hơn thiếu 1
skill bắt buộc. JD không nêu skill nào ở **cả 3 tier** → D2 = 1.0 (trung lập,
cùng quy tắc "JD không yêu cầu → không có gì để thiếu" như D3/D4).

`evaluate_tiers()` là **nguồn duy nhất** cho cả `scorer.score_skills` (D2) lẫn
`evaluator._analyze_skills` (hiển thị cho HR) → `skill_match_rate` luôn khớp
đúng điểm `skills` trong `scores`.

> **Không có bước dedup chéo tier trong code.** `JD_EXTRACT_PROMPT` chịu trách
> nhiệm bảo đảm mỗi skill chỉ xuất hiện ở đúng **một** tier — 3 dòng tag
> "Required / Preferred / Nice to Have Skills:" do .NET gửi xuống được copy
> **nguyên văn** theo đúng tier của chúng, và skill khai thác thêm từ prose chỉ
> được thêm khi chưa nằm trong bất kỳ dòng tag nào.

### Cascade 4 tầng + 1 tầng phụ

| Tầng | Cơ chế | Dữ liệu | Ví dụ |
| --- | --- | --- | --- |
| **Layer 0** | Direct match trên output LLM thô (lowercase + strip) | — | `"Python"` ↔ `"python"` |
| **Layer 1** | Canonical hóa **cả 2 phía** rồi so exact | `skill_data.json` | `"Node.js"` ↔ `"nodejs"` → cùng canonical `node.js` |
| **Layer 2** | Entailment "biết X thì biết Y" | `skill_implies.json` | CV có `django` → thỏa JD đòi `python` |
| **Layer 3** | Fuzzy `SequenceMatcher ≥ 0.85` trên chuỗi thô | — | `"Postgresql"` ↔ `"PostgreSQL"` |
| **Phụ** | Trình độ ngôn ngữ so theo **thứ bậc** trong cùng framework | regex | CV `JLPT N2` thỏa JD đòi `JLPT N3` |

Thứ tự là **cascade ưu tiên precision**: tầng chính xác chạy trước, tầng lỏng
nhất (fuzzy) chạy sau cùng và chỉ khi 3 tầng trên đã trượt. Mỗi requirement
dừng ngay tại tầng sớm nhất thỏa nó.

**Fuzzy bị chặn trên token trình độ ngôn ngữ**: `"N4"` giống `"N3"` về ký tự
nhưng **thấp hơn về chất** — phải để tầng proficiency so theo thứ bậc.

### Dữ liệu tĩnh

| File | Kích thước | Nguồn | Vai trò |
| --- | --- | --- | --- |
| `app/data/skill_data.json` | **9.524 entry** (3.988 canonical + 5.536 synonym) | Stack Overflow Tags API + tag synonyms + bổ sung thủ công | Layer 1 |
| `app/data/skill_implies.json` | **1.504 key / 1.707 cạnh** (đã đóng bắc cầu) | Viết tay + `close_implies.py` | Layer 2 |

Pipeline dựng dữ liệu (chạy **tay**, commit output):

```
crawl_so_tags.py                  → so_raw_data.json   (crawl toàn bộ SO tag, loại collective tag)
build_skill_data.py               → skill_data.json    (gọi /tags/{tags}/synonyms → map synonym → canonical)
add_misc_skills.py                ┐
add_qa_skills.py                  │ bổ sung thủ công theo domain (idempotent):
add_ai_python_skills.py           │ ghi thêm vào skill_data.json + skill_implies.json
add_devops_support_qa_skills.py   ┘
close_implies.py                  → skill_implies.json (đóng bắc cầu: nestjs→typescript→javascript
                                                        ⟹ nestjs cũng liệt kê javascript)
```

Mỗi script `add_*.py` đều **idempotent** và phải chạy `close_implies.py` **sau
cùng** để đóng lại bắc cầu (test nhóm L trong `test_d2_skills.py` fail ngay nếu
quên bước này).

Đồ thị implies là **DAG** → bao đóng bắc cầu luôn hội tụ (lặp tới điểm bất
động). Vật chất hóa **offline** để runtime chỉ cần **tra hash O(1)**, không
duyệt đồ thị lúc chấm điểm.

`app/data/top_dev_skill_data.json` là **artifact thô** còn sót lại từ một lần
gọi API (không có code nào đọc file này) — không phải nguồn dữ liệu của Layer 1/2.

### Ngôn ngữ / chứng chỉ

Framework hỗ trợ: **JLPT** (N5→N1, thứ tự nghịch), **HSK** (1→9), **TOPIK**
(1→6), **IELTS**, **TOEIC**, **TOEFL**, **CEFR** (A1→C2). Chỉ so **trong cùng
framework** — IELTS 6.5 và TOEIC 800 không quy đổi chéo.

Chuỗi chứng chỉ được **tách sub-token**: `"Japanese - JLPT N3"` → `{"japanese
- jlpt n3", "japanese", "jlpt n3"}`, để JD đòi `"JLPT N3"` khớp được.

### Nguồn kỹ năng từ CV

`cv.skills` + mọi `work_experience[].tech_stack` + mọi `projects[].tech_stack`
+ `languages` + `certifications` (2 mục cuối được tách sub-token).

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
| D1 Semantic   | Vai trò/bối cảnh CV ↔ JD có khớp   | Được                              |
| D2 Skills     | Đúng skills nào có mặt             | Không — cần structured list       |
| D3 Experience | Tổng số năm làm việc               | Không — cần tính số               |
| D4 Education  | Degree level (Bach < Master < PhD) | Không — cần lookup                |
| D5 Location   | Driving-time giữa CV ↔ JD address  | Không — cần geocode + routing     |

**D5 — Location + Work Mode:**

- **Parse-time** (`/ai/parse-jd`, `/ai/parse-cv`): LLM trích `raw_address` thô,
  sau đó gọi **Nominatim** (OpenStreetMap, miễn phí, không cần key) **một lần**
  để geocode → `lat`/`lng`. Giống hệt cách `embedding` được tính một lần tại
  parse-time — vì lat/lng là thuộc tính của bản thân JD/CV, không phụ thuộc
  cặp CV↔JD nào. .NET lưu `lat`/`lng` cùng `parsed_jd`/`parsed_cv`.
- **Score-time** (`score_location()`): đọc thẳng `lat`/`lng` đã lưu, **không
  geocode lại**. Chỉ gọi **OSRM public demo server** để tính route driving
  duration giữa 2 tọa độ — vì route phụ thuộc cặp CV↔JD cụ thể.
- Geocode thất bại → thiếu lat/lng → **0.5** (trung lập).
- OSRM lỗi → retry 1 lần sau 0.5s; vẫn lỗi → **0.5**. Không có fallback
  haversine (đường chim bay không phản ánh giao thông đô thị — sông, đường 1
  chiều, tắc đường — dễ sai lệch hơn là trả điểm trung lập).

**3 thứ .NET lưu sau mỗi CV:**

1. `cv_raw_text` — hiển thị / audit / re-parse
2. `parsed_cv` JSON — D2, D3, D4, D5 + evaluation
3. `cv_embedding` float[3072] — D1 semantic

---

## API Contract (AI Service ↔ .NET)

### POST /ai/parse-jd

Nhận **`application/json`** hoặc **`text/plain`** (tự nhận diện: nếu body parse
được thành JSON có field `jd_text` thì dùng field đó, ngược lại coi toàn bộ
body là raw JD text).

```json
Request:  { "jd_text": "string" }

Response: {
  "parsed_jd": {
    "title": "Junior .NET Backend Developer",
    "responsibilities": "Phát triển và bảo trì các API nội bộ cho hệ thống ...",
    "required_skills": [
      { "skill": "C#",      "weight": 3, "alternatives": [] },
      { "skill": "React",   "weight": 2, "alternatives": ["Vue", "Angular"] }
    ],
    "preferred_skills": ["Docker"],
    "nice_to_have_skills": ["Agile & Scrum"],
    "min_experience_years": 2,
    "education_degree": "bachelor",
    "work_location": {
      "city": "Ha Noi",
      "raw_address": "Tòa nhà ABC, 123 Cầu Giấy, Hà Nội",
      "work_mode": "onsite",
      "lat": 21.0313,
      "lng": 105.8014
    }
  },
  "jd_embedding": [0.123, ...],
  "error": null
}
```

- `city` bị **ràng buộc cứng** vào 3 giá trị: `"Ha Noi" | "Ho Chi Minh" | "Da Nang"`.
- `work_mode` ∈ `"onsite" | "hybrid" | "remote"`, **mặc định `"onsite"`** khi JD
  không nêu — đây là **giả định heuristic** (đa số JD không ghi rõ trong thị
  trường này là onsite), không phải giá trị trung lập.
- `education_degree` ∈ `high_school | associate | bachelor | master | phd | other | null`.
- `responsibilities` **cố ý không chứa tên skill/tool** — skill nằm ở 3 tier
  skill; trường này chỉ để D1 embed narrative.
- 3 tier skill (`required_skills` / `preferred_skills` / `nice_to_have_skills`)
  ánh xạ đúng 3 dòng tag `Required Skills:` / `Preferred Skills:` / `Nice to
  Have Skills:` trong `jd_text` do .NET sinh ra (mirror `tags.*` bên BE). **Cả
  3 đều tham gia D2** với trọng số giảm dần — xem [D2 — Skills](#d2--skills-chi-tiết).
- `lat`/`lng` = `null` nếu geocode thất bại → `/ai/score` coi là trung lập.
- `jd_embedding` = `null` + `error != null` nếu embedding lỗi (parse vẫn OK).
- Soft skill chung chung ("teamwork", "problem solving", "programming
  fundamentals"...) bị **lọc bỏ tự động** (`GENERIC_NON_SKILLS`, 44 mục) khỏi
  **cả 3** danh sách skill — chúng không bao giờ khớp được với CV và sẽ tạo
  "missing must-have" giả cho **mọi** ứng viên.

### POST /ai/parse-cv

Nhận **URL** (S3/R2/presigned), không nhận multipart. Tối đa **50 URL**/request.

```json
Request:  { "cv_url":  "https://s3.amazonaws.com/bucket/cv.pdf" }
      hoặc { "cv_urls": ["https://...", "https://..."] }

Response: {
  "results": [
    {
      "url": "https://s3.amazonaws.com/bucket/cv.pdf",
      "cv_raw_text": "string",
      "parsed_cv": {
        "name": "Nguyen Van A",
        "summary": "Backend developer with 3 years ...",
        "skills": ["Python", "FastAPI", "Docker"],
        "work_experience": [
          {
            "company": "ABC", "role": "Backend Dev",
            "start": "2021-06", "end": "present",
            "months": 49, "is_current": true,
            "tech_stack": ["Python", "FastAPI"],
            "description": "..."
          }
        ],
        "education": [
          { "institution": "HCMUT", "degree": "bachelor",
            "degree_raw": "Bachelor of Software Engineering", "major": "SE" }
        ],
        "projects": [
          { "name": "...", "tech_stack": ["FastAPI", "Redis"], "description": "..." }
        ],
        "certifications": ["AWS Cloud Practitioner"],
        "languages": ["English - TOEIC 835"],
        "candidate_location": {
          "raw_address": "45 Lê Lợi, Quận 1, TP. Hồ Chí Minh",
          "lat": 10.7757,
          "lng": 106.7004,
          "willing_to_relocate": null
        }
      },
      "cv_embedding": [0.456, ...],
      "error": null
    }
  ]
}
```

- `months` do **Python tính** từ `start`/`end` (không giao cho LLM — LLM dễ sai
  ±1–2 tháng).
- `willing_to_relocate` = `true` **chỉ khi** CV nói rõ; không bao giờ suy diễn.
- Lỗi ở 1 URL chỉ set `error` cho phần tử đó; các URL còn lại vẫn trả kết quả.

### POST /ai/score

```json
Request: {
  "parsed_cv": { ... },
  "parsed_jd": { ... },
  "cv_embedding": [0.456, ...],
  "jd_embedding": [0.123, ...],
  "weights": { "semantic": 0.30, "skills": 0.35, "experience": 0.20,
               "education": 0.10, "location": 0.05 },
  "include_narrative": false
}

Response: {
  "final_score": 78.5,
  "scores": {
    "semantic": 82.0, "skills": 75.0, "experience": 80.0,
    "education": 100.0, "location": 60.0
  },
  "weights_used": { "semantic": 0.30, "skills": 0.35, "experience": 0.20,
                    "education": 0.10, "location": 0.05 },
  "evaluation": {
    "skill_details": [
      { "skill": "C#", "status": "matched", "weight": 3 },
      { "skill": "React / Vue / Angular", "status": "matched_implied", "weight": 2 },
      { "skill": "Kubernetes", "status": "missing_must_have", "weight": 3 }
    ],
    "missing_must_have": ["Kubernetes"],
    "missing_preferred": ["Docker"],
    "missing_nice_to_have": ["Agile & Scrum"],
    "bonus_skills": ["GraphQL", "Redis"],
    "skill_match_rate": 71.4,
    "experience_verdict": "sufficient",
    "experience_detail": "CV có 3.2 năm, JD yêu cầu 2 năm ✓",
    "education_verdict": "meets",
    "narrative": ""
  }
}
```

- `weights` **tùy chọn**. Nếu truyền thì phải có **đúng 5 key**, mỗi giá trị
  ∈ [0,1], **tổng = 1.0** (sai → HTTP 422). Bỏ trống → dùng default từ `.env`.
- `weights_used` echo lại bộ trọng số **thực sự áp dụng** — để .NET/UI hiển thị
  và audit.
- `include_narrative: true` → chạy thêm 1 LLM call sinh `narrative` (chi phí
  bằng gọi `/ai/evaluate`). Mặc định `false`.
- Chấm điểm chạy trong thread (`asyncio.to_thread`) **song song** với evaluator.

### POST /ai/evaluate

```json
Request:  { "parsed_cv": { ... }, "parsed_jd": { ... } }

Response: {          ← cùng shape với khối "evaluation" ở trên
  "skill_details": [...],
  "missing_must_have": [...],
  "missing_preferred": [...],
  "missing_nice_to_have": [...],
  "bonus_skills": [...],
  "skill_match_rate": 71.4,
  "experience_verdict": "sufficient",
  "experience_detail": "CV có 3.2 năm, JD yêu cầu 2 năm ✓",
  "education_verdict": "meets",
  "narrative": "Ứng viên có nền tảng backend vững với 3.2 năm kinh nghiệm ..."
}
```

- `status` của mỗi skill ∈ `matched | matched_implied | missing_must_have |
  missing_preferred | missing_nice_to_have`.
- Skill thiếu được xếp bucket theo **tier + weight**:
  `missing_must_have` = tier `required` và `weight >= 3`;
  `missing_preferred` = tier `preferred`, **hoặc** tier `required` với
  `weight < 3`; `missing_nice_to_have` = tier `nice_to_have`.
- `skill_match_rate` dùng **đúng công thức 3 tier** của D2 (`evaluate_tiers`),
  nên con số này luôn bằng điểm `skills` trong `/ai/score`.
- `bonus_skills`: skill CV có mà JD không nêu ở **bất kỳ tier nào** (so trên
  dạng canonical, tối đa 8 mục).
- **Không có trường `recommendation`** (interview/reject). Narrative chỉ mô tả;
  quyết định do HR đưa ra dựa trên `final_score`, tránh mâu thuẫn giữa nhãn của
  LLM và điểm số của hệ thống.
- Mọi con số trong narrative (tỷ lệ khớp, số năm) đều do **Python tính trước**
  rồi đưa vào prompt — LLM không tự suy luận số liệu.

---

## Xử lý lỗi — quy tắc chung

| Tình huống | Hành vi |
| --- | --- |
| Embedding lỗi lúc parse | `embedding = null` + `error != null`, parse vẫn trả về |
| Thiếu embedding lúc score | D1 = **0.5** (trung lập) |
| CV không có bằng cấp | D4 = **0.5** |
| Thiếu lat/lng | D5 = **0.5** |
| OSRM lỗi | retry 1 lần sau 0.5s → vẫn lỗi thì **0.5** |
| JD không có skill ở cả 3 tier / không yêu cầu exp/degree | chiều tương ứng = **1.0** (không phạt) |
| LLM trả JSON hỏng | strip trailing comma → `json_repair` → raise nếu vẫn hỏng |
| CV parse thiếu skills/work_exp | retry prompt tập trung (song song) |
| 1 URL trong batch lỗi | chỉ phần tử đó có `error`, batch vẫn thành công |

Nguyên tắc xuyên suốt: **thiếu dữ liệu → điểm trung lập 0.5, không phạt** —
ứng viên không bị trừ điểm vì hệ thống không trích xuất được thông tin.

---

## Tech Stack Summary

| Stage | Công việc              | Tech                                                         |
| ----- | ---------------------- | ------------------------------------------------------------ |
| 1     | PDF/DOCX → clean text  | `PyMuPDF (fitz)`, `pytesseract`, `python-docx`               |
| 2     | Text → structured JSON | `anthropic` SDK · `openai` SDK trỏ endpoint Gemini/Groq       |
| 3     | Text → vector          | `openai` SDK → `gemini-embedding-001` (3072-dim)             |
| 3b    | Address → lat/lng      | `Nominatim` (OpenStreetMap, free, no key)                    |
| 4     | Scoring 5 dimensions   | `numpy` (cosine), pure Python (math)                          |
| 4b    | Driving time           | `OSRM` public demo server (free, no key)                     |
| 5     | Skill matching         | Pure Python — 4-layer cascade + `difflib.SequenceMatcher`    |
| 6     | HR narrative           | LLM 1 call (cùng provider Stage 2)                            |

**LLM provider** đổi qua `.env` `LLM_PROVIDER` = `gemini` (mặc định) |
`anthropic` | `groq`. **Embedding chỉ hỗ trợ Gemini.**

## Project Structure (AI Service)

```
MVP_AI_Matching/
├── app/
│   ├── main.py                  # FastAPI app, mount routers, /health
│   ├── config.py                # Settings (pydantic-settings), SCORE_DIMENSIONS
│   ├── schemas.py               # ParsedCV / ParsedJD / CVJobEvaluation + helpers
│   │
│   ├── api/
│   │   ├── parse.py             # POST /ai/parse-jd, POST /ai/parse-cv
│   │   ├── score.py             # POST /ai/score
│   │   └── evaluate.py          # POST /ai/evaluate
│   │
│   ├── services/
│   │   ├── pdf_extractor.py     # Stage 1 — smart layout + OCR fallback
│   │   ├── parser.py            # Stage 2 — LLM prompts + retry + geocode
│   │   ├── llm_client.py        # LLM provider abstraction (3 provider)
│   │   ├── embedder.py          # Stage 3 — Gemini embedding 3072-dim
│   │   ├── scorer.py            # Stage 4 — 5-dimension scoring engine
│   │   ├── skill_matcher.py     # D2 — 4-layer cascade + proficiency
│   │   ├── location_service.py  # Nominatim geocode + OSRM route
│   │   └── evaluator.py         # Stage 5 — qualitative evaluation + narrative
│   │
│   └── data/
│       ├── skill_data.json      # 9.524 entry — Layer 1 canonical map
│       ├── skill_implies.json   # 1.504 key / 1.707 cạnh — Layer 2 entailment
│       ├── so_raw_data.json     # raw crawl từ Stack Overflow Tags API
│       ├── top_dev_skill_data.json          # artifact thô, KHÔNG được code đọc
│       ├── crawl_so_tags.py                 # (offline) crawl tag
│       ├── build_skill_data.py              # (offline) tag → canonical map
│       ├── close_implies.py                 # (offline) đóng bắc cầu DAG
│       ├── add_misc_skills.py               # (offline) bổ sung thủ công
│       ├── add_qa_skills.py                 # (offline) bổ sung nhóm QA
│       ├── add_ai_python_skills.py          # (offline) bổ sung AI/Python ecosystem
│       └── add_devops_support_qa_skills.py  # (offline) bổ sung DevOps/IT support/QA
│
├── tests/                       # 194 test, không cần LLM/network (~1s)
│   ├── test_d2_skills.py        # 103 test — D2 end-to-end (nhóm A–L)
│   ├── test_skill_matcher.py    # 45 test — từng tầng của cascade
│   ├── test_scorer.py           # 34 test — D1–D5 + aggregate
│   ├── test_evaluator.py        # 6 test
│   └── test_parser.py           # 6 test
│
├── docs/
├── quick_test.py                # smoke test CLI với server đang chạy
├── requirements.txt
├── .env
├── Dockerfile
├── docker-compose.yml
└── run.sh                       # helper start/stop uvicorn local
```

> **Trạng thái test hiện tại: 192 pass / 2 fail.** Cả 2 test fail đều là **test
> cũ chưa cập nhật** theo việc Layer 3 fuzzy được thêm lại
> (`test_scorer.py::test_score_skills_typo_no_longer_fuzzy_matched` và
> `test_d2_skills.py::test_J9_ui_ux_compound_term` — XPASS strict), không phải
> lỗi code.

## Dependencies

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
pydantic>=2.5.0
pydantic-settings>=2.1.0   # config từ .env
pymupdf>=1.24.0            # PDF extraction — smart layout 2-column
pytesseract>=0.3.10        # OCR fallback cho scan PDF (cần binary Tesseract)
pillow>=10.0.0             # image processing cho OCR
python-docx>=1.1.0         # DOCX extraction
anthropic>=0.40.0          # LLM provider: Claude
openai>=1.30.0             # LLM provider: Gemini/Groq (OpenAI-compatible) + embedding
json-repair>=0.61.0        # sửa JSON hỏng do LLM sinh
httpx>=0.27.0              # download CV từ URL + gọi Nominatim/OSRM
numpy>=1.26.0              # cosine similarity
pytest>=8.0.0              # dev
pytest-asyncio>=0.23.0     # dev
```

**Yêu cầu hệ thống ngoài Python:** binary `tesseract-ocr` + gói ngôn ngữ
`tesseract-ocr-vie` (cho OCR fallback tiếng Việt) — phải cài trong Docker image.

---

## Ngoài phạm vi bản hiện tại

Các tính năng từng có trong thiết kế nhưng **chưa được cài đặt** trong code:

| Tính năng | Trạng thái | Ghi chú |
| --- | --- | --- |
| `POST /ai/recalculate` | Chưa có | .NET tự tính được (tổ hợp tuyến tính trên 5 điểm đã lưu) |
| `POST /ai/search` — NL search | Chưa có | Cần: LLM parse query → embed query → cosine → filter → re-rank → LLM explain |
| Hard-rule penalties | Chưa có | Ý tưởng cũ: phạt −20%/must-have thiếu. Hiện `missing_must_have` chỉ được **báo cáo** trong `evaluation`, không trừ điểm |
| D3 modifiers (relevance/recency/over-qual) | Chưa có | D3 hiện chỉ là tỷ lệ số năm |
| Work-mode multiplier `M` cho D5 | Chưa có | `score_location()` chưa nhân hệ số tương thích work-mode |
| Fallback haversine cho D5 | Đã bỏ hẳn | Trả 0.5 thay vì ước lượng bằng đường chim bay |
| Category partial credit cho D2 | Đã bỏ hẳn | Thay bằng cascade 4 tầng, chấm nhị phân |
