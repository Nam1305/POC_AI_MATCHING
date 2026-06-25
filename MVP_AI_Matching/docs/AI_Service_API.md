# AI Service — API Reference

---

## Hướng dẫn tích hợp cho .NET Backend

Đây là tài liệu mô tả các API của **AI Service** (Python/FastAPI) cần được gọi từ **.NET Backend**.

AI Service là một microservice stateless — nó **không đọc/ghi database**, không giữ state. Toàn bộ việc lưu trữ kết quả do .NET Backend đảm nhiệm.

### Nguyên tắc chung

- Mỗi API call từ .NET phải được thực hiện tại đúng **business event** được chỉ định bên dưới.
- Kết quả trả về từ AI Service phải được **lưu ngay vào PostgreSQL** theo đúng cột/bảng đã mô tả.
- Các lần gọi sau (ví dụ: `/ai/score`) sẽ **đọc lại data đã lưu từ DB** rồi truyền vào — không gọi lại parse.
- Base URL của AI Service cấu hình qua biến môi trường, không hardcode.

### Tổng quan: API gọi ở đâu trong .NET

| API | Gọi ở đâu trong .NET | Lưu kết quả vào DB |
|---|---|---|
| `POST /ai/parse-jd` | Service/Handler xử lý **tạo mới hoặc cập nhật JD** | `job_descriptions`: `parsed_jd` (JSONB), `jd_embedding` (vector) |
| `POST /ai/parse-cv` | Service/Handler xử lý **ứng viên upload CV** | `candidates`: `cv_raw_text` (TEXT), `parsed_cv` (JSONB), `cv_embedding` (vector) |
| `POST /ai/score` | Service/Handler xử lý **ứng viên apply vào job** | `applications`: `final_score` (FLOAT), `scores` (JSONB), `evaluation` (JSONB) |
| `POST /ai/evaluate` | *(Tùy chọn)* Endpoint riêng để **refresh nhận xét** mà không tính lại điểm | `applications`: cập nhật lại `evaluation` (JSONB) |

### Dependency giữa các API

```
parse-jd  ──┐
             ├──► score  (cần cả parsed_jd + jd_embedding + parsed_cv + cv_embedding)
parse-cv  ──┘
```

`/ai/score` và `/ai/evaluate` **chỉ được gọi sau khi** cả parse-jd và parse-cv đã chạy xong và kết quả đã có trong DB.

### Xử lý lỗi

- Nếu AI Service trả HTTP 4xx/5xx hoặc timeout: log lỗi, **không lưu** kết quả rỗng vào DB, trả về lỗi phù hợp cho client.
- `/ai/parse-cv` trả lỗi **per-item** trong mảng `results` (field `error` không null) — .NET phải kiểm tra từng item, không chỉ check HTTP status.
- `/ai/parse-jd` có thể trả `error` không null (embed thất bại) nhưng `parsed_jd` vẫn hợp lệ — .NET vẫn lưu `parsed_jd`, chỉ bỏ qua `jd_embedding` nếu null.

---

> Base URL mặc định: `http://localhost:8000` (cấu hình qua env/config trong .NET)

---

## Mục lục

- [POST /ai/parse-jd](#post-aiparse-jd)
- [POST /ai/parse-cv](#post-aiparse-cv)
- [POST /ai/score](#post-aiscore)
- [POST /ai/evaluate](#post-aievaluate)
- [Enum Reference](#enum-reference)
- [Luồng tích hợp .NET + PostgreSQL](#luồng-tích-hợp-net--postgresql)
- [Gợi ý schema PostgreSQL](#gợi-ý-schema-postgresql)

---

## POST /ai/parse-jd

Parse text JD thô → cấu trúc JSON + embedding vector.

**.NET gọi khi:** HR tạo mới hoặc cập nhật JD.  
**.NET lưu:** `parsed_jd` → `JSONB`, `jd_embedding` → `vector(N)` vào bảng `job_descriptions`.

### Request

`Content-Type: application/json`

```json
{
  "jd_text": "Job Title: Senior Backend Developer\nRequirements: 5+ years .NET, PostgreSQL..."
}
```

> AI service cũng nhận `text/plain` (raw text trong body), tự detect — không cần set Content-Type chính xác.

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| `jd_text` | string | ✅ | Toàn bộ nội dung JD dạng plain text |

### Response 200

```json
{
  "parsed_jd": {
    "title": "Senior Backend Developer",
    "required_skills": [
      { "skill": ".NET", "weight": 3 },
      { "skill": "PostgreSQL", "weight": 2 },
      { "skill": "Docker", "weight": 1 }
    ],
    "preferred_skills": ["Kubernetes", "Redis"],
    "min_experience_years": 5,
    "education_degree": "bachelor",
    "keywords": ["microservices", "REST API", "CI/CD"]
  },
  "jd_embedding": [0.012, -0.034, 0.091, ...],
  "error": null
}
```

| Field | Type | Mô tả |
|---|---|---|
| `parsed_jd.title` | string | Tên vị trí |
| `parsed_jd.required_skills` | array | Kỹ năng yêu cầu, kèm `weight` (1=nice-to-have, 2=preferred, 3=must-have) |
| `parsed_jd.preferred_skills` | array\<string\> | Kỹ năng ưu tiên thêm (không bắt buộc) |
| `parsed_jd.min_experience_years` | int | Số năm kinh nghiệm tối thiểu |
| `parsed_jd.education_degree` | string\|null | Bằng cấp yêu cầu tối thiểu — xem [Enum](#enum-degreerevel) |
| `parsed_jd.keywords` | array\<string\> | Từ khóa công nghệ/domain trích từ JD |
| `jd_embedding` | array\<float\> | Dense vector ~1536 chiều, lưu vào `pgvector` |
| `error` | string\|null | Không null nếu bước embed thất bại (parsed_jd vẫn hợp lệ) |

---

## POST /ai/parse-cv

Download CV từ S3/R2 URL → extract text → parse → embedding vector.

**.NET gọi khi:** Ứng viên upload CV (sau khi .NET đã upload file lên S3 và có URL).  
**.NET lưu:** `cv_raw_text` → `TEXT`, `parsed_cv` → `JSONB`, `cv_embedding` → `vector(N)` vào bảng `candidates`.

### Request

`Content-Type: application/json`

```json
// Một CV:
{
  "cv_url": "https://s3.amazonaws.com/bucket/cv_nguyen_van_a.pdf"
}

// Hoặc nhiều CV cùng lúc (tối đa 10):
{
  "cv_urls": [
    "https://s3.amazonaws.com/bucket/cv1.pdf",
    "https://s3.amazonaws.com/bucket/cv2.pdf"
  ]
}
```

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| `cv_url` | string (URL) | Một trong hai | URL trỏ tới file CV (PDF hoặc DOCX) |
| `cv_urls` | array\<string\> | Một trong hai | Mảng URL, tối đa 10 CV mỗi request |

### Response 200

```json
{
  "results": [
    {
      "url": "https://s3.amazonaws.com/bucket/cv_nguyen_van_a.pdf",
      "cv_raw_text": "Nguyen Van A\nSoftware Engineer\nSkills: .NET, C#, PostgreSQL...",
      "parsed_cv": {
        "name": "Nguyen Van A",
        "summary": "5 years of experience as a backend developer...",
        "skills": [".NET", "C#", "PostgreSQL", "Redis", "Docker"],
        "work_experience": [
          {
            "company": "ABC Technology",
            "role": "Senior Backend Developer",
            "start": "2021-03",
            "end": "present",
            "months": 39,
            "is_current": true,
            "tech_stack": [".NET", "PostgreSQL", "Redis"],
            "description": "Built and maintained microservices for e-commerce platform."
          },
          {
            "company": "XYZ Corp",
            "role": "Backend Developer",
            "start": "2019-06",
            "end": "2021-02",
            "months": 20,
            "is_current": false,
            "tech_stack": ["Java", "MySQL"],
            "description": "Developed REST APIs for internal ERP system."
          }
        ],
        "education": [
          {
            "institution": "Ho Chi Minh City University of Technology",
            "degree": "bachelor",
            "degree_raw": "Bachelor of Engineering",
            "major": "Computer Science"
          }
        ],
        "projects": [
          {
            "name": "E-commerce Order Management",
            "tech_stack": ["ASP.NET Core", "PostgreSQL", "RabbitMQ"],
            "description": "Designed order processing pipeline handling 10k orders/day."
          }
        ],
        "certifications": ["AWS Certified Solutions Architect"],
        "languages": ["English (B2)", "Vietnamese"]
      },
      "cv_embedding": [0.021, -0.013, 0.067, ...],
      "error": null
    }
  ]
}
```

| Field | Type | Mô tả |
|---|---|---|
| `results[i].url` | string | URL của CV tương ứng |
| `results[i].cv_raw_text` | string\|null | Toàn bộ text extract từ file |
| `results[i].parsed_cv` | object\|null | CV đã parse thành cấu trúc — xem chi tiết bên dưới |
| `results[i].cv_embedding` | array\<float\>\|null | Dense vector ~1536 chiều |
| `results[i].error` | string\|null | Không null nếu CV đó bị lỗi (các CV khác không bị ảnh hưởng) |

**Chi tiết `parsed_cv`:**

| Field | Type | Mô tả |
|---|---|---|
| `name` | string | Tên ứng viên |
| `summary` | string | Đoạn tóm tắt profile |
| `skills` | array\<string\> | Danh sách kỹ năng |
| `work_experience[i].company` | string | Tên công ty |
| `work_experience[i].role` | string | Chức danh |
| `work_experience[i].start` | string | Ngày bắt đầu `YYYY-MM` |
| `work_experience[i].end` | string | Ngày kết thúc `YYYY-MM` hoặc `"present"` |
| `work_experience[i].months` | int | Số tháng làm việc (tính tự động) |
| `work_experience[i].is_current` | bool | `true` nếu đang làm |
| `work_experience[i].tech_stack` | array\<string\> | Stack công nghệ dùng tại vị trí đó |
| `work_experience[i].description` | string | Mô tả công việc |
| `education[i].institution` | string | Tên trường |
| `education[i].degree` | string\|null | Bằng cấp chuẩn hóa — xem [Enum](#enum-degreerevel) |
| `education[i].degree_raw` | string | Tên bằng cấp gốc trong CV |
| `education[i].major` | string | Chuyên ngành |
| `projects[i].name` | string | Tên dự án |
| `projects[i].tech_stack` | array\<string\> | Stack dùng trong dự án |
| `projects[i].description` | string | Mô tả dự án |
| `certifications` | array\<string\> | Danh sách chứng chỉ |
| `languages` | array\<string\> | Ngôn ngữ |

---

## POST /ai/score

Tính điểm match CV ↔ JD theo 5 chiều + đánh giá định tính.

**.NET gọi khi:** Ứng viên apply vào job (sau khi đã có parse data trong DB).  
**.NET lưu:** `final_score` → `FLOAT`, `scores` → `JSONB`, `evaluation` → `JSONB` vào bảng `applications`.

> **Quan trọng:** .NET tự đọc `parsed_cv`, `cv_embedding`, `parsed_jd`, `jd_embedding` từ DB rồi truyền vào — AI service không đọc DB.

### Request

`Content-Type: application/json`

```json
{
  "parsed_cv": { /* ParsedCV object đã lưu từ /parse-cv */ },
  "parsed_jd": { /* ParsedJD object đã lưu từ /parse-jd */ },
  "cv_embedding": [0.021, -0.013, 0.067, ...],
  "jd_embedding": [0.012, -0.034, 0.091, ...]
}
```

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| `parsed_cv` | ParsedCV | ✅ | Object lấy từ DB (JSONB) |
| `parsed_jd` | ParsedJD | ✅ | Object lấy từ DB (JSONB) |
| `cv_embedding` | array\<float\> | ✅ | Vector lấy từ DB |
| `jd_embedding` | array\<float\> | ✅ | Vector lấy từ DB |

### Response 200

```json
{
  "final_score": 78.5,
  "scores": {
    "semantic":   82.3,
    "skills":     75.0,
    "experience": 80.0,
    "education":  100.0,
    "keywords":   60.0
  },
  "evaluation": {
    "skill_details": [
      { "skill": ".NET",       "status": "matched",           "weight": 3 },
      { "skill": "Kubernetes", "status": "missing_must_have", "weight": 3 },
      { "skill": "Docker",     "status": "missing_preferred", "weight": 1 },
      { "skill": "Redis",      "status": "matched",           "weight": 2 }
    ],
    "missing_must_have":  ["Kubernetes"],
    "missing_preferred":  ["Docker"],
    "bonus_skills":       ["RabbitMQ"],
    "skill_match_rate":   0.75,
    "experience_verdict": "sufficient",
    "experience_detail":  "5.5 years vs required 5 years",
    "education_verdict":  "meets",
    "seniority_match":    "match",
    "seniority_detail":   "Current role Senior Backend Developer aligns with JD seniority level",
    "recommendation":     "possible_fit",
    "narrative":          "Ứng viên có nền tảng .NET vững chắc và kinh nghiệm phù hợp. Điểm trừ chính là thiếu Kubernetes — kỹ năng bắt buộc của vị trí..."
  }
}
```

| Field | Type | Mô tả |
|---|---|---|
| `final_score` | float 0–100 | Điểm tổng hợp |
| `scores.semantic` | float 0–100 | Độ tương đồng ngữ nghĩa (cosine similarity giữa 2 embedding) |
| `scores.skills` | float 0–100 | Điểm khớp kỹ năng (có tính weight) |
| `scores.experience` | float 0–100 | Điểm kinh nghiệm so với yêu cầu |
| `scores.education` | float 0–100 | Điểm bằng cấp so với yêu cầu |
| `scores.keywords` | float 0–100 | Điểm keyword overlap |
| `evaluation.skill_details` | array | Chi tiết từng kỹ năng — xem [Enum](#enum-skill-status) |
| `evaluation.missing_must_have` | array\<string\> | Kỹ năng must-have còn thiếu |
| `evaluation.missing_preferred` | array\<string\> | Kỹ năng preferred còn thiếu |
| `evaluation.bonus_skills` | array\<string\> | Kỹ năng ứng viên có nhưng JD không yêu cầu |
| `evaluation.skill_match_rate` | float 0–1 | Tỷ lệ kỹ năng khớp |
| `evaluation.experience_verdict` | string | Đánh giá kinh nghiệm — xem [Enum](#enum-experience-verdict) |
| `evaluation.experience_detail` | string | Mô tả chi tiết kinh nghiệm |
| `evaluation.education_verdict` | string | Đánh giá bằng cấp — xem [Enum](#enum-education-verdict) |
| `evaluation.seniority_match` | string | Đánh giá cấp độ — xem [Enum](#enum-seniority-match) |
| `evaluation.seniority_detail` | string | Mô tả chi tiết seniority |
| `evaluation.recommendation` | string | Kết luận tổng — xem [Enum](#enum-recommendation) |
| `evaluation.narrative` | string | Đoạn nhận xét dạng văn xuôi do LLM viết, HR đọc được |

---

## POST /ai/evaluate

Chỉ chạy đánh giá định tính — không tính điểm số, không cần embedding.  
Dùng khi cần refresh narrative/recommendation mà không tính lại score.

### Request

`Content-Type: application/json`

```json
{
  "parsed_cv": { /* ParsedCV object */ },
  "parsed_jd": { /* ParsedJD object */ }
}
```

### Response 200

Trả về đúng cấu trúc `evaluation` trong `/score` (không có `final_score` và `scores`):

```json
{
  "skill_details": [...],
  "missing_must_have": [...],
  "missing_preferred": [...],
  "bonus_skills": [...],
  "skill_match_rate": 0.75,
  "experience_verdict": "sufficient",
  "experience_detail": "...",
  "education_verdict": "meets",
  "seniority_match": "match",
  "seniority_detail": "...",
  "recommendation": "possible_fit",
  "narrative": "..."
}
```

---

## Enum Reference

### Enum: DegreeLevel

| Value | Ý nghĩa |
|---|---|
| `high_school` | Trung học phổ thông |
| `associate` | Cao đẳng |
| `bachelor` | Đại học |
| `master` | Thạc sĩ |
| `phd` | Tiến sĩ |
| `other` | Khác |
| `null` | Không yêu cầu / không xác định |

### Enum: Skill Status

| Value | Ý nghĩa |
|---|---|
| `matched` | Ứng viên có kỹ năng này |
| `missing_must_have` | Thiếu kỹ năng bắt buộc (weight=3) |
| `missing_preferred` | Thiếu kỹ năng ưu tiên (weight ≤ 2) |

### Enum: Experience Verdict

| Value | Ý nghĩa |
|---|---|
| `sufficient` | Đủ kinh nghiệm |
| `insufficient` | Chưa đủ kinh nghiệm |
| `over_qualified` | Kinh nghiệm vượt yêu cầu |
| `not_required` | JD không yêu cầu kinh nghiệm cụ thể |

### Enum: Education Verdict

| Value | Ý nghĩa |
|---|---|
| `exceeds` | Bằng cấp cao hơn yêu cầu |
| `meets` | Đáp ứng đúng yêu cầu |
| `below` | Bằng cấp thấp hơn yêu cầu |
| `not_required` | JD không yêu cầu bằng cấp cụ thể |

### Enum: Seniority Match

| Value | Ý nghĩa |
|---|---|
| `match` | Cấp độ phù hợp |
| `over_qualified` | Ứng viên senior hơn yêu cầu |
| `under_qualified` | Ứng viên junior hơn yêu cầu |
| `unknown` | Không xác định được |

### Enum: Recommendation

| Value | Ngưỡng | Ý nghĩa |
|---|---|---|
| `strong_fit` | skill_match ≥ 80%, đủ kinh nghiệm, không thiếu must-have | Ứng viên rất phù hợp |
| `possible_fit` | skill_match ≥ 60%, thiếu tối đa 1 must-have | Có thể phù hợp |
| `weak_fit` | skill_match 40–60%, hoặc thiếu 2 must-have | Phù hợp yếu |
| `poor_fit` | skill_match < 40%, hoặc thiếu > 2 must-have | Không phù hợp |

---

## Luồng tích hợp .NET + PostgreSQL

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. HR tạo JD                                                            │
│    .NET → POST /ai/parse-jd { jd_text }                                 │
│         ← { parsed_jd, jd_embedding }                                   │
│    .NET lưu DB: job_descriptions { parsed_jd JSONB, jd_embedding vector }│
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Ứng viên upload CV                                                   │
│    .NET upload file → S3 → lấy URL                                      │
│    .NET → POST /ai/parse-cv { cv_url }                                  │
│         ← { results[0]: { cv_raw_text, parsed_cv, cv_embedding } }      │
│    .NET lưu DB: candidates { cv_raw_text TEXT, parsed_cv JSONB,         │
│                              cv_embedding vector }                       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Ứng viên apply vào job                                               │
│    .NET đọc DB: parsed_cv, cv_embedding, parsed_jd, jd_embedding        │
│    .NET → POST /ai/score { parsed_cv, parsed_jd,                        │
│                            cv_embedding, jd_embedding }                  │
│         ← { final_score, scores, evaluation }                           │
│    .NET lưu DB: applications { final_score FLOAT, scores JSONB,         │
│                                evaluation JSONB }                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Gợi ý schema PostgreSQL

```sql
-- Bảng job descriptions
ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS parsed_jd    JSONB;
ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS jd_embedding vector(1536);

-- Bảng candidates / CVs
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS cv_raw_text   TEXT;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS parsed_cv     JSONB;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS cv_embedding  vector(1536);

-- Bảng applications (kết quả matching)
ALTER TABLE applications ADD COLUMN IF NOT EXISTS final_score  FLOAT;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS scores       JSONB;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS evaluation   JSONB;

-- Index vector search (nếu cần tìm CV tương tự JD)
CREATE INDEX IF NOT EXISTS idx_cv_embedding  ON candidates    USING ivfflat (cv_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_jd_embedding  ON job_descriptions USING ivfflat (jd_embedding vector_cosine_ops);
```

> Cần cài extension `pgvector` trước: `CREATE EXTENSION IF NOT EXISTS vector;`  
> Dimension `1536` tương ứng model embedding mặc định (`text-embedding-3-small`). Kiểm tra lại `AI_SERVICE_EMBED_MODEL` trong config nếu khác.

---

*Generated from source: `app/api/parse.py`, `app/api/score.py`, `app/api/evaluate.py`, `app/schemas.py`*
