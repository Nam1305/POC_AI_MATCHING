Bạn là một senior Python engineer, nhiệm vụ của bạn là refactor và nâng cấp module scoring CV–JD dưới đây.

Bối cảnh hệ thống:

- Có 5 dimension để tính độ khớp CV–JD:
  D1 Semantic : cosine_sim(cv_embedding, jd_embedding), normalized to 0–1  
  D2 Skills : weighted skill overlap (cv.skills ∪ tech_stack vs jd.required_skills)  
  D3 Experience : cv_total_years / jd_min_years, capped at 1.0  
  D4 Education : cv_degree_level / jd_required_degree_level, capped at 1.0  
  D5 Keywords : matched_keywords / total_jd_keywords (substring on raw text)

- final_score = Σ(Di × Wi) × 100
- Code hiện tại là pure Python + numpy, không được phép gọi LLM trong quá trình chạy scoring.

YÊU CẦU CHUNG:

1. Không thay đổi interface tổng thể:
   - Hàm `calculate_score(...)` vẫn tồn tại và trả về cùng cấu trúc:
     {
     "final_score": float,
     "scores": {
     "semantic": float (0-100),
     "skills": float (0-100),
     "experience": float (0-100),
     "education": float (0-100),
     "keywords": float (0-100),
     }
     }
   - Hàm `recalculate_final(scores, weights)` vẫn giữ signature và logic cơ bản.

2. Được phép:
   - Thêm hàm mới.
   - Thêm class helper.
   - Đổi implementation bên trong các hàm dimension (D2, D3, D5).
   - Thêm dimension mới (ví dụ: role_fit) nhưng phải OPTIONAL, không phá vỡ flow cũ.
   - Thêm logic “business rules” (must-have) ở một hàm calculate_score mở rộng, nhưng vẫn giữ hàm cũ nếu cần.

3. Không được:
   - Thêm dependency nặng (no external libs ngoài standard library + numpy).
   - Gọi LLM, API ngoài.
   - Thay đổi schema của ParsedCV, ParsedJD (giả định như code hiện tại).

---

## CẦN THỰC HIỆN CÁC CẢI TIẾN SAU (RẤT CỤ THỂ):

[A] CẢI TIẾN D2: SKILLS

Hiện tại:

- \_\_collect_cv_skills gom skills từ:
  - cv.skills
  - exp.tech_stack của từng work_experience
  - proj.tech_stack của từng project
- score_skills: match exact string, weight theo jd.required_skills.weight.

Vấn đề: so khớp quá thô, không xử lý alias (js/javascript, react/reactjs...), không fuzzy match, không partial/categorical match.

Yêu cầu cải tiến:

1. Tạo 1 class `SkillMatcher` (hoặc tương đương) với các khả năng:
   - Mapping alias → canonical skill, ví dụ:
     - "js", "javascript", "es6" → "javascript"
     - "react", "reactjs", "react.js" → "react"
     - "node", "nodejs", "node.js" → "nodejs"
     - "postgres", "postgresql", "psql" → "postgresql"
     - "mongo", "mongodb" → "mongodb"
     - "k8s", "kubernetes" → "kubernetes"
     - "aws", "amazon web services" → "aws"
       (Tự bổ sung thêm 1 số alias phổ biến cho web/backend/data/ML)

   - Nhóm skill theo category (đủ dùng, không cần quá rộng), ví dụ:
     - "frontend": {react, angular, vue, javascript, typescript, html, css}
     - "backend": {django, flask, fastapi, spring, express, nestjs}
     - "database": {mysql, postgresql, mongodb, redis}
     - "cloud": {aws, gcp, azure}
     - "ml_frameworks": {tensorflow, pytorch, keras, scikit-learn}

   - Có các method:
     - normalize_skill(skill: str) -> str
       Trả về canonical skill nếu nằm trong alias mapping, ngược lại trả về skill.lower().strip().

     - fuzzy_match(skill1: str, skill2: str, threshold: float = 0.85) -> bool
       Dùng difflib.SequenceMatcher (standard lib) để fuzzy match, trả về True nếu similarity ≥ threshold.

     - category_match(cv_skills: set[str], jd_skill: str) -> float
       - Nếu jd_skill (đã normalize) thuộc 1 category, và cv_skills có bất kỳ skill nào cùng category:
         → trả partial credit, khoảng 0.3–0.5 tùy số lượng skill cv có trong category.
       - Nếu không: 0.0

2. Viết lại hàm `score_skills` (hoặc tạo `score_skills_enhanced` và dùng nó trong calculate_score) theo logic:
   - Thu thập skills từ CV bằng `_collect_cv_skills` như cũ.
   - Normalize toàn bộ cv_skills bằng SkillMatcher.normalize_skill.
   - Duyệt từng `required_skill` trong `jd.required_skills`:
     - B1: Normalize jd_skill.
     - B2: Nếu exact match trong cv_skills → cộng full weight.
     - B3: Nếu không, thử fuzzy match với bất kỳ cv_skill:
       - Nếu matched → cộng 0.9 \* weight (90% credit).
     - B4: Nếu vẫn không, dùng category_match:
       - matched_weight += weight \* category_score.

   - Cuối cùng trả về matched_weight / total_weight như cũ.

[B] CẢI TIẾN D3: EXPERIENCE

Hiện tại:

- score_experience = cv_years / jd_min_years, capped 1.0.

Yêu cầu:

- Viết `score_experience_enhanced` (hoặc sửa hàm hiện tại) với các yếu tố:
  1. Base: vẫn là min(cv_total_years / jd_min_experience_years, 1.0).
  2. Thêm modifiers (bonus/penalty):
     - Bonus cho **relevant experience**:
       - Nếu ParsedJD có thuộc tính kiểu `required_domain` hay tương tự (nếu không có thì bỏ qua phần này).
       - Duyệt work_experience:
         - Nếu job_title hoặc description chứa các keyword domain từ jd (simple substring).
         - Cộng duration_months vào `relevant_months`.
       - relevant_years = relevant_months / 12.
       - relevance_ratio = min(relevant_years / jd_min_experience_years, 1.0)
       - Bonus tối đa khoảng +0.2 (20%).
     - Bonus/penalty cho **recency**:
       - Nếu exp mới nhất (giả định exp[0]) có end_date gần hiện tại:
         - Nếu < 3 tháng → +0.1
         - Nếu > 12 tháng → -0.1
           (Nếu schema không có end_date thì check tồn tại rồi mới xử lý; nếu không có thì bỏ qua phần này.)
     - Optional: nhỏ penalty cho over-qualification:
       - Nếu cv_total_years > 2 \* jd_min_experience_years → -0.05
  - final_score = base_score + sum(modifiers), clamp trong [0.0, 1.0].

[C] CẢI TIẾN D5: KEYWORDS

Hiện tại:

- score_keywords: đơn giản `kw.lower() in cv_raw_text.lower()`.

Yêu cầu:

- Viết `score_keywords_enhanced` với:
  1. Chuẩn hoá text CV:
     - lowercase
     - loại bỏ ký tự đặc biệt: re.sub(r'[^\w\s]', ' ', text_lower)
  2. Cho từng keyword trong jd.keywords:
     - Nếu exact substring trong text_cleaned → 1.0
     - Nếu match theo word boundary: dùng regex r'\b{kw}\b' → 1.0
     - Nếu keyword là cụm từ (nhiều từ):
       - Nếu tất cả các từ con xuất hiện đâu đó trong text → 0.7
     - Nếu không: 0.0
  3. Điểm = trung bình các keyword_scores (sum / len).

[D] THÊM DIMENSION ROLE FIT (TUỲ CHỌN)

- Thêm hàm `score_role_fit(cv: ParsedCV, jd: ParsedJD) -> float` (0–1) với logic:
  1. Nếu jd không có job_title → 1.0 (không có tiêu chí).
  2. Xác định “level” từ job_title: dùng các keyword:
     - 'intern': 0
     - 'junior': 1
     - 'developer', 'engineer': 2
     - 'senior': 3
     - 'lead', 'manager': 3
     - 'principal', 'architect': 4
       (Chỉ cần logic đơn giản: gặp từ nào thì gán level đó.)
  3. Xét một vài role gần nhất trong cv.work_experience (ví dụ 3 job gần nhất):
     - Tính title similarity giữa jd_title và exp.job_title bằng difflib.SequenceMatcher.
     - Tính level cho exp.job_title tương tự như trên.
     - level_diff = abs(jd_level - exp_level), level_score = max(0, 1 - 0.25 \* level_diff).
     - combined*score = title_similarity * 0.6 + level*score * 0.4.
  4. Trả về max(combined_score) trong các role gần nhất, hoặc 0.0 nếu không có kinh nghiệm.

- Không bắt buộc phải đưa role_fit vào final_score mặc định, nhưng nếu có thì:
  - Thêm weight "role_fit" nhỏ (ví dụ 0.05–0.10) và normalize lại tổng weight = 1.0.
  - Có thể tạo hàm weight tự động, xem phần [E].

[E] ADAPTIVE WEIGHTS (TUỲ CHỌN)

- Thêm class `AdaptiveWeights` với hàm:
  - `calculate_weights(jd: ParsedJD) -> dict[str, float]`
- Ý tưởng:
  - Xuất phát từ weights mặc định tương đương hiện tại (semantic ~0.25, skills ~0.30, experience ~0.20, education ~0.10, keywords ~0.05, role_fit ~0.10).
  - Điều chỉnh:
    - Nếu jd.required_skills nhiều ( > 5 ) → tăng weight "skills", giảm nhẹ "semantic" và "keywords".
    - Nếu jd.min_experience_years ≥ 5 → tăng weight "experience", giảm "education" và "keywords".
    - Nếu jd.required_degree_level ≥ 3 (Master+) → tăng "education", giảm "skills"/"keywords".
  - Sau khi chỉnh → normalize sum = 1.0.

- Không bắt buộc dùng AdaptiveWeights trong calculate_score mặc định, nhưng nên thiết kế sao cho có thể truyền vào weights đã tính từ đó.

[F] BUSINESS RULES (MUST-HAVE)

- Tạo một hàm mới, ví dụ:
  - `calculate_score_with_rules(...)` hoặc mở rộng calculate_score nếu bạn giữ được backward compatibility rõ ràng.
- Logic:
  1. Gọi calculate_score (bản enhanced) để lấy final_score ban đầu.
  2. Nếu enforce_must_have = True:
     - Must-have skills: định nghĩa tạm là những skill có weight = 3 trong jd.required_skills.
     - Nếu thiếu bất kỳ must-have skill nào (kể cả sau SkillMatcher normalize):
       - Mỗi skill thiếu áp penalty khoảng 0.2 (20%), tổng penalty cap ~0.7 (70%).
     - Nếu cv_years < 0.8 \* jd.min_experience_years → penalty ~0.3.
  3. final_score_new = final_score \* (1 - total_penalty).
  4. Trả về cả:
     - final_score (sau penalty)
     - scores per dimension
     - penalty_applied (float)
     - penalty_reasons (list hoặc dict đơn giản).

[G] TÍCH HỢP VỚI HÀM calculate_score HIỆN TẠI

- Bạn cần:
  - Giữ nguyên signature của calculate_score hiện tại (để không phá các call site cũ).
  - Bên trong, thay `score_skills`, `score_experience`, `score_keywords` bằng phiên bản enhanced.
  - Nếu thêm role_fit:
    - Có thể:
      - Hoặc chỉ tính thêm và trả về trong "scores" (ví dụ "role_fit") nhưng không cộng vào final_score mặc định (hoặc cộng với weight rất nhỏ).
      - Hoặc tạo tham số optional (vd: use_role_fit: bool = False) để bật/tắt.
- Giữ nguyên cách làm round(...) và cấu trúc dict trả về như code gốc.

---

YÊU CẦU KẾT QUẢ:

1. Trả về đoạn code Python hoàn chỉnh (có thể là 1 module), KHÔNG chỉ pseudo-code.
2. Code phải:
   - Chạy được ngay nếu copy-paste vào chỗ module scoring hiện tại (giả định schemas ParsedCV, ParsedJD giống như trước).
   - Không dùng thêm dependency ngoài standard library + numpy.
   - Có comment ngắn gọn cho các phần logic chính.
3. Không cần viết test, nhưng code nên đủ sạch để dễ test về sau.

Dưới đây đường dẫn của file bạn cần chỉnh sửa:
/MVP_AI_Matching/app/services/scorer.py
