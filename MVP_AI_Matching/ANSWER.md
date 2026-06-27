# Câu hỏi & Trả lời — Kiến trúc AI Matching

---

## Embedding & Semantic Similarity

**Q1. Tại sao dùng embedding để so sánh CV với JD thay vì chỉ dùng keyword matching?**

Keyword matching chỉ bắt được exact/near-exact match. Embedding capture semantic meaning: CV viết "xây dựng REST API với Python" và JD yêu cầu "backend developer" sẽ có cosine sim cao mà không cần cùng từ. Ngoài ra, keyword matching bỏ sót các alias thông thường ("NodeJS" vs "Node.js" vs "Node") trong khi embedding đã được trained để hiểu các khái niệm tương đương. D5 (keyword scoring) vẫn được giữ lại để catch các domain-specific terms quan trọng mà embedding có thể dilute.

---

**Q2. Cosine similarity trả về [-1, 1] — tại sao text embedding thường cho kết quả [0, 1]?**

Text embedding models được trained với contrastive learning (ví dụ: SentenceTransformer dùng SBERT với cosine similarity loss). Kết quả là các vector text thường nằm ở phần dương của không gian vector — các components không âm sau khi normalize. Thêm vào đó, các model như `gemini-embedding-001` và `text-embedding-3-small` áp dụng L2 normalization, khiến dot product bằng cosine sim và range thực tế là [0, 1] cho các cặp text có liên quan hay không liên quan. Về lý thuyết vẫn có thể âm nhưng hiếm xảy ra trong practice với text.

---

**Q3. `normalize_cosine()` stretch range [0.55, 0.90] → [0, 1]. Các con số này lấy từ đâu?**

Từ thực nghiệm với `gemini-embedding-001` — được ghi trong `config.py`:

```python
cosine_min: float = 0.55  # floor: 2 văn bản không liên quan (CV kế toán vs JD backend)
cosine_max: float = 0.90  # ceiling: cùng tech stack, cùng seniority level
```

Lý do range này hẹp: model đã học ngôn ngữ chung nên cosine sim của 2 văn bản hoàn toàn không liên quan vẫn ~0.55 (không bao giờ về 0 như các domains khác). Ceiling 0.90 vì ngay cả CV và JD cùng stack gần như không đạt trên 0.90 vì vẫn có sự khác biệt về ngữ cảnh. Nếu đổi sang provider khác (SentenceTransformer, OpenAI) thì cần re-calibrate 2 con số này — `scorer.py` expose tham số `cosine_min` và `cosine_max` để override.

---

**Q4. Tại sao CV embedding và JD embedding phải dùng cùng 1 provider?**

Mỗi embedding model tạo ra vector space riêng. Cosine similarity chỉ có nghĩa khi 2 vector nằm trong cùng không gian. `gemini-embedding-001` (3072-dim) và `all-MiniLM-L6-v2` (384-dim) không chỉ khác dimension mà khác cả cách organize semantic space — vector "Python developer" ở 2 model trỏ về 2 hướng hoàn toàn khác nhau trong không gian của chúng. Cosine sim giữa 2 model khác nhau là con số vô nghĩa. Hệ thống enforce điều này qua config: cùng `EMBED_PROVIDER` cho cả CV lẫn JD.

---

**Q5. Embedding dimension khác nhau (384 vs 1536 vs 3072) ảnh hưởng gì đến chất lượng matching?**

Dimension cao hơn = nhiều "slots" để encode thông tin = richer representation về mặt lý thuyết. Thực tế:

- `all-MiniLM-L6-v2` (384-dim, local): nhanh, miễn phí, đủ tốt cho keyword-heavy domains
- `text-embedding-3-small` (1536-dim, OpenAI): tốt hơn cho nuance, multilingual
- `gemini-embedding-001` (3072-dim): capture được context sâu hơn, hiểu được implied skills

Tradeoff: dim cao hơn → lưu trữ nhiều hơn, tính cosine sim chậm hơn, vector DB cần nhiều RAM hơn. Với bài toán CV matching, sự khác biệt giữa 1536 và 3072 không lớn bằng sự khác biệt giữa 384 và 1536.

---

## Scoring Algorithm (5D)

**Q6. Tại sao cần đến 5 dimension thay vì chỉ dùng cosine similarity của embedding?**

Embedding (D1) có điểm yếu cốt lõi: nó average toàn bộ nội dung CV thành 1 vector — CV dài với nhiều context sẽ "dilute" các skills cụ thể. Ví dụ: CV có 1 dòng đề cập Python nhưng 20 dòng về quản lý dự án → embedding vẫn mang semantic "project management" nhiều hơn → D1 thấp dù Python có thể relevant. Các dimension còn lại handle những gì embedding bỏ sót:

- **D2 (Skills)**: explicit check từng skill bắt buộc với alias/fuzzy/category matching
- **D3 (Experience)**: hard threshold về số năm — semantic không đủ để phân biệt "5 năm kinh nghiệm" và "fresher"
- **D4 (Education)**: degree level comparison — cần numeric mapping, không phải semantic
- **D5 (Keywords)**: domain-specific terms mà embedding có thể smooth over

---

**Q7. Weight mặc định `skills=0.35, semantic=0.30, experience=0.20, ...` — cơ sở nào?**

Đây là empirical weights, không có statistical basis từ labeled data. Logic được áp dụng:

- `skills=0.35` cao nhất: trong tuyển dụng tech, match về technical skills là yếu tố quyết định nhất
- `semantic=0.30`: holistic fit quan trọng, nhưng sau skills
- `experience=0.20`: quan trọng nhưng nhiều công ty linh hoạt ±1-2 năm
- `education=0.10`: trong tech, bằng cấp ít quyết định hơn skills thực tế
- `keywords=0.05`: rất thấp vì dễ bị game và đã được capture một phần bởi D2

Weights có thể override qua `default_weight_*` trong `.env` và `AdaptiveWeights` tự adjust theo đặc điểm JD.

---

**Q8. `AdaptiveWeights` điều chỉnh weight theo JD — có rủi ro gì?**

Rủi ro chính là **explainability**: HR không biết weight đang thay đổi → không giải thích được tại sao candidate A score cao hơn candidate B. Thêm vào đó:

- JD có >5 skills → `skills` weight tăng 0.10, `semantic` giảm 0.05 → có thể miss candidate có overall fit tốt nhưng thiếu vài skills không quan trọng
- Weight thay đổi → cùng 1 candidate apply 2 JD tương tự nhưng score khác nhau không rõ lý do
- `AdaptiveWeights` hiện tại là optional và không được dùng mặc định trong `calculate_score()` — phải pass tường minh vào tham số `weights=`

---

**Q9. D5 keyword scoring — edge case nào nó fail?**

- **Tiếng Việt có dấu**: JD keyword "kiến trúc microservice" → sau `_clean_text_for_match` (chỉ giữ `\w\s`) thì dấu bị strip → "kiến trúc" thành "ki n tr c" → match fail
- **Viết liền**: JD keyword "ci/cd" → clean thành "ci cd", CV viết "CI/CD pipeline" → clean thành "ci cd pipeline" → "ci cd" in text ✓ (works), nhưng "devops" không match "ci_cd" trong alias
- **Partial word**: keyword "SQL" nhưng CV có "NoSQL" → word-boundary check: `\bSQL\b` trong "NoSQL" → fail ✓ (correct) nhưng cũng fail khi keyword "sql" và CV có "MySQL" → `\bsql\b` không match trong "mysql" (no boundary)

---

**Q10. `score_experience()` có penalty cho over-qualification. Có trường hợp nào penalty này gây sai không?**

```python
if cv_years > 2 * jd.min_experience_years:
    modifiers -= 0.05
```

Penalty nhỏ (0.05) và chỉ áp dụng khi vượt gấp đôi. Trường hợp có thể gây sai:

- Senior developer muốn **career change** sang domain mới → apply vào junior role để học → bị penalty oan
- **Consulting/freelance** model: người 10 năm kinh nghiệm apply vào startup junior role vì lý do cá nhân → vẫn bị -0.05
- Mức penalty thấp (0.05) nên ảnh hưởng không lớn, nhưng về nguyên tắc là false negative

---

**Q11. Business rule: thiếu 1 must-have skill → penalty 20%. Basis của con số này?**

Không có statistical basis — là judgment call dựa trên logic:

- 1 must-have missing → moderate issue: candidate còn có thể learn nhanh → 20% penalty, không reject hẳn
- 3 missing → 60% penalty (near deal-breaker)
- Cap tại 70%: tránh score về 0 vì thiếu nhiều skills (vẫn muốn giữ semantic/experience score có ý nghĩa)

Must-have được định nghĩa là `weight >= 3` (scale 1-3 từ JD parser). Threshold này có thể điều chỉnh qua `enforce_must_have=False` để tắt hoàn toàn business rules.

---

## LLM Integration & Prompt Engineering

**Q12. Tại sao evaluator chỉ dùng 1 LLM call cho toàn bộ narrative thay vì nhiều call nhỏ?**

Từ thiết kế được comment rõ trong `evaluator.py`: "5. LLM narrative — 1 call duy nhất". Lý do:

- **Cost**: mỗi API call = latency + token cost. 5 calls nhỏ đắt hơn 1 call đầy đủ
- **Coherence**: 1 call với full context → LLM tạo narrative nhất quán, không contradiction giữa các đoạn
- **Holistic view**: LLM thấy toàn bộ picture (skills + experience + education + seniority) → narrative tự nhiên hơn
- Steps 1-4 (Python analysis) đã chuẩn bị sẵn tất cả data → LLM chỉ cần viết, không cần reasoning về facts

---

**Q13. Prompt inject structured data từ Python analysis. Ưu điểm so với cho LLM tự phân tích raw CV?**

Kiến trúc hiện tại: Python xử lý logic → inject kết quả vào prompt LLM. Ưu điểm:

- **Deterministic facts**: skill_match_rate, missing_must_have, exp_detail được Python tính chính xác — LLM không thể hallucinate các con số này
- **Giảm token**: inject summary (~200 tokens) thay vì raw CV (~2000 tokens) → rẻ hơn và ít noise hơn
- **Tách biệt trách nhiệm**: Python làm điều Python giỏi (so sánh, tính toán), LLM làm điều LLM giỏi (viết natural language)
- **Explainable**: có thể kiểm tra từng bước Python output độc lập với LLM

---

**Q14. Tại sao parse recommendation bằng string split thay vì structured output / JSON mode?**

Narrative là free text (đoạn văn tự nhiên) — không thể enforce toàn bộ response là JSON. Recommendation chỉ là 1 từ ở cuối, string split đủ đơn giản và robust:

```python
if "RECOMMENDATION:" in raw_text:
    parts = raw_text.split("RECOMMENDATION:")
    narrative = parts[0].strip()
    rec_raw = parts[1].strip().lower().split()[0]
```

JSON mode sẽ phức tạp hóa không cần thiết: phải design schema gộp cả narrative (text dài) và recommendation (enum) vào 1 JSON object, và Gemini 2.5 Flash với JSON mode đôi khi format narrative kém tự nhiên hơn.

---

**Q15. `temperature=0.4` trong narrative generation — tại sao không dùng 0.0 cho deterministic?**

- `temperature=0.0`: tất cả HR đọc narrative của mọi candidate đều có cùng pattern diễn đạt → cảm giác robotic, copy-paste
- `temperature=0.4`: có đủ variability trong cách diễn đạt → tự nhiên như người viết, nhưng không quá cao để hallucinate
- Parser dùng `temperature=0` (JSON extraction) vì cần deterministic structure. Narrative dùng 0.4 vì đây là creative writing task

---

**Q16. Nếu LLM hallucinate (bịa skill mà CV không có) trong narrative — hệ thống detect được không?**

Không có mechanism detect trực tiếp. Tuy nhiên có mitigation:

- Toàn bộ facts (skills matched/missing, exp_detail, edu_verdict) được inject từ Python → LLM chỉ cần diễn đạt lại, ít phải "sáng tạo" về facts
- Narrative phản ánh kết quả Python analysis, không phải đọc raw CV độc lập
- Rủi ro còn lại: LLM có thể thêm qualitative judgment ("candidate có vẻ có tiềm năng về X") dựa trên inference không có cơ sở — đây là acceptable risk cho narrative generation

---

## Skill Matching

**Q17. `SkillMatcher` dùng alias map hardcode. Limitation lớn nhất là gì?**

- **Static maintenance**: framework mới ra (Bun.js, Astro, Remix) không có trong alias → bị treat là unknown skill
- **Domain limited**: map chỉ cover web/cloud/data/devops, thiếu embedded systems, game dev, mobile (Swift, Kotlin)
- **Không handle tiếng Việt**: "Lập trình Python" không match "Python"
- **Multi-word edge cases**: "Spring Boot" → alias map có "spring boot" → "spring", nhưng CV viết "Spring Framework" → "spring framework" không trong alias → normalize thành "spring framework" (không match "spring")

---

**Q18. "Python" vs "Cython" có bị fuzzy match không?**

`SequenceMatcher(None, "python", "cython").ratio()`:
- Common subsequence: "ython" (5 chars)
- Total chars: 6 + 6 = 12
- ratio = 2 × 5 / 12 ≈ **0.833**

0.833 < threshold 0.85 → **KHÔNG match** ✓. Đây là behavior đúng. Tương tự "numpy" vs "sympy": ratio ≈ 0.727 → không match ✓.

---

**Q19. Category match — false positive case?**

```python
CATEGORIES = {
    "database": {"mysql", "postgresql", "mongodb", "redis", "sqlserver", "elasticsearch"},
    "cloud":    {"aws", "gcp", "azure"},
}
```

JD yêu cầu `Redis` (in-memory cache, pub/sub), CV chỉ có `MongoDB` (document DB) → cùng category "database" → partial credit 0.3. Nhưng Redis và MongoDB là hoàn toàn khác use case — candidate không thể substitute Redis bằng MongoDB cho caching layer.

Tương tự: JD cần `AWS` expertise (Lambda, ECS, RDS), CV chỉ có `GCP` (BigQuery, Cloud Run) → category "cloud" → credit 0.3 dù skills không transferable trực tiếp. Category match nên được xem là "better than nothing" chứ không phải "equivalent".

---

**Q20. Tại sao collect skills từ cả `cv.skills`, `work_experience.tech_stack`, và `projects.tech_stack`?**

```python
def _collect_cv_skills(cv: ParsedCV) -> set[str]:
    skills = {s.lower() for s in cv.skills}
    for exp in cv.work_experience:
        skills.update(s.lower() for s in exp.tech_stack)
    for proj in cv.projects:
        skills.update(s.lower() for s in proj.tech_stack)
    return skills
```

Candidate thường quên liệt kê skill trong section "Skills" nhưng mention trong mô tả công việc hoặc project. Ví dụ: CV không có "Docker" trong skills list nhưng work experience ghi "Deployed services using Docker and Kubernetes". Thu thập từ cả 3 nguồn đảm bảo không bỏ sót skills thực sự được sử dụng. `tech_stack` đặc biệt có giá trị vì nó represent skills đã applied trong thực tế (có evidence), không chỉ self-declared.

---

## Architecture & Design Decisions

**Q21. Parser dùng LLM để extract structured data từ PDF. Tại sao không dùng regex/rule-based parser?**

CV không có format chuẩn — mỗi người có layout riêng (Canva template, Word, LinkedIn export, handmade PDF). Regex cần template cố định:

- "3 years of experience" vs "2021-2024" vs "since Q1 2021" vs "3 năm kinh nghiệm" → LLM handle được hết
- Section headers khác nhau: "Work History" vs "Professional Experience" vs "Kinh nghiệm làm việc"
- Nested information: skill mention trong job description phải được extract vào `tech_stack`

Thêm vào đó: `parser.py` có retry mechanism — nếu `work_experience` hoặc `skills` rỗng sau parse đầu tiên, tự động retry với focused prompt. Rule-based parser không có fallback thông minh như vậy.

---

**Q22. Tại sao tách scorer (số) và evaluator (narrative)?**

**Scorer** (pure Python, no LLM):
- Fast: ~1ms per pair
- Cheap: không tốn API cost
- Scalable: có thể chạy trên hàng nghìn CV/JD pairs

**Evaluator** (LLM narrative):
- Slow: 2-5 seconds per pair
- Expensive: ~1000-2000 tokens per call
- Chỉ cần cho top candidates

Workflow thực tế: score tất cả candidates → sort → chỉ evaluate top-N candidates. Ngoài ra, `evaluator.py` reuse code từ `scorer.py` (`SkillMatcher`, `_collect_cv_skills`, `_detect_level`) thay vì duplicate logic.

---

**Q23. LLM parse sai CV → lỗi propagate qua pipeline như thế nào?**

Parse sai `work_experience.start/end` → `_diff_months()` tính sai → `total_exp_months` sai → D3 score sai → `experience_verdict` sai → narrative misleading.

Mitigations hiện tại:
- **Python tính months**: `WorkExperience._set_current_and_months()` tính từ start/end strings (không trust LLM-provided months)
- **Filter hallucination**: `_filter_empty_entries()` loại entries không có company/role/start
- **Retry**: nếu `work_experience == []` sau parse → retry với `WORK_EXP_RETRY_PROMPT` focused hơn
- **Điểm yếu còn lại**: skills extracted sai → D2 sai và `build_embed_text()` tạo wrong embedding → D1 sai

---

**Q24. Tại sao `embedder.py` chạy trong thread executor thay vì async trực tiếp?**

FastAPI chạy trên async event loop (uvicorn). Các SDK embedding là **blocking/synchronous**:

- `SentenceTransformer.encode()`: blocking Python call (torch inference)
- `OpenAI().embeddings.create()`: blocking HTTP call (sync requests)

Nếu gọi blocking code trực tiếp trong `async def` → block toàn bộ event loop → tất cả requests freeze trong khi 1 embedding đang chạy. `run_in_executor(None, ...)` push blocking call ra thread pool → event loop free để handle requests khác. `llm_client.py` dùng cùng pattern vì Anthropic/Groq SDK cũng là sync.

---

## RAG & Scalability

**Q25. Kiến trúc hiện tại scale thế nào nếu có 10,000 CV cần match với 1 JD?**

Hiện tại là O(N): mỗi request → embed 1 CV + embed JD + score. Với 10,000 CVs:
- 10,000 embedding calls × ~200ms = ~33 phút (sequential) hoặc ~2-3 phút (parallel, nhưng tốn cost)
- 10,000 score calculations × ~1ms = ~10 giây (fine)

Bottleneck là embedding. Giải pháp: pre-index (embed tất cả CVs 1 lần khi upload, lưu vào vector DB) → khi có JD mới chỉ cần embed JD 1 lần → vector search O(log N) → rerank top-K bằng scorer.

---

**Q26. Sau vector search retrieve top-100 CV, bước rerank dùng gì?**

Dùng `calculate_score_with_rules()` từ `scorer.py`:

1. D1 (semantic): dùng stored embeddings từ index step (không cần embed lại)
2. D2 (skills), D3 (experience), D4 (education), D5 (keywords): pure Python, ~1ms mỗi pair
3. Business rules: must-have skill penalty + experience floor penalty

Rerank top-100 với scorer → lấy top-10 → chạy `evaluator.evaluate_cv_for_job()` cho top-10. LLM chỉ được gọi 10 lần thay vì 10,000 lần.

---

**Q27. Vector DB nào phù hợp cho bài toán này?**

| | pgvector | Qdrant |
|---|---|---|
| Infrastructure | Add extension vào PostgreSQL hiện có | Service riêng |
| Metadata filter | Có, qua WHERE clause SQL | Native, rất mạnh |
| Scale | Tốt đến ~100k vectors | Tốt đến hàng triệu vectors |
| ANN algorithm | IVFFlat / HNSW | HNSW |
| Phù hợp khi | MVP, đã có PostgreSQL | Scale thật sự |

Recommendation: **pgvector** cho MVP (zero new infra, SQL familiar), **Qdrant** nếu cần scale >100k CVs hoặc cần metadata filter phức tạp (filter theo skills + exp_years + location cùng lúc).

---

**Q28. Metadata filter trong vector search thay thế hay bổ sung cho semantic search?**

**Bổ sung, không thay thế.** Workflow tối ưu:

```
Metadata pre-filter: exp_years >= jd.min_experience_years AND location = "HCM"
        ↓
Vector search trong subset đã filter (nhanh hơn, chính xác hơn)
        ↓
Rerank với full scorer
```

Metadata filter loại bỏ candidates không đủ điều kiện cứng (hard requirements) trước khi vector search. Nếu search toàn bộ rồi mới filter → tốn compute cho candidates sẽ bị reject anyway. Metadata filter không thay thế được semantic search vì không capture "holistic fit".

---

## Evaluation & Quality

**Q29. Làm sao đo được hệ thống này có chính xác không?**

Ground truth lý tưởng là HR decisions từ hiring data thực tế (invite to interview / reject). Metrics:

- **Precision@K**: trong top-K candidates hệ thống recommend, bao nhiêu % HR đồng ý là phù hợp?
- **Recall@K**: trong số candidates HR chọn, bao nhiêu % nằm trong top-K của hệ thống?
- **NDCG**: đánh giá ranking quality

Thực tế hiện tại: hệ thống chưa có labeled dataset → không thể đo offline. Approach khả thi: collect HR feedback sau mỗi recommendation (thumbs up/down), accumulate 200-300 data points rồi backtest.

---

**Q30. HR nói "điểm 85 nhưng candidate này không phù hợp" — debug pipeline thế nào?**

Bước 1 — check dimension breakdown trong response:
```json
"scores": {"semantic": 72, "skills": 90, "experience": 85, "education": 100, "keywords": 60}
```

Bước 2 — check `penalty_reasons`: missing must-have skills có bị bỏ qua không?

Bước 3 — check D2 detail: `skill_details` list trong evaluator response → skill nào "matched" có thực sự relevant?

Bước 4 — check D1 raw cosine: có nằm trong calibration range [0.55, 0.90] không? Nếu cosine_raw = 0.56 (normalized thành D1=3%) thì semantic mismatch rõ

Bước 5 — check parser output: LLM có parse skills/experience đúng không? (có thể call `/parse` endpoint riêng để verify)

---

**Q31. Khi nào D1 (semantic) cao nhưng D2 (skills) thấp? Ý nghĩa gì?**

Xảy ra khi CV và JD cùng domain/field nhưng specific tech stack khác nhau. Ví dụ:

- CV: Python backend developer (FastAPI, PostgreSQL, Redis)
- JD: Java backend developer (Spring Boot, MySQL, Kafka)

→ D1 cao (~0.75): cả 2 đều "backend development", distributed systems, API design
→ D2 thấp (~0.20): Python ≠ Java, FastAPI ≠ Spring, Redis pub/sub ≠ Kafka

**Ý nghĩa cho HR**: candidate có nền tảng backend phù hợp, hiểu architecture concepts, nhưng cần upskill về Java/Spring stack. Đây là "possible_fit" cho role junior nhưng "weak_fit" cho senior role cần productive ngay.

---

**Q32. Bias nào có thể xuất hiện trong scoring?**

- **CV length bias**: CV dài hơn → nhiều keywords → D5 score cao hơn, dù cùng năng lực. Người viết CV chi tiết được lợi hơn người viết ngắn gọn
- **Language bias**: CV tiếng Anh → keyword matching tốt hơn (D5) + LLM parse chính xác hơn so với CV tiếng Việt
- **Alias coverage bias**: skills phổ biến (React, Python, AWS) có alias đầy đủ → match chính xác. Skills niche không có alias → normalize thành raw string → dễ miss
- **Experience calculation bias**: gap year, career break → tổng `total_exp_months` thấp hơn thực tế → D3 bị penalize
- **Seniority bias trong D6**: dùng keyword matching trong title ("senior", "lead") → candidate senior nhưng title là "Software Engineer" bị classify sai level

---

## Câu hỏi "bẫy"

**Q33. Cosine similarity của embedding đã đủ để matching CV-JD chưa, cần gì thêm D2-D5?**

Không đủ một mình. Vấn đề cốt lõi: embedding là **average** của toàn bộ content → các thông tin cụ thể bị dilute:

- CV dài 500 words với Python xuất hiện 2 lần → embedding mostly semantic về các chủ đề khác → D1 thấp dù Python relevant
- "Must-have: Kubernetes" → embedding không phân biệt được "biết Kubernetes" vs "nghe tên Kubernetes" — cần D2 explicit skill check
- Experience requirement (≥5 years) → embedding của "3 năm kinh nghiệm" và "7 năm kinh nghiệm" có thể rất gần nhau về semantic

D2-D5 là explicit guardrails cho các business requirements cụ thể mà semantic similarity không enforce được.

---

**Q34. Tại sao không fine-tune 1 model chuyên biệt cho CV matching thay vì dùng general LLM?**

- **Thiếu labeled data**: cần hàng nghìn cặp (CV, JD, HR_decision) để fine-tune có ý nghĩa — chưa có
- **Cost và complexity**: fine-tuning embedding model cần GPU infrastructure, hyperparameter tuning, evaluation pipeline riêng
- **MVP priority**: general LLM + structured prompt + rule-based scoring đã đủ tốt để validate product-market fit
- **Iteration speed**: thay đổi prompt nhanh hơn nhiều so với retrain model
- Fine-tune phù hợp **sau khi** có đủ production data và đã xác định được chính xác điểm yếu cụ thể của general model.

---

**Q35. Hệ thống này có thể bị "gaming" không — ứng viên cố tình nhồi keywords vào CV?**

Có thể bị game một phần, nhưng multi-dimension scoring giảm impact đáng kể:

- **D5 tăng**: keyword stuffing trực tiếp ảnh hưởng D5 (weight=0.05 — thấp nhất)
- **D2 tăng một phần**: nếu nhồi skill names → skill match tăng, nhưng category match không bị game vì dựa trên set overlap
- **D3 không bị game**: experience dựa trên dates (start/end), không thể fake
- **D1 khó game**: embedding capture holistic meaning, nhồi keywords không tăng semantic similarity nhiều nếu context không natural
- **Evaluator narrative**: LLM đọc structured facts → có thể detect inconsistency ("khai PostgreSQL nhưng không có project/role nào dùng DB → đáng ngờ")

So với pure keyword matching (dễ game 100%), hệ thống này resilient hơn đáng kể. Không phòng được hoàn toàn nhưng đủ tốt cho use case recruitment.

---

*Tất cả câu trả lời dựa trên code thực tế tại `app/services/` và `app/config.py`.*
