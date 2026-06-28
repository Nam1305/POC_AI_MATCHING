# 🎯 Hệ Thống Matching CV-JD Bằng AI — Script Thuyết Trình

---

## 📋 MỤC LỤC

1. **Tổng Quan Kiến Trúc Toàn Hệ Thống** (5 phút)
2. **Pipeline 3 Giai Đoạn** (2 phút)
3. **Giai Đoạn 1: Tiền Xử Lý Dữ Liệu** (8 phút)
4. **Giai Đoạn 2: Dense Embeddings** (3 phút)
5. **Giai Đoạn 3: Scoring Đa Chiều** (12 phút)
6. **Những Hiểu Biết Chính & Kết Luận** (2 phút)

---

## 🏗️ PHẦN 1: TỔNG QUAN KIẾN TRÚC TOÀN HỆ THỐNG (5 phút)

### Đây là gì?

Chúng ta đang xây dựng một **Hệ Thống Matching CV-JD Bằng AI** tự động đánh giá mức độ phù hợp giữa CV của ứng viên và mô tả công việc.

**Mục tiêu:** Cho phép input CV và JD, output một điểm số khớp (0-100) với chi tiết breakdown.

### Tại sao lại quan trọng?

- **Cho HR/Recruiters:** Tự động screening ứng viên, tính nhất quán, tiết kiệm thời gian
- **Cho Ứng Viên:** Đánh giá công bằng, phản hồi chi tiết về vị trí của họ
- **Cho Công Ty:** Tuyển dụng dựa trên dữ liệu, giảm thiên vị, matching tốt hơn

### Kiến Trúc Cấp Cao

```
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI AI Service                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  INPUT: File CV (PDF/text) + text JD                            │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Giai Đoạn 1  │  │ Giai Đoạn 2  │  │ Giai Đoạn 3  │           │
│  │ PHÂN TÍCH    │→ │ EMBEDDING    │→ │ SCORING      │           │
│  │              │  │              │  │              │           │
│  │ Dùng LLM     │  │ Neural net   │  │ Toán học     │           │
│  │ trích xuất   │  │ (transformer)│  │ (không LLM)  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│         ↓                  ↓                  ↓                   │
│      Dữ liệu      Dense vectors       5 Chiều Điểm              │
│      JSON         (384-1536 dims)    + Điểm Cuối (0-100)       │
│      (có cấu trúc)                                               │
│                                                                   │
│  OUTPUT: Điểm số khớp với chi tiết breakdown                    │
│          (semantic, kỹ năng, kinh nghiệm, bằng cấp, từ khóa)   │
└─────────────────────────────────────────────────────────────────┘
```

### Những Quyết Định Thiết Kế Chính

1. **Ba giai đoạn riêng biệt** — mỗi cái có thể được tối ưu độc lập
2. **Không dùng LLM trong Giai Đoạn 3 (Scoring)** — toán học thuần Python để tốc độ & tính nhất quán
3. **Microservice stateless** — có thể scale ngang
4. **Tính linh hoạt về provider** — swap embedding hoặc LLM provider qua .env

---

## ⚙️ PHẦN 2: PIPELINE 3 GIAI ĐOẠN (2 phút)

### Tổng Quan Nhanh

| Giai Đoạn | Input | Quá Trình | Output | Chi Phí |
|-----------|-------|----------|--------|---------|
| **1: Phân Tích** | Raw CV/JD text | LLM trích xuất dữ liệu có cấu trúc | JSON (kỹ năng, kinh nghiệm, bằng cấp, từ khóa) | 💰 Chi phí LLM |
| **2: Embedding** | Text đã được phân tích | Neural net vector hóa | Dense vectors (384-1536 dims) | 💰 Chi phí Embed API |
| **3: Scoring** | CV + JD embeddings + dữ liệu phân tích | Toán học & heuristics | 5 chiều điểm + điểm match cuối (0-100) | ✅ Free (local) |

### Tại Sao Kiến Trúc Này?

- **Separation of concerns** — ranh giới rõ ràng giữa LLM, embedding, và scoring
- **Hiệu quả chi phí** — công việc LLM tốn kém xảy ra một lần, scoring rẻ
- **Dễ test** — mỗi giai đoạn có input/output rõ ràng
- **Linh hoạt** — có thể swap provider mà không cần viết lại logic

---

## 🔍 PHẦN 3: GIAI ĐOẠN 1 — TIỀN XỬ LÝ DỮ LIỆU (8 phút)

### Tiền Xử Lý Là Gì?

Raw CV/JD text là **không có cấu trúc** và **lộn xộn**. Chúng ta cần chuyển nó thành **structured JSON** sạch cho processing sau.

**Ví Dụ:**
```
Raw CV (lộn xộn):
"Senior Full-Stack Developer tại TechCorp (2020-2023)
Dẫn dắt phát triển microservices dùng Node.js, React, PostgreSQL.
Thành tích chính: giảm latency API 40%, hướng dẫn 5 dev junior.
Kỹ năng: JavaScript, TypeScript, React, Node.js, Docker, AWS..."

↓ PHÂN TÍCH ↓

Structured JSON:
{
  "work_experience": [{
    "company": "TechCorp",
    "role": "Senior Full-Stack Developer",
    "start": "2020-01",
    "end": "2023-01",
    "months": 36,
    "tech_stack": ["nodejs", "react", "postgresql", "docker", "aws"],
    "description": "Dẫn dắt phát triển microservices... giảm latency 40%..."
  }],
  "skills": ["javascript", "typescript", "react", "nodejs", ...],
  "education": [{
    "institution": "Tech University",
    "degree": "bachelor",
    "major": "Computer Science"
  }]
}
```

### Phân Tích Hoạt Động Như Thế Nào?

**Bước 1: Trích Xuất CV/JD Text**

```
POST /ai/parse-cv
{
  "cv_file": <PDF hoặc text file>,
}

POST /ai/parse-jd
{
  "jd_text": "Senior Developer tại Company X..."
}
```

**Bước 2: Gửi Cho LLM (Claude hoặc Llama)**

Chúng ta dùng **structured prompts** với JSON output format rõ ràng. Prompt nói cho LLM:
- Cái gì cần trích xuất (kỹ năng, kinh nghiệm, bằng cấp, dự án, v.v.)
- Định dạng gì (JSON schema)
- Trường hợp đặc biệt (nếu không có bằng cấp? nếu ngày thiếu?)

**Ví Dụ Cấu Trúc Prompt:**
```
"Trích xuất thông tin từ text CV dưới đây.
Trả về CHỈ valid JSON. Không có giải thích, không có markdown.

Cấu trúc JSON:
{
  "name": "...",
  "skills": ["kỹ năng1", "kỹ năng2", ...],
  "work_experience": [
    {
      "company": "...",
      "role": "...",
      "start": "YYYY-MM",
      "end": "YYYY-MM hoặc present",
      "tech_stack": [...],
      "description": "..."
    }
  ],
  "education": [
    {
      "institution": "...",
      "degree": "high_school | associate | bachelor | master | phd | other",
      "major": "..."
    }
  ],
  ...
}"
```

**Bước 3: Xác Thực Dữ Liệu & Auto-Retry**

Sau khi LLM trả về JSON, chúng ta xác thực:
- ✅ Tất cả field bắt buộc có không?
- ✅ Kiểu dữ liệu đúng không?
- ✅ Các field quan trọng (work_experience, skills) không trống không?

Nếu xác thực thất bại, chúng ta **auto-retry với focused prompts**:
```
Ví dụ: Nếu work_experience thiếu, retry với:
"Tập trung CHỈ vào mục lịch sử việc làm.
Trích xuất TẤT CẢ công việc: full-time, part-time, internships, freelance."
```

**Tại Sao Auto-Retry?** Vì đôi khi lần phân tích đầu tiên bỏ sót thông tin quan trọng, nhưng retry focused thường thành công.

**Bước 4: Tính Toán Ngày Tháng**

Sau khi có dữ liệu có cấu trúc, chúng ta tính **tháng kinh nghiệm** cục bộ (không hỏi LLM):

```python
def _diff_months(start: "2020-06", end: "2023-03") → int:
    return (2023 - 2020) * 12 + (3 - 6) = 33 tháng
```

Tại Sao? **Độ chính xác** — ngày là deterministic, không cần hỏi LLM.

**Bước 5: Chuẩn Hóa Bằng Cấp**

Map các string bằng cấp tùy ý thành canonical enum:

```
"Bachelor of Software Engineering" → DegreeLevel.BACHELOR (numeric: 3)
"Master of Business Admin" → DegreeLevel.MASTER (numeric: 4)
"High School Diploma" → DegreeLevel.HIGH_SCHOOL (numeric: 1)
```

Mapping numeric này rất quan trọng cho **scoring** sau.

### Cái Gì Được Trích Xuất?

**Cấu Trúc CV:**
```json
{
  "name": "John Doe",
  "summary": "Tóm tắt chuyên nghiệp...",
  "skills": ["Python", "React", "PostgreSQL", ...],
  "work_experience": [
    {
      "company": "Company A",
      "role": "Senior Developer",
      "start": "2022-01",
      "end": "present",
      "is_current": true,
      "months": 24,
      "tech_stack": ["Python", "Django", "PostgreSQL"],
      "description": "Trách nhiệm chính và thành tích..."
    },
    ...
  ],
  "education": [
    {
      "institution": "University of X",
      "degree": "bachelor",
      "degree_raw": "B.Sc. in Computer Science",
      "major": "Computer Science"
    }
  ],
  "projects": [
    {
      "name": "Tên Dự Án",
      "tech_stack": ["Tech1", "Tech2"],
      "description": "Dự án làm gì..."
    }
  ],
  "certifications": ["AWS Solutions Architect", ...],
  "languages": ["English - Fluent", "Vietnamese - Native"]
}
```

**Cấu Trúc JD:**
```json
{
  "title": "Senior Full-Stack Engineer",
  "description": "Mô tả công việc...",
  "min_experience_years": 5,
  "required_skills": [
    {"skill": "Python", "weight": 3},
    {"skill": "React", "weight": 3},
    {"skill": "PostgreSQL", "weight": 2},
    {"skill": "Docker", "weight": 1}
  ],
  "required_degree_level": 3,  // Bachelor
  "keywords": ["agile", "CI/CD", "microservices"],
  "seniority": "senior"
}
```

### Những Thách Thức Chính & Giải Pháp

| Thách Thức | Giải Pháp |
|-----------|----------|
| **LLM hallucination** | Focused auto-retry, validation checks |
| **Ngày thiếu** | Dùng empty string, fallback sang year-only |
| **Tên kỹ năng mơ hồ** | Normalize qua alias map (xử lý ở giai đoạn Scoring) |
| **Đa ngôn ngữ** | Claude xử lý tốt out-of-box |
| **PDF parsing** | Pre-convert thành text trước khi gửi cho LLM |

---

## 💡 PHẦN 4: GIAI ĐOẠN 2 — DENSE EMBEDDINGS (3 phút)

### Embedding Là Gì?

Một **dense vector** (danh sách 300-1500 số) đại diện cho ý nghĩa semantic của text.

```
Text: "Senior Python Developer với 5 năm kinh nghiệm"
                        ↓ Embedding ↓
Vector: [-0.123, 0.456, 0.789, -0.234, 0.567, ...]  (384-1536 chiều)
```

**Tại Sao Dense Vectors?**
- Bắt được các mối quan hệ semantic (text tương tự → vectors tương tự)
- Cho phép so sánh **cosine similarity** (hai text tương tự bao nhiêu?)
- Hoạt động với transformer models

### Embeddings Hoạt Động Thế Nào Trong Hệ Thống?

**Bước 1: Chuẩn Bị Text**
```python
cv_text = "Senior Python Developer... Docker, Kubernetes, PostgreSQL...
           5 năm kinh nghiệm tại TechCorp..."

jd_text = "Chúng tôi tuyển dụng Senior Backend Engineer với Python và cloud experience..."
```

**Bước 2: Gửi Cho Embedding Provider**

Ba lựa chọn (qua `.env EMBED_PROVIDER`):

| Provider | Model | Chiều | Chi Phí | Tốc Độ |
|----------|-------|-------|---------|--------|
| **sentence_transformer** | all-MiniLM-L6-v2 | 384 | Free ✅ | Nhanh (local) |
| **openai** | text-embedding-3-small | 1536 | Có Phí | API call |
| **gemini** | gemini-embedding-001 | 3072 | Có Phí | API call |

Chúng ta mặc định dùng **sentence_transformer** vì nó free và chạy cục bộ.

**Bước 3: Lấy Dense Vectors**
```python
cv_embedding = [0.12, -0.45, 0.78, ...]  # 384 số
jd_embedding = [0.11, -0.46, 0.80, ...]  # 384 số
```

**Bước 4: Tính Độ Tương Tự**

```python
similarity = cosine_similarity(cv_embedding, jd_embedding)
# Kết quả: 0.82 (range -1 to 1, thường 0-1 cho text)
```

Cái này trở thành **D1: Semantic Score** sau này.

### Tại Sao Embeddings Quan Trọng?

- **Hiểu ý nghĩa semantic** — bắt được ý nghĩa ngoài exact keyword match
- **Linh hoạt** — xử lý paraphrasing, synonyms
- **Định lượng được** — cho phép scoring

---

## 🎯 PHẦN 5: GIAI ĐOẠN 3 — SCORING ĐA CHIỀU (12 phút)

### Vấn Đề

Làm cách nào để so sánh CV và JD **công bằng**?

- ❌ Chỉ semantic similarity (embedding alone) → bỏ sót yêu cầu cụ thể
- ❌ Chỉ keyword matching → dễ vỡ, không context
- ❌ Một số scoring → không rõ ràng

**Giải Pháp:** **Hệ Thống Scoring 5 Chiều**

### 5 Chiều Scoring

Mỗi chiều đánh giá một **khía cạnh khác nhau** của CV-JD match:

```
Điểm Cuối = (D1×0.25 + D2×0.30 + D3×0.20 + D4×0.10 + D5×0.05) × 100
            ─────────────────────────────────────────────────────────
                          Weights mặc định (có thể điều chỉnh)
```

---

### **D1: Semantic Similarity** (25% weight)

**Cái Gì:** CV và JD tương tự semantic bao nhiêu?

**Cách:**
```python
cosine_similarity = cosine(cv_embedding, jd_embedding)
# Kết quả: 0.55–0.90 range cho matching liên quan

normalized = (raw - 0.55) / (0.90 - 0.55)
# Stretch [0.55, 0.90] → [0, 1]
# Dưới 0.55 → các field không liên quan
# Trên 0.90 → cùng tech stack
```

**Ví Dụ:**
- CV: "Senior Python Developer, 5 năm, microservices, Docker, AWS"
- JD: "Python Backend Engineer, cloud-native experience, Docker"
- Similarity: 0.85 → **D1 = 100**

---

### **D2: Skills Matching** (30% weight) ⭐ Quan Trọng Nhất

**Cái Gì:** Kỹ năng của ứng viên khớp với yêu cầu JD bao nhiêu?

**Tại Sao 30%?** Vì kỹ năng là chỉ báo trực tiếp nhất của khả năng.

**Cách (3-tier matching):**

**Tier 1: Exact Match**
```
Kỹ năng CV: "Python" (normalized)
Kỹ năng JD: "Python" (normalized)
→ Full weight (1.0)
```

**Tier 2: Fuzzy Match** (xử lý typos & variants)
```
Kỹ năng CV: "Reactjs" 
Kỹ năng JD: "React"
Similarity: 92% > 85% threshold
→ 90% weight (0.9)
```

**Tier 3: Category Match** (partial credit cho kỹ năng liên quan)
```
JD yêu cầu: "Angular"
CV có: "React", "Vue" (cả hai frontend)
Cùng category (frontend) với 2 overlaps
→ 40% weight (0.3–0.5 scale)
```

**Ví Dụ Tính Toán:**
```
Kỹ năng yêu cầu JD:
├─ Python (weight: 3) — PHẢI CÓ
├─ Django (weight: 2)
└─ Docker (weight: 1)
Total weight: 6

Kỹ năng CV: Python ✅, Flask (không phải Django, nhưng category backend), Docker ✅

Matched weight:
├─ Python: 3 (exact match)
├─ Django: 2 × 0.4 = 0.8 (category match — Flask cũng là backend)
└─ Docker: 1 (exact match)
Total matched: 3 + 0.8 + 1 = 4.8

D2 = 4.8 / 6 = 0.80 (80%)
```

**Skill Aliases (xử lý ecosystem variants):**
- "JS" ↔ "JavaScript" ↔ "ES6" → tất cả normalize thành "javascript"
- "K8s" ↔ "kubernetes" → "kubernetes"
- "Postgres" ↔ "PostgreSQL" → "postgresql"
- "ts" ↔ "TypeScript" → "typescript"

**Categories (cho partial credit):**
- **Frontend:** React, Vue, Angular, JavaScript, TypeScript, HTML, CSS, Tailwind
- **Backend:** Django, Flask, FastAPI, Spring, Express, NestJS, ASP.NET
- **Database:** MySQL, PostgreSQL, MongoDB, Redis, Elasticsearch
- **Cloud:** AWS, GCP, Azure
- **DevOps:** Docker, Kubernetes, CI/CD, Jenkins, Terraform
- **ML:** TensorFlow, PyTorch, Keras, Scikit-learn

---

### **D3: Experience Relevance** (20% weight)

**Cái Gì:** Ứng viên có đủ kinh nghiệm liên quan không?

**Cách:**

**Base Score:**
```python
base = min(cv_total_years / jd_required_years, 1.0)

Ví Dụ:
CV: 5 năm kinh nghiệm
JD: "3+ năm yêu cầu"
base = min(5/3, 1.0) = 1.0
```

**Sau Đó Áp Dụng Modifiers:**

| Modifier | Tác Dụng | Ví Dụ |
|----------|----------|--------|
| **Domain Relevance** | +0.20 nếu lịch sử công việc overlap keywords JD | CV có kinh nghiệm "microservices", JD nhắc "microservices" → +0.20 |
| **Recency** | +0.10 nếu job cuối cùng < 3 tháng ago (hiện tại) | Job cuối vẫn đang làm → +0.10 |
| **Employment Gap** | -0.10 nếu job cuối > 12 tháng ago (gap dài) | Job cuối cách đây: 18 tháng → -0.10 |
| **Over-qualification** | -0.05 nếu cv_years > 2 × jd_required | CV: 8 năm, JD: 3 năm → -0.05 |

**Ví Dụ Tính Toán:**
```
CV: 6 năm tổng, job cuối hiện tại, domain overlap tồn tại
JD: "5+ năm yêu cầu"

base = min(6/5, 1.0) = 1.0
modifiers:
  + domain relevance: +0.20
  + current job: +0.10
  − over-qualification: −0.05
                        ─────
  tổng modifiers: +0.25

D3 = clamp(1.0 + 0.25, 0, 1.0) = 1.0 (capped at 1.0)
```

---

### **D4: Education Match** (10% weight)

**Cái Gì:** Bằng cấp của ứng viên có đáp ứng yêu cầu không?

**Cách (chiều đơn giản nhất):**
```python
D4 = min(cv_degree_level / jd_required_degree_level, 1.0)
```

**Degree Level Mapping:**
| Mức | Giá Trị | Ví Dụ |
|-----|--------|--------|
| **High School** | 1 | Bằng Cấp 3 |
| **Associate** | 2 | Associate Degree |
| **Bachelor** | 3 | B.Sc., B.A., Bachelor |
| **Master** | 4 | M.Sc., MBA, Master |
| **PhD** | 5 | PhD, Tiến Sĩ |

**Ví Dụ:**
```
CV: Bachelor (3), JD yêu cầu: Bachelor (3)
D4 = 3/3 = 1.0 ✅

CV: Master (4), JD yêu cầu: Bachelor (3)
D4 = 4/3 = 1.33 → capped at 1.0 ✅ (over-qualified là OK)

CV: High School (1), JD yêu cầu: Master (4)
D4 = 1/4 = 0.25 ❌ (under-qualified)
```

---

### **D5: Keywords & Specific Requirements** (5% weight)

**Cái Gì:** Các từ khóa/yêu cầu cụ thể có được nhắc đến trong CV không?

**Cách (3-level matching):**

**Level 1: Exact Substring Match**
```
Từ khóa JD: "CI/CD"
Text CV: "...implemented CI/CD pipelines using Jenkins..."
Match found → Score: 1.0
```

**Level 2: Word-Boundary Match**
```
Từ khóa JD: "agile"
Text CV: "...following agile methodology and scrum practices..."
Word "agile" found → Score: 1.0
```

**Level 3: Multi-word Phrase (tất cả subwords có)**
```
Từ khóa JD: "microservices architecture"
Text CV: "...worked on microservices... AWS architecture design..."
Cả "microservices" và "architecture" có → Score: 0.7 (partial credit)
```

**Final Score:**
```
D5 = trung bình của tất cả keyword scores

Ví Dụ:
Keywords: ["CI/CD", "Docker", "Kubernetes", "Agile"]
CV matches:
├─ CI/CD: found (1.0)
├─ Docker: found (1.0)
├─ Kubernetes: NOT found (0.0)
└─ Agile: found (1.0)

D5 = (1 + 1 + 0 + 1) / 4 = 0.75 (75%)
```

---

### **Ghép Tất Cả Lại**

**Ví Dụ Final Scoring:**

```
Ứng Viên: "John Doe"
CV Analysis:
├─ D1 (Semantic):    0.85 (vectors tương tự)
├─ D2 (Skills):      0.80 (80% skill overlap)
├─ D3 (Experience):  1.00 (5+ năm, đang làm, liên quan)
├─ D4 (Education):   1.00 (Bachelor, yêu cầu Bachelor)
└─ D5 (Keywords):    0.75 (75% keywords có)

Weights (mặc định):
├─ semantic:   0.25
├─ skills:     0.30
├─ experience: 0.20
├─ education:  0.10
└─ keywords:   0.05

Tính Toán:
final = (0.85×0.25 + 0.80×0.30 + 1.00×0.20 + 1.00×0.10 + 0.75×0.05) × 100
      = (0.2125 + 0.240 + 0.200 + 0.100 + 0.0375) × 100
      = 0.79 × 100
      = 79.0 / 100
```

**Output:**
```json
{
  "final_score": 79.0,
  "scores": {
    "semantic":   85.0,
    "skills":     80.0,
    "experience": 100.0,
    "education":  100.0,
    "keywords":   75.0
  }
}
```

### Business Rules (Hard Constraints)

Chúng ta cũng áp dụng **penalties** cho deal-breakers:

```python
if enforce_must_have:
    # Missing critical skills (weight ≥ 3)
    for each missing must-have skill:
        penalty += 0.20 (tối đa -0.70)
    
    # Insufficient experience
    if cv_years < 0.8 × jd_required_years:
        penalty += 0.30

final_score *= (1 - penalty)
```

**Tại Sao?** Vì bỏ sót một kỹ năng quan trọng không chỉ nên giảm score — nó nên là một red flag mạnh mẽ.

---

## 🎓 PHẦN 6: NHỮNG HIỂU BIẾT CHÍNH & KẾT LUẬN (2 phút)

### Cái Gì Làm Hệ Thống Này Hiệu Quả?

1. **Đa chiều** — không dựa vào single metric
2. **Rõ ràng** — mỗi chiều là explainable
3. **Có thể điều chỉnh** — weights có thể được điều chỉnh theo client need
4. **Nhanh & Rẻ** — không có LLM ở giai đoạn scoring
5. **Mở rộng được** — có thể thêm chiều (culture fit, location, v.v.)

### Tại Sao Không Dùng Một Con Số?

```
❌ Tệ: "Điểm khớp của bạn là 75%"
   → Nó đến từ đâu? Không có insight.

✅ Tốt: 
   "Điểm Khớp: 75%
    ├─ Semantic fit: 85% ✅ (aligned mạnh)
    ├─ Skills: 80% ✅ (good overlap)
    ├─ Experience: 100% ✅ (meets requirement)
    ├─ Education: 100% ✅ (exceeds requirement)
    └─ Keywords: 75% ⚠️  (missing some specifics)"
```

Tính rõ ràng này xây dựng trust với recruiters và ứng viên.

### Tuning Real-World

Các industry khác nhau có nhu cầu khác:

**Các vị trí Data Science:**
- Tăng `education` weight (advanced degree common)
- Tăng `keywords` weight (specific tools matter)

**Startup positions:**
- Giảm `education` weight (experience over credentials)
- Tăng `semantic` weight (culture & innovation mindset)

**Enterprise roles:**
- Tăng `experience` weight (stability & proven track record)
- Tăng `education` weight (formal credentials valued)

---

## 🚀 NHỮNG ĐIỂM RÚT RA

1. **AI ≠ chỉ LLM** — Hệ thống của chúng ta dùng LLM cho parsing, neural nets cho embedding, và toán học thuần cho scoring. Công cụ khác nhau cho công việc khác nhau.

2. **Tiền xử lý dữ liệu là critical** — Dành công sức để có dữ liệu sạch, có cấu trúc từ đầu giúp ích rất nhiều cho chất lượng scoring.

3. **Explainability quan trọng** — Scoring đa chiều tốt hơn black box, ngay cả khi black box có thể hơi "chính xác" hơn.

4. **Linh hoạt là giá trị** — Bằng cách tách các giai đoạn, chúng ta có thể swap components, điều chỉnh weights, thêm chiều mới mà không cần viết lại mọi cái.

5. **Transparent scoring = better outcomes** — Ứng viên hiểu cần cải thiện gì; recruiters có thể đặt kỳ vọng rõ ràng.

---

## ❓ ĐIỂM THẢO LUẬN Q&A

**Q: Tại Sao Không Dùng LLM Để Score?**
A: LLM tốn kém, non-deterministic, khó debug. Toán học nhanh, predictable, và rõ ràng.

**Q: Nếu CV Không Có Bằng Cấp?**
A: D4 mặc định là 0.5, không penalize nặng. Các chiều khác có thể bù đắp. Điểm cuối phụ thuộc vào các yếu tố khác.

**Q: Có Thể Custom Weights Per Client Không?**
A: Có! Mỗi client có thể có config weight riêng. AdaptiveWeights class thậm chí còn suggest weights dựa trên JD characteristics.

**Q: Xử Lý Evolving Tech Stack Thế Nào?**
A: Skill aliases dễ update. Nếu "WebAssembly" trở nên quan trọng, chỉ cần thêm vào ALIASES dict. Không cần retraining.

**Q: Nếu Ứng Viên Không Kỹ Thuật?**
A: Hệ thống vẫn hoạt động — chỉ ít technical skills hơn. Các chiều education & experience sẽ carry more weight.

---

## 📊 DEMO / WALKTHROUGH

**Show live API call:**

```bash
POST /ai/score
{
  "parsed_cv": { ... },
  "parsed_jd": { ... },
  "cv_embedding": [0.12, -0.45, ...],
  "jd_embedding": [0.11, -0.46, ...]
}

Response:
{
  "final_score": 79.0,
  "scores": {
    "semantic": 85.0,
    "skills": 80.0,
    "experience": 100.0,
    "education": 100.0,
    "keywords": 75.0
  }
}
```

**Hoặc show screenshots:**
- CV parsing result (JSON structure)
- Embedding vectors (visual similarity chart)
- Score breakdown (bar chart của 5 chiều)

---

## 📚 APPENDIX: TECHNICAL REFERENCES

**Key Files:**
- [scorer.py](MVP_AI_Matching/app/services/scorer.py) — Tất cả 5 chiều + scoring logic
- [parser.py](MVP_AI_Matching/app/services/parser.py) — LLM extraction
- [embedder.py](MVP_AI_Matching/app/services/embedder.py) — Embedding providers
- [schemas.py](MVP_AI_Matching/app/schemas.py) — Data models

**API Endpoints:**
- `POST /ai/parse-cv` — Phân tích CV file
- `POST /ai/parse-jd` — Phân tích JD text
- `POST /ai/score` — Score CV vs JD

**Configuration (.env):**
```
LLM_PROVIDER=claude|groq
EMBED_PROVIDER=sentence_transformer|openai|gemini
OPENAI_API_KEY=...
GEMINI_API_KEY=...
```

---

**HẾT SCRIPT THUYẾT TRÌNH**

