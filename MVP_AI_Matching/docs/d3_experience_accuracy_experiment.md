# Thực nghiệm: chứng minh tính chính xác của D3 (Experience Score) trên bộ dữ liệu 700 test case

Sinh tự động bởi `scripts/d3_experience_accuracy_experiment.py`. Đối tượng kiểm
chứng: `score_experience()` trong
[`app/services/scorer.py`](../app/services/scorer.py#L167-L190) (dùng
`_skill_experience_ratio` L133-164, `_skill_group_months` L117-130,
`_job_matches_group` L108-114) — xem đặc tả đầy đủ ở
[`docs/thesis_report.md` mục 4.6](thesis_report.md#46-experience-score-d3).

Gồm 3 thực nghiệm độc lập, trả lời 3 câu hỏi KHÁC NHAU — "đúng cài đặt",
"đúng thực tế", và "giới hạn thực tế" không phải cùng một thứ, và **kết quả
100% ở Phần A KHÔNG có nghĩa là D3 luôn đúng trên CV/JD thực** — xem Phần C.

> ⚠️ **Đọc trước khi trích dẫn con số "100%" ở Phần A:** con số này đo tính
> đúng của CÔNG THỨC (arithmetic/branching của `score_experience`), giả định
> kết quả so khớp skill (matched/missing) đã có sẵn và đúng. Phần lớn test
> case ở A.2/A.3 CỐ Ý dùng token so khớp chính xác (exact string) hoặc alias
> sạch đã có trong `skill_data.json`, để tách bạch khỏi câu hỏi "so khớp có
> đúng không" — đó là trách nhiệm của `SkillMatcher` (D2), không phải D3.
> Trên CV/JD thực (tên kỹ năng viết dưới dạng cụm mô tả, viết tắt lạ, không
> có trong KB...), việc so khớp **không đạt 100%** (độ phủ `skill_data.json`
> đo được 92.1% — xem `docs/d2_kb_coverage_experiment.md`; recall Layer 3
> fuzzy đo được 91.5% tại threshold 0.85 — xem
> `docs/d2_layer3_threshold_experiment.md`) — khi so khớp trượt, D3 âm thầm
> trả về 0 tháng cho skill đó dù ứng viên thực sự có kinh nghiệm. **Phần C**
> đo trực tiếp cơ chế này bằng chính pipeline `SkillMatcher` thật.

## PHẦN A — Đúng cài đặt (correctness) CỦA CÔNG THỨC, 700 test case

**Phương pháp:** dựng 700 tổ hợp CV/JD theo thiết kế factorial
(liệt kê tường minh, không lấy mẫu ngẫu nhiên — tái lập được y hệt mỗi lần
chạy vì mọi mốc thời gian dùng neo cố định `2020-01`, không
phụ thuộc `datetime.date.today()`), tính giá trị kỳ vọng bằng **cài đặt tham
chiếu độc lập** (thuật toán gộp khoảng thời gian viết lại từ đầu trên offset
tháng nguyên — không import `merge_month_intervals`/`parse_month` của app),
rồi so với output thật của `score_experience()` trên object `ParsedCV`/
`ParsedJD` dựng qua `app.schemas`. Chia 5 lớp trường hợp, phủ toàn bộ các
nhánh rẽ của công thức (fallback / theo chiều sâu / canonical hóa / OR-group
/ trọng số 0), cộng 5 property test kiểm tra bất biến.

### A.1 Fallback formula — JD không có required_skills (250 tổ hợp)

25 giá trị `cv_months` (0..144, bước 6) × 10 giá trị `jd_years` (0..9) —
kiểm tra nhánh fallback `min(cv_years/jd_min_years, 1.0)` và trường hợp biên
`jd_years=0 → 1.0`.

| cv_months | jd_years | Kỳ vọng | Thực tế | Khớp? |
| --- | --- | --- | --- | --- |
| 0 | 0 | 1.000 | 1.000 | ✅ |
| 0 | 1 | 0.000 | 0.000 | ✅ |
| 0 | 2 | 0.000 | 0.000 | ✅ |
| 0 | 3 | 0.000 | 0.000 | ✅ |
| 0 | 4 | 0.000 | 0.000 | ✅ |
| 0 | 5 | 0.000 | 0.000 | ✅ |
| 0 | 6 | 0.000 | 0.000 | ✅ |
| 0 | 7 | 0.000 | 0.000 | ✅ |
| 0 | 8 | 0.000 | 0.000 | ✅ |
| 0 | 9 | 0.000 | 0.000 | ✅ |
| 6 | 0 | 1.000 | 1.000 | ✅ |
| 6 | 1 | 0.500 | 0.500 | ✅ |
| 6 | 2 | 0.250 | 0.250 | ✅ |
| 6 | 3 | 0.167 | 0.167 | ✅ |
| 6 | 4 | 0.125 | 0.125 | ✅ |
| 6 | 5 | 0.100 | 0.100 | ✅ |
| 6 | 6 | 0.083 | 0.083 | ✅ |
| 6 | 7 | 0.071 | 0.071 | ✅ |
| 6 | 8 | 0.062 | 0.062 | ✅ |
| 6 | 9 | 0.056 | 0.056 | ✅ |
| 12 | 0 | 1.000 | 1.000 | ✅ |
| 12 | 1 | 1.000 | 1.000 | ✅ |
| 12 | 2 | 0.500 | 0.500 | ✅ |
| 12 | 3 | 0.333 | 0.333 | ✅ |
| 12 | 4 | 0.250 | 0.250 | ✅ |
| 12 | 5 | 0.200 | 0.200 | ✅ |
| 12 | 6 | 0.167 | 0.167 | ✅ |
| 12 | 7 | 0.143 | 0.143 | ✅ |
| 12 | 8 | 0.125 | 0.125 | ✅ |
| 12 | 9 | 0.111 | 0.111 | ✅ |
| 18 | 0 | 1.000 | 1.000 | ✅ |
| 18 | 1 | 1.000 | 1.000 | ✅ |
| 18 | 2 | 0.750 | 0.750 | ✅ |
| 18 | 3 | 0.500 | 0.500 | ✅ |
| 18 | 4 | 0.375 | 0.375 | ✅ |
| 18 | 5 | 0.300 | 0.300 | ✅ |
| 18 | 6 | 0.250 | 0.250 | ✅ |
| 18 | 7 | 0.214 | 0.214 | ✅ |
| 18 | 8 | 0.188 | 0.188 | ✅ |
| 18 | 9 | 0.167 | 0.167 | ✅ |
| 24 | 0 | 1.000 | 1.000 | ✅ |
| 24 | 1 | 1.000 | 1.000 | ✅ |
| 24 | 2 | 1.000 | 1.000 | ✅ |
| 24 | 3 | 0.667 | 0.667 | ✅ |
| 24 | 4 | 0.500 | 0.500 | ✅ |
| 24 | 5 | 0.400 | 0.400 | ✅ |
| 24 | 6 | 0.333 | 0.333 | ✅ |
| 24 | 7 | 0.286 | 0.286 | ✅ |
| 24 | 8 | 0.250 | 0.250 | ✅ |
| 24 | 9 | 0.222 | 0.222 | ✅ |
| 30 | 0 | 1.000 | 1.000 | ✅ |
| 30 | 1 | 1.000 | 1.000 | ✅ |
| 30 | 2 | 1.000 | 1.000 | ✅ |
| 30 | 3 | 0.833 | 0.833 | ✅ |
| 30 | 4 | 0.625 | 0.625 | ✅ |
| 30 | 5 | 0.500 | 0.500 | ✅ |
| 30 | 6 | 0.417 | 0.417 | ✅ |
| 30 | 7 | 0.357 | 0.357 | ✅ |
| 30 | 8 | 0.312 | 0.312 | ✅ |
| 30 | 9 | 0.278 | 0.278 | ✅ |
| 36 | 0 | 1.000 | 1.000 | ✅ |
| 36 | 1 | 1.000 | 1.000 | ✅ |
| 36 | 2 | 1.000 | 1.000 | ✅ |
| 36 | 3 | 1.000 | 1.000 | ✅ |
| 36 | 4 | 0.750 | 0.750 | ✅ |
| 36 | 5 | 0.600 | 0.600 | ✅ |
| 36 | 6 | 0.500 | 0.500 | ✅ |
| 36 | 7 | 0.429 | 0.429 | ✅ |
| 36 | 8 | 0.375 | 0.375 | ✅ |
| 36 | 9 | 0.333 | 0.333 | ✅ |
| 42 | 0 | 1.000 | 1.000 | ✅ |
| 42 | 1 | 1.000 | 1.000 | ✅ |
| 42 | 2 | 1.000 | 1.000 | ✅ |
| 42 | 3 | 1.000 | 1.000 | ✅ |
| 42 | 4 | 0.875 | 0.875 | ✅ |
| 42 | 5 | 0.700 | 0.700 | ✅ |
| 42 | 6 | 0.583 | 0.583 | ✅ |
| 42 | 7 | 0.500 | 0.500 | ✅ |
| 42 | 8 | 0.438 | 0.438 | ✅ |
| 42 | 9 | 0.389 | 0.389 | ✅ |
| 48 | 0 | 1.000 | 1.000 | ✅ |
| 48 | 1 | 1.000 | 1.000 | ✅ |
| 48 | 2 | 1.000 | 1.000 | ✅ |
| 48 | 3 | 1.000 | 1.000 | ✅ |
| 48 | 4 | 1.000 | 1.000 | ✅ |
| 48 | 5 | 0.800 | 0.800 | ✅ |
| 48 | 6 | 0.667 | 0.667 | ✅ |
| 48 | 7 | 0.571 | 0.571 | ✅ |
| 48 | 8 | 0.500 | 0.500 | ✅ |
| 48 | 9 | 0.444 | 0.444 | ✅ |
| 54 | 0 | 1.000 | 1.000 | ✅ |
| 54 | 1 | 1.000 | 1.000 | ✅ |
| 54 | 2 | 1.000 | 1.000 | ✅ |
| 54 | 3 | 1.000 | 1.000 | ✅ |
| 54 | 4 | 1.000 | 1.000 | ✅ |
| 54 | 5 | 0.900 | 0.900 | ✅ |
| 54 | 6 | 0.750 | 0.750 | ✅ |
| 54 | 7 | 0.643 | 0.643 | ✅ |
| 54 | 8 | 0.562 | 0.562 | ✅ |
| 54 | 9 | 0.500 | 0.500 | ✅ |
| 60 | 0 | 1.000 | 1.000 | ✅ |
| 60 | 1 | 1.000 | 1.000 | ✅ |
| 60 | 2 | 1.000 | 1.000 | ✅ |
| 60 | 3 | 1.000 | 1.000 | ✅ |
| 60 | 4 | 1.000 | 1.000 | ✅ |
| 60 | 5 | 1.000 | 1.000 | ✅ |
| 60 | 6 | 0.833 | 0.833 | ✅ |
| 60 | 7 | 0.714 | 0.714 | ✅ |
| 60 | 8 | 0.625 | 0.625 | ✅ |
| 60 | 9 | 0.556 | 0.556 | ✅ |
| 66 | 0 | 1.000 | 1.000 | ✅ |
| 66 | 1 | 1.000 | 1.000 | ✅ |
| 66 | 2 | 1.000 | 1.000 | ✅ |
| 66 | 3 | 1.000 | 1.000 | ✅ |
| 66 | 4 | 1.000 | 1.000 | ✅ |
| 66 | 5 | 1.000 | 1.000 | ✅ |
| 66 | 6 | 0.917 | 0.917 | ✅ |
| 66 | 7 | 0.786 | 0.786 | ✅ |
| 66 | 8 | 0.688 | 0.688 | ✅ |
| 66 | 9 | 0.611 | 0.611 | ✅ |
| 72 | 0 | 1.000 | 1.000 | ✅ |
| 72 | 1 | 1.000 | 1.000 | ✅ |
| 72 | 2 | 1.000 | 1.000 | ✅ |
| 72 | 3 | 1.000 | 1.000 | ✅ |
| 72 | 4 | 1.000 | 1.000 | ✅ |
| 72 | 5 | 1.000 | 1.000 | ✅ |
| 72 | 6 | 1.000 | 1.000 | ✅ |
| 72 | 7 | 0.857 | 0.857 | ✅ |
| 72 | 8 | 0.750 | 0.750 | ✅ |
| 72 | 9 | 0.667 | 0.667 | ✅ |
| 78 | 0 | 1.000 | 1.000 | ✅ |
| 78 | 1 | 1.000 | 1.000 | ✅ |
| 78 | 2 | 1.000 | 1.000 | ✅ |
| 78 | 3 | 1.000 | 1.000 | ✅ |
| 78 | 4 | 1.000 | 1.000 | ✅ |
| 78 | 5 | 1.000 | 1.000 | ✅ |
| 78 | 6 | 1.000 | 1.000 | ✅ |
| 78 | 7 | 0.929 | 0.929 | ✅ |
| 78 | 8 | 0.812 | 0.812 | ✅ |
| 78 | 9 | 0.722 | 0.722 | ✅ |
| 84 | 0 | 1.000 | 1.000 | ✅ |
| 84 | 1 | 1.000 | 1.000 | ✅ |
| 84 | 2 | 1.000 | 1.000 | ✅ |
| 84 | 3 | 1.000 | 1.000 | ✅ |
| 84 | 4 | 1.000 | 1.000 | ✅ |
| 84 | 5 | 1.000 | 1.000 | ✅ |
| 84 | 6 | 1.000 | 1.000 | ✅ |
| 84 | 7 | 1.000 | 1.000 | ✅ |
| 84 | 8 | 0.875 | 0.875 | ✅ |
| 84 | 9 | 0.778 | 0.778 | ✅ |
| 90 | 0 | 1.000 | 1.000 | ✅ |
| 90 | 1 | 1.000 | 1.000 | ✅ |
| 90 | 2 | 1.000 | 1.000 | ✅ |
| 90 | 3 | 1.000 | 1.000 | ✅ |
| 90 | 4 | 1.000 | 1.000 | ✅ |
| 90 | 5 | 1.000 | 1.000 | ✅ |
| 90 | 6 | 1.000 | 1.000 | ✅ |
| 90 | 7 | 1.000 | 1.000 | ✅ |
| 90 | 8 | 0.938 | 0.938 | ✅ |
| 90 | 9 | 0.833 | 0.833 | ✅ |
| 96 | 0 | 1.000 | 1.000 | ✅ |
| 96 | 1 | 1.000 | 1.000 | ✅ |
| 96 | 2 | 1.000 | 1.000 | ✅ |
| 96 | 3 | 1.000 | 1.000 | ✅ |
| 96 | 4 | 1.000 | 1.000 | ✅ |
| 96 | 5 | 1.000 | 1.000 | ✅ |
| 96 | 6 | 1.000 | 1.000 | ✅ |
| 96 | 7 | 1.000 | 1.000 | ✅ |
| 96 | 8 | 1.000 | 1.000 | ✅ |
| 96 | 9 | 0.889 | 0.889 | ✅ |
| 102 | 0 | 1.000 | 1.000 | ✅ |
| 102 | 1 | 1.000 | 1.000 | ✅ |
| 102 | 2 | 1.000 | 1.000 | ✅ |
| 102 | 3 | 1.000 | 1.000 | ✅ |
| 102 | 4 | 1.000 | 1.000 | ✅ |
| 102 | 5 | 1.000 | 1.000 | ✅ |
| 102 | 6 | 1.000 | 1.000 | ✅ |
| 102 | 7 | 1.000 | 1.000 | ✅ |
| 102 | 8 | 1.000 | 1.000 | ✅ |
| 102 | 9 | 0.944 | 0.944 | ✅ |
| 108 | 0 | 1.000 | 1.000 | ✅ |
| 108 | 1 | 1.000 | 1.000 | ✅ |
| 108 | 2 | 1.000 | 1.000 | ✅ |
| 108 | 3 | 1.000 | 1.000 | ✅ |
| 108 | 4 | 1.000 | 1.000 | ✅ |
| 108 | 5 | 1.000 | 1.000 | ✅ |
| 108 | 6 | 1.000 | 1.000 | ✅ |
| 108 | 7 | 1.000 | 1.000 | ✅ |
| 108 | 8 | 1.000 | 1.000 | ✅ |
| 108 | 9 | 1.000 | 1.000 | ✅ |
| 114 | 0 | 1.000 | 1.000 | ✅ |
| 114 | 1 | 1.000 | 1.000 | ✅ |
| 114 | 2 | 1.000 | 1.000 | ✅ |
| 114 | 3 | 1.000 | 1.000 | ✅ |
| 114 | 4 | 1.000 | 1.000 | ✅ |
| 114 | 5 | 1.000 | 1.000 | ✅ |
| 114 | 6 | 1.000 | 1.000 | ✅ |
| 114 | 7 | 1.000 | 1.000 | ✅ |
| 114 | 8 | 1.000 | 1.000 | ✅ |
| 114 | 9 | 1.000 | 1.000 | ✅ |
| 120 | 0 | 1.000 | 1.000 | ✅ |
| 120 | 1 | 1.000 | 1.000 | ✅ |
| 120 | 2 | 1.000 | 1.000 | ✅ |
| 120 | 3 | 1.000 | 1.000 | ✅ |
| 120 | 4 | 1.000 | 1.000 | ✅ |
| 120 | 5 | 1.000 | 1.000 | ✅ |
| 120 | 6 | 1.000 | 1.000 | ✅ |
| 120 | 7 | 1.000 | 1.000 | ✅ |
| 120 | 8 | 1.000 | 1.000 | ✅ |
| 120 | 9 | 1.000 | 1.000 | ✅ |
| 126 | 0 | 1.000 | 1.000 | ✅ |
| 126 | 1 | 1.000 | 1.000 | ✅ |
| 126 | 2 | 1.000 | 1.000 | ✅ |
| 126 | 3 | 1.000 | 1.000 | ✅ |
| 126 | 4 | 1.000 | 1.000 | ✅ |
| 126 | 5 | 1.000 | 1.000 | ✅ |
| 126 | 6 | 1.000 | 1.000 | ✅ |
| 126 | 7 | 1.000 | 1.000 | ✅ |
| 126 | 8 | 1.000 | 1.000 | ✅ |
| 126 | 9 | 1.000 | 1.000 | ✅ |
| 132 | 0 | 1.000 | 1.000 | ✅ |
| 132 | 1 | 1.000 | 1.000 | ✅ |
| 132 | 2 | 1.000 | 1.000 | ✅ |
| 132 | 3 | 1.000 | 1.000 | ✅ |
| 132 | 4 | 1.000 | 1.000 | ✅ |
| 132 | 5 | 1.000 | 1.000 | ✅ |
| 132 | 6 | 1.000 | 1.000 | ✅ |
| 132 | 7 | 1.000 | 1.000 | ✅ |
| 132 | 8 | 1.000 | 1.000 | ✅ |
| 132 | 9 | 1.000 | 1.000 | ✅ |
| 138 | 0 | 1.000 | 1.000 | ✅ |
| 138 | 1 | 1.000 | 1.000 | ✅ |
| 138 | 2 | 1.000 | 1.000 | ✅ |
| 138 | 3 | 1.000 | 1.000 | ✅ |
| 138 | 4 | 1.000 | 1.000 | ✅ |
| 138 | 5 | 1.000 | 1.000 | ✅ |
| 138 | 6 | 1.000 | 1.000 | ✅ |
| 138 | 7 | 1.000 | 1.000 | ✅ |
| 138 | 8 | 1.000 | 1.000 | ✅ |
| 138 | 9 | 1.000 | 1.000 | ✅ |
| 144 | 0 | 1.000 | 1.000 | ✅ |
| 144 | 1 | 1.000 | 1.000 | ✅ |
| 144 | 2 | 1.000 | 1.000 | ✅ |
| 144 | 3 | 1.000 | 1.000 | ✅ |
| 144 | 4 | 1.000 | 1.000 | ✅ |
| 144 | 5 | 1.000 | 1.000 | ✅ |
| 144 | 6 | 1.000 | 1.000 | ✅ |
| 144 | 7 | 1.000 | 1.000 | ✅ |
| 144 | 8 | 1.000 | 1.000 | ✅ |
| 144 | 9 | 1.000 | 1.000 | ✅ |

**Kết quả: 250/250 tổ hợp khớp tuyệt đối (100.0%).**

### A.2 Per-required-skill depth — thiết kế factorial đầy đủ (324 tổ hợp)

Đây là phần lõi của D3 (thiết kế mới, đo độ sâu theo từng required_skill).
6 trục biến thiên, tích Descartes đầy đủ (không rút gọn):

| Trục | Giá trị | Ý nghĩa |
| --- | --- | --- |
| `n_skills` | 1, 2, 3 | Số required_skill (OR-group) trong JD |
| `n_jobs` | 1, 2, 3 | Số job trong CV |
| `jd_years` | 1, 2, 4 | Số năm JD yêu cầu (áp dùng chung mọi skill) |
| `overlap` | disjoint, overlapping | Các job có khoảng thời gian chồng lấn hay không |
| `alt` | 0, 1 | required_skill có 1 alternative hay không (test OR-group) |
| `miss_pattern` | all_match, one_missing, flat_only | Skill đầu tiên: có job chứng minh / không job nào chứng minh / chỉ nằm rời rạc trong `cv.skills` |

3×3×3×2×2×3 = **324 tổ hợp**.

<details><summary>Xem đầy đủ 324 dòng</summary>

| n_skills | n_jobs | jd_years | overlap | alt | miss_pattern | Kỳ vọng | Thực tế | Khớp? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 1 | disjoint | 0 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 1 | 1 | disjoint | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 1 | disjoint | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 1 | disjoint | 1 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 1 | 1 | disjoint | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 1 | disjoint | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 1 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 1 | 1 | overlapping | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 1 | overlapping | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 1 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 1 | 1 | overlapping | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 1 | overlapping | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 2 | disjoint | 0 | all_match | 0.750 | 0.750 | ✅ |
| 1 | 1 | 2 | disjoint | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 2 | disjoint | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 2 | disjoint | 1 | all_match | 0.750 | 0.750 | ✅ |
| 1 | 1 | 2 | disjoint | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 2 | disjoint | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 2 | overlapping | 0 | all_match | 0.750 | 0.750 | ✅ |
| 1 | 1 | 2 | overlapping | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 2 | overlapping | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 2 | overlapping | 1 | all_match | 0.750 | 0.750 | ✅ |
| 1 | 1 | 2 | overlapping | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 2 | overlapping | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 4 | disjoint | 0 | all_match | 0.375 | 0.375 | ✅ |
| 1 | 1 | 4 | disjoint | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 4 | disjoint | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 4 | disjoint | 1 | all_match | 0.375 | 0.375 | ✅ |
| 1 | 1 | 4 | disjoint | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 4 | disjoint | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 4 | overlapping | 0 | all_match | 0.375 | 0.375 | ✅ |
| 1 | 1 | 4 | overlapping | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 4 | overlapping | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 1 | 4 | overlapping | 1 | all_match | 0.375 | 0.375 | ✅ |
| 1 | 1 | 4 | overlapping | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 1 | 4 | overlapping | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 1 | disjoint | 0 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 2 | 1 | disjoint | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 1 | disjoint | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 1 | disjoint | 1 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 2 | 1 | disjoint | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 1 | disjoint | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 1 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 2 | 1 | overlapping | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 1 | overlapping | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 1 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 2 | 1 | overlapping | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 1 | overlapping | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 2 | disjoint | 0 | all_match | 0.750 | 0.750 | ✅ |
| 1 | 2 | 2 | disjoint | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 2 | disjoint | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 2 | disjoint | 1 | all_match | 0.750 | 0.750 | ✅ |
| 1 | 2 | 2 | disjoint | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 2 | disjoint | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 2 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 2 | 2 | overlapping | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 2 | overlapping | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 2 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 2 | 2 | overlapping | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 2 | overlapping | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 4 | disjoint | 0 | all_match | 0.375 | 0.375 | ✅ |
| 1 | 2 | 4 | disjoint | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 4 | disjoint | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 4 | disjoint | 1 | all_match | 0.375 | 0.375 | ✅ |
| 1 | 2 | 4 | disjoint | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 4 | disjoint | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 4 | overlapping | 0 | all_match | 0.562 | 0.562 | ✅ |
| 1 | 2 | 4 | overlapping | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 4 | overlapping | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 2 | 4 | overlapping | 1 | all_match | 0.562 | 0.562 | ✅ |
| 1 | 2 | 4 | overlapping | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 2 | 4 | overlapping | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 1 | disjoint | 0 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 3 | 1 | disjoint | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 1 | disjoint | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 1 | disjoint | 1 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 3 | 1 | disjoint | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 1 | disjoint | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 1 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 3 | 1 | overlapping | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 1 | overlapping | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 1 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 3 | 1 | overlapping | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 1 | overlapping | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 2 | disjoint | 0 | all_match | 0.750 | 0.750 | ✅ |
| 1 | 3 | 2 | disjoint | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 2 | disjoint | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 2 | disjoint | 1 | all_match | 0.750 | 0.750 | ✅ |
| 1 | 3 | 2 | disjoint | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 2 | disjoint | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 2 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 3 | 2 | overlapping | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 2 | overlapping | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 2 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 1 | 3 | 2 | overlapping | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 2 | overlapping | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 4 | disjoint | 0 | all_match | 0.375 | 0.375 | ✅ |
| 1 | 3 | 4 | disjoint | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 4 | disjoint | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 4 | disjoint | 1 | all_match | 0.375 | 0.375 | ✅ |
| 1 | 3 | 4 | disjoint | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 4 | disjoint | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 4 | overlapping | 0 | all_match | 0.562 | 0.562 | ✅ |
| 1 | 3 | 4 | overlapping | 0 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 4 | overlapping | 0 | flat_only | 0.000 | 0.000 | ✅ |
| 1 | 3 | 4 | overlapping | 1 | all_match | 0.562 | 0.562 | ✅ |
| 1 | 3 | 4 | overlapping | 1 | one_missing | 0.000 | 0.000 | ✅ |
| 1 | 3 | 4 | overlapping | 1 | flat_only | 0.000 | 0.000 | ✅ |
| 2 | 1 | 1 | disjoint | 0 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 1 | 1 | disjoint | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 1 | 1 | disjoint | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 1 | 1 | disjoint | 1 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 1 | 1 | disjoint | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 1 | 1 | disjoint | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 1 | 1 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 1 | 1 | overlapping | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 1 | 1 | overlapping | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 1 | 1 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 1 | 1 | overlapping | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 1 | 1 | overlapping | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 1 | 2 | disjoint | 0 | all_match | 0.750 | 0.750 | ✅ |
| 2 | 1 | 2 | disjoint | 0 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 1 | 2 | disjoint | 0 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 1 | 2 | disjoint | 1 | all_match | 0.750 | 0.750 | ✅ |
| 2 | 1 | 2 | disjoint | 1 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 1 | 2 | disjoint | 1 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 1 | 2 | overlapping | 0 | all_match | 0.750 | 0.750 | ✅ |
| 2 | 1 | 2 | overlapping | 0 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 1 | 2 | overlapping | 0 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 1 | 2 | overlapping | 1 | all_match | 0.750 | 0.750 | ✅ |
| 2 | 1 | 2 | overlapping | 1 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 1 | 2 | overlapping | 1 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 1 | 4 | disjoint | 0 | all_match | 0.375 | 0.375 | ✅ |
| 2 | 1 | 4 | disjoint | 0 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 1 | 4 | disjoint | 0 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 1 | 4 | disjoint | 1 | all_match | 0.375 | 0.375 | ✅ |
| 2 | 1 | 4 | disjoint | 1 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 1 | 4 | disjoint | 1 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 1 | 4 | overlapping | 0 | all_match | 0.375 | 0.375 | ✅ |
| 2 | 1 | 4 | overlapping | 0 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 1 | 4 | overlapping | 0 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 1 | 4 | overlapping | 1 | all_match | 0.375 | 0.375 | ✅ |
| 2 | 1 | 4 | overlapping | 1 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 1 | 4 | overlapping | 1 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 2 | 1 | disjoint | 0 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 2 | 1 | disjoint | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 2 | 1 | disjoint | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 2 | 1 | disjoint | 1 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 2 | 1 | disjoint | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 2 | 1 | disjoint | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 2 | 1 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 2 | 1 | overlapping | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 2 | 1 | overlapping | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 2 | 1 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 2 | 1 | overlapping | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 2 | 1 | overlapping | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 2 | 2 | disjoint | 0 | all_match | 0.750 | 0.750 | ✅ |
| 2 | 2 | 2 | disjoint | 0 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 2 | 2 | disjoint | 0 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 2 | 2 | disjoint | 1 | all_match | 0.750 | 0.750 | ✅ |
| 2 | 2 | 2 | disjoint | 1 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 2 | 2 | disjoint | 1 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 2 | 2 | overlapping | 0 | all_match | 0.875 | 0.875 | ✅ |
| 2 | 2 | 2 | overlapping | 0 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 2 | 2 | overlapping | 0 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 2 | 2 | overlapping | 1 | all_match | 0.875 | 0.875 | ✅ |
| 2 | 2 | 2 | overlapping | 1 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 2 | 2 | overlapping | 1 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 2 | 4 | disjoint | 0 | all_match | 0.375 | 0.375 | ✅ |
| 2 | 2 | 4 | disjoint | 0 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 2 | 4 | disjoint | 0 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 2 | 4 | disjoint | 1 | all_match | 0.375 | 0.375 | ✅ |
| 2 | 2 | 4 | disjoint | 1 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 2 | 4 | disjoint | 1 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 2 | 4 | overlapping | 0 | all_match | 0.469 | 0.469 | ✅ |
| 2 | 2 | 4 | overlapping | 0 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 2 | 4 | overlapping | 0 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 2 | 4 | overlapping | 1 | all_match | 0.469 | 0.469 | ✅ |
| 2 | 2 | 4 | overlapping | 1 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 2 | 4 | overlapping | 1 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 3 | 1 | disjoint | 0 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 3 | 1 | disjoint | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 3 | 1 | disjoint | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 3 | 1 | disjoint | 1 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 3 | 1 | disjoint | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 3 | 1 | disjoint | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 3 | 1 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 3 | 1 | overlapping | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 3 | 1 | overlapping | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 3 | 1 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 2 | 3 | 1 | overlapping | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 2 | 3 | 1 | overlapping | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 2 | 3 | 2 | disjoint | 0 | all_match | 0.750 | 0.750 | ✅ |
| 2 | 3 | 2 | disjoint | 0 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 3 | 2 | disjoint | 0 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 3 | 2 | disjoint | 1 | all_match | 0.750 | 0.750 | ✅ |
| 2 | 3 | 2 | disjoint | 1 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 3 | 2 | disjoint | 1 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 3 | 2 | overlapping | 0 | all_match | 0.875 | 0.875 | ✅ |
| 2 | 3 | 2 | overlapping | 0 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 3 | 2 | overlapping | 0 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 3 | 2 | overlapping | 1 | all_match | 0.875 | 0.875 | ✅ |
| 2 | 3 | 2 | overlapping | 1 | one_missing | 0.375 | 0.375 | ✅ |
| 2 | 3 | 2 | overlapping | 1 | flat_only | 0.375 | 0.375 | ✅ |
| 2 | 3 | 4 | disjoint | 0 | all_match | 0.375 | 0.375 | ✅ |
| 2 | 3 | 4 | disjoint | 0 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 3 | 4 | disjoint | 0 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 3 | 4 | disjoint | 1 | all_match | 0.375 | 0.375 | ✅ |
| 2 | 3 | 4 | disjoint | 1 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 3 | 4 | disjoint | 1 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 3 | 4 | overlapping | 0 | all_match | 0.469 | 0.469 | ✅ |
| 2 | 3 | 4 | overlapping | 0 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 3 | 4 | overlapping | 0 | flat_only | 0.188 | 0.188 | ✅ |
| 2 | 3 | 4 | overlapping | 1 | all_match | 0.469 | 0.469 | ✅ |
| 2 | 3 | 4 | overlapping | 1 | one_missing | 0.188 | 0.188 | ✅ |
| 2 | 3 | 4 | overlapping | 1 | flat_only | 0.188 | 0.188 | ✅ |
| 3 | 1 | 1 | disjoint | 0 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 1 | 1 | disjoint | 0 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 1 | 1 | disjoint | 0 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 1 | 1 | disjoint | 1 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 1 | 1 | disjoint | 1 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 1 | 1 | disjoint | 1 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 1 | 1 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 1 | 1 | overlapping | 0 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 1 | 1 | overlapping | 0 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 1 | 1 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 1 | 1 | overlapping | 1 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 1 | 1 | overlapping | 1 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 1 | 2 | disjoint | 0 | all_match | 0.750 | 0.750 | ✅ |
| 3 | 1 | 2 | disjoint | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 1 | 2 | disjoint | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 1 | 2 | disjoint | 1 | all_match | 0.750 | 0.750 | ✅ |
| 3 | 1 | 2 | disjoint | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 1 | 2 | disjoint | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 1 | 2 | overlapping | 0 | all_match | 0.750 | 0.750 | ✅ |
| 3 | 1 | 2 | overlapping | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 1 | 2 | overlapping | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 1 | 2 | overlapping | 1 | all_match | 0.750 | 0.750 | ✅ |
| 3 | 1 | 2 | overlapping | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 1 | 2 | overlapping | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 1 | 4 | disjoint | 0 | all_match | 0.375 | 0.375 | ✅ |
| 3 | 1 | 4 | disjoint | 0 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 1 | 4 | disjoint | 0 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 1 | 4 | disjoint | 1 | all_match | 0.375 | 0.375 | ✅ |
| 3 | 1 | 4 | disjoint | 1 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 1 | 4 | disjoint | 1 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 1 | 4 | overlapping | 0 | all_match | 0.375 | 0.375 | ✅ |
| 3 | 1 | 4 | overlapping | 0 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 1 | 4 | overlapping | 0 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 1 | 4 | overlapping | 1 | all_match | 0.375 | 0.375 | ✅ |
| 3 | 1 | 4 | overlapping | 1 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 1 | 4 | overlapping | 1 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 2 | 1 | disjoint | 0 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 2 | 1 | disjoint | 0 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 2 | 1 | disjoint | 0 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 2 | 1 | disjoint | 1 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 2 | 1 | disjoint | 1 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 2 | 1 | disjoint | 1 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 2 | 1 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 2 | 1 | overlapping | 0 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 2 | 1 | overlapping | 0 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 2 | 1 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 2 | 1 | overlapping | 1 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 2 | 1 | overlapping | 1 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 2 | 2 | disjoint | 0 | all_match | 0.750 | 0.750 | ✅ |
| 3 | 2 | 2 | disjoint | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 2 | 2 | disjoint | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 2 | 2 | disjoint | 1 | all_match | 0.750 | 0.750 | ✅ |
| 3 | 2 | 2 | disjoint | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 2 | 2 | disjoint | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 2 | 2 | overlapping | 0 | all_match | 0.833 | 0.833 | ✅ |
| 3 | 2 | 2 | overlapping | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 2 | 2 | overlapping | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 2 | 2 | overlapping | 1 | all_match | 0.833 | 0.833 | ✅ |
| 3 | 2 | 2 | overlapping | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 2 | 2 | overlapping | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 2 | 4 | disjoint | 0 | all_match | 0.375 | 0.375 | ✅ |
| 3 | 2 | 4 | disjoint | 0 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 2 | 4 | disjoint | 0 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 2 | 4 | disjoint | 1 | all_match | 0.375 | 0.375 | ✅ |
| 3 | 2 | 4 | disjoint | 1 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 2 | 4 | disjoint | 1 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 2 | 4 | overlapping | 0 | all_match | 0.438 | 0.438 | ✅ |
| 3 | 2 | 4 | overlapping | 0 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 2 | 4 | overlapping | 0 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 2 | 4 | overlapping | 1 | all_match | 0.438 | 0.438 | ✅ |
| 3 | 2 | 4 | overlapping | 1 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 2 | 4 | overlapping | 1 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 3 | 1 | disjoint | 0 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 3 | 1 | disjoint | 0 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 3 | 1 | disjoint | 0 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 3 | 1 | disjoint | 1 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 3 | 1 | disjoint | 1 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 3 | 1 | disjoint | 1 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 3 | 1 | overlapping | 0 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 3 | 1 | overlapping | 0 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 3 | 1 | overlapping | 0 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 3 | 1 | overlapping | 1 | all_match | 1.000 | 1.000 | ✅ |
| 3 | 3 | 1 | overlapping | 1 | one_missing | 0.667 | 0.667 | ✅ |
| 3 | 3 | 1 | overlapping | 1 | flat_only | 0.667 | 0.667 | ✅ |
| 3 | 3 | 2 | disjoint | 0 | all_match | 0.750 | 0.750 | ✅ |
| 3 | 3 | 2 | disjoint | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 3 | 2 | disjoint | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 3 | 2 | disjoint | 1 | all_match | 0.750 | 0.750 | ✅ |
| 3 | 3 | 2 | disjoint | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 3 | 2 | disjoint | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 3 | 2 | overlapping | 0 | all_match | 0.833 | 0.833 | ✅ |
| 3 | 3 | 2 | overlapping | 0 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 3 | 2 | overlapping | 0 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 3 | 2 | overlapping | 1 | all_match | 0.833 | 0.833 | ✅ |
| 3 | 3 | 2 | overlapping | 1 | one_missing | 0.500 | 0.500 | ✅ |
| 3 | 3 | 2 | overlapping | 1 | flat_only | 0.500 | 0.500 | ✅ |
| 3 | 3 | 4 | disjoint | 0 | all_match | 0.375 | 0.375 | ✅ |
| 3 | 3 | 4 | disjoint | 0 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 3 | 4 | disjoint | 0 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 3 | 4 | disjoint | 1 | all_match | 0.375 | 0.375 | ✅ |
| 3 | 3 | 4 | disjoint | 1 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 3 | 4 | disjoint | 1 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 3 | 4 | overlapping | 0 | all_match | 0.438 | 0.438 | ✅ |
| 3 | 3 | 4 | overlapping | 0 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 3 | 4 | overlapping | 0 | flat_only | 0.250 | 0.250 | ✅ |
| 3 | 3 | 4 | overlapping | 1 | all_match | 0.438 | 0.438 | ✅ |
| 3 | 3 | 4 | overlapping | 1 | one_missing | 0.250 | 0.250 | ✅ |
| 3 | 3 | 4 | overlapping | 1 | flat_only | 0.250 | 0.250 | ✅ |

</details>

**Kết quả: 324/324 tổ hợp khớp tuyệt đối (100.0%).**

### A.3 Canonical hóa qua skill_data.json (Layer 1) — 100 tổ hợp

`_job_matches_group` dùng lại `SkillMatcher.evaluate_name` (đúng pipeline
D2) để so khớp tech_stack của job với required_skill — nghĩa là D3 phải
canonical hóa đúng khi JD và CV ghi tên kỹ năng KHÁC NHAU (alias vs
canonical, ví dụ JD ghi `nodejs`, CV ghi `node.js`). 10 cặp alias/canonical
chép nguyên văn từ `app/data/skill_data.json` × 5 mức `jd_years` × 2 chiều
(JD ghi alias/CV ghi canonical, và ngược lại) = 100 tổ hợp:

| Alias | Canonical | Bên nào ghi alias | jd_years | Kỳ vọng | Thực tế | Khớp? |
| --- | --- | --- | --- | --- | --- | --- |
| `nodejs` | `node.js` | JD=alias/CV=canonical | 1 | 1.000 | 1.000 | ✅ |
| `nodejs` | `node.js` | JD=canonical/CV=alias | 1 | 1.000 | 1.000 | ✅ |
| `nodejs` | `node.js` | JD=alias/CV=canonical | 2 | 1.000 | 1.000 | ✅ |
| `nodejs` | `node.js` | JD=canonical/CV=alias | 2 | 1.000 | 1.000 | ✅ |
| `nodejs` | `node.js` | JD=alias/CV=canonical | 3 | 0.667 | 0.667 | ✅ |
| `nodejs` | `node.js` | JD=canonical/CV=alias | 3 | 0.667 | 0.667 | ✅ |
| `nodejs` | `node.js` | JD=alias/CV=canonical | 4 | 0.500 | 0.500 | ✅ |
| `nodejs` | `node.js` | JD=canonical/CV=alias | 4 | 0.500 | 0.500 | ✅ |
| `nodejs` | `node.js` | JD=alias/CV=canonical | 5 | 0.400 | 0.400 | ✅ |
| `nodejs` | `node.js` | JD=canonical/CV=alias | 5 | 0.400 | 0.400 | ✅ |
| `golang` | `go` | JD=alias/CV=canonical | 1 | 1.000 | 1.000 | ✅ |
| `golang` | `go` | JD=canonical/CV=alias | 1 | 1.000 | 1.000 | ✅ |
| `golang` | `go` | JD=alias/CV=canonical | 2 | 1.000 | 1.000 | ✅ |
| `golang` | `go` | JD=canonical/CV=alias | 2 | 1.000 | 1.000 | ✅ |
| `golang` | `go` | JD=alias/CV=canonical | 3 | 0.667 | 0.667 | ✅ |
| `golang` | `go` | JD=canonical/CV=alias | 3 | 0.667 | 0.667 | ✅ |
| `golang` | `go` | JD=alias/CV=canonical | 4 | 0.500 | 0.500 | ✅ |
| `golang` | `go` | JD=canonical/CV=alias | 4 | 0.500 | 0.500 | ✅ |
| `golang` | `go` | JD=alias/CV=canonical | 5 | 0.400 | 0.400 | ✅ |
| `golang` | `go` | JD=canonical/CV=alias | 5 | 0.400 | 0.400 | ✅ |
| `postgres` | `postgresql` | JD=alias/CV=canonical | 1 | 1.000 | 1.000 | ✅ |
| `postgres` | `postgresql` | JD=canonical/CV=alias | 1 | 1.000 | 1.000 | ✅ |
| `postgres` | `postgresql` | JD=alias/CV=canonical | 2 | 1.000 | 1.000 | ✅ |
| `postgres` | `postgresql` | JD=canonical/CV=alias | 2 | 1.000 | 1.000 | ✅ |
| `postgres` | `postgresql` | JD=alias/CV=canonical | 3 | 0.667 | 0.667 | ✅ |
| `postgres` | `postgresql` | JD=canonical/CV=alias | 3 | 0.667 | 0.667 | ✅ |
| `postgres` | `postgresql` | JD=alias/CV=canonical | 4 | 0.500 | 0.500 | ✅ |
| `postgres` | `postgresql` | JD=canonical/CV=alias | 4 | 0.500 | 0.500 | ✅ |
| `postgres` | `postgresql` | JD=alias/CV=canonical | 5 | 0.400 | 0.400 | ✅ |
| `postgres` | `postgresql` | JD=canonical/CV=alias | 5 | 0.400 | 0.400 | ✅ |
| `vuejs` | `vue.js` | JD=alias/CV=canonical | 1 | 1.000 | 1.000 | ✅ |
| `vuejs` | `vue.js` | JD=canonical/CV=alias | 1 | 1.000 | 1.000 | ✅ |
| `vuejs` | `vue.js` | JD=alias/CV=canonical | 2 | 1.000 | 1.000 | ✅ |
| `vuejs` | `vue.js` | JD=canonical/CV=alias | 2 | 1.000 | 1.000 | ✅ |
| `vuejs` | `vue.js` | JD=alias/CV=canonical | 3 | 0.667 | 0.667 | ✅ |
| `vuejs` | `vue.js` | JD=canonical/CV=alias | 3 | 0.667 | 0.667 | ✅ |
| `vuejs` | `vue.js` | JD=alias/CV=canonical | 4 | 0.500 | 0.500 | ✅ |
| `vuejs` | `vue.js` | JD=canonical/CV=alias | 4 | 0.500 | 0.500 | ✅ |
| `vuejs` | `vue.js` | JD=alias/CV=canonical | 5 | 0.400 | 0.400 | ✅ |
| `vuejs` | `vue.js` | JD=canonical/CV=alias | 5 | 0.400 | 0.400 | ✅ |
| `k8s` | `kubernetes` | JD=alias/CV=canonical | 1 | 1.000 | 1.000 | ✅ |
| `k8s` | `kubernetes` | JD=canonical/CV=alias | 1 | 1.000 | 1.000 | ✅ |
| `k8s` | `kubernetes` | JD=alias/CV=canonical | 2 | 1.000 | 1.000 | ✅ |
| `k8s` | `kubernetes` | JD=canonical/CV=alias | 2 | 1.000 | 1.000 | ✅ |
| `k8s` | `kubernetes` | JD=alias/CV=canonical | 3 | 0.667 | 0.667 | ✅ |
| `k8s` | `kubernetes` | JD=canonical/CV=alias | 3 | 0.667 | 0.667 | ✅ |
| `k8s` | `kubernetes` | JD=alias/CV=canonical | 4 | 0.500 | 0.500 | ✅ |
| `k8s` | `kubernetes` | JD=canonical/CV=alias | 4 | 0.500 | 0.500 | ✅ |
| `k8s` | `kubernetes` | JD=alias/CV=canonical | 5 | 0.400 | 0.400 | ✅ |
| `k8s` | `kubernetes` | JD=canonical/CV=alias | 5 | 0.400 | 0.400 | ✅ |
| `mongo` | `mongodb` | JD=alias/CV=canonical | 1 | 1.000 | 1.000 | ✅ |
| `mongo` | `mongodb` | JD=canonical/CV=alias | 1 | 1.000 | 1.000 | ✅ |
| `mongo` | `mongodb` | JD=alias/CV=canonical | 2 | 1.000 | 1.000 | ✅ |
| `mongo` | `mongodb` | JD=canonical/CV=alias | 2 | 1.000 | 1.000 | ✅ |
| `mongo` | `mongodb` | JD=alias/CV=canonical | 3 | 0.667 | 0.667 | ✅ |
| `mongo` | `mongodb` | JD=canonical/CV=alias | 3 | 0.667 | 0.667 | ✅ |
| `mongo` | `mongodb` | JD=alias/CV=canonical | 4 | 0.500 | 0.500 | ✅ |
| `mongo` | `mongodb` | JD=canonical/CV=alias | 4 | 0.500 | 0.500 | ✅ |
| `mongo` | `mongodb` | JD=alias/CV=canonical | 5 | 0.400 | 0.400 | ✅ |
| `mongo` | `mongodb` | JD=canonical/CV=alias | 5 | 0.400 | 0.400 | ✅ |
| `csharp` | `c#` | JD=alias/CV=canonical | 1 | 1.000 | 1.000 | ✅ |
| `csharp` | `c#` | JD=canonical/CV=alias | 1 | 1.000 | 1.000 | ✅ |
| `csharp` | `c#` | JD=alias/CV=canonical | 2 | 1.000 | 1.000 | ✅ |
| `csharp` | `c#` | JD=canonical/CV=alias | 2 | 1.000 | 1.000 | ✅ |
| `csharp` | `c#` | JD=alias/CV=canonical | 3 | 0.667 | 0.667 | ✅ |
| `csharp` | `c#` | JD=canonical/CV=alias | 3 | 0.667 | 0.667 | ✅ |
| `csharp` | `c#` | JD=alias/CV=canonical | 4 | 0.500 | 0.500 | ✅ |
| `csharp` | `c#` | JD=canonical/CV=alias | 4 | 0.500 | 0.500 | ✅ |
| `csharp` | `c#` | JD=alias/CV=canonical | 5 | 0.400 | 0.400 | ✅ |
| `csharp` | `c#` | JD=canonical/CV=alias | 5 | 0.400 | 0.400 | ✅ |
| `python3` | `python-3.x` | JD=alias/CV=canonical | 1 | 1.000 | 1.000 | ✅ |
| `python3` | `python-3.x` | JD=canonical/CV=alias | 1 | 1.000 | 1.000 | ✅ |
| `python3` | `python-3.x` | JD=alias/CV=canonical | 2 | 1.000 | 1.000 | ✅ |
| `python3` | `python-3.x` | JD=canonical/CV=alias | 2 | 1.000 | 1.000 | ✅ |
| `python3` | `python-3.x` | JD=alias/CV=canonical | 3 | 0.667 | 0.667 | ✅ |
| `python3` | `python-3.x` | JD=canonical/CV=alias | 3 | 0.667 | 0.667 | ✅ |
| `python3` | `python-3.x` | JD=alias/CV=canonical | 4 | 0.500 | 0.500 | ✅ |
| `python3` | `python-3.x` | JD=canonical/CV=alias | 4 | 0.500 | 0.500 | ✅ |
| `python3` | `python-3.x` | JD=alias/CV=canonical | 5 | 0.400 | 0.400 | ✅ |
| `python3` | `python-3.x` | JD=canonical/CV=alias | 5 | 0.400 | 0.400 | ✅ |
| `dockerfile` | `docker` | JD=alias/CV=canonical | 1 | 1.000 | 1.000 | ✅ |
| `dockerfile` | `docker` | JD=canonical/CV=alias | 1 | 1.000 | 1.000 | ✅ |
| `dockerfile` | `docker` | JD=alias/CV=canonical | 2 | 1.000 | 1.000 | ✅ |
| `dockerfile` | `docker` | JD=canonical/CV=alias | 2 | 1.000 | 1.000 | ✅ |
| `dockerfile` | `docker` | JD=alias/CV=canonical | 3 | 0.667 | 0.667 | ✅ |
| `dockerfile` | `docker` | JD=canonical/CV=alias | 3 | 0.667 | 0.667 | ✅ |
| `dockerfile` | `docker` | JD=alias/CV=canonical | 4 | 0.500 | 0.500 | ✅ |
| `dockerfile` | `docker` | JD=canonical/CV=alias | 4 | 0.500 | 0.500 | ✅ |
| `dockerfile` | `docker` | JD=alias/CV=canonical | 5 | 0.400 | 0.400 | ✅ |
| `dockerfile` | `docker` | JD=canonical/CV=alias | 5 | 0.400 | 0.400 | ✅ |
| `java-core` | `java` | JD=alias/CV=canonical | 1 | 1.000 | 1.000 | ✅ |
| `java-core` | `java` | JD=canonical/CV=alias | 1 | 1.000 | 1.000 | ✅ |
| `java-core` | `java` | JD=alias/CV=canonical | 2 | 1.000 | 1.000 | ✅ |
| `java-core` | `java` | JD=canonical/CV=alias | 2 | 1.000 | 1.000 | ✅ |
| `java-core` | `java` | JD=alias/CV=canonical | 3 | 0.667 | 0.667 | ✅ |
| `java-core` | `java` | JD=canonical/CV=alias | 3 | 0.667 | 0.667 | ✅ |
| `java-core` | `java` | JD=alias/CV=canonical | 4 | 0.500 | 0.500 | ✅ |
| `java-core` | `java` | JD=canonical/CV=alias | 4 | 0.500 | 0.500 | ✅ |
| `java-core` | `java` | JD=alias/CV=canonical | 5 | 0.400 | 0.400 | ✅ |
| `java-core` | `java` | JD=canonical/CV=alias | 5 | 0.400 | 0.400 | ✅ |

**Kết quả: 100/100 tổ hợp khớp tuyệt đối (100.0%).**

### A.4 Edge case: kích thước OR-group và trọng số 0 (26 tổ hợp)

**A.4a — Kích thước OR-group** (24 tổ hợp): `alternatives` có 1-3
phần tử (tổng 2-4 tên trong group), khớp lần lượt tại từng vị trí (kể cả
"không khớp gì") × 2 mức `jd_years`:

| Số alternatives | Khớp tại vị trí | jd_years | Kỳ vọng | Thực tế | Khớp? |
| --- | --- | --- | --- | --- | --- |
| 2 | vị trí 0 | 1 | 1.000 | 1.000 | ✅ |
| 2 | vị trí 0 | 3 | 0.667 | 0.667 | ✅ |
| 2 | vị trí 1 | 1 | 1.000 | 1.000 | ✅ |
| 2 | vị trí 1 | 3 | 0.667 | 0.667 | ✅ |
| 2 | không khớp | 1 | 0.000 | 0.000 | ✅ |
| 2 | không khớp | 3 | 0.000 | 0.000 | ✅ |
| 3 | vị trí 0 | 1 | 1.000 | 1.000 | ✅ |
| 3 | vị trí 0 | 3 | 0.667 | 0.667 | ✅ |
| 3 | vị trí 1 | 1 | 1.000 | 1.000 | ✅ |
| 3 | vị trí 1 | 3 | 0.667 | 0.667 | ✅ |
| 3 | vị trí 2 | 1 | 1.000 | 1.000 | ✅ |
| 3 | vị trí 2 | 3 | 0.667 | 0.667 | ✅ |
| 3 | không khớp | 1 | 0.000 | 0.000 | ✅ |
| 3 | không khớp | 3 | 0.000 | 0.000 | ✅ |
| 4 | vị trí 0 | 1 | 1.000 | 1.000 | ✅ |
| 4 | vị trí 0 | 3 | 0.667 | 0.667 | ✅ |
| 4 | vị trí 1 | 1 | 1.000 | 1.000 | ✅ |
| 4 | vị trí 1 | 3 | 0.667 | 0.667 | ✅ |
| 4 | vị trí 2 | 1 | 1.000 | 1.000 | ✅ |
| 4 | vị trí 2 | 3 | 0.667 | 0.667 | ✅ |
| 4 | vị trí 3 | 1 | 1.000 | 1.000 | ✅ |
| 4 | vị trí 3 | 3 | 0.667 | 0.667 | ✅ |
| 4 | không khớp | 1 | 0.000 | 0.000 | ✅ |
| 4 | không khớp | 3 | 0.000 | 0.000 | ✅ |

**A.4b — Trọng số 0 (fallback)** (2 tổ hợp): mọi required_skill có
`weight=0` → `total_w <= 0` → `_skill_experience_ratio` trả `None` → sập về
công thức fallback cũ dùng TOÀN BỘ kinh nghiệm CV, không theo skill:

| Số required_skills (weight=0) | Kỳ vọng (fallback) | Thực tế | Khớp? |
| --- | --- | --- | --- |
| 1 | 0.500 | 0.500 | ✅ |
| 2 | 0.500 | 0.500 | ✅ |

**Kết quả A.4: 26/26 tổ hợp khớp tuyệt đối.**

### A.5 Property-based tests

| Property | Mô tả bất biến | Kết quả | Chi tiết |
| --- | --- | --- | --- |
| P1 — Cận trên (cap ở 1.0) | Số tháng làm skill vượt yêu cầu không được cộng điểm vượt 1.0 | ✅ PASS | OK — không vi phạm trong 33 tổ hợp (jd_years x months) |
| P2 — Đơn điệu không giảm theo số tháng | Số tháng làm skill tăng (0->60, jd_years cố định) -> D3 không giảm | ✅ PASS | OK — đơn điệu trên cả 3 giá trị jd_years |
| P3 — Bất biến với thứ tự required_skills[] | Xáo trộn thứ tự required_skills (6 hoán vị của 3 skill có weight khác nhau) không được đổi D3 | ✅ PASS | OK — 6 hoán vị đều cho cùng 1 điểm |
| P4 — Gộp khoảng chồng lấn không đếm trùng | 2 job overlap 9 tháng cùng 1 skill (18mo + 18mo, merged=27mo) -> D3 dùng merged span, không phải tổng thô | ✅ PASS | OK — D3=0.750 khớp merged-span=0.750 (khác với nếu cộng dồn ngây thơ=1.000) |
| P5 — cv.skills rời rạc không tính vào độ sâu | Skill chỉ khai trong cv.skills, không gắn job nào -> D3 cho skill đó = 0, bất kể tổng năm kinh nghiệm CV | ✅ PASS | OK — 0.0 trên cả 3 mức tổng kinh nghiệm (12/36/60 tháng) |

**Kết quả: 5/5 property PASS.**

### A.6 Kết luận Phần A

Trên tổng cộng **700 test case correctness** (A.1 fallback +
A.2 per-skill depth factorial + A.3 canonical alias + A.4 OR-group/trọng số
0) cộng 5 property test, `score_experience()` cài đặt **đúng
100.00%** đặc tả công thức: 700/700
tổ hợp khớp tuyệt đối, 5/5 property PASS — bao trùm cả
nhánh fallback (JD không có required_skills hoặc trọng số 0), nhánh chính
(độ sâu theo từng required_skill, kể cả OR-group/alternatives và gộp khoảng
chồng lấn), và tích hợp đúng với pipeline canonical hóa của D2
(`skill_data.json`).

**Đây là kết luận về CÔNG THỨC, không phải kết luận về độ chính xác của D3
trên CV/JD thực tế** — xem Phần C ngay dưới đây để biết giới hạn thực tế.

## PHẦN C — Giới hạn thực tế: D3 phụ thuộc vào so khớp skill (D2), chưa 100%

**Câu hỏi:** Phần A báo 700/700 = 100% —
điều đó có nghĩa D3 luôn cho điểm đúng trên CV/JD thực không? **Không.** D3
chỉ tính đúng số tháng của 1 required_skill NẾU `_job_matches_group()` (dùng
lại đúng pipeline so khớp của D2 — `SkillMatcher.evaluate_name`, 4 tầng
layer0-3) xác định đúng job nào "có" skill đó. Trên dữ liệu thật, tên kỹ
năng trong `tech_stack` không phải lúc nào cũng viết y hệt tên trong
`required_skills` của JD — và pipeline so khớp đó **chưa đạt 100%**, như
chính các thực nghiệm D2 khác trong repo này đã đo được.

### C.1 Corpus lớn (105 cặp × 3 mức jd_years = 315 test case), dựa trên phương pháp của `d2_kb_coverage_experiment.py`

**Khác gì với `docs/d2_kb_coverage_experiment.xlsx`?** D2's coverage experiment
đo "1 tên kỹ năng LLM trích ra có được `resolve_canonical()` nhận diện
không" — 1 phía. Ở đây đo đúng thứ D3 cần: "khi JD và CV mô tả CÙNG 1 kỹ
năng bằng 2 CÁCH VIẾT ĐỘC LẬP thật (JD và CV được 2 lượt LLM-parse khác
nhau tạo ra, hoàn toàn có thể chọn cách diễn đạt khác nhau), D3 có nhận ra
qua ĐÚNG pipeline `SkillMatcher.evaluate_name()` không?" — 2 phía, và chạy
qua **toàn bộ D3 thật** (`score_experience`), không chỉ hàm lookup canonical.

**Phương pháp:** viết tay 105 cặp (required_skill JD, cách
diễn đạt tech_stack CV hợp lý — tên đầy đủ, viết tắt lĩnh vực, sub-feature
của 1 framework, KHÔNG phải câu mô tả dài dòng) trải rộng 13
nhóm công nghệ, cùng tinh thần nhóm hóa với `d2_kb_coverage_experiment.py`,
rồi nhân với 3 mức `jd_years` (mở rộng bằng tham
số số học, cùng kỹ thuật đã dùng ở A.2/A.3) để có 315 test case. Mỗi
cặp chạy qua `SkillMatcher.evaluate_name()` THẬT (không phải cài đặt tham
chiếu) và `score_experience()` THẬT.

**Độ phủ theo nhóm:**

| Nhóm | Số case | So khớp được | Tỷ lệ khớp |
| --- | --- | --- | --- |
| Ngôn ngữ | 24 | 6 | 25.0% |
| Frontend | 30 | 6 | 20.0% |
| Backend | 30 | 0 | 0.0% |
| Mobile | 21 | 0 | 0.0% |
| Database | 30 | 3 | 10.0% |
| Cloud/DevOps | 36 | 6 | 16.7% |
| Data/ML | 30 | 3 | 10.0% |
| Testing/QA | 24 | 3 | 12.5% |
| Design/UI-UX | 18 | 0 | 0.0% |
| Security | 18 | 0 | 0.0% |
| Process | 18 | 0 | 0.0% |
| Office/ERP | 18 | 0 | 0.0% |
| Blockchain/IoT | 18 | 0 | 0.0% |

<details><summary>Xem đầy đủ 105 cặp (đại diện tại jd_years=2 — khớp/trượt không đổi theo jd_years, bảng 315 dòng đầy đủ nằm trong file Excel)</summary>

| Nhóm | required_skill (JD) | tech_stack thực tế (CV) | So khớp? | Layer |
| --- | --- | --- | --- | --- |
| Ngôn ngữ | `python` | `python scripting` | ❌ TRƯỢT | missing |
| Ngôn ngữ | `java` | `oop java` | ❌ TRƯỢT | missing |
| Ngôn ngữ | `javascript` | `vanilla javascript` | ✅ khớp | layer1 |
| Ngôn ngữ | `c++` | `modern c++ (c++17)` | ❌ TRƯỢT | missing |
| Ngôn ngữ | `golang` | `concurrent programming in go` | ❌ TRƯỢT | missing |
| Ngôn ngữ | `typescript` | `typescript type system` | ❌ TRƯỢT | missing |
| Ngôn ngữ | `kotlin` | `kotlin coroutines` | ✅ khớp | layer2 |
| Ngôn ngữ | `rust` | `systems programming in rust` | ❌ TRƯỢT | missing |
| Frontend | `react` | `react hooks` | ✅ khớp | layer2 |
| Frontend | `react` | `react context api` | ❌ TRƯỢT | missing |
| Frontend | `vue` | `vue composition api` | ✅ khớp | layer2 |
| Frontend | `angular` | `angular dependency injection` | ❌ TRƯỢT | missing |
| Frontend | `redux` | `state management with redux` | ❌ TRƯỢT | missing |
| Frontend | `webpack` | `module bundling with webpack` | ❌ TRƯỢT | missing |
| Frontend | `tailwind css` | `utility-first css styling` | ❌ TRƯỢT | missing |
| Frontend | `sass` | `css preprocessing with sass` | ❌ TRƯỢT | missing |
| Frontend | `next.js` | `server side rendering with next` | ❌ TRƯỢT | missing |
| Frontend | `jquery` | `dom manipulation with jquery` | ❌ TRƯỢT | missing |
| Backend | `node.js` | `server-side javascript with node` | ❌ TRƯỢT | missing |
| Backend | `express` | `restful api with express` | ❌ TRƯỢT | missing |
| Backend | `django` | `python web framework django` | ❌ TRƯỢT | missing |
| Backend | `spring boot` | `java microservices with spring` | ❌ TRƯỢT | missing |
| Backend | `laravel` | `php mvc framework laravel` | ❌ TRƯỢT | missing |
| Backend | `graphql` | `api query language graphql` | ❌ TRƯỢT | missing |
| Backend | `rest api` | `restful api design` | ❌ TRƯỢT | missing |
| Backend | `microservices` | `microservices architecture` | ❌ TRƯỢT | missing |
| Backend | `grpc` | `remote procedure calls with grpc` | ❌ TRƯỢT | missing |
| Backend | `websocket` | `real-time communication with websocket` | ❌ TRƯỢT | missing |
| Mobile | `react native` | `cross-platform mobile with react native` | ❌ TRƯỢT | missing |
| Mobile | `flutter` | `flutter widget development` | ❌ TRƯỢT | missing |
| Mobile | `android sdk` | `native android development` | ❌ TRƯỢT | missing |
| Mobile | `ios development` | `building apps for iphone and ipad` | ❌ TRƯỢT | missing |
| Mobile | `xamarin` | `cross platform apps with xamarin` | ❌ TRƯỢT | missing |
| Mobile | `ionic` | `hybrid mobile apps with ionic` | ❌ TRƯỢT | missing |
| Mobile | `swiftui` | `declarative ui for ios` | ❌ TRƯỢT | missing |
| Database | `postgresql` | `relational database management` | ❌ TRƯỢT | missing |
| Database | `mongodb` | `nosql document database` | ❌ TRƯỢT | missing |
| Database | `mysql` | `mysql database administration` | ❌ TRƯỢT | missing |
| Database | `redis` | `in-memory caching with redis` | ❌ TRƯỢT | missing |
| Database | `elasticsearch` | `full text search with elasticsearch` | ❌ TRƯỢT | missing |
| Database | `sql` | `structured query language` | ❌ TRƯỢT | missing |
| Database | `database design` | `designing normalized database schemas` | ❌ TRƯỢT | missing |
| Database | `orm` | `object relational mapping` | ✅ khớp | layer1 |
| Database | `dynamodb` | `aws nosql database` | ❌ TRƯỢT | missing |
| Database | `firebase` | `google's mobile backend platform` | ❌ TRƯỢT | missing |
| Cloud/DevOps | `aws` | `amazon web services` | ✅ khớp | layer1 |
| Cloud/DevOps | `kubernetes` | `eks` | ❌ TRƯỢT | missing |
| Cloud/DevOps | `kubernetes` | `container orchestration` | ❌ TRƯỢT | missing |
| Cloud/DevOps | `docker` | `containerization with docker` | ❌ TRƯỢT | missing |
| Cloud/DevOps | `terraform` | `infrastructure as code with terraform` | ❌ TRƯỢT | missing |
| Cloud/DevOps | `ci/cd` | `continuous integration and deployment` | ❌ TRƯỢT | missing |
| Cloud/DevOps | `jenkins` | `build automation with jenkins` | ❌ TRƯỢT | missing |
| Cloud/DevOps | `ansible` | `configuration management with ansible` | ❌ TRƯỢT | missing |
| Cloud/DevOps | `azure` | `microsoft cloud platform` | ❌ TRƯỢT | missing |
| Cloud/DevOps | `gcp` | `google cloud platform` | ✅ khớp | layer1 |
| Cloud/DevOps | `nginx` | `reverse proxy configuration with nginx` | ❌ TRƯỢT | missing |
| Cloud/DevOps | `linux` | `linux system administration` | ❌ TRƯỢT | missing |
| Data/ML | `pandas` | `data manipulation with pandas` | ❌ TRƯỢT | missing |
| Data/ML | `numpy` | `numerical computing with numpy` | ❌ TRƯỢT | missing |
| Data/ML | `tensorflow` | `deep learning with tensorflow` | ❌ TRƯỢT | missing |
| Data/ML | `pytorch` | `neural network training with pytorch` | ❌ TRƯỢT | missing |
| Data/ML | `scikit-learn` | `machine learning with sklearn` | ❌ TRƯỢT | missing |
| Data/ML | `power bi` | `business intelligence dashboards` | ❌ TRƯỢT | missing |
| Data/ML | `tableau` | `data visualization with tableau` | ❌ TRƯỢT | missing |
| Data/ML | `apache spark` | `big data processing with spark` | ❌ TRƯỢT | missing |
| Data/ML | `etl` | `extract transform load pipelines` | ❌ TRƯỢT | missing |
| Data/ML | `nlp` | `natural language processing` | ✅ khớp | layer1 |
| Testing/QA | `jest` | `unit testing with jest` | ❌ TRƯỢT | missing |
| Testing/QA | `selenium` | `automated browser testing` | ❌ TRƯỢT | missing |
| Testing/QA | `cypress` | `end to end testing with cypress` | ❌ TRƯỢT | missing |
| Testing/QA | `junit` | `java unit testing framework` | ❌ TRƯỢT | missing |
| Testing/QA | `postman` | `api testing with postman` | ❌ TRƯỢT | missing |
| Testing/QA | `test automation` | `writing automated test scripts` | ❌ TRƯỢT | missing |
| Testing/QA | `load testing` | `performance testing under load` | ❌ TRƯỢT | missing |
| Testing/QA | `tdd` | `test driven development` | ✅ khớp | layer1 |
| Design/UI-UX | `figma` | `figma prototyping` | ❌ TRƯỢT | missing |
| Design/UI-UX | `adobe xd` | `ui design with adobe xd` | ❌ TRƯỢT | missing |
| Design/UI-UX | `photoshop` | `adobe photoshop cc` | ❌ TRƯỢT | missing |
| Design/UI-UX | `ui/ux design` | `user interface and experience design` | ❌ TRƯỢT | missing |
| Design/UI-UX | `wireframing` | `creating low fidelity wireframes` | ❌ TRƯỢT | missing |
| Design/UI-UX | `design system` | `building reusable design systems` | ❌ TRƯỢT | missing |
| Security | `oauth` | `oauth 2.0 authentication` | ❌ TRƯỢT | missing |
| Security | `jwt` | `json web token authentication` | ❌ TRƯỢT | missing |
| Security | `penetration testing` | `ethical hacking and pentesting` | ❌ TRƯỢT | missing |
| Security | `owasp` | `web application security best practices` | ❌ TRƯỢT | missing |
| Security | `ssl/tls` | `secure socket layer encryption` | ❌ TRƯỢT | missing |
| Security | `firewall` | `network firewall configuration` | ❌ TRƯỢT | missing |
| Process | `agile` | `working in scrum methodology` | ❌ TRƯỢT | missing |
| Process | `scrum` | `sprint planning and scrum ceremonies` | ❌ TRƯỢT | missing |
| Process | `kanban` | `kanban board workflow management` | ❌ TRƯỢT | missing |
| Process | `git` | `git version control` | ❌ TRƯỢT | missing |
| Process | `jira` | `project tracking with jira` | ❌ TRƯỢT | missing |
| Process | `code review` | `peer reviewing pull requests` | ❌ TRƯỢT | missing |
| Office/ERP | `excel` | `advanced microsoft excel` | ❌ TRƯỢT | missing |
| Office/ERP | `sap` | `sap erp system` | ❌ TRƯỢT | missing |
| Office/ERP | `salesforce` | `crm management with salesforce` | ❌ TRƯỢT | missing |
| Office/ERP | `power point` | `creating presentations` | ❌ TRƯỢT | missing |
| Office/ERP | `google sheets` | `spreadsheet analysis with google sheets` | ❌ TRƯỢT | missing |
| Office/ERP | `erp` | `enterprise resource planning systems` | ❌ TRƯỢT | missing |
| Blockchain/IoT | `solidity` | `smart contract development` | ❌ TRƯỢT | missing |
| Blockchain/IoT | `ethereum` | `blockchain development on ethereum` | ❌ TRƯỢT | missing |
| Blockchain/IoT | `arduino` | `embedded programming with arduino` | ❌ TRƯỢT | missing |
| Blockchain/IoT | `raspberry pi` | `iot projects with raspberry pi` | ❌ TRƯỢT | missing |
| Blockchain/IoT | `mqtt` | `iot messaging protocol` | ❌ TRƯỢT | missing |
| Blockchain/IoT | `rtos` | `real time operating systems` | ❌ TRƯỢT | missing |

</details>

**Kết quả: 27/315 test case so khớp được (8.6%),
288/315 test case trượt (91.4%)** — với mỗi
cặp trượt, D3 cho skill đó tụt từ 0.833 (điểm nếu
so khớp đúng, trung bình trên các cặp trượt) xuống 0.0, dù ứng viên trong
data test THỰC SỰ có 24 tháng kinh nghiệm với skill đó.

**Lưu ý về phạm vi của C.1 (khác với A.1-A.4):** 105 cặp
gốc này viết tay từ tri thức miền — có thể mở rộng cỡ mẫu hơn nữa (như D2
làm với 1000 case), nhưng KHÔNG THỂ pad tự động như D2 (biến thể định dạng
`space<->dash`, đổi hoa/thường...) vì bản chất phép thử này là "2 cách viết
ĐỘC LẬP thật" — pad tự động 1 phía từ phía kia sẽ vô tình làm 2 phía LẠI phụ
thuộc nhau, phá vỡ chính tính độc lập cần đo. Đây vẫn KHÔNG phải mẫu ngẫu
nhiên đại diện tần suất chính xác trong production (cần dữ liệu CV/JD thật +
nhãn người gán để đo tần suất đó, ngoài phạm vi đồ án) — nhưng ở quy mô
315 test case / 105 cặp trải 13
nhóm công nghệ, đây là **số đo trực tiếp trên chính pipeline D3 dùng**, không
còn là minh họa nhỏ lẻ. **Con số 91.4% này CAO HƠN
NHIỀU** so với 8.0%/8.5% của D2 — 2 thực nghiệm đo 2 kịch bản khác nhau, KHÔNG
mâu thuẫn nhau: D2 đo "1 tên kỹ năng viết theo phong cách LLM thông thường
(Title Case, dấu chấm, viết tắt phổ biến) có nằm trong KB không" — phần lớn
biến thể đó ĐÃ được `to_stackoverflow_format()` xử lý; C.1 cố ý chọn các
cụm diễn đạt PHÂN KỲ NHIỀU hơn (đổi hẳn sang mô tả chức năng như "restful
api design" thay vì giữ nguyên tên riêng) — đại diện tình huống KHÓ hơn
"trung bình". Sự thật production nằm ở đâu đó GIỮA 2 con số này, tùy JD/CV
thực tế phân kỳ cách diễn đạt tới đâu — không đo được chính xác nếu không
có dữ liệu CV/JD thật (cùng hạn chế đã nêu).

### C.2 Rủi ro theo độ phức tạp JD (3 kịch bản, KHÔNG phải 1 số duy nhất)

JD càng liệt kê nhiều `required_skills`, xác suất **ít nhất 1** skill bị so
khớp trượt càng cao (giả định các skill so khớp độc lập nhau — đơn giản
hóa). 3 dòng dưới đây là 3 KỊCH BẢN khác nhau (không phải đo cùng 1 hiện
tượng nên KHÔNG được gộp/lấy trung bình): 2 dòng đầu ứng với kịch bản
"JD/CV dùng cách diễn đạt gần giống nhau" (số đo D2), dòng cuối ứng với kịch
bản "JD/CV diễn đạt phân kỳ nhiều" (số đo C.1 ở trên):

| Số required_skill trong JD (k) | P(≥1 trượt) — độ phủ KB (D2) | P(≥1 trượt) — recall Layer 3 (D2) | P(≥1 trượt) — đo trực tiếp C.1 |
| --- | --- | --- | --- |
| 1 | 7.9% | 8.5% | 91.4% |
| 2 | 15.2% | 16.3% | 99.3% |
| 3 | 21.9% | 23.4% | 99.9% |
| 4 | 28.0% | 29.9% | 100.0% |
| 5 | 33.7% | 35.9% | 100.0% |
| 6 | 39.0% | 41.3% | 100.0% |
| 7 | 43.8% | 46.3% | 100.0% |
| 8 | 48.2% | 50.9% | 100.0% |
| 9 | 52.3% | 55.0% | 100.0% |
| 10 | 56.1% | 58.9% | 100.0% |

Với JD điển hình yêu cầu 5 required_skill: nếu JD/CV diễn đạt gần giống
nhau, xác suất có ≥1 skill bị chấm sai khoảng **34–36%**
(kịch bản D2); nếu diễn đạt phân kỳ nhiều, xác suất này gần như
**chắc chắn xảy ra (100%)** (kịch
bản C.1). **Không nhỏ ở kịch bản nào**, và khoảng cách lớn giữa 2 kịch bản
tự nó là 1 phát hiện: độ chính xác thực tế của D3 nhạy cảm CAO với việc JD
và CV được viết/parse giống nhau tới đâu — 1 yếu tố ngoài tầm kiểm soát của
cả D2 lẫn D3.

### C.3 Kết luận Phần C

D3 kế thừa giới hạn của D2 (`SkillMatcher`): độ phủ `skill_data.json` 92.1%,
recall Layer 3 fuzzy 91.5% (2 thực nghiệm D2 khác đo sẵn), VÀ đo trực tiếp
thêm ở C.1 trên chính pipeline D3 dùng: chỉ 8.6%
trong 315 test case (viết tay, 105 cặp × 3
mức jd_years, trải 13 nhóm công nghệ) so
khớp đúng khi JD/CV dùng 2 cách diễn đạt độc lập cho cùng 1 skill. Khi so
khớp trượt, sai số của D3 không phải là "lệch nhẹ" mà là **tụt thẳng về 0**
cho skill đó (C.1) —
nghiêm trọng hơn nhiều so với các nguồn sai số khác đã đo ở Phần A/B của
chính D3. **Kết luận đúng cho toàn bộ thực nghiệm D3 này là:** công thức
D3 cài đặt đúng 100% ĐẶC TẢ CỦA NÓ (Phần A), thiết kế theo chiều sâu hợp lý
hơn hẳn công thức cũ nó thay thế (Phần B) — nhưng **độ chính xác thực tế
của D3 trên CV/JD thật bị chặn trên bởi độ chính xác so khớp skill của D2**,
hiện chưa đạt 100% (Phần C). Cải thiện D3 tiếp theo nên nhắm vào việc mở
rộng `skill_data.json`/`skill_implies.json` (D2) hơn là chỉnh công thức D3
(đã đúng đặc tả).

## PHẦN B — Đúng thực tế (validity): D3 mới so với D3 cũ

**Câu hỏi:** D3 được thiết kế lại (đo độ sâu theo từng required_skill thay
vì tỷ lệ số năm thô) — thiết kế mới có thực sự bám sát tín hiệu "kinh
nghiệm liên quan" tốt hơn thiết kế cũ hay không? Đây đúng là lý do D3 được
viết lại (xem docstring `score_experience`): "3 năm kinh nghiệm nhưng rải
rác 4 công ty, mỗi công ty 1 skill khác nhau không nên được tính là 3 năm
kinh nghiệm Java+React".

**Phương pháp:** cố định tổng kinh nghiệm CV = 3 năm (36
tháng), thay đổi **concentration** — tỷ lệ % thời gian đó thực sự dành cho
`target_skill` mà JD yêu cầu (phần còn lại ở 1 công ty khác, làm
`other_skill` không liên quan) — từ 0.0 đến 1.0, bước 0.1, × 3 mức
`jd_years`. Nhãn proxy = chính giá trị concentration (tỷ lệ thời gian sự
nghiệp thực sự dành cho kỹ năng JD cần — đúng tín hiệu 1 HR đọc CV sẽ nhìn
vào). So 2 công thức, cả 2 đều là code thật đang chạy trong `scorer.py`
(D3 cũ chính là nhánh fallback khi `required_skills=[]`, KHÔNG phải suy
diễn), với nhãn proxy đó bằng Spearman rank correlation và MAE.

### B.1 Toàn bộ điểm so sánh (33 điểm)

| jd_years | Concentration (nhãn proxy) | D3 mới (theo chiều sâu) | D3 cũ (tỷ lệ năm thô) | \|D3mới−proxy\| | \|D3cũ−proxy\| |
| --- | --- | --- | --- | --- | --- |
| 2 | 0.0 | 0.000 | 1.000 | 0.000 | 1.000 |
| 2 | 0.1 | 0.167 | 1.000 | 0.067 | 0.900 |
| 2 | 0.2 | 0.292 | 1.000 | 0.092 | 0.800 |
| 2 | 0.3 | 0.458 | 1.000 | 0.158 | 0.700 |
| 2 | 0.4 | 0.583 | 1.000 | 0.183 | 0.600 |
| 2 | 0.5 | 0.750 | 1.000 | 0.250 | 0.500 |
| 2 | 0.6 | 0.917 | 1.000 | 0.317 | 0.400 |
| 2 | 0.7 | 1.000 | 1.000 | 0.300 | 0.300 |
| 2 | 0.8 | 1.000 | 1.000 | 0.200 | 0.200 |
| 2 | 0.9 | 1.000 | 1.000 | 0.100 | 0.100 |
| 2 | 1.0 | 1.000 | 1.000 | 0.000 | 0.000 |
| 3 | 0.0 | 0.000 | 1.000 | 0.000 | 1.000 |
| 3 | 0.1 | 0.111 | 1.000 | 0.011 | 0.900 |
| 3 | 0.2 | 0.194 | 1.000 | 0.006 | 0.800 |
| 3 | 0.3 | 0.306 | 1.000 | 0.006 | 0.700 |
| 3 | 0.4 | 0.389 | 1.000 | 0.011 | 0.600 |
| 3 | 0.5 | 0.500 | 1.000 | 0.000 | 0.500 |
| 3 | 0.6 | 0.611 | 1.000 | 0.011 | 0.400 |
| 3 | 0.7 | 0.694 | 1.000 | 0.006 | 0.300 |
| 3 | 0.8 | 0.806 | 1.000 | 0.006 | 0.200 |
| 3 | 0.9 | 0.889 | 1.000 | 0.011 | 0.100 |
| 3 | 1.0 | 1.000 | 1.000 | 0.000 | 0.000 |
| 4 | 0.0 | 0.000 | 0.750 | 0.000 | 0.750 |
| 4 | 0.1 | 0.083 | 0.750 | 0.017 | 0.650 |
| 4 | 0.2 | 0.146 | 0.750 | 0.054 | 0.550 |
| 4 | 0.3 | 0.229 | 0.750 | 0.071 | 0.450 |
| 4 | 0.4 | 0.292 | 0.750 | 0.108 | 0.350 |
| 4 | 0.5 | 0.375 | 0.750 | 0.125 | 0.250 |
| 4 | 0.6 | 0.458 | 0.750 | 0.142 | 0.150 |
| 4 | 0.7 | 0.521 | 0.750 | 0.179 | 0.050 |
| 4 | 0.8 | 0.604 | 0.750 | 0.196 | 0.050 |
| 4 | 0.9 | 0.667 | 0.750 | 0.233 | 0.150 |
| 4 | 1.0 | 0.750 | 0.750 | 0.250 | 0.250 |

### B.2 Chỉ số tổng hợp

| Chỉ số | D3 mới (theo chiều sâu) | D3 cũ (tỷ lệ năm thô) | Ý nghĩa |
| --- | --- | --- | --- |
| Spearman ρ (vs nhãn proxy concentration) | 0.9159 | 0.0000 | D3 có sắp đúng thứ tự ứng viên theo mức độ liên quan thực sự không |
| MAE (vs nhãn proxy concentration) | 0.0942 | 0.4439 | Giá trị tuyệt đối lệch bao nhiêu trên thang 0-1 |

### B.3 Kết luận Phần B

D3 mới đạt Spearman ρ = 0.916, MAE = 0.094 so với nhãn
concentration — **bám sát tín hiệu "kinh nghiệm liên quan thực sự"** (lệch
chủ yếu ở vùng concentration cao/`jd_years` thấp, do D3 chặn trần ở 1.0 khi
số tháng làm skill đã vượt yêu cầu — đúng chủ ý thiết kế, không cộng thêm
điểm cho việc "thừa" kinh nghiệm). D3 cũ đạt ρ = 0.000, MAE =
0.444 — **hoàn toàn không phân biệt được** các mức concentration
khác nhau, vì D3 cũ chỉ nhìn tổng số năm kinh nghiệm (36
tháng, không đổi trong toàn bộ Phần B) mà không biết bao nhiêu trong số đó
thực sự liên quan tới skill JD cần — đúng vấn đề D3 mới được thiết kế lại để
giải quyết, và ở đây được **định lượng** thay vì chỉ nêu định tính.

**Hạn chế của thực nghiệm này:** nhãn proxy (concentration) là tín hiệu có
lý giải domain trực tiếp từ định nghĩa vấn đề D3 giải quyết, không phải dữ
liệu khảo sát HR thật (ngoài phạm vi thu thập được của đồ án) — cùng hạn
chế đã nêu ở các thực nghiệm D2/D4 khác trong `docs/`.

## Tổng kết

| | Kết quả |
| --- | --- |
| Đúng cài đặt CỦA CÔNG THỨC (Phần A) | 700/700 test case khớp tuyệt đối (100.00%) + 5/5 property PASS → **cài đặt đúng đặc tả trên toàn bộ các nhánh rẽ chính (fallback, theo chiều sâu, canonical hóa, OR-group, trọng số 0)** — GIẢ ĐỊNH so khớp skill đã đúng |
| Giới hạn thực tế — so khớp skill (Phần C, corpus 315 case dựa trên phương pháp D2) | 27/315 test case so khớp được (8.6%) qua pipeline D2 thật; JD 5 required_skill → 34–100% khả năng có ≥1 skill bị chấm sai (3 nguồn số liệu đối chiếu chéo) → **độ chính xác D3 trên CV/JD thật bị chặn trên bởi độ chính xác so khớp của D2, KHÔNG phải 100%** |
| Đúng thực tế — giá trị thiết kế (Phần B) | D3 mới: ρ=0.916, MAE=0.094 — D3 cũ: ρ=0.000, MAE=0.444 → **khi so khớp skill đúng, thiết kế theo chiều sâu bám sát tín hiệu kinh nghiệm liên quan tốt hơn hẳn công thức tỷ lệ năm thô mà nó thay thế** |

**Kết luận ngắn gọn:** D3 đúng về mặt công thức và là một cải tiến thiết kế
hợp lý so với bản cũ — nhưng "chính xác của D3" trong thực tế phụ thuộc trực
tiếp vào "chính xác so khớp skill của D2", hiện đo được ở mức 92.1% (độ phủ
KB, `d2_kb_coverage_experiment.md`), 91.5% (recall fuzzy,
`d2_layer3_threshold_experiment.md`), và 8.6%
(đo trực tiếp trên 315 test case JD-vs-CV ở Phần C.1 của chính thực
nghiệm này) — 3 nguồn độc lập, không nguồn nào đạt 100%.

---
*Tái tạo báo cáo này: `python scripts/d3_experience_accuracy_experiment.py`*
