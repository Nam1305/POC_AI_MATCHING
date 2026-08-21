# Thực nghiệm: LLM-as-a-Judge đánh giá độc lập JD↔CV, đối chiếu với mô hình 5D

> Thực hiện thủ công (không script hoá) bởi Claude Sonnet 5 trong phiên làm việc
> ngày 2026-08-19. Judge = chính model đang viết báo cáo này, đọc trực tiếp CV
> gốc và tự chấm theo rubric ở mục 2 — **không** gọi qua Gemini (LLM mà pipeline
> sản xuất đang dùng), nhằm đảm bảo 2 phép đo độc lập về nguồn model. Toàn bộ
> điểm 5D trong báo cáo là **điểm thật**, lấy từ pipeline production (`/ai/parse-jd`,
> `/ai/parse-cv`, `/ai/score`) chạy trên server local, không phải số mô phỏng.

---

## 0. Bối cảnh & phạm vi

- **JD**: 1 vị trí Java Backend Developer (remote), required = `Java Spring, Java`;
  preferred = `CI/CD, Docker, HTML, JUnit`; nice-to-have = `Postman, PostgreSql`;
  tối thiểu 2 năm kinh nghiệm; bằng Cử nhân CNTT/related field.
- **CV**: 11 file PDF thật (`JavaDev-CV01…12.pdf`, thiếu CV05) do người dùng cung
  cấp qua link GitHub (`anhtth20/careerhub-documents`).
- **Mục tiêu**: dùng LLM-judge làm điểm đối chiếu **độc lập** với `final_score`/
  5 chiều điểm của hệ thống hiện có trong repo, để phát hiện chỗ 2 phương pháp
  đồng thuận và chỗ bất đồng — từ đó chẩn đoán xem bất đồng đến từ đâu (thiết
  kế có chủ đích, hay lỗi thật).
- **Không phải** là bước validate LLM-judge với nhãn người thật (xem mục 9 —
  hạn chế). Đây là bước đối chiếu 2 phương pháp độc lập với nhau, chưa phải
  đối chiếu với ground truth.

---

## 1. Phương pháp luận

Theo khung đã thống nhất trước khi chạy thực nghiệm:

| Lựa chọn | Quyết định | Lý do |
| --- | --- | --- |
| Kiểu judge | **Rubric-decomposed pointwise** — chấm riêng 4 chiều (semantic/skills/experience/education) + 1 điểm holistic | Khớp trực tiếp với cấu trúc D1–D4 của repo, cho phép so sánh per-dimension thay vì chỉ 1 số tổng |
| Model judge | **Claude Sonnet 5** (chính model này) | Pipeline dùng `gemini-2.5-flash` (Stage 2) — dùng model khác nhà tránh **self-preference bias**: nếu judge cùng họ với model được đánh giá, lỗi hệ thống của model đó dễ lặp lại ở cả hai phía, gây correlation cao giả tạo |
| Nguồn text cho judge | **`cv_raw_text`** — output Stage 1 (PyMuPDF, không LLM) lấy thẳng từ response `/ai/parse-cv` | Nếu chấm trên `parsed_cv` (đã qua Gemini Stage 2), judge sẽ kế thừa mọi lỗi extraction của Gemini, làm hỏng tính độc lập. Đọc raw text giữ judge độc lập hoàn toàn với LLM nội bộ pipeline, chỉ dùng chung bước trích xuất PDF→text thuần cơ học |
| Ẩn danh | Không dùng tên ứng viên khi chấm, chỉ dùng CV01…CV12 | Giảm rủi ro bias theo tên/giới tính/trường học — xem system prompt mục 2 |
| Phạm vi chấm | **Không chấm D5 (location)** | Location là bài toán geocode/route, không phải thứ LLM có thể đánh giá đáng tin từ text |
| Vòng lặp validate với người thật | **Chưa chạy trong thực nghiệm này** | Bạn xác nhận đã có tập nhãn HR ở nơi khác nhưng không được cung cấp trong yêu cầu này — xem khuyến nghị mục 10 |

---

## 2. System prompt (nguyên văn đã dùng)

Thiết kế theo các nguyên tắc giảm bias đã thống nhất: grounding constraint (cấm
suy diễn), rubric có anchor theo từng khoảng điểm, extract-then-score, CoT
trước khi ra điểm, ẩn danh, loại trừ location, không đưa ra khuyến nghị
tuyển/loại (giữ nguyên tắc này giống `evaluator.py` của repo — số liệu do hệ
thống tính, quyết định thuộc về người).

```text
ROLE
You are an experienced, neutral technical recruiter evaluating how well ONE
candidate CV fits ONE job description. You are not affiliated with any
recruiting tool or automated scoring system; your judgment must stand on its
own, independent of any other score.

SCOPE / GROUNDING
- Base every judgment ONLY on evidence explicitly present in the CV and JD
  text given to you. Do not infer skills, years of experience, or
  qualifications that are not stated or directly demonstrated (e.g. in a
  listed project's tech stack, a work-experience description, or an explicit
  skill list).
- Treat course names, stated interests, or "familiar with" mentions as weaker
  evidence than skills explicitly used in a real job or project.
- If information is missing or ambiguous, say so explicitly in your rationale
  and reflect the uncertainty with a lower / hedged score rather than
  assuming the best or worst case.
- Do not consider the candidate's name, gender, age, nationality, or school
  prestige. Do not reward or penalize based on CV formatting, length, or
  writing style — evaluate substance only.

TASK STRUCTURE (apply to every candidate, in this order)
1. EXTRACT: list concrete evidence found in the CV for (a) required skills,
   (b) preferred skills, (c) nice-to-have skills, (d) years/nature of
   directly relevant work experience, (e) education level and field.
2. RATIONALE: reason about fit for each of the 4 dimensions below, using
   ONLY the evidence extracted in step 1.
3. SCORE: assign each dimension 0-100 using the anchors below, then a
   holistic 0-100 score.

DIMENSIONS AND ANCHORS

[semantic_role_fit] - does the overall role/title/responsibilities match the JD?
  90-100 role title & responsibilities directly match JD
  60-89  technical developer role, partial overlap, clearly hands-on backend/API work
  30-59  technical role but different specialization (frontend-heavy, PM/lead
         with little hands-on coding, IT support/QA)
  0-29   non-technical or unrelated-domain role

[skills_fit] - weighted evidence for required > preferred > nice-to-have.
  Treat a specific, well-known implementation as satisfying a general
  required skill (e.g. "Spring Boot / Spring MVC / Spring Security" satisfy
  a requirement written as "Java Spring"). Do NOT credit a skill only
  because it is implied by an unrelated technology that happens to be built
  in that language (e.g. "uses Cassandra" does not imply "knows Java").
  85-100 all required skills evidenced with real usage, most preferred/nice-to-have present
  55-84  required skills evidenced but gaps in preferred/nice-to-have, OR one
         required skill only partially evidenced
  25-54  required skills only partially/superficially evidenced (e.g. "basic
         knowledge", coursework mention only, no project usage)
  0-24   required skills not evidenced at all

[experience_fit] - years AND relevance vs the JD's stated minimum. Total
  career length only counts to the extent it is demonstrably relevant;
  unrelated roles (sales, admin, generalist IT support, QA/BA-only) do not
  count toward relevant backend experience.
  85-100 meets/exceeds required years with clearly relevant, hands-on work
  40-84  some relevant experience but under threshold, or diluted by mostly
         unrelated work history
  0-39   no demonstrable relevant experience regardless of total career length

[education_fit] - degree level AND field vs the JD's stated requirement.
  Explicitly flag if the CV indicates the degree is still in progress / not
  yet conferred.
  85-100 completed degree at/above required level, in the specified or closely related field
  50-84  completed degree at required level but loosely related field, OR
         right field but not yet completed/conferred
  0-49   no evidence of required degree level, or field unrelated AND level uncertain

OUTPUT FORMAT (JSON per candidate)
{
  "candidate_id": "...",
  "evidence": { "required_skills_found": [...], "preferred_skills_found": [...],
                "nice_to_have_found": [...], "relevant_experience_summary": "...",
                "education_summary": "..." },
  "rationale": { "semantic_role_fit": "...", "skills_fit": "...",
                 "experience_fit": "...", "education_fit": "..." },
  "scores": { "semantic_role_fit": 0-100, "skills_fit": 0-100,
              "experience_fit": 0-100, "education_fit": 0-100, "holistic": 0-100 },
  "confidence_notes": "flag ambiguity, missing info, or low-confidence judgment"
}

EXCLUSIONS
- Do NOT score location/commute - this JD is fully remote, geographic fit is
  outside your evaluation scope.
- Do NOT produce a hire/reject recommendation - output scores and rationale
  only; the hiring decision belongs to a human recruiter.
```

---

## 3. Cách lấy dữ liệu 5D thật (không phải số mô phỏng)

1. Tải 11 PDF trực tiếp từ `raw.githubusercontent.com/anhtth20/careerhub-documents`.
2. Bật server local (`uvicorn app.main:app --port 8000`), phục vụ PDF qua static
   file server nội bộ để mô phỏng đúng luồng `cv_url` mà `/ai/parse-cv` cần.
3. Gọi thật `POST /ai/parse-jd` với JD text nguyên văn bạn cung cấp.
4. Gọi thật `POST /ai/parse-cv` (batch 11 URL, `asyncio.gather` — đúng code path
   production).
5. Gọi thật `POST /ai/score` cho từng cặp (JD, CV) với `include_narrative=true`.

**Sự cố gặp phải khi chạy bước 3**: 2/3 lần gọi `/ai/parse-jd` đầu tiên trả về
HTTP 500:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for ParsedJD
preferred_skills.12
  Input should be a valid string [type=string_type,
  input_value={'skill': 'MySQL', 'alter...'SQL Server', 'Oracle']}, ...}
```

Nguyên nhân: câu JD *"Experience working with at least one relational database
such as MySQL, PostgreSQL, SQL Server, or Oracle"* khiến Gemini đôi khi áp dụng
nhầm cấu trúc `{skill, weight, alternatives}` (vốn chỉ hợp lệ cho
`required_skills`) sang `preferred_skills` (chỉ nhận `list[str]`) — xem
[`app/schemas.py`](../app/schemas.py) field `preferred_skills: list[str]` so
với `required_skills: list[SkillRequirement]`. Đây là lỗi thật, không phải do
tôi dàn dựng — ghi lại ở mục 8.5 vì đáng để sửa dù không chặn thực nghiệm này
(lần gọi thứ 3 thành công, dùng kết quả đó cho toàn bộ phần còn lại).

---

## 4. Kết quả LLM-judge — báo cáo đầy đủ từng ứng viên

Ẩn danh khi chấm (chỉ dùng CV-ID); tên thật liệt kê riêng ở bảng cuối mục này
cho tiện đối chiếu.

### CV01
- **Evidence**: Java, Spring Boot, Microservices, PostgreSQL, JUnit/Mockito, Docker,
  CI/CD (Jenkins pipelines), AWS — toàn bộ có bằng chứng dự án cụ thể (Axon
  Ivy Marketplace, UNO Bank, eContract). Thiếu bằng chứng HTML, Postman.
- **semantic_role_fit = 92** — tự mô tả "Java Backend Developer", trách nhiệm khớp JD gần như tuyệt đối.
- **skills_fit = 90** — Spring Boot/JUnit/Docker/CI-CD/PostgreSQL đều có bằng chứng thật; chỉ thiếu HTML, Postman (nice-to-have, không đáng kể).
- **experience_fit = 95** — tự nhận "nearly 3 years", toàn bộ là vai trò Spring Boot backend liên tục, đúng lĩnh vực.
- **education_fit = 100** — Cử nhân Khoa học Máy tính, ĐH Kỹ thuật Ostrava (Czech) — đúng cấp bậc + đúng ngành.
- **holistic = 90**. Confidence: cao.

### CV02
- **Evidence**: Java chỉ xuất hiện ở 1 vị trí intern 3 tháng làm game (LibGDX) — không liên quan backend/Spring. Còn lại là Frontend (Webflow/Wix), IT support, C#/PHP cá nhân.
- **semantic_role_fit = 30** — "IT Generalist", không phải backend developer.
- **skills_fit = 12** — Java chỉ xuất hiện nêu tên, không có Spring, không có CI/CD/Docker/JUnit/Postman.
- **experience_fit = 5** — 0 năm kinh nghiệm backend Java thật sự.
- **education_fit = 100** — Cử nhân Kỹ thuật phần mềm, ĐH Sài Gòn — đúng ngành.
- **holistic = 22**. Confidence: cao.

### CV03
- **Evidence**: 13+ năm Java EE (EJB, JSF, Weblogic, Hibernate, JAX-WS) — Java Core rất sâu nhưng **không có Spring ở bất kỳ đâu**. REST Jersey xuất hiện 1 lần.
- **semantic_role_fit = 55** — đúng là backend Java developer, nhưng stack Java EE 2010s, không phải Spring như JD ngụ ý.
- **skills_fit = 30** — Java Core mạnh, nhưng Java Spring thật sự không có bằng chứng (khác EJB, không phải lỗi chấm nhầm). Không có CI/CD/Docker/JUnit/Postman.
- **experience_fit = 65** — JD yêu cầu chung "2 năm backend/server-side development" (không giới hạn riêng Spring) — 13 năm backend Java thoả mãn phần này rất dư, dù kinh nghiệm Spring cụ thể = 0. Tách riêng khỏi skills_fit để không phạt 2 lần cùng 1 lỗ hổng.
- **education_fit = 100** — Cử nhân CNTT, ĐH Công nghệ - ĐHQGHN.
- **holistic = 50**. Confidence: cao — đây là trường hợp kinh nghiệm Java thật nhưng lệch framework, không phải ứng viên yếu.

### CV04
- **Evidence**: "Java Backend Developer | Spring Boot" ngay dòng đầu. Spring Boot, Spring MVC, Spring Security, Spring Data JPA/Hibernate, Docker, Jenkins (CI/CD), JUnit/Mockito (95% coverage), Postman/Swagger, PostgreSQL — **toàn bộ required/preferred/nice-to-have đều có bằng chứng dự án thật**.
- **semantic_role_fit = 95** — khớp gần như hoàn hảo về title lẫn trách nhiệm.
- **skills_fit = 95** — hiếm có CV nào khớp đủ cả 3 tier rõ như vậy.
- **experience_fit = 55** — sinh viên năm cuối, 1 năm part-time chuyên nghiệp (JD yêu cầu 2 năm); phần còn lại là project học thuật — chiều sâu kỹ năng bù đắp phần nào nhưng thời lượng chuyên nghiệp thực tế chưa đạt.
- **education_fit = 70** — đúng ngành (RMIT, Web & Mobile Dev), nhưng CV tự nhận "final-year student" — bằng có thể **chưa cấp** tại thời điểm ứng tuyển.
- **holistic = 78**. Confidence: cao. Đây là ứng viên có mật độ bằng chứng kỹ năng tốt nhất trong tập 11 CV, điểm holistic bị kéo xuống chủ yếu vì thâm niên/tình trạng tốt nghiệp, không phải vì thiếu năng lực.

### CV06
- **Evidence**: 10+ năm, nhưng vai trò "Dev Manager"/PM, toàn bộ dự án dùng C#/SQL Server. Java chỉ liệt kê tên trong danh sách ngôn ngữ, không có dự án nào dùng.
- **semantic_role_fit = 35** — vai trò quản lý dự án, không phải hands-on backend Java.
- **skills_fit = 15** — Java không có bằng chứng sử dụng thật; không Spring/CI-CD/Docker/JUnit/Postman.
- **experience_fit = 10** — 0 năm kinh nghiệm Java backend thật (kinh nghiệm PM/C# không tính).
- **education_fit = 75** — Bách Khoa Hà Nội, "Sư phạm kỹ thuật Tin" (thiên về sư phạm/đào tạo) — liên quan nhưng không khớp thẳng "Software Engineering".
- **holistic = 25**. Confidence: cao.

### CV07
- **Evidence**: Toàn bộ stack là .NET/Angular/C#. Không một dòng nào nhắc Java.
- **semantic_role_fit = 15**, **skills_fit = 5**, **experience_fit = 0**.
- **education_fit = 50** — sinh viên năm 4 (chưa tốt nghiệp), CV không nêu ngày tốt nghiệp dự kiến, không rõ đã hoàn thành bằng hay chưa tại thời điểm hiện tại → hạ độ tin cậy thay vì chấm tuyệt đối 0 hay 100.
- **holistic = 12**. Confidence: cao cho 3 chiều đầu, trung bình cho education (do thiếu mốc thời gian rõ ràng).

### CV08
- **Evidence**: Technical Leader 10+ năm, stack Node.js/PHP/.NET/React — rất rộng và sâu về backend/DB/DevOps nói chung, nhưng **không một dòng nào nhắc tới Java hay bất kỳ ngôn ngữ JVM nào**.
- **semantic_role_fit = 40** — kinh nghiệm backend/kiến trúc cấp senior thật, nhưng sai hoàn toàn hệ sinh thái ngôn ngữ so với JD.
- **skills_fit = 8** — cả 2 required skill (Java, Java Spring) đều không có bằng chứng; chỉ có preferred (Docker, Git) là có thật.
- **experience_fit = 5** — 0 năm kinh nghiệm Java, dù giàu kinh nghiệm backend nói chung.
- **education_fit = 85** — bằng "Software Engineer", đúng ngành (dù thông tin trường bị trích xuất không rõ ràng — xem mục 8.3 về chất lượng OCR).
- **holistic = 22**. Confidence: cao. **Lưu ý quan trọng**: mô hình 5D chấm "Java: matched_implied" cho CV này — theo bằng chứng văn bản, đây là false positive (xem mục 8.2).

### CV09
- **Evidence**: Kinh nghiệm là bán hàng/tuyển dụng, CSKH, kỹ thuật viên Shopify, thực tập sinh web. Kỹ năng lập trình tự nhận "kiến thức cơ bản" (basic knowledge) về Java/PHP/C++, không có dự án minh chứng.
- **semantic_role_fit = 15**, **skills_fit = 8** (chỉ là tự nhận biết cơ bản, không có usage thật), **experience_fit = 0** (không có công việc lập trình backend nào).
- **education_fit = 45** — vẫn đang học ("hiện nay"/ongoing), Học viện Nông nghiệp VN, ngành CNTT — đúng ngành nhưng chưa tốt nghiệp, không rõ mốc hoàn thành.
- **holistic = 10**. Confidence: cao.

### CV10
- **Evidence**: Tự nhận "Backend Developer (Fresher)". Dự án thật dùng PHP/JavaScript/SQL Server/Python. "Java" chỉ xuất hiện dưới mục **"Môn học tiêu biểu" (tên môn học đã học ở trường)**, không nằm trong danh sách kỹ năng tự khai, không xuất hiện ở bất kỳ dự án nào.
- **semantic_role_fit = 40** — đúng tinh thần backend fresher, nhưng sai ngôn ngữ.
- **skills_fit = 8** — theo nguyên tắc "tên môn học ≠ kỹ năng đã dùng" trong system prompt, Java **không được tính** là kỹ năng có bằng chứng ở đây.
- **experience_fit = 0** — không có dự án Java nào.
- **education_fit = 100** — Đại học Đại Nam, CNTT, GPA 3.52, thời gian học 2023–2025 (đã qua so với hiện tại 2026).
- **holistic = 18**. Confidence: cao. **Lưu ý quan trọng**: mô hình 5D chấm "Java: matched" cho CV này dựa trên `parsed_cv.skills` có chứa "Java" — đây là lỗi trích xuất (xem mục 8.3), không phải bằng chứng thật trong CV gốc.

### CV11
- **Evidence**: Vai trò hiện tại "Quản lý hành chính"; lịch sử làm việc là BA/tester/content-SEO tại Maiatech. Kỹ năng lập trình tự nhận "hiểu biết cơ bản" C/C++/PHP/Java/HTML từ 2018-2022 (đại học), không có dự án lập trình nào minh chứng.
- **semantic_role_fit = 15**, **skills_fit = 8**, **experience_fit = 0**.
- **education_fit = 80** — mốc học 2018-2022 đã qua từ lâu (nay là 2026) nên khả năng cao đã tốt nghiệp, ngành CNTT — nhưng văn bản CV bị lỗi OCR/font khá nặng (mất dấu tiếng Việt, ví dụ "Hoc Vién Néng Nghiép" thay vì "Học Viện Nông Nghiệp"), hạ độ tin cậy nhẹ.
- **holistic = 12**. Confidence: trung bình (do chất lượng text nguồn).

### CV12
- **Evidence**: 10 năm tại VNPAY, các hệ thống thanh toán QRCODE/ngân hàng thật. Java Core, Spring Boot, Spring MVC, Oracle, PostgreSQL, RabbitMQ, Redis, Elasticsearch — bằng chứng dự án rất cụ thể và có tính production cao (Agribank, Vietinbank). Không thấy CI/CD, Docker, HTML, JUnit, Postman được nêu tường minh.
- **semantic_role_fit = 92** — đúng vai trò Java backend cho hệ thống thanh toán, cấp độ senior.
- **skills_fit = 70** — cả 2 required skill đều có bằng chứng rất mạnh (Spring Boot **và** Spring MVC, không phải suy diễn); nhưng thiếu bằng chứng cho 4/6 preferred+nice-to-have skill.
- **experience_fit = 100** — ~10 năm kinh nghiệm Java Spring liên tục, đúng lĩnh vực, độ phức tạp cao (ngân hàng/thanh toán).
- **education_fit = 55** — Kỹ sư Điện - Điện tử (ĐH Giao thông Vận tải) — **không phải** CNTT/SE, chỉ liên quan gián tiếp qua nền tảng kỹ thuật.
- **holistic = 78**. Confidence: cao.

### Bảng tra tên thật

| CV-ID | Tên trên CV |
| --- | --- |
| CV01 | Truong Ha Xuan Huy |
| CV02 | Nguyễn Huỳnh Hưng |
| CV03 | Dao Cong Anh |
| CV04 | Tran Dang Duong |
| CV06 | Đàm Phương Đồng |
| CV07 | Nguyễn Hồng Nam |
| CV08 | Nguyễn Đình Hùng |
| CV09 | Nguyễn Tiến Bình |
| CV10 | Vũ Đức Nam |
| CV11 | Duong Thi Xinh |
| CV12 | Nguyễn Quang Trường |

---

## 5. Kết quả 5D thật — số liệu và cơ chế

### 5.1 Cách từng chiều được tính (tham chiếu code, áp dụng chung cho cả 11 CV)

| Chiều | Công thức | Nguồn |
| --- | --- | --- |
| D1 Semantic | cosine(embedding CV, embedding JD), embed trên `build_embed_text()` (loại bỏ skills) | [`scorer.py`](../app/services/scorer.py) |
| D2 Skills | cascade 4 tầng (exact → canonical → entailment → fuzzy) trên cả 3 tier, nhị phân | [`skill_matcher.py`](../app/services/skill_matcher.py) |
| D3 Experience | **theo chiều sâu từng required-skill**: chỉ tính tháng làm việc mà `tech_stack` của job đó thật sự chứa skill required, KHÔNG phải tổng số năm toàn CV | [`scorer.py:133-190`](../app/services/scorer.py#L133) |
| D4 Education | `min(cv_degree_level / jd_degree_level, 1.0)` — **chỉ so cấp bậc, không so ngành học** | [`scorer.py:197-211`](../app/services/scorer.py#L197) |
| D5 Location | driving-time OSRM; **không có hệ số work-mode** dù JD là remote — bị loại khỏi phạm vi so sánh của thực nghiệm này | [`scorer.py`](../app/services/scorer.py) |

### 5.2 Bảng điểm đầy đủ

| CV | D1 Semantic | D2 Skills | D3 Exp | D4 Edu | D5 Loc | **final_score** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CV01 | 76.1 | 55.6 | 45.8 | 100 | 100 | **66.5** |
| CV02 | 64.2 | 36.1 | 6.2  | 100 | 100 | **48.2** |
| CV03 | 69.6 | 19.4 | 50.0 | 100 | 100 | **52.7** |
| CV04 | 72.9 | 52.8 | 25.0 | 100 | 100 | **60.4** |
| CV06 | 62.4 | 33.3 | 50.0 | 100 | 100 | **55.4** |
| CV07 | 60.3 | 19.4 | 0.0  | 100 | 100 | **39.9** |
| CV08 | 64.5 | 44.4 | 0.0  | 100 | 100 | **49.9** |
| CV09 | 56.3 | 13.9 | 0.0  | 100 | 100 | **36.7** |
| CV10 | 66.2 | 41.7 | 0.0  | 100 | 100 | **49.5** |
| CV11 | 58.2 | 25.0 | 0.0  | 100 | 100 | **41.2** |
| CV12 | 60.3 | 22.2 | 50.0 | 100 | 100 | **50.9** |

**Quan sát ngay từ bảng**: D4 = 100 cho **cả 11/11 CV** — không có phân biệt nào,
kể cả với CV12 (ngành Điện-Điện tử, không phải CNTT) và CV07/CV09 (còn đang đi
học, chưa tốt nghiệp). D5 = 100 cho cả 11/11 CV — công việc remote nhưng D5 vẫn
chấm như onsite (theo đúng giới hạn đã ghi trong `docs/Overview.md`: "Work-mode
multiplier M cho D5: Chưa có"). Hai chiều này gần như không đóng góp tín hiệu
phân biệt nào trong tập dữ liệu này.

### 5.3 Vì sao mỗi CV có điểm như vậy — giải thích theo cơ chế 5D

- **CV01/CV04/CV12** (Spring Boot/MVC thật, có dự án cụ thể): D2 vẫn bị kéo
  xuống vì `missing_must_have: ['Java Spring']` xuất hiện — **không phải vì
  thiếu Spring thật**, mà vì cụm "Java Spring" (nguyên văn JD) không canonical
  hoá về đúng tag `spring` trong `skill_data.json` — xem cơ chế đầy đủ ở mục 8.1.
  Đây là nguyên nhân chính khiến D2 của các ứng viên mạnh nhất bị đánh giá
  thấp hơn thực tế.
- **CV03**: D2 thấp (19.4) là **đúng theo thiết kế** — ứng viên dùng Java EE
  (EJB/JSF/Weblogic), không có Spring thật, nên dù bug canonicalization ở
  trên có được sửa thì D2 vẫn thấp, hợp lý.
  D3 = 50.0 dù có 17 năm kinh nghiệm vì công thức D3 hiện tại đo theo tháng
  làm việc **trực tiếp với từng required-skill** (`Java Spring`, `Java`) chứ
  không phải tổng năm — do CV03 không có tháng nào gắn với "Java Spring" cụ
  thể trong `tech_stack`, chỉ riêng skill "Java" được tính (qua entailment từ
  EJB/JPA/Hibernate → java, hợp lý) nên ratio trung bình có trọng số ra 0.5.
- **CV08**: D2 = 44.4 dù CV **không có Java ở bất kỳ đâu** — vì `Cassandra`
  trong skill list của ứng viên bị `skill_implies.json` gán nhầm là "implies
  java" (transitive closure lỗi) → skill "Java" được chấm `matched_implied`.
  Đây là false positive thật trong dữ liệu Layer 2 — xem mục 8.2.
- **CV09/CV10/CV11**: D3 = 0.0 ở cả 3 — đúng, vì không có job/project nào có
  Java trong `tech_stack`. Với CV10, "Java" vẫn được D2 chấm "matched" vì
  `parsed_cv.skills` (do Gemini trích xuất) chứa "Java" — trong khi CV gốc
  chỉ nhắc "Java" như **tên môn học đã học**, không phải kỹ năng đã dùng. Đây
  là lỗi Stage 2 (LLM extraction), không phải lỗi Stage 4 (scoring logic) —
  xem mục 8.3.
- **experience_verdict / experience_detail hiển thị cho HR** (`sufficient`,
  `over_qualified`...) — với **tất cả 11 CV**, các nhãn này được tính từ
  `cv.total_exp_years` (tổng số năm **toàn bộ CV**, không lọc theo skill liên
  quan), khác hoàn toàn công thức tính điểm D3 thật (lọc theo skill). Ở 6/11
  CV, hai con số này mâu thuẫn rõ ràng nhau (bảng chi tiết ở mục 8.4) — đây là
  phát hiện quan trọng nhất về mặt kỹ thuật của thực nghiệm này.

---

## 6. Bảng so sánh & correlation

### 6.1 Per-dimension

| So sánh | Spearman ρ | p-value | Pearson r | p-value |
| --- | ---: | ---: | ---: | ---: |
| Holistic (judge) vs `final_score` (model) | **0.934** | 0.000 | 0.811 | 0.002 |
| semantic_role_fit (judge) vs D1 (model) | 0.769 | 0.006 | 0.713 | 0.014 |
| skills_fit (judge) vs D2 (model) | **0.438** | 0.177 | 0.524 | 0.098 |
| experience_fit (judge) vs D3 (model) | 0.884 | 0.000 | 0.798 | 0.003 |
| education_fit (judge) vs D4 (model) | không xác định | — | — | — |

D4 không tính được correlation vì `model.D4` **không có phương sai** (100 cho
mọi CV) — bản thân điều này đã là một phát hiện, không phải một hạn chế thống
kê đơn thuần.

### 6.2 Ranking side-by-side (theo final_score / holistic, giảm dần)

| Hạng (model) | CV | final_score | Hạng (judge) | holistic (judge) |
| ---: | --- | ---: | ---: | ---: |
| 1 | CV01 | 66.5 | 1 | 90 |
| 2 | CV04 | 60.4 | 2 | 78 |
| 3 | CV06 | 55.4 | 5 | 25 |
| 4 | CV03 | 52.7 | 4 | 50 |
| 5 | CV12 | 50.9 | 3 | 78 |
| 6 | CV08 | 49.9 | 7 | 22 |
| 7 | CV10 | 49.5 | 8 | 18 |
| 8 | CV02 | 48.2 | 6 | 22 |
| 9 | CV11 | 41.2 | 10 | 12 |
| 10 | CV07 | 39.9 | 9 | 12 |
| 11 | CV09 | 36.7 | 11 | 10 |

**Nhận định**: Top-2 (CV01, CV04) và bottom-1 (CV09) trùng khớp tuyệt đối giữa
2 phương pháp — tín hiệu mạnh, đáng tin. Lệch hạng lớn nhất là **CV06** (model
xếp #3, judge xếp #5) và **CV12** (model xếp #5, judge xếp #3) — model đang
đánh giá CV06 (Dev Manager, không có Spring thật) cao hơn CV12 (10 năm Spring
Boot thật tại VNPAY), trong khi judge cho kết quả ngược lại và rõ ràng hơn.
Nguyên nhân: D2 của CV12 bị bug canonicalization "Java Spring" kéo xuống ngang
CV06 (22.2 vs 33.3) dù bằng chứng Spring của CV12 mạnh hơn CV06 rất nhiều —
đúng như dự đoán ở mục 5.3.

**Vì sao correlation tổng thể (0.934) vẫn cao dù D2 lệch nhiều (0.438)**: bug
"Java Spring" không canonical hoá được ảnh hưởng gần như đồng đều lên **toàn
bộ 11/11 CV** (100% bị gắn `missing_must_have: Java Spring`, bất kể có Spring
thật hay không) — một bias hệ thống *đồng đều* làm tất cả điểm D2 bị trừ một
lượng gần giống nhau, nên **không** phá vỡ nhiều thứ hạng tương đối, dù nó phá
vỡ độ chính xác tuyệt đối của điểm số. Đây là lý do quan trọng cần hiểu: đo
correlation tổng thể có thể "che" một lỗi hệ thống nếu lỗi đó tác động đồng đều
— per-dimension correlation (đặc biệt D2 = 0.438) mới lộ ra vấn đề.

---

## 7. Phát hiện chi tiết (root cause, có tham chiếu code)

### 8.1 [Nghiêm trọng — ảnh hưởng cả 11/11 CV] "Java Spring" không canonical hoá được

**Root cause chính xác** — [`resolve_canonical()`](../app/services/skill_matcher.py#L140)
tự mô tả rõ trong docstring của chính nó:

```python
# "Không tìm thấy ở bất kỳ biến thể nào -> fallback về input đã lowercase/
#  strip (coi như skill lạ, không có trong danh mục)."
for variant in to_stackoverflow_format(skill):
    if variant in skill_data:
        ...
return skill.strip().lower()   # <-- fallback: tự nó thành "canonical" của chính nó
```

`to_stackoverflow_format('Java Spring')` chỉ thử các biến thể **định dạng lại
nguyên cụm** (`"java spring"`, `"java-spring"`, `"javaspring"`) — không thử
**tách cụm 2 từ thành từng từ riêng** để tra cứu độc lập. `"java-spring"`
không phải tag thật trên Stack Overflow (cộng đồng chỉ dùng `spring`/
`spring-boot`/`spring-mvc`), nên cả 6 biến thể đều trượt, và hàm fallback về
đúng input đã chuẩn hoá — tạo ra một canonical "ma" `java-spring`, không trùng
`spring` (canonical thật), và cũng không phải target của bất kỳ cạnh nào
trong `skill_implies.json` (`spring-boot implies ['spring','java']`, không
phải `['java-spring', ...]`). Kết quả: **toàn bộ cascade 4 tầng thất bại**
với mọi ứng viên, kể cả CV04 có nguyên văn "Java Spring Boot, Spring MVC,
Spring Security, Spring Data JPA".

**Vì sao đây là root cause thật, không phải chỉ là thiếu 1 entry trong KB**:
ngay cả khi thêm `"java spring"` làm synonym thủ công (fix nhanh, xem dưới),
lỗ hổng cấu trúc vẫn còn — bất kỳ cụm 2 từ nào khác không có trong
`skill_data.json` dưới dạng cụm nguyên vẹn (dù từng từ riêng lẻ đều là
canonical hợp lệ) sẽ gặp lại đúng lỗi này. `to_stackoverflow_format()` thiếu
một bước fallback tách-từ (decompose cụm không khớp thành các token, tra từng
token riêng) — đây mới là chỗ cần vá về lâu dài.

**Đề xuất sửa**:
- Ngắn hạn: thêm `"java spring"` như synonym trỏ về canonical `spring` trong
  `skill_data.json` (theo đúng khuôn mẫu `add_misc_skills.py`), rồi chạy lại
  `close_implies.py`.
- Dài hạn: thêm bước fallback trong `resolve_canonical()`/`to_stackoverflow_format()`
  để tách cụm không khớp thành các từ đơn và thử canonical hoá từng từ, tránh
  lặp lại lỗi này với các cụm 2-từ khác trong tương lai.

### 8.2 [Trung bình — xác nhận ảnh hưởng CV08, tiềm ẩn với 9 skill khác] 2 cạnh gán sai thủ công trong `skill_implies.json`, bị nhân bản qua transitive closure

**Root cause chính xác** — đây **không phải** lỗi thuật toán `close_implies.py`
(thuật toán bắc cầu chạy đúng như thiết kế). Root cause là 2 cạnh **gán tay
sai** tại [`app/data/add_kb_coverage_gap_skills.py:171-172`](../app/data/add_kb_coverage_gap_skills.py#L171):

```python
"elasticsearch": ["java"],
"cassandra":     ["java"],
```

File này áp một quy tắc chung "tool X → ngôn ngữ nền tảng Y" cho một danh sách
lớn thư viện (`"prettier": ["javascript"]`, `"yarn": ["node.js"]`,
`"retrofit": ["java"]`...) — quy tắc này **đúng** cho thư viện/client bạn viết
code trực tiếp lên trên (dùng npm/retrofit ⇒ chắc chắn viết JS/Java). Nhưng
Elasticsearch và Cassandra là **database/search-engine server độc lập**, truy
vấn qua REST/CQL từ **bất kỳ ngôn ngữ client nào** (Python, Node.js, Go...) —
việc server tự thân được cài bằng Java không có nghĩa người dùng nó biết lập
trình Java. Đây là lỗi phân loại tiêu chí gán nhãn (category error), áp dụng
đồng nhất một quy tắc chỉ đúng cho một nhóm con của tập hợp.

`close_implies.py` sau đó **nhân bản đúng-theo-thiết-kế** lỗi này ra 9 key
khác vốn tự thân đúng đắn khi implies `elasticsearch`/`cassandra` (bản thân
việc "Kibana implies Elasticsearch" là hợp lý — Kibana thuộc bộ Elastic
Stack):

```python
>>> implies['kibana']              # -> ['elasticsearch', 'java']
>>> implies['logstash']            # -> ['elasticsearch', 'java']
>>> implies['elk']                 # -> ['elasticsearch', 'java']
>>> implies['cassandra-2.0']       # -> ['cassandra', 'java']
>>> implies['cassandra-3.0']       # -> ['cassandra', 'java']
# + elastic-stack, elasticsearch-5, elasticsearch-aggregation
```

CV08 dùng Cassandra như key-value/wide-column store (không viết code Java nào)
nhưng vẫn được chấm `Java: matched_implied`, kéo D2 (44.4) cao hơn thực tế —
ứng viên này **hoàn toàn không có Java**.

**Đề xuất sửa** (rất cụ thể, không cần audit mò): xoá 2 dòng
`"elasticsearch": ["java"]` và `"cassandra": ["java"]` tại
`add_kb_coverage_gap_skills.py:171-172`, chạy lại `close_implies.py` để lan
truyền việc xoá xuống 9 key phái sinh. Nên rà thêm các entry còn lại trong
cùng file xem có cặp "server độc lập ↔ ngôn ngữ implement" nào khác bị áp
nhầm quy tắc tương tự không (ví dụ kiểm tra lại toàn bộ danh sách ở dòng
100-200 theo tiêu chí "đây là thư viện-viết-code-lên-trên hay server-độc-lập").

### 8.3 [Trung bình — xác nhận CV10, khả năng lặp lại ở CV khác có mục "môn học"] Prompt trích xuất CV không loại trừ ngữ cảnh "tên môn học"

**Root cause chính xác** — [`CV_EXTRACT_PROMPT`](../app/services/parser.py#L116),
dòng chỉ dẫn duy nhất về phạm vi quét skill:

```
- For skills: scan the entire CV — skills section, work experience, projects, summary.
```

Chỉ dẫn này liệt kê "quét toàn bộ CV" nhưng **không loại trừ mục học vấn/môn
học đã học** (education/coursework section), và không có quy tắc nào phân
biệt "kỹ năng đã dùng thật" (self-declared skill, hoặc xuất hiện trong
tech_stack của 1 job/project) với "tên môn học từng học ở trường". CV10 liệt
kê "Lập trình Java" **chỉ dưới mục "Môn học tiêu biểu"**, không nằm trong mục
kỹ năng tự khai (`Lập trình Python, C++, HTML/CSS, MySql`), không xuất hiện ở
bất kỳ project/tech_stack nào — nhưng Gemini vẫn đưa `"Java"` vào
`parsed_cv.skills`, khiến D2 chấm required-skill "Java" matched dựa trên bằng
chứng không tồn tại trong thực tế nghề nghiệp của ứng viên.

**Đề xuất sửa**: thêm 1 dòng loại trừ tường minh vào
`SKILL NORMALIZATION & EXTRACTION RULES` (khoảng dòng 120), ví dụ: "Do NOT
extract a skill solely because its name appears as a course/subject title in
an education section (e.g. 'Coursework: Java Programming') — only extract it
if it also appears as a self-declared skill, or is used in a work_experience/
project tech_stack." Đây là lỗi ở prompt trích xuất CV, nằm ngoài logic
scoring — khác hẳn 2 phát hiện ở trên (vốn là lỗi ở KB/canonicalization).

### 8.4 [Nghiêm trọng — ảnh hưởng 6/11 CV] `experience_verdict` (hiển thị cho HR) mâu thuẫn với điểm D3 thật

| CV | D3 điểm thật | Verdict hiển thị cho HR | Mâu thuẫn? |
| --- | ---: | --- | :---: |
| CV03 | 50.0 | over_qualified (17.0 năm) | Có |
| CV06 | 50.0 | over_qualified (10.6 năm) | Có |
| CV08 | **0.0** | **over_qualified** (14.4 năm) | **Có, nghiêm trọng** |
| CV09 | **0.0** | **sufficient** ✓ (2.6 năm) | **Có, nghiêm trọng** |
| CV11 | 0.0 | over_qualified (5.0 năm) | Có |
| CV12 | 50.0 | over_qualified (10.9 năm) | Có (nhẹ hơn — CV12 thật sự có Spring) |

**Root cause chính xác, xác nhận qua git history** — commit
`a070201 "feat: enhance experience scoring to measure per-required-skill depth
and adjust fallback logic"` nâng cấp `score_experience()`
([`scorer.py:167-190`](../app/services/scorer.py#L167)) sang đo theo chiều sâu
**từng required-skill** (chỉ tính tháng làm việc thật sự gắn với skill đó
trong `tech_stack`), nhưng:

```
$ git show --stat a070201
 app/services/scorer.py     | 96 +++++++++++++++++++++++++++++----
 tests/test_scorer.py       | 79 +++++++++++++++++++++++++++
```

Commit này **chỉ đụng tới `scorer.py` và test của nó** — không hề chạm vào
`evaluator.py`. `evaluator._analyze_experience()`
([`evaluator.py:136-173`](../app/services/evaluator.py#L136)) — hàm sinh
`experience_verdict`/`experience_detail` hiển thị trực tiếp cho HR — vẫn dùng
công thức cũ `cv.total_exp_years` (tổng mọi công việc, không lọc liên quan).
Đây đúng nghĩa là **code drift**: 2 hàm lẽ ra phải mô tả cùng một khái niệm
("ứng viên có đủ kinh nghiệm liên quan không") nhưng không chia sẻ 1 nguồn
tính toán duy nhất — khác với D2, nơi `evaluate_tiers()` được dùng làm "nguồn
duy nhất" cho cả `scorer.score_skills` lẫn `evaluator._analyze_skills` (đã ghi
rõ trong `docs/Overview.md`). Kỷ luật "1 nguồn tính duy nhất" này đã không
được áp dụng khi D3 được nâng cấp. Hậu quả thực tế nghiêm trọng nhất là
**CV08**: điểm số nói "0% kinh nghiệm liên quan" nhưng dòng chữ HR nhìn thấy
lại là "over-qualified — vượt gấp đôi yêu cầu" — hai tín hiệu trực tiếp mâu
thuẫn nhau trên cùng một màn hình.

**Đề xuất sửa**: cho `evaluator._analyze_experience()` gọi lại
`_skill_experience_ratio()`/kết quả của `score_experience()` thay vì tính lại
từ `cv.total_exp_years` — áp dụng đúng nguyên tắc "1 nguồn duy nhất" đã dùng
cho D2.

### 8.5 [Nhẹ — không chặn nhưng nên sửa] `preferred_skills` đôi khi nhận nhầm object thay vì string

**Root cause chính xác** — mục
[`ALTERNATIVES / OR-GROUPS`](../app/services/parser.py#L429) trong
`JD_EXTRACT_PROMPT` dạy model cách gói 1 OR-group thành object
`{skill, weight, alternatives}` (ví dụ `"React.js, TypeScript, or Vue.js" →
{"skill": "React.js", ..., "alternatives": [...]}`), nhưng **không giới hạn
tường minh** rằng cấu trúc object này chỉ hợp lệ khi kết quả đổ vào
`required_skills`. Câu ví dụ duy nhất trong mục này ("emit ONE
required_skills entry") ngụ ý phạm vi qua tên biến, không phải một ràng buộc
nêu rõ. Khi JD có câu prose dạng OR-group nhưng thứ tự xử lý (mục
`DUPLICATE PREVENTION`, dòng 340-341) phân loại nó vào `preferred_skills`
(vì không nằm trong tag `Required Skills:`), Gemini vẫn áp lại đúng cấu trúc
object đã học ở mục OR-GROUPS — vi phạm schema `preferred_skills: list[str]`
([`schemas.py`](../app/schemas.py)), gây `ValidationError` chặn toàn bộ
`/ai/parse-jd`. Đúng JD này có câu *"at least one relational database such as
MySQL, PostgreSQL, SQL Server, or Oracle"* trong khối Requirements (prose, không
phải tag list) — khớp chính xác pattern OR-group nhưng lại được phân vào tier
preferred, nên xảy ra đúng xung đột này. Không tái hiện 100% (phụ thuộc
sampling của Gemini dù `temperature=0`), nhưng đã xảy ra 2/3 lần thử với đúng
JD này.

**Đề xuất sửa**: thêm 1 câu vào cuối mục `ALTERNATIVES / OR-GROUPS`: "This
`{skill, weight, alternatives}` object structure applies ONLY when the entry
lands in `required_skills`. If an OR-group is classified as preferred or
nice-to-have instead, emit it as a single plain string (the primary/first
option only) — `preferred_skills`/`nice_to_have_skills` accept flat strings
only, never an object."

### 8.6 [Thiết kế có chủ đích, không phải bug] D4 không phân biệt ngành học

D4 chỉ so **cấp bậc** bằng cấp (`bachelor`/`master`/...), không so **ngành
học** — nên CV12 (Kỹ sư Điện-Điện tử) vẫn nhận D4 = 100 dù JD ghi rõ "Computer
Science, Information Technology, Software Engineering, or a related field".
Đây là giản lược có ghi chú rõ trong code, không phải lỗi — nhưng cộng với
mục 8.4 (D3 hiển thị sai) và việc D4 hoàn toàn không có phương sai trên tập 11
CV này (mục 6.1), nó góp phần làm educaiton trở thành chiều **ít thông tin
nhất** trong 5D đối với JD/tập ứng viên này.

---

## 8. Hạn chế của thực nghiệm này

1. **N = 11, 1 JD duy nhất.** Không đủ để ước lượng correlation với độ tin cậy
   thống kê cao (p-value ở mục 6.1 chỉ mang tính minh hoạ, khoảng tin cậy
   rộng). Đây là một pilot định tính, không phải một validation quy mô lớn.
2. **Chưa đối chiếu với nhãn người thật.** Bạn xác nhận đã có tập (JD, CV) có
   nhãn HR ở nơi khác, nhưng tập đó **không được cung cấp trong yêu cầu này**.
   Báo cáo này so 2 phương pháp **độc lập với nhau**, chưa so với ground
   truth — theo đúng framework đã thống nhất trước khi chạy (mục "Vòng lặp
   validate" ở phần trao đổi trước), bước tiếp theo bắt buộc là chạy lại rubric
   này trên tập có nhãn người thật để biết judge (hay model, hay cả hai) lệch
   khỏi đánh giá HR thật ở đâu.
3. **Judge chạy 1 lần / CV, không lặp lại để đo variance.** Do đây là suy luận
   trực tiếp trong phiên làm việc (không phải gọi API hàng loạt), tôi chưa đo
   được độ ổn định của chính judge qua nhiều lần chấm cùng 1 cặp — một khuyến
   nghị đã nêu ở phần thảo luận phương pháp luận trước đó nhưng chưa áp dụng
   ở đây.
4. **Chất lượng text nguồn không đồng đều.** CV11 bị lỗi font/OCR khá nặng —
   độ tin cậy của cả judge lẫn Gemini Stage-2 extraction trên CV này thấp hơn
   các CV còn lại; đã ghi chú "confidence: trung bình" tương ứng ở mục 4.
5. **D5/location bị loại khỏi phạm vi so sánh** — nên "final_score" của model
   (có D5=100 đều cho tất cả) và "holistic" của judge (không tính D5) không
   hoàn toàn cùng thang đo; correlation ở mục 6.1 vẫn hợp lệ vì D5 hằng số
   (100 mọi CV) không đóng góp phương sai nào cho final_score trong tập này,
   nhưng cần lưu ý nếu áp dụng cách so sánh này cho JD có địa điểm cụ thể.

---

## 9. Khuyến nghị tiếp theo

1. **Ưu tiên sửa 8.1** (canonicalization "Java Spring") — ảnh hưởng rộng nhất
   (11/11 CV), sửa đơn giản nhất (thêm synonym vào `skill_data.json`).
2. **Sửa 8.4** (`evaluator._analyze_experience` dùng lại công thức cũ) — đây
   là lỗi hiển thị sai cho HR, mức độ ưu tiên cao vì ảnh hưởng trực tiếp tới
   quyết định tuyển dụng thật, không chỉ điểm số nội bộ.
3. Audit `skill_implies.json` quanh các cạnh "X implies java/python/..." sinh
   bởi `close_implies.py` (8.2) — kiểm tra xem còn ngôn ngữ nào khác (không chỉ
   Java) bị transitive closure gán nhầm.
4. Chạy lại đúng rubric + system prompt ở mục 2 trên **tập có nhãn HR thật**
   bạn đã có sẵn, để biết mức agreement(judge, human) trước khi dùng judge làm
   proxy ở quy mô lớn hơn — đúng vòng lặp đã thống nhất ban đầu.
5. Nếu muốn chạy thực nghiệm này tự động, lặp lại ở quy mô lớn hơn (nhiều JD,
   nhiều CV, nhiều lần chấm/cặp để đo variance): viết script gọi Claude API
   (Anthropic SDK) với đúng system prompt ở mục 2, theo mẫu
   `scripts/d1_embedding_accuracy_experiment.py` đã có trong repo — thay vì
   tôi đóng vai judge thủ công như lần này.
