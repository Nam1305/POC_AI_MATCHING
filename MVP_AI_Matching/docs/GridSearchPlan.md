# Grid Search Plan — Tìm trọng số W1-W5 cho 5-Dimension Scoring Engine

## 1. Bối cảnh

Khảo sát AHP đã chứng minh D1 (semantic) và D2 (skills) có tầm quan trọng cao hơn
D3 (experience), D4 (education), D5 (location). Mục tiêu tiếp theo: chạy grid
search để tìm ra bộ trọng số cụ thể W1-W5, nhất quán với thứ tự ưu tiên đó,
tối ưu theo dữ liệu thực tế thay vì chỉ dùng con số AHP thô.

Tài liệu này chỉ mô tả **kế hoạch**, chưa phải code. Script thực tế sẽ được
viết ở `MVP_AI_Matching/scripts/grid_search_weights.py` khi tập nhãn HR sẵn sàng.

## 2. Kiến trúc scoring hiện tại (đã xác nhận trong code)

- 5 dimension, mỗi hàm trả về giá trị `[0,1]`, định nghĩa trong
  [`app/services/scorer.py`](../app/services/scorer.py):
  - D1 semantic — `cosine_sim` + `normalize_cosine` (scorer.py:41-55)
  - D2 skills — `score_skills`, weighted skill overlap qua `SkillMatcher` (scorer.py:63-92)
  - D3 experience — `score_experience`, `min(cv_years / jd_min_years, 1.0)` (scorer.py:100-111)
  - D4 education — `score_education`, `min(cv_level/jd_level, 1.0)` (scorer.py:118-132)
  - D5 location — `score_location`, thời gian di chuyển × hệ số work-mode (scorer.py:144-200)
- Công thức tổng hợp: `final_score = 100 × Σ(Di × Wi)` — `calculate_score()`,
  scorer.py:336-376, cụ thể tại scorer.py:371.
- Default weights hiện tại — `app/config.py:47-51`:
  `semantic=0.30, skills=0.35, experience=0.20, education=0.10, location=0.05`,
  bắt buộc `Σ Wi = 1.0` (validator ở config.py:63-71).
- Danh sách tên dimension chuẩn: `SCORE_DIMENSIONS` — config.py:19.
- API override trọng số theo request: `ScoreRequest.weights` — `app/api/score.py:41-57`.

### Điểm nghẽn hiệu năng cần xử lý

`calculate_score()` tính lại cả 5 dimension (bao gồm cosine similarity, skill
matching) **mỗi lần gọi**, bất kể trọng số truyền vào là gì. Gọi thẳng hàm này
trong vòng lặp grid search (có thể hàng nghìn/triệu tổ hợp W) sẽ lãng phí rất
nhiều compute vì D1-D5 không đổi giữa các tổ hợp trọng số. → Cần tách riêng
phần "tính dimension" khỏi phần "áp trọng số" (xem Bước 3).

### Đã xác nhận: chưa có ground-truth dataset trong repo

Không tìm thấy dataset CV+JD+nhãn (điểm hoặc match/no-match do người chấm) ở
`tests/`, `scripts/`, hay các model Mongo bên `test-ai/` (chỉ lưu kết quả AI
tự sinh, không có nhãn con người). Đây là việc phải làm trước tiên.

## 3. Quyết định đã chốt

**Nguồn ground-truth: HR/chuyên gia tự chấm điểm thủ công** cho từng cặp
CV-JD (không dùng dữ liệu tuyển dụng lịch sử, không dùng LLM làm proxy).

## 4. Kế hoạch từng bước

### Bước 1 — Xây tập dữ liệu đánh giá có nhãn

Tạo `scripts/data/labeled_pairs.json`:

```json
[
  {
    "pair_id": "cv001_jd003",
    "cv_source": "path/to/cv001.pdf",
    "jd_source": "path/to/jd003.txt",
    "human_score": 78,
    "human_verdict": "match"
  }
]
```

Quy trình:
1. Chọn N cặp CV-JD, khuyến nghị **N ≥ 40-50** để chia k-fold còn ý nghĩa.
   Phủ đa dạng: có cặp rõ match, rõ không match, và borderline — để grid
   search có tín hiệu phân biệt thay vì toàn điểm gần giống nhau.
2. Chạy qua `/ai/parse-cv` + `/ai/parse-jd` **một lần duy nhất** để lấy
   `parsed_cv`, `parsed_jd`, `cv_embedding`, `jd_embedding` → cache vào
   `scripts/data/parsed_cache.json` theo `pair_id`. Tránh gọi lại
   LLM/embedding API mỗi lần chạy grid search sau này.
3. HR chấm điểm **độc lập**, không xem điểm AI sinh ra trước (tránh anchoring
   bias) → điền `human_score` (0-100).

### Bước 2 — Mã hoá kết quả AHP thành ràng buộc cho search space

Dùng thứ tự AHP (D1, D2 > D3, D4, D5) làm constraint lọc bớt tổ hợp vô lý về
chuyên môn khi sinh grid:

```
W_semantic ≥ W_experience
W_semantic ≥ W_education
W_semantic ≥ W_location
W_skills   ≥ W_experience
W_skills   ≥ W_education
W_skills   ≥ W_location
```

Vừa thu hẹp không gian tìm kiếm, vừa tránh grid search "học" ra một bộ trọng
số đi ngược lại bằng chứng khảo sát đã có.

### Bước 3 — Tách phần tính D1-D5 ra khỏi phần weighting

Viết hàm tái sử dụng đúng logic ở scorer.py:363-369:

```python
def compute_dims(parsed_cv, parsed_jd, cv_emb, jd_emb) -> dict[str, float]:
    return {
        "semantic":   normalize_cosine(cosine_sim(cv_emb, jd_emb)),
        "skills":     score_skills(parsed_cv, parsed_jd),
        "experience": score_experience(parsed_cv, parsed_jd),
        "education":  score_education(parsed_cv, parsed_jd),
        "location":   score_location(parsed_jd, parsed_cv),
    }
```

Chạy **một lần** cho mỗi cặp trong tập nhãn → ma trận numpy `dims_matrix`
shape `(N, 5)` + vector `labels` shape `(N,)`. Vòng lặp grid search sau đó
chỉ là `dims_matrix @ w * 100` — phép nhân ma trận cực rẻ, chạy hàng triệu tổ
hợp trong mili giây.

### Bước 4 — Sinh grid trọng số hợp lệ

Sinh tổ hợp `(W1..W5)` với bước nhảy cố định (vd 0.05), ràng buộc `Wi ≥ 0`
và `Σ Wi = 1` bằng đệ quy sinh trực tiếp (không dùng `itertools.product` rồi
lọc — tránh nổ tổ hợp), sau đó lọc tiếp theo constraint AHP ở Bước 2.

### Bước 5 — Metric mục tiêu

Nhãn là điểm liên tục 0-100 → dùng song song 2 metric khi đánh giá mỗi bộ
trọng số:
- **Spearman correlation** giữa `final_score` và `human_score` — metric
  chính, vì xếp hạng đúng thứ tự ứng viên quan trọng hơn khớp tuyệt đối
  từng con số.
- **MAE** làm metric phụ, tránh chọn bộ W chỉ đúng thứ hạng nhưng lệch điểm
  quá xa (gây hiểu lầm khi HR nhìn số 0-100 hiển thị trên UI).

### Bước 6 — Chống overfitting

Với dataset nhỏ (vài chục cặp), dùng **k-fold (k=5)** thay vì 1 lần
train/test split: tìm W tối ưu trên fold train, kiểm chứng trên fold
validation, lấy trung bình qua các fold để chọn bộ W ổn định thay vì khớp
ngẫu nhiên với vài mẫu.

### Bước 7 — Viết script

Đặt tại `scripts/grid_search_weights.py`, theo đúng convention offline
script hiện có (`scripts/generate_implies.py` — docstring mô tả flow, chạy
trực tiếp `python scripts/xxx.py`, không qua HTTP/LLM lúc match). Cấu trúc:

```
load_labeled_dataset(path)                    # đọc JSON từ Bước 1
compute_dims_matrix(dataset)                  # Bước 3 → (dims_matrix, labels)
generate_weight_grid(step, ahp_constraints)   # Bước 2 + 4
evaluate(dims_matrix, labels, w)              # Bước 5, trả về (spearman, mae)
k_fold_search(dims_matrix, labels, grid, k=5) # Bước 6, vòng lặp chính
```

In top-K bộ trọng số tốt nhất, so sánh với `default_weights` hiện tại
(config.py:47-51) và với vector AHP.

### Bước 8 — Đối chiếu & áp dụng

So kết quả grid search với AHP: nếu nhất quán (D1, D2 vẫn cao nhất) → cân
nhắc cập nhật `DEFAULT_WEIGHT_*` trong `.env`. Thêm 1 test nhỏ trong
`tests/test_scorer.py` kiểm tra `dims_matrix @ w` cho kết quả khớp với
`calculate_score()`, tránh 2 cách tính lệch nhau về sau.

## 5. Dependency

`numpy` + `itertools` (stdlib) đủ cho phần lõi, đã có sẵn trong
`requirements.txt`. Nếu muốn dùng `scipy.stats.spearmanr` hoặc `pandas` để
export CSV, cần thêm chính thức vào `requirements.txt` (hiện chỉ có trong
`.venv` cục bộ, chưa khai báo là dependency chính thức).

## 6. Việc cần làm tiếp theo

- [ ] HR/chuyên gia chấm điểm N ≥ 40-50 cặp CV-JD → `scripts/data/labeled_pairs.json`
- [ ] Viết `scripts/grid_search_weights.py` theo cấu trúc ở Bước 7
- [ ] Chạy grid search, đối chiếu kết quả với AHP + default weights
- [ ] Quyết định có cập nhật `DEFAULT_WEIGHT_*` trong `.env` hay không
