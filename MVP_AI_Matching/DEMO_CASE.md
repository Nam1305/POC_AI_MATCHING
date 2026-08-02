# DEMO CASE — Kịch bản demo cho từng Dimension (D1–D5)

> Mọi con số trong file này đã được **chạy thật và xác nhận** bằng code hiện tại
> của repo (không suy đoán) — xem log kiểm chứng ở cuối mỗi case nếu cần đối
> chiếu lại. Dùng kèm [PRESENTATION.md](PRESENTATION.md) — file đó giải thích
> *vì sao*, file này chứng minh *đúng là vậy* bằng ví dụ chạy được.

---

## 0. Nguyên tắc chuẩn bị dữ liệu — đọc trước khi làm bất kỳ case nào

Có **2 cách** đưa dữ liệu vào hệ thống để demo, chọn đúng cách theo mục đích:

### Cách A — Qua pipeline đầy đủ (`/ai/parse-cv` + `/ai/parse-jd` + `/ai/score`)

Dùng khi: muốn chứng minh **cả pipeline** hoạt động (kể cả LLM trích xuất, OCR,
geocode). Nhược điểm: **không tất định** — LLM có thể trích xuất hơi khác nhau
giữa 2 lần chạy (dù `temperature=0`), nên số điểm chính xác có thể lệch vài
điểm giữa lần chuẩn bị và lần demo thật.

**Dùng cho:** case D1 (bắt buộc — cosine cần embedding thật từ model, không
thể giả lập có ý nghĩa) và 1 case end-to-end minh họa toàn luồng.

### Cách B — Gọi thẳng `/ai/score` với JSON đã viết tay (KHUYẾN NGHỊ cho D2–D5)

`/ai/score` nhận `parsed_cv` + `parsed_jd` là JSON thuần theo đúng schema
([app/schemas.py](app/schemas.py)) — **không bắt buộc phải đi qua LLM**. Vì
D2/D3/D4/D5 hoàn toàn là Python tất định (không phụ thuộc LLM), viết tay JSON
đầu vào cho ra **kết quả giống hệt nhau 100% mỗi lần chạy** — an toàn tuyệt đối
cho buổi bảo vệ (không lo mạng lag, không lo LLM trả khác đi phút chót).

`cv_embedding`/`jd_embedding` có thể **bỏ trống** khi demo case không liên quan
đến D1 — hệ thống tự trả `D1 = 0.5` (trung lập) và không ảnh hưởng D2–D5.

```bash
curl -s -X POST http://localhost:8000/ai/score \
  -H "Content-Type: application/json" \
  -d @case_payload.json | python3 -m json.tool
```

**Dùng cho:** tất cả case D2, D3, D4, D5 bên dưới — mỗi case có sẵn JSON mẫu,
chỉ cần copy vào file `.json` rồi `curl`.

### Cách C — Gọi thẳng vào code Python (KHUYẾN NGHỊ RIÊNG cho demo D2 theo layer)

Vì API **không** trả về `matched_layer`/`matched_via` (đây là dữ liệu nội bộ,
xem [skill_matcher.py:262](app/services/skill_matcher.py#L262) — `Match` có
field `layer`/`via` nhưng `CVJobEvaluation.SkillMatchDetail` trong
[schemas.py:203](app/schemas.py#L203) chỉ expose `skill`/`status`/`weight`,
không có `matched_layer`). Muốn **chỉ tận nơi** JD skill nào khớp qua tầng nào,
cách rõ ràng nhất là gọi thẳng `SkillMatcher` bằng vài dòng Python — không qua
HTTP, không qua LLM, chạy trong &lt;1 giây, tuyệt đối tất định. Xem case D2 bên dưới.

> **Việc cần làm trước buổi bảo vệ:** chạy thử mỗi case ít nhất 1 lần, lưu lại
> output thật (chụp màn hình hoặc copy JSON) làm phương án dự phòng nếu demo
> trực tiếp gặp sự cố mạng.

---

## 1. D1 — Semantic (ngữ nghĩa)

**Mục tiêu chứng minh:** D1 đo *mức độ gần về câu chuyện nghề nghiệp/vai trò*,
không đo kỹ năng cụ thể (đó là việc của D2) — và mức độ gần giảm dần đúng theo
trực giác con người khi domain nghề nghiệp càng xa nhau.

### Bảng case

| # | Case | JD | CV | Kỳ vọng | Ghi chú |
| --- | --- | --- | --- | --- | --- |
| D1-1 | CV cùng domain, đúng vai trò | ".NET Backend Developer" | Backend Developer, 3 năm kinh nghiệm .NET/C#/SQL Server, mô tả công việc: xây dựng REST API, microservices | **D1 cao nhất** trong 3 case (kỳ vọng > 70) |
| D1-2 | CV khác domain nhưng cùng ngành phần mềm | ".NET Backend Developer" | Frontend Developer, 3 năm kinh nghiệm React/CSS, mô tả: xây dựng giao diện người dùng, tối ưu UX | **D1 trung bình** (thấp hơn D1-1, cao hơn D1-3) |
| D1-3 | CV hoàn toàn khác ngành | ".NET Backend Developer" | Giáo viên Toán THPT, mô tả: giảng dạy, soạn giáo án, quản lý lớp học | **D1 thấp nhất** trong 3 case |
| D1-4 | ⚠️ Tài liệu ngẫu nhiên, không phải CV | JD bất kỳ | Một bài báo khoa học / hợp đồng / công thức nấu ăn (không phải CV) | D1 **vẫn ra một số khác 0 đáng kể** (ví dụ ~0.4–0.6) — đây là hiện tượng **anisotropy**, không phải lỗi. Dùng để chứng minh vì sao cần cơ chế `COSINE_MIN/MAX` và vì sao không thể để D1 một mình quyết định |
| D1-5 | Thiếu embedding | bất kỳ | bất kỳ | Gọi `/ai/score` **không kèm** `cv_embedding`/`jd_embedding` → `scores.semantic = 50.0` (giá trị trung lập cứng, không phải tính toán) |

### Hướng dẫn chuẩn bị

1. Viết 3 file text CV (D1-1, D1-2, D1-3) — **cố ý giữ số năm kinh nghiệm và
   trình độ học vấn giống hệt nhau** giữa 3 CV (ví dụ đều 3 năm, đều cử nhân) để
   D3/D4 không gây nhiễu khi so sánh riêng D1. Có thể **cố ý không liệt kê
   skills** hoặc liệt kê skills giống nhau ở cả 3 CV, để chênh lệch điểm final
   score chủ yếu đến từ D1 (không lo D2 làm nhiễu kết luận).
2. Chạy qua **Cách A** (pipeline đầy đủ): `POST /ai/parse-jd` 1 lần lấy
   `jd_embedding`, rồi `POST /ai/parse-cv` cho từng CV lấy `cv_embedding`, rồi
   `POST /ai/score` cho từng cặp — so `scores.semantic`.
3. Case D1-4: lấy bất kỳ file PDF nào không phải CV (báo cáo, bài báo...), đưa
   qua `/ai/parse-cv` — hệ thống vẫn cố trích xuất và vẫn ra 1 embedding. Đây
   chính là demo bạn đã tự phát hiện được trong quá trình test thật.

### Câu nói khi trình bày

> "Ba CV này có cùng số năm kinh nghiệm, cùng bằng cấp, thậm chí liệt kê cùng bộ
> kỹ năng — điểm khác nhau **duy nhất** là câu chuyện nghề nghiệp trong phần mô
> tả. D1 giảm dần đúng theo mức độ gần domain — đây là bằng chứng D1 đang đo
> đúng thứ nó được thiết kế để đo: sự phù hợp về vai trò, không phải kỹ năng."

---

## 2. D2 — Skills (kỹ năng) — demo theo từng layer

**Mục tiêu chứng minh:** thác 4 tầng + tầng phụ hoạt động đúng, dừng ở đúng
tầng sớm nhất, và phân biệt được các loại "khớp" khác nhau.

### 2.1 Demo theo từng layer — chạy thẳng Python, không qua HTTP (Cách C)

**Dữ liệu CV dùng chung cho cả 6 case** (mỗi kỹ năng cố ý chỉ trúng đúng 1 tầng,
không lẫn lộn): `skills=["Docker", "Node.js", "React", "Kubernetees"]`,
`languages=["Japanese - JLPT N2"]`.

### Bảng case — theo từng layer

| # | Layer | JD đòi hỏi | CV có gì (liên quan) | Vì sao khớp ở đúng tầng này | `status` kỳ vọng | `layer` kỳ vọng | `via` kỳ vọng |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D2-L0 | **Layer 0** — Direct | `Docker` | `Docker` | Hai chuỗi giống hệt nhau sau lowercase — không cần canonical hóa | `matched` | `layer0` | `docker` |
| D2-L1 | **Layer 1** — Identity | `NodeJS` | `Node.js` | Khác chuỗi thô nhưng cùng quy về 1 tên chuẩn qua `skill_data.json` | `matched` | `layer1` | `node.js` |
| D2-L2 | **Layer 2** — Entailment | `JavaScript` | *(không ghi trực tiếp)* | CV có `React`/`Node.js`, cả hai đều suy ra biết JavaScript qua `skill_implies.json` | `matched_implied` | `layer2` | `node.js` (hoặc `react` nếu tách riêng, xem lưu ý bên dưới) |
| D2-L3 | **Layer 3** — Fuzzy | `Kubernetes` | `Kubernetees` (lỗi chính tả cố ý) | 3 tầng chính xác đều trượt, `SequenceMatcher` cho ratio ≥ 0.85 | `matched` | `layer3` | `kubernetees` |
| D2-P | **Proficiency** (tầng phụ) | `JLPT N3` | `Japanese - JLPT N2` | N2 cao hơn N3 trong cùng framework JLPT — so theo thứ bậc, không so chuỗi | `matched` | `proficiency` | `jlpt n2` |
| D2-M | **Missing** | `Rust` | *(không có gì liên quan)* | Không tầng nào thỏa | `missing` | `missing` | `` (rỗng) |

Lưu thành file `demo_d2_layers.py` ở thư mục gốc repo rồi chạy
`.venv/bin/python demo_d2_layers.py` để chứng minh trực tiếp bảng trên:

```python
from app.schemas import ParsedCV
from app.services.skill_matcher import SkillMatcher

# CV cố ý dựng để mỗi kỹ năng chỉ trúng đúng 1 tầng, không lẫn lộn
cv = ParsedCV(
    skills=["Docker", "Node.js", "React", "Kubernetees"],  # "Kubernetees" = lỗi chính tả cố ý
    languages=["Japanese - JLPT N2"],
)
matcher = SkillMatcher()
ctx = matcher.build_cv_context(cv)

cases = [
    ("Docker",     "Layer 0 — direct match (CV và JD viết giống hệt nhau)"),
    ("NodeJS",     "Layer 1 — canonical hóa: CV ghi 'Node.js', JD ghi 'NodeJS', khác chuỗi nhưng cùng 1 tag chuẩn"),
    ("JavaScript", "Layer 2 — entailment: CV không hề ghi 'JavaScript', nhưng có 'React' → suy ra biết JS"),
    ("Kubernetes", "Layer 3 — fuzzy: CV lỡ gõ lỗi chính tả 'Kubernetees', JD ghi đúng 'Kubernetes'"),
    ("JLPT N3",    "Proficiency — CV có N2 (cao hơn N3) → thỏa yêu cầu dù chuỗi khác nhau"),
    ("Rust",       "Missing — CV không có gì liên quan"),
]

for name, note in cases:
    m = matcher.evaluate_name(name, ctx)
    print(f"JD đòi: {name:12} -> status={m.status:16} layer={m.layer:12} via={m.via!r}")
    print(f"   ({note})\n")
```

**Output thật đã chạy kiểm chứng:**

```
JD đòi: Docker       -> status=matched          layer=layer0       via='docker'
JD đòi: NodeJS       -> status=matched          layer=layer1       via='node.js'
JD đòi: JavaScript   -> status=matched_implied  layer=layer2       via='node.js'
JD đòi: Kubernetes   -> status=matched          layer=layer3       via='kubernetees'
JD đòi: JLPT N3      -> status=matched          layer=proficiency  via='jlpt n2'
JD đòi: Rust         -> status=missing          layer=missing      via=''
```

> **Lưu ý khi trình bày Layer 2:** ở trên `JavaScript` khớp qua `via='node.js'`
> chứ không phải `'react'`, vì CV có cả 2 skill cùng suy ra JavaScript và code
> lấy skill xử lý trước trong tập hợp (thứ tự set không cố định). Nếu muốn demo
> **rõ ràng chỉ với `React`**, xóa `"Node.js"` khỏi danh sách `skills` — đã kiểm
> chứng riêng, kết quả là `via='react'` sạch, không lẫn:
> ```
> cv = ParsedCV(skills=["React"])
> matcher.evaluate_name("JavaScript", ctx)
> -> status=matched_implied layer=layer2 via='react'
> ```

### 2.2 Demo OR-group, tier weighting, missing, bonus — qua `/ai/score` (Cách B)

**File `d2_case.json`:**

```json
{
  "parsed_jd": {
    "title": "Backend Developer",
    "required_skills": [
      {"skill": "React", "weight": 3, "alternatives": ["Vue", "Angular"]},
      {"skill": "PostgreSQL", "weight": 3, "alternatives": []},
      {"skill": "Rust", "weight": 2, "alternatives": []}
    ],
    "preferred_skills": ["Docker"],
    "nice_to_have_skills": ["Kubernetes"]
  },
  "parsed_cv": {
    "name": "Ứng viên demo",
    "skills": ["Vue", "PostgreSQL", "Docker", "GraphQL"]
  }
}
```

Chạy:
```bash
curl -s -X POST http://localhost:8000/ai/score -H "Content-Type: application/json" \
  -d @d2_case.json | python3 -m json.tool
```

**Kết quả đã chạy thật để đối chiếu** (trỏ vào field nào để giải thích):

| Field cần chỉ | Giá trị thật (đã chạy xác nhận) | Giải thích khi trình bày |
| --- | --- | --- |
| `scores.skills` | **`72.7`** | Tính tay: matched_w = React(3, qua alt "Vue") + PostgreSQL(3) + Docker(2) = 8; total_w = 3+3+2+2+1 = 11 → 8/11 = 0.7272... → **72.7** |
| `evaluation.missing_must_have` | `[]` (rỗng) | Rust là `required_skills` nhưng `weight=2 < 3` nên **không** rơi vào must-have — xem quy tắc ở [evaluator.py:69](app/services/evaluator.py#L69): required mà weight &lt; 3 → xếp vào `missing_preferred` |
| `evaluation.missing_preferred` | `["Rust"]` | Đúng như trên |
| `evaluation.missing_nice_to_have` | `["Kubernetes"]` | CV không có Kubernetes, đúng tier nice_to_have |
| `evaluation.bonus_skills` | `["GraphQL"]` | Kỹ năng CV có nhưng JD không đòi ở bất kỳ tier nào |
| `evaluation.skill_details` | mục `"React / Vue / Angular"` có `status="matched"`, weight 3 | Chứng minh **OR-group thỏa bởi alternative** (CV có Vue, không có React) |
| `evaluation.skill_match_rate` | `72.7` | Khớp đúng với `scores.skills` — bằng chứng evaluator và scorer **dùng chung 1 nguồn tính** (`evaluate_tiers`), không lệch nhau |

> Con số `72.7` ở trên đã được chạy trực tiếp qua `score_skills()` để xác nhận
> — không phải suy đoán. Khi demo qua `/ai/score` (có cả `evaluate_cv_for_job`
> chạy song song), số ở `scores.skills` phải khớp đúng `72.7`; nếu chạy full
> pipeline qua LLM parse thay vì JSON viết tay, số có thể lệch nhẹ do LLM trích
> xuất khác đi.

---

## 3. D3 — Experience (kinh nghiệm)

**Mục tiêu chứng minh:** số tháng/năm kinh nghiệm được tính đúng, đặc biệt là
xử lý **chồng lấn thời gian (merge interval)** — điểm kỹ thuật hay bị hỏi nhất.

### 3.1 Demo merge-interval — đã kiểm chứng chạy thật

**Dữ liệu CV — 3 công việc, có 1 công việc chồng lấn thời gian:**

| Company | start | end | Số tháng riêng lẻ | Có chồng lấn với dòng khác? |
| --- | --- | --- | --- | --- |
| A | 2020-01 | 2021-01 | 12 tháng | Không |
| B | 2021-01 | 2022-01 | 12 tháng | Không (nối tiếp A, không đè lên A) |
| Freelance | 2021-06 | 2021-09 | 3 tháng | **Có** — nằm trọn trong khoảng của B (06/2021–09/2021 ⊂ 01/2021–01/2022) |

| Cách tính | Công thức | Kết quả |
| --- | --- | --- |
| Cộng ngây thơ (SAI) | 12 + 12 + 3 | **27 tháng** |
| Merge interval (ĐÚNG — `total_exp_months`) | Gộp A+B+Freelance thành 1 khoảng liên tục 2020-01 → 2022-01 | **24 tháng** = **2.0 năm** |

```python
from app.schemas import ParsedCV, WorkExperience

cv = ParsedCV(work_experience=[
    WorkExperience(company="A", role="Dev", start="2020-01", end="2021-01"),        # 12 tháng
    WorkExperience(company="B", role="Dev", start="2021-01", end="2022-01"),        # 12 tháng, nối tiếp A
    WorkExperience(company="Freelance", role="Dev", start="2021-06", end="2021-09"), # 3 tháng, NẰM TRỌN trong B
])
print(cv.total_exp_months)   # kỳ vọng 24, KHÔNG PHẢI 27
print(cv.total_exp_years)    # kỳ vọng 2.0
```

**Output thật:**
```
24
2.0
```

**Câu nói khi trình bày:**
> "Nếu cộng dồn ngây thơ từng job: 12 + 12 + 3 = 27 tháng. Nhưng job freelance ở
> đây **chạy song song** với job B (cả hai đều rơi vào tháng 6–9/2021) — ứng
> viên chỉ *sống* qua 24 tháng thực tế, không phải 27. Đây là lý do em không
> dùng phép cộng đơn giản mà dùng thuật toán **merge interval**: sắp xếp các
> khoảng thời gian theo ngày bắt đầu, gộp các khoảng chồng lấn hoặc liền kề lại
> làm một trước khi cộng tổng."

### 3.2 Demo "present" (đang làm việc)

| Company | start | end | Quy đổi `"present"` | Số tháng (tính tại ngày 2026-08) |
| --- | --- | --- | --- | --- |
| C | 2023-01 | `"present"` | → tháng hiện tại lúc chạy code | **43 tháng** (2023-01 → 2026-08) |

```python
cv2 = ParsedCV(work_experience=[
    WorkExperience(company="C", role="Dev", start="2023-01", end="present"),
])
print(cv2.total_exp_months)
```

⚠️ Kết quả phụ thuộc **ngày chạy thật** (vì `"present"` quy về tháng hiện tại) —
con số `43` chỉ đúng nếu chạy đúng lúc còn là 2026-08. **Chạy lại gần ngày demo
thật để cập nhật số tháng đúng**, không hard-code 43 vào slide.

### 3.3 Demo D3 qua `/ai/score` — tỷ lệ, chặn trần, JD không yêu cầu

**File `d3_case.json`** (3 case gộp 1 lần gọi để tiết kiệm thời gian — đổi
`min_experience_years` giữa các lần gọi):

```json
{
  "parsed_jd": {"title": "Backend Developer", "min_experience_years": 3},
  "parsed_cv": {
    "name": "Ứng viên demo",
    "work_experience": [
      {"company": "X", "role": "Dev", "start": "2023-01", "end": "2025-01"}
    ]
  }
}
```

| Đổi `min_experience_years` | CV có (tháng) | D3 kỳ vọng | Ý nghĩa |
| --- | --- | --- | --- |
| `3` | 24 tháng = 2 năm | `min(2/3, 1.0) = 0.667` → **66.7** | Thiếu kinh nghiệm, tỷ lệ đúng theo công thức |
| `2` | 24 tháng = 2 năm | `min(2/2, 1.0) = 1.0` → **100** | Đúng bằng yêu cầu |
| `1` | 24 tháng = 2 năm | `min(2/1, 1.0) = 1.0` → **100 (chặn trần)** | Vượt yêu cầu **không được cộng thêm điểm** — chứng minh quy tắc "chặn trần ở 1.0" |
| `0` (hoặc bỏ trường) | bất kỳ | **100** | JD không yêu cầu → mặc nhiên đủ điểm |

---

## 4. D4 — Education (học vấn)

**Mục tiêu chứng minh:** quy đổi bậc học đúng, chặn trần khi vượt yêu cầu,
trung lập khi thiếu dữ liệu.

**File `d4_case.json`** — đổi `"degree"` của CV giữa các lần gọi:

```json
{
  "parsed_jd": {"title": "Backend Developer", "education_degree": "bachelor"},
  "parsed_cv": {
    "name": "Ứng viên demo",
    "education": [
      {"institution": "Đại học Bách Khoa", "degree": "associate", "degree_raw": "Cao đẳng CNTT"}
    ]
  }
}
```

| `degree` của CV | JD yêu cầu | D4 kỳ vọng | Verdict (`evaluation.education_verdict`) |
| --- | --- | --- | --- |
| `associate` (2) | `bachelor` (3) | `min(2/3,1)=0.667` → **66.7** | `below` |
| `bachelor` (3) | `bachelor` (3) | `1.0` → **100** | `meets` |
| `master` (4) | `bachelor` (3) | `min(4/3,1)=1.0` → **100 (chặn trần)** | `exceeds` (nhưng điểm số vẫn 100, không hơn) |
| bỏ hẳn field `"education": []` | `bachelor` (3) | **50** (trung lập) | — CV không ghi bằng cấp, không bị phạt nặng |
| bất kỳ | bỏ `"education_degree"` khỏi JD | **100** | JD không yêu cầu → mặc nhiên đủ điểm |

**Case phụ — chuẩn hóa bằng cấp tiếng Việt** (chứng minh Pydantic validator
[schemas.py:142](app/schemas.py#L142) hoạt động đúng, không cần LLM):

```python
from app.schemas import Education
print(Education(degree="Cử nhân Công nghệ thông tin").degree)   # -> DegreeLevel.BACHELOR
print(Education(degree="Thạc sĩ").degree)                        # -> DegreeLevel.MASTER
print(Education(degree="THPT").degree)                            # -> DegreeLevel.HIGH_SCHOOL
```

---

## 5. D5 — Location + Work Mode

**Mục tiêu chứng minh:** remote/relocate cho điểm tuyệt đối, khoảng cách gần
cho điểm cao, khoảng cách xa cho điểm thấp, và **cùng khoảng cách nhưng khác
work_mode thì ra điểm khác nhau**.

> ⚠️ D5 gọi API bản đồ thật (Nominatim + OSRM) khi chấm điểm — **cần mạng**.
> Tọa độ dưới đây đã kiểm chứng chạy thật, ghi lại làm phương án dự phòng nếu
> mất mạng lúc demo.

### Bảng case

| # | Case | JD `work_location` | CV `candidate_location` | D5 kỳ vọng |
| --- | --- | --- | --- | --- |
| D5-1 | JD remote | `work_mode="remote"` (lat/lng bất kỳ) | bất kỳ, kể cả ở tỉnh khác | **100** — vô điều kiện |
| D5-2 | CV sẵn sàng chuyển chỗ ở | `work_mode="onsite"`, cách xa | `willing_to_relocate=true` | **100** — vô điều kiện |
| D5-3 | Thiếu tọa độ | `work_mode="onsite"`, không geocode được | `lat/lng=null` | **50** (trung lập) |
| D5-4 | Gần — cùng thành phố, onsite | Hoàn Kiếm, Hà Nội (`lat=21.0285, lng=105.8542`) | Cầu Giấy, Hà Nội (`lat=21.0333, lng=105.7826`) | **~73.7** (đã đo thật: 11.8 phút / 45 phút ngưỡng onsite) |
| D5-5 | Gần — CÙNG tọa độ D5-4 nhưng đổi `work_mode="hybrid"` | như trên | như trên | **~84.2** (ngưỡng nới ra 75 phút → cùng quãng đường, hybrid cho điểm cao hơn onsite) |
| D5-6 | Xa — khác miền | Quận 1, TP.HCM (`lat=10.7769, lng=106.7009`) | Hoàn Kiếm, Hà Nội (`lat=21.0285, lng=105.8542`) | **0** (đã đo thật: 1132.7 phút ≈ 18.9 giờ lái xe, vượt xa ngưỡng 45 phút) |

### File `d5_case.json` (case D5-4 — gần, onsite)

```json
{
  "parsed_jd": {
    "title": "Backend Developer",
    "work_location": {"city": "Ha Noi", "work_mode": "onsite", "lat": 21.0285, "lng": 105.8542}
  },
  "parsed_cv": {
    "name": "Ứng viên demo",
    "candidate_location": {"lat": 21.0333, "lng": 105.7826, "willing_to_relocate": false}
  }
}
```

Đổi `"work_mode": "hybrid"` → case D5-5. Đổi `lat/lng` của JD thành
`{"lat": 10.7769, "lng": 106.7009}` (Q1 TP.HCM) → case D5-6.

**Số liệu đã đo thật qua OSRM (để đối chiếu, tránh bất ngờ nếu số lúc demo lệch
nhẹ do giao thông/routing thay đổi):**

```
Cầu Giấy -> Hoàn Kiếm : 8.86 km,  11.8 phút lái xe
Hà Nội   -> TP.HCM     : 1495.4 km, 1132.7 phút lái xe (~18.9 giờ)
```

**Câu nói khi trình bày D5-4 vs D5-5:**
> "Hai case này dùng **đúng một quãng đường** — chỉ đổi `work_mode` từ `onsite`
> sang `hybrid`. Điểm tăng từ 73.7 lên 84.2 vì hybrid chỉ lên văn phòng vài
> buổi mỗi tuần nên chấp nhận được quãng đường xa hơn — ngưỡng chịu đựng
> `T_max` nới từ 45 lên 75 phút. Đây là bằng chứng D5 không chỉ đo khoảng cách
> vật lý mà đo **đúng cái ứng viên thật sự cảm nhận**: mức độ khả thi khi đi
> làm, có điều kiện theo hình thức làm việc."

---

## 6. Case tổng hợp — final_score + trọng số tùy chỉnh (HR override)

**Mục tiêu chứng minh:** `final_score` tổng hợp đúng công thức, và HR chỉnh
được trọng số theo nhu cầu riêng của từng tin tuyển dụng.

Dùng lại `d2_case.json` ở mục 2.2, gọi 2 lần — 1 lần không có `weights` (dùng
mặc định `.env`), 1 lần có `weights` tùy chỉnh:

```json
{
  "parsed_jd": { "...": "giữ nguyên như d2_case.json" },
  "parsed_cv": { "...": "giữ nguyên như d2_case.json" },
  "weights": {
    "semantic": 0.10,
    "skills": 0.60,
    "experience": 0.20,
    "education": 0.05,
    "location": 0.05
  }
}
```

**Kết quả đã chạy thật với đúng CV/JD của mục 2.2** — 5 điểm thành phần
(`scores`) **giữ nguyên** ở cả 2 lần gọi (semantic=50, skills=72.7,
experience=100, education=100, location=50); chỉ `final_score` thay đổi vì
trọng số áp vào khác nhau:

| | W-semantic | W-skills | W-experience | W-education | W-location | `final_score` |
| --- | --- | --- | --- | --- | --- | --- |
| **Mặc định** (`.env`) | 0.30 | 0.35 | 0.20 | 0.10 | 0.05 | **73.0** |
| **Tùy chỉnh** (request) | 0.10 | 0.60 | 0.20 | 0.05 | 0.05 | **76.1** |

**Vì sao tăng:** skill của ứng viên này (72.7) cao hơn semantic trung lập (50)
và location trung lập (50). Khi tăng trọng số skills từ 0.35 → 0.60 (và giảm
semantic, education), công thức nghiêng nhiều hơn về chiều mà ứng viên đang
mạnh → `final_score` tăng từ 73.0 lên 76.1. Đây là bằng chứng sống rằng đổi
trọng số **thực sự đổi kết quả xếp hạng**, không phải tham số cho có.

Nếu gửi tổng trọng số ≠ 1.0 hoặc thiếu 1 trong 5 khóa → API trả lỗi **422**
ngay ở tầng validate (xem [score.py:45](app/api/score.py#L45)) — có thể demo
luôn ca lỗi này để chứng minh hệ thống **không âm thầm nhận dữ liệu sai**.

**Câu nói khi trình bày:**
> "HR không bị khóa cứng vào một công thức. Nếu một job đặc biệt coi kỹ năng là
> tối quan trọng còn vị trí địa lý không đáng kể, HR gửi kèm bộ trọng số riêng
> ngay trong request — không cần sửa code, không cần deploy lại."

---

## 7. Bảng tổng kết thứ tự demo đề xuất (khớp với PRESENTATION.md §11)

| Thứ tự | Case | Thời gian | Công cụ |
| --- | --- | --- | --- |
| 1 | D2 — 6 layer qua Python script | 1 phút | `.venv/bin/python demo_d2_layers.py` |
| 2 | D3 — merge interval | 30 giây | Python REPL / script |
| 3 | D1 — 3 CV domain khác nhau | 2 phút | Swagger `/ai/parse-jd`, `/ai/parse-cv`, `/ai/score` |
| 4 | D1-4 — tài liệu lạc đề (anisotropy) | 1 phút | Swagger, dùng file đã chuẩn bị sẵn |
| 5 | D4 — chặn trần + trung lập | 1 phút | `curl` với `d4_case.json` |
| 6 | D5 — remote / gần / xa / onsite vs hybrid | 1.5 phút | `curl` với `d5_case.json`, đổi field trực tiếp trên terminal |
| 7 | Tổng hợp — trọng số tùy chỉnh | 1 phút | `curl` với `weights` override |

**Tổng: ~8 phút** — vừa khít trong khung 5–10 phút demo thường được cho phép.
Nếu bị cắt ngắn, ưu tiên giữ lại **case 1 (D2 layer)** và **case 4 (anisotropy)**
— đây là 2 case chứng minh chiều sâu kỹ thuật rõ nhất và ít phụ thuộc mạng nhất.

---

## PHỤ LỤC — Checklist chuẩn bị file trước ngày demo

- [ ] Viết 3 file CV text cho D1-1/D1-2/D1-3 (giữ số năm + bằng cấp giống nhau)
- [ ] Tìm 1 file PDF không phải CV (báo cáo/bài báo bất kỳ) cho D1-4
- [ ] Lưu `d2_case.json`, `d3_case.json`, `d4_case.json`, `d5_case.json` vào
      một thư mục riêng (gợi ý: `demo_payloads/`, KHÔNG commit vào git nếu chứa
      dữ liệu thật của ứng viên)
- [ ] Lưu `demo_d2_layers.py` ở gốc repo, chạy thử xác nhận output khớp bảng ở
      mục 2.1
- [ ] Chạy thử **toàn bộ 7 case** ít nhất 1 lần trong tuần trước buổi bảo vệ,
      chụp màn hình kết quả làm phương án dự phòng khi mất mạng/API rate-limit
- [ ] Xác nhận `.env` đang trỏ đúng `LLM_PROVIDER` ổn định nhất (khuyến nghị
      `gemini` — rẻ và đủ nhanh cho demo trực tiếp)
- [ ] Với case D5, chạy lại gần ngày demo để cập nhật số phút lái xe thật (OSRM
      public server có thể cho số hơi khác theo thời điểm)