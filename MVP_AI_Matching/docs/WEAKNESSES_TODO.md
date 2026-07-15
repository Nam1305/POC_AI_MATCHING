# Danh sách điểm yếu hệ thống matching JD–CV (để fix dần)

> Tổng hợp từ rà soát toàn bộ pipeline: `parser.py` → `embedder.py` → `scorer.py` (5 chiều)
> + `evaluator.py` (narrative LLM), dữ liệu skill trong `skill_data.py` / `skill_implies.py`,
> endpoint `api/score.py`.
>
> Công thức hiện tại: `final_score = (D1·0.30 + D2·0.35 + D3·0.20 + D4·0.10 + D5·0.05) × 100`,
> rồi nhân `(1 − penalty)` cho must-have / kinh nghiệm thiếu.
>
> Đánh dấu `[x]` khi đã fix. Mỗi mục ghi: hiện trạng → vấn đề → hướng sửa → vị trí code.

---

## 🔴 Nghiêm trọng — ảnh hưởng trực tiếp độ chính xác

- [x] **W1. Hai nguồn sự thật mâu thuẫn: `final_score` vs `recommendation`.**
  - Hiện trạng: điểm số tính bằng Python (`scorer.py`), `recommendation` (`strong_fit`...) do LLM tự sinh trong narrative dựa trên quy tắc bằng chữ.
  - Vấn đề: penalty có thể đè điểm xuống 45 nhưng LLM vẫn ghi `possible_fit` (hoặc ngược lại) → HR nhận hai tín hiệu xung đột.
  - Hướng sửa đã chọn: **bỏ hẳn `recommendation`** thay vì suy nó từ `final_score` — không cần thêm 1 tầng nhãn nữa, HR đọc `final_score`/`scores` (đã là single source of truth) để tự đánh giá.
  - Đã fix: xoá field `recommendation` khỏi `CVJobEvaluation` (`app/schemas.py`); bỏ `VALID_RECOMMENDATIONS`/`_DEFAULT_RECOMMENDATION`, bỏ khối `RECOMMENDATION: ...` + quy tắc chọn nhãn khỏi `_NARRATIVE_PROMPT`, `_llm_narrative()` giờ trả thẳng string narrative (`app/services/evaluator.py`). Cập nhật `quick_test.py` (bỏ cột/màu recommendation, tô màu theo `final_score` thay thế) và docstring liên quan ở `app/api/score.py`, `app/api/evaluate.py`, `app/main.py`.
  - Đã xác nhận: scorer/`​/ai/score` vốn đã KHÔNG bắt buộc gọi LLM — `include_narrative` mặc định `false` (`app/api/score.py`), narrative LLM tách hẳn thành endpoint riêng `POST /ai/evaluate` (`app/api/evaluate.py`, `app/services/evaluator.py`); `/score` chỉ gọi LLM khi request set `include_narrative=true`.
  - Code: `app/schemas.py`, `app/services/evaluator.py`, `app/api/score.py`, `app/api/evaluate.py`, `quick_test.py`

- [ ] **W2. Taxonomy kỹ năng quá hẹp — nhiều mảng nghề bị "mù".**
  - Hiện trạng: `skill_data.py` chỉ phủ ~90 skill web/backend/ML.
  - Vấn đề: thiếu mobile (Flutter, React Native, Kotlin, Swift, iOS/Android), data engineering, QA/testing, security, game, embedded, Scala, Elixir... Skill ngoài bảng không có alias/implies/category → chỉ còn exact/fuzzy. D2 (35%) gần như vô dụng cho các JD đó.
  - Hướng sửa: mở rộng taxonomy theo domain; hoặc fallback semantic-similarity cho skill ngoài bảng.
  - Code: `app/services/skill_data.py`, `app/services/skill_implies.py`

- [ ] **W3. D1 Semantic hardcode calibration cho đúng 1 embedding provider.**
  - Hiện trạng: `normalize_cosine` kéo dãn `[0.55, 0.90] → [0,1]`, `cosine_min/max` cố định bất kể `EMBED_PROVIDER`.
  - Vấn đề: đổi sang `sentence_transformer` / OpenAI thì phân bố cosine khác hẳn → D1 lệch mà không cảnh báo.
  - Hướng sửa: calibrate `cosine_min/max` theo từng provider, hoặc chuẩn hóa/hiệu chuẩn động; ít nhất cảnh báo khi provider ≠ cấu hình calibrate.
  - Code: `app/services/scorer.py:257`, `app/config.py:44-45`

- [x] **W4. `total_exp_months` cộng dồn khoảng thời gian chồng lấn.**
  - Hiện trạng: `sum(e.months for e in work_experience)`.
  - Vấn đề: freelance song song full-time / job overlap bị đếm gấp đôi số năm → thổi phồng D3 và qua mặt penalty kinh nghiệm.
  - Hướng sửa: merge các interval (start,end) trước khi cộng tháng.
  - Đã fix: thêm `merge_month_intervals()` (`app/schemas.py:59-80`), dùng lại trong `ParsedCV.total_exp_months` (`app/schemas.py:356-372`) và trong tính `relevant_months` theo domain của `score_experience()` (`app/services/scorer.py:415-431`), vốn mắc cùng lỗi. Test: `tests/test_scorer.py` (`test_total_exp_months_merges_overlapping_jobs`, `test_total_exp_months_sums_non_overlapping_jobs`, `test_score_experience_overlapping_jobs_not_double_counted`).
  - Code: `app/schemas.py:332`

- [ ] **W5. Điểm là tổng tuyến tính, gần như không có "cổng chặn".**
  - Hiện trạng: cơ chế chặn duy nhất là penalty must-have, phụ thuộc `weight ≥ 3` do LLM gán.
  - Vấn đề: ứng viên sai lĩnh vực (D1 thấp) nhưng mạnh 4 chiều còn lại vẫn ra điểm cao; weight LLM nhiễu, không nhất quán giữa các lần parse.
  - Hướng sửa: thêm gating/floor theo D1 hoặc D2; ổn định hoá cách gán weight (rule-based hoặc chuẩn hoá).
  - Code: `app/services/scorer.py:655-708`, `app/services/parser.py:200`

## 🟠 Quan trọng

- [ ] **W6. Toàn bộ chất lượng phụ thuộc parse LLM, không xác định (non-deterministic).**
  - Vấn đề: cùng CV/JD parse 2 lần có thể ra skill/weight/OR-group khác nhau → điểm khác nhau; không có confidence, không kiểm tra ổn định.
  - Hướng sửa: giảm temperature khi parse, thêm kiểm tra ổn định / cache parse theo hash nội dung, log confidence.
  - Code: `app/services/parser.py`, `app/services/llm_client.py`

- [ ] **W7. Domain-token relevance trong D3 nhiễu.**
  - Hiện trạng: lấy token từ title/keywords, lọc `len > 3`.
  - Vấn đề: từ chung ("software", "developer", "engineer") khớp mọi CV dev → thổi phồng relevance; token ngắn quan trọng (`go`, `ml`, `ai`, `css`) bị loại.
  - Hướng sửa: dùng danh sách stopword nghề nghiệp; whitelist token kỹ thuật ngắn; hoặc match theo skill đã chuẩn hoá thay vì token thô.
  - Code: `app/services/scorer.py:348-362`

- [ ] **W8. Recency giả định list đã sort newest-first.**
  - Hiện trạng: `latest = work_experience[0]` nhưng thứ tự do LLM trả về.
  - Vấn đề: sai thứ tự → modifier recency (+0.10/−0.10) tính sai.
  - Hướng sửa: sort `work_experience` theo end-date giảm dần trước khi tính.
  - Code: `app/services/scorer.py:394-405`

- [ ] **W9. Fuzzy match SequenceMatcher 0.85 dễ dương tính giả trên token ngắn.**
  - Vấn đề: so ký tự thuần, không hiểu ngữ nghĩa — `spark`/`spring`, `sql`/`ssl` có nguy cơ khớp nhầm → full 0.9 credit.
  - Hướng sửa: nâng ngưỡng cho token ngắn, hoặc yêu cầu độ dài tối thiểu / prefix match; ưu tiên alias trước fuzzy.
  - Code: `app/services/scorer.py:60-64`

- [ ] **W10. IMPLIES là đồ thị do LLM sinh, chưa được kiểm.**
  - Vấn đề: cạnh sai ("X guarantees Y") cho "matched_implied" credit sai mà không ai kiểm; chỉ `MANUAL_IMPLIES` được neo cứng.
  - Hướng sửa: review thủ công đồ thị sinh ra; đối chiếu nguồn (Wikidata P277); thêm test cho các cạnh quan trọng.
  - Code: `app/services/skill_implies.py`, `scripts/generate_implies_llm.py`

- [ ] **W11. D5 Location phụ thuộc OSRM demo + Nominatim public, không cache.**
  - Vấn đề: server demo rate-limit/hay sập; geocode địa chỉ VN thiếu chính xác; fail → rơi về `0.5` hàng loạt; `T_max = 45/75 phút` hardcode.
  - Hướng sửa: cache geocode + route theo địa chỉ; cân nhắc self-host OSRM/Nominatim hoặc provider có key; tham số hoá `T_max`.
  - Code: `app/services/location_service.py`, `app/services/scorer.py:435-491`

- [ ] **W12. D4 không xét field-of-study.**
  - Hiện trạng: `other = 1 = high_school`; chỉ so level bằng cấp.
  - Vấn đề: PhD trái ngành = full credit; bằng đúng ngành và bằng lạ ngành không phân biệt.
  - Hướng sửa: thêm so khớp `major` với domain JD (bonus/penalty nhẹ).
  - Code: `app/schemas.py:71-74`, `app/services/scorer.py:417-425`

## 🟡 Hệ thống / phương pháp luận

- [ ] **W13. Trọng số không được kiểm chứng bằng dữ liệu thực + doc lệch code.**
  - Vấn đề: AHP chỉ là phán đoán chuyên gia, không có feedback loop từ kết quả tuyển thật; điểm 70 không map với xác suất phù hợp. `WEIGHTPROVED.md` vẫn mô tả 6 chiều cũ (D5 keywords, D6 role_fit) trong khi code đã là 5 chiều (D5 = location).
  - Hướng sửa: đồng bộ lại doc; thu thập ground-truth (hired/interviewed) để tinh chỉnh/calibrate trọng số.
  - Code: `docs/WEIGHTPROVED.md`, `app/config.py:47-51`

- [ ] **W14. Không xử lý thiên lệch / công bằng.**
  - Vấn đề: tên, giới tính, tuổi, trường "top" lọt vào embedding D1; location gián tiếp phân biệt theo khu vực sống.
  - Hướng sửa: loại trường nhạy cảm khỏi `build_embed_text`; audit fairness; cân nhắc ẩn danh khi embed.
  - Code: `app/schemas.py:353-393`

- [ ] **W15. Không có "độ sâu / level" của kỹ năng.**
  - Vấn đề: dùng React 1 lần ở bootcamp = 5 năm React; CV skill là `set` phẳng, không gắn recency/số năm dùng.
  - Hướng sửa: gắn skill với số năm/lần dùng gần nhất (từ tech_stack theo job có ngày tháng); trọng số theo độ thành thạo.
  - Code: `app/services/scorer.py:291-306`

- [ ] **W16. Seniority không vào điểm số, dễ bị title lạm phát.**
  - Vấn đề: chỉ dựa `current_role`; "Senior" ghi tràn lan qua mặt `_detect_level`; mismatch seniority chỉ hiện trong narrative (chỉ −0.05 over-qual vào điểm).
  - Hướng sửa: đưa seniority-match thành modifier/penalty trong D3; suy seniority từ số năm + level, không chỉ từ title.
  - Code: `app/services/evaluator.py:153-172`, `app/services/scorer.py:407-410`

- [ ] **W17. `min_experience_years` bị `ceil`.**
  - Vấn đề: "6 tháng" → 1 năm, "1.5 năm" → 2 → méo base ratio lẫn ngưỡng penalty 0.8×.
  - Hướng sửa: giữ float (không ceil) cho `min_experience_years`.
  - Code: `app/schemas.py:469-477`

---

## Thứ tự đề xuất fix (quick win → tác động cao)

1. **W1** — thống nhất recommendation với final_score.
2. **W4** — merge interval kinh nghiệm chồng lấn.
3. **W17** — bỏ `ceil` cho `min_experience_years`.
4. **W8** — sort work_experience theo ngày trước khi tính recency.
5. **W7** — lọc domain-token chung.
6. **W3** — calibrate cosine theo provider.
7. **W2** — mở rộng taxonomy skill.
8. **W11 / W13** — cache location + đồng bộ doc trọng số.
