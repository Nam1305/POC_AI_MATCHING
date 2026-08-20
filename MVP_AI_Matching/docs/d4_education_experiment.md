# Thực nghiệm: chứng minh tính chính xác của D4 (Education Score)

Sinh tự động bởi `scripts/d4_education_experiment.py`. Đối tượng kiểm chứng:
`score_education()` trong
[`app/services/scorer.py`](../app/services/scorer.py#L197-L211), công thức
$D_4 = \min(L_{cv}/L_{jd}, 1.0)$ — xem đặc tả đầy đủ ở
[`docs/thesis_report.md` mục 4.8](thesis_report.md#48-education-score-d4).

Gồm 2 thực nghiệm độc lập, trả lời 2 câu hỏi khác nhau — "đúng cài đặt" và
"đúng thực tế" không phải cùng một thứ, và một công thức có thể đúng cài đặt
100% nhưng vẫn là một xấp xỉ thô với thực tế (điều mà Phần B chỉ ra rõ).

## PHẦN A — Đúng cài đặt (correctness)

**Phương pháp:** liệt kê toàn bộ tổ hợp đầu vào có thể xảy ra trong hệ, tính
giá trị kỳ vọng bằng **cài đặt tham chiếu độc lập** viết lại từ đặc tả (không
import/gọi lại `score_education`), rồi so với output thật trên các object
`ParsedCV`/`ParsedJD` dựng qua `app.schemas`. Chia 3 lớp trường hợp — CV có
**1 bằng cấp** (A.1), CV có **nhiều bằng cấp cùng lúc** (A.2, kiểm tra kỹ
logic `max` trên `education[]`), và CV/JD **ghi bằng cấp bằng tiếng Việt**
(A.3, dùng đúng từ đồng nghĩa trong LLM prompt — sản phẩm xử lý CV/JD tiếng
Việt là chính) — cộng thêm 4 property test kiểm tra bất biến không phụ thuộc
giá trị cụ thể (A.4). Tổng cộng **366 test case correctness**, toàn
bộ đều exhaustive (liệt kê hết, không lấy mẫu).

### A.1 CV có 1 bằng cấp — ma trận đầy đủ (36 tổ hợp)

6 giá trị jd_level × 6 giá trị cv_level (kể cả 0 = "không có/không yêu cầu").

| jd_level (yêu cầu) | cv_level (CV) | Kỳ vọng (tham chiếu) | Thực tế (score_education) | Khớp? |
| --- | --- | --- | --- | --- |
| 0 `(none/không có)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| 1 `high_school (THPT)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| 2 `associate (Cao đẳng)` | 1 `high_school (THPT)` | 0.500 | 0.500 | ✅ |
| 2 `associate (Cao đẳng)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| 3 `bachelor (Đại học)` | 1 `high_school (THPT)` | 0.333 | 0.333 | ✅ |
| 3 `bachelor (Đại học)` | 2 `associate (Cao đẳng)` | 0.667 | 0.667 | ✅ |
| 3 `bachelor (Đại học)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| 4 `master (Thạc sĩ)` | 1 `high_school (THPT)` | 0.250 | 0.250 | ✅ |
| 4 `master (Thạc sĩ)` | 2 `associate (Cao đẳng)` | 0.500 | 0.500 | ✅ |
| 4 `master (Thạc sĩ)` | 3 `bachelor (Đại học)` | 0.750 | 0.750 | ✅ |
| 4 `master (Thạc sĩ)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| 5 `phd (Tiến sĩ)` | 1 `high_school (THPT)` | 0.200 | 0.200 | ✅ |
| 5 `phd (Tiến sĩ)` | 2 `associate (Cao đẳng)` | 0.400 | 0.400 | ✅ |
| 5 `phd (Tiến sĩ)` | 3 `bachelor (Đại học)` | 0.600 | 0.600 | ✅ |
| 5 `phd (Tiến sĩ)` | 4 `master (Thạc sĩ)` | 0.800 | 0.800 | ✅ |
| 5 `phd (Tiến sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |

**Kết quả: 36/36 tổ hợp khớp tuyệt đối với công thức
tham chiếu (100.0%).**

### A.2 CV có nhiều bằng cấp cùng lúc — mọi tập con khác rỗng (186 tổ hợp)

A.1 chỉ test CV có đúng 1 bằng, không chạm tới logic `highest_degree_level`
(lấy `max` trên toàn bộ `education[]`) khi CV khai nhiều bằng — trường hợp
thực tế phổ biến (vừa có bằng đại học vừa có bằng thạc sĩ, v.v.). Phần này
liệt kê **toàn bộ 2⁵−1 = 31 tập con khác rỗng** của 5 bậc bằng cấp
(high_school…phd) × 6 giá trị jd_level = 186 tổ hợp, mỗi CV giữ
đồng thời nhiều bằng, kỳ vọng = công thức tham chiếu áp trên **bằng cao nhất**
CV đang giữ.

| jd_level (yêu cầu) | Bằng cấp CV nắm giữ (nhiều bằng) | cv_level = max | Kỳ vọng | Thực tế | Khớp? |
| --- | --- | --- | --- | --- | --- |
| 0 `(none/không có)` | `high_school (THPT)` | 1 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)` | 1 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)` | 1 | 0.500 | 0.500 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)` | 1 | 0.333 | 0.333 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)` | 1 | 0.250 | 0.250 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)` | 1 | 0.200 | 0.200 | ✅ |
| 0 `(none/không có)` | `associate (Cao đẳng)` | 2 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `associate (Cao đẳng)` | 2 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `associate (Cao đẳng)` | 2 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `associate (Cao đẳng)` | 2 | 0.667 | 0.667 | ✅ |
| 4 `master (Thạc sĩ)` | `associate (Cao đẳng)` | 2 | 0.500 | 0.500 | ✅ |
| 5 `phd (Tiến sĩ)` | `associate (Cao đẳng)` | 2 | 0.400 | 0.400 | ✅ |
| 0 `(none/không có)` | `bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `bachelor (Đại học)` | 3 | 0.750 | 0.750 | ✅ |
| 5 `phd (Tiến sĩ)` | `bachelor (Đại học)` | 3 | 0.600 | 0.600 | ✅ |
| 0 `(none/không có)` | `master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `master (Thạc sĩ)` | 4 | 0.800 | 0.800 | ✅ |
| 0 `(none/không có)` | `phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+associate (Cao đẳng)` | 2 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+associate (Cao đẳng)` | 2 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+associate (Cao đẳng)` | 2 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+associate (Cao đẳng)` | 2 | 0.667 | 0.667 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+associate (Cao đẳng)` | 2 | 0.500 | 0.500 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+associate (Cao đẳng)` | 2 | 0.400 | 0.400 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+bachelor (Đại học)` | 3 | 0.750 | 0.750 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+bachelor (Đại học)` | 3 | 0.600 | 0.600 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+master (Thạc sĩ)` | 4 | 0.800 | 0.800 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `associate (Cao đẳng)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `associate (Cao đẳng)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `associate (Cao đẳng)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `associate (Cao đẳng)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `associate (Cao đẳng)+bachelor (Đại học)` | 3 | 0.750 | 0.750 | ✅ |
| 5 `phd (Tiến sĩ)` | `associate (Cao đẳng)+bachelor (Đại học)` | 3 | 0.600 | 0.600 | ✅ |
| 0 `(none/không có)` | `associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 0.800 | 0.800 | ✅ |
| 0 `(none/không có)` | `associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `bachelor (Đại học)+master (Thạc sĩ)` | 4 | 0.800 | 0.800 | ✅ |
| 0 `(none/không có)` | `bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)` | 3 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)` | 3 | 0.750 | 0.750 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)` | 3 | 0.600 | 0.600 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)` | 4 | 0.800 | 0.800 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+associate (Cao đẳng)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 0.800 | 0.800 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 0.800 | 0.800 | ✅ |
| 0 `(none/không có)` | `associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)` | 4 | 0.800 | 0.800 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+associate (Cao đẳng)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 0 `(none/không có)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 1 `high_school (THPT)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 2 `associate (Cao đẳng)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 3 `bachelor (Đại học)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 4 `master (Thạc sĩ)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |
| 5 `phd (Tiến sĩ)` | `high_school (THPT)+associate (Cao đẳng)+bachelor (Đại học)+master (Thạc sĩ)+phd (Tiến sĩ)` | 5 | 1.000 | 1.000 | ✅ |

**Kết quả: 186/186 tổ hợp khớp tuyệt đối
(100.0%).**

### A.3 CV/JD ghi bằng cấp bằng tiếng Việt (144 tổ hợp)

Sản phẩm xử lý CV/JD **tiếng Việt** là chính, nhưng A.1/A.2 chỉ dùng tên
`DegreeLevel` tiếng Anh (`bachelor`, `master`...). `score_education()` chỉ
nhận `DegreeLevel` đã canonical hóa — bước dịch text tiếng Việt
("Đại học", "Thạc sĩ", ...) sang `DegreeLevel` xảy ra ở LLM parser
([`app/services/parser.py`](../app/services/parser.py), khối `EDUCATION`),
**không** nằm trong `score_education()`, nên không thể unit-test bước dịch
đó mà không gọi LLM thật. Phần này test đúng phần kiểm định được: **cho
trước ánh xạ đúng mà prompt yêu cầu** (bảng dưới, chép nguyên văn từ
`parser.py` dòng 364-368), D4 có tính đúng khi `degree_raw` của CV/JD là
tiếng Việt hay không — tức xác nhận D4 hoạt động đúng trên dữ liệu tiếng
Việt thực tế, tách bạch với việc kiểm định bản thân bước dịch của LLM
(nằm ngoài phạm vi unit test offline).

**Bảng ánh xạ tiếng Việt/Anh → DegreeLevel** (nguyên văn từ LLM prompt):

| DegreeLevel (numeric) | Từ đồng nghĩa tiếng Việt/Anh |
| --- | --- |
| 1 `high_school (THPT)` | `THPT`, `Trung học phổ thông` |
| 2 `associate (Cao đẳng)` | `Trung cấp`, `Cao đẳng` |
| 3 `bachelor (Đại học)` | `Đại học`, `Cử nhân`, `Bachelor` |
| 4 `master (Thạc sĩ)` | `Thạc sĩ`, `Master` |
| 5 `phd (Tiến sĩ)` | `Tiến sĩ`, `PhD`, `Doctor` |

**144 tổ hợp kiểm tra** = 12 từ đồng nghĩa × 6 mức
còn lại × 2 chiều (CV ghi tiếng Việt / JD ghi tiếng Việt):

| Bên ghi tiếng Việt | Từ tiếng Việt/Anh trong CV/JD | → DegreeLevel (numeric) | Mức còn lại (jd_level/cv_level) | Kỳ vọng | Thực tế | Khớp? |
| --- | --- | --- | --- | --- | --- | --- |
| CV | `THPT` | 1 `high_school (THPT)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `THPT` | 1 `high_school (THPT)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `THPT` | 1 `high_school (THPT)` | 2 `associate (Cao đẳng)` | 0.500 | 0.500 | ✅ |
| CV | `THPT` | 1 `high_school (THPT)` | 3 `bachelor (Đại học)` | 0.333 | 0.333 | ✅ |
| CV | `THPT` | 1 `high_school (THPT)` | 4 `master (Thạc sĩ)` | 0.250 | 0.250 | ✅ |
| CV | `THPT` | 1 `high_school (THPT)` | 5 `phd (Tiến sĩ)` | 0.200 | 0.200 | ✅ |
| CV | `Trung học phổ thông` | 1 `high_school (THPT)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `Trung học phổ thông` | 1 `high_school (THPT)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `Trung học phổ thông` | 1 `high_school (THPT)` | 2 `associate (Cao đẳng)` | 0.500 | 0.500 | ✅ |
| CV | `Trung học phổ thông` | 1 `high_school (THPT)` | 3 `bachelor (Đại học)` | 0.333 | 0.333 | ✅ |
| CV | `Trung học phổ thông` | 1 `high_school (THPT)` | 4 `master (Thạc sĩ)` | 0.250 | 0.250 | ✅ |
| CV | `Trung học phổ thông` | 1 `high_school (THPT)` | 5 `phd (Tiến sĩ)` | 0.200 | 0.200 | ✅ |
| CV | `Trung cấp` | 2 `associate (Cao đẳng)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `Trung cấp` | 2 `associate (Cao đẳng)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `Trung cấp` | 2 `associate (Cao đẳng)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| CV | `Trung cấp` | 2 `associate (Cao đẳng)` | 3 `bachelor (Đại học)` | 0.667 | 0.667 | ✅ |
| CV | `Trung cấp` | 2 `associate (Cao đẳng)` | 4 `master (Thạc sĩ)` | 0.500 | 0.500 | ✅ |
| CV | `Trung cấp` | 2 `associate (Cao đẳng)` | 5 `phd (Tiến sĩ)` | 0.400 | 0.400 | ✅ |
| CV | `Cao đẳng` | 2 `associate (Cao đẳng)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `Cao đẳng` | 2 `associate (Cao đẳng)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `Cao đẳng` | 2 `associate (Cao đẳng)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| CV | `Cao đẳng` | 2 `associate (Cao đẳng)` | 3 `bachelor (Đại học)` | 0.667 | 0.667 | ✅ |
| CV | `Cao đẳng` | 2 `associate (Cao đẳng)` | 4 `master (Thạc sĩ)` | 0.500 | 0.500 | ✅ |
| CV | `Cao đẳng` | 2 `associate (Cao đẳng)` | 5 `phd (Tiến sĩ)` | 0.400 | 0.400 | ✅ |
| CV | `Đại học` | 3 `bachelor (Đại học)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `Đại học` | 3 `bachelor (Đại học)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `Đại học` | 3 `bachelor (Đại học)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| CV | `Đại học` | 3 `bachelor (Đại học)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| CV | `Đại học` | 3 `bachelor (Đại học)` | 4 `master (Thạc sĩ)` | 0.750 | 0.750 | ✅ |
| CV | `Đại học` | 3 `bachelor (Đại học)` | 5 `phd (Tiến sĩ)` | 0.600 | 0.600 | ✅ |
| CV | `Cử nhân` | 3 `bachelor (Đại học)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `Cử nhân` | 3 `bachelor (Đại học)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `Cử nhân` | 3 `bachelor (Đại học)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| CV | `Cử nhân` | 3 `bachelor (Đại học)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| CV | `Cử nhân` | 3 `bachelor (Đại học)` | 4 `master (Thạc sĩ)` | 0.750 | 0.750 | ✅ |
| CV | `Cử nhân` | 3 `bachelor (Đại học)` | 5 `phd (Tiến sĩ)` | 0.600 | 0.600 | ✅ |
| CV | `Bachelor` | 3 `bachelor (Đại học)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `Bachelor` | 3 `bachelor (Đại học)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `Bachelor` | 3 `bachelor (Đại học)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| CV | `Bachelor` | 3 `bachelor (Đại học)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| CV | `Bachelor` | 3 `bachelor (Đại học)` | 4 `master (Thạc sĩ)` | 0.750 | 0.750 | ✅ |
| CV | `Bachelor` | 3 `bachelor (Đại học)` | 5 `phd (Tiến sĩ)` | 0.600 | 0.600 | ✅ |
| CV | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| CV | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| CV | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| CV | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 5 `phd (Tiến sĩ)` | 0.800 | 0.800 | ✅ |
| CV | `Master` | 4 `master (Thạc sĩ)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `Master` | 4 `master (Thạc sĩ)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `Master` | 4 `master (Thạc sĩ)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| CV | `Master` | 4 `master (Thạc sĩ)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| CV | `Master` | 4 `master (Thạc sĩ)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| CV | `Master` | 4 `master (Thạc sĩ)` | 5 `phd (Tiến sĩ)` | 0.800 | 0.800 | ✅ |
| CV | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| CV | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| CV | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| CV | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| CV | `PhD` | 5 `phd (Tiến sĩ)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `PhD` | 5 `phd (Tiến sĩ)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `PhD` | 5 `phd (Tiến sĩ)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| CV | `PhD` | 5 `phd (Tiến sĩ)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| CV | `PhD` | 5 `phd (Tiến sĩ)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| CV | `PhD` | 5 `phd (Tiến sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| CV | `Doctor` | 5 `phd (Tiến sĩ)` | 0 `(none/không có)` | 1.000 | 1.000 | ✅ |
| CV | `Doctor` | 5 `phd (Tiến sĩ)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| CV | `Doctor` | 5 `phd (Tiến sĩ)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| CV | `Doctor` | 5 `phd (Tiến sĩ)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| CV | `Doctor` | 5 `phd (Tiến sĩ)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| CV | `Doctor` | 5 `phd (Tiến sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `THPT` | 1 `high_school (THPT)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `THPT` | 1 `high_school (THPT)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| JD | `THPT` | 1 `high_school (THPT)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| JD | `THPT` | 1 `high_school (THPT)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| JD | `THPT` | 1 `high_school (THPT)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `THPT` | 1 `high_school (THPT)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Trung học phổ thông` | 1 `high_school (THPT)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `Trung học phổ thông` | 1 `high_school (THPT)` | 1 `high_school (THPT)` | 1.000 | 1.000 | ✅ |
| JD | `Trung học phổ thông` | 1 `high_school (THPT)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| JD | `Trung học phổ thông` | 1 `high_school (THPT)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| JD | `Trung học phổ thông` | 1 `high_school (THPT)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Trung học phổ thông` | 1 `high_school (THPT)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Trung cấp` | 2 `associate (Cao đẳng)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `Trung cấp` | 2 `associate (Cao đẳng)` | 1 `high_school (THPT)` | 0.500 | 0.500 | ✅ |
| JD | `Trung cấp` | 2 `associate (Cao đẳng)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| JD | `Trung cấp` | 2 `associate (Cao đẳng)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| JD | `Trung cấp` | 2 `associate (Cao đẳng)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Trung cấp` | 2 `associate (Cao đẳng)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Cao đẳng` | 2 `associate (Cao đẳng)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `Cao đẳng` | 2 `associate (Cao đẳng)` | 1 `high_school (THPT)` | 0.500 | 0.500 | ✅ |
| JD | `Cao đẳng` | 2 `associate (Cao đẳng)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | ✅ |
| JD | `Cao đẳng` | 2 `associate (Cao đẳng)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| JD | `Cao đẳng` | 2 `associate (Cao đẳng)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Cao đẳng` | 2 `associate (Cao đẳng)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Đại học` | 3 `bachelor (Đại học)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `Đại học` | 3 `bachelor (Đại học)` | 1 `high_school (THPT)` | 0.333 | 0.333 | ✅ |
| JD | `Đại học` | 3 `bachelor (Đại học)` | 2 `associate (Cao đẳng)` | 0.667 | 0.667 | ✅ |
| JD | `Đại học` | 3 `bachelor (Đại học)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| JD | `Đại học` | 3 `bachelor (Đại học)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Đại học` | 3 `bachelor (Đại học)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Cử nhân` | 3 `bachelor (Đại học)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `Cử nhân` | 3 `bachelor (Đại học)` | 1 `high_school (THPT)` | 0.333 | 0.333 | ✅ |
| JD | `Cử nhân` | 3 `bachelor (Đại học)` | 2 `associate (Cao đẳng)` | 0.667 | 0.667 | ✅ |
| JD | `Cử nhân` | 3 `bachelor (Đại học)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| JD | `Cử nhân` | 3 `bachelor (Đại học)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Cử nhân` | 3 `bachelor (Đại học)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Bachelor` | 3 `bachelor (Đại học)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `Bachelor` | 3 `bachelor (Đại học)` | 1 `high_school (THPT)` | 0.333 | 0.333 | ✅ |
| JD | `Bachelor` | 3 `bachelor (Đại học)` | 2 `associate (Cao đẳng)` | 0.667 | 0.667 | ✅ |
| JD | `Bachelor` | 3 `bachelor (Đại học)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | ✅ |
| JD | `Bachelor` | 3 `bachelor (Đại học)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Bachelor` | 3 `bachelor (Đại học)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 1 `high_school (THPT)` | 0.250 | 0.250 | ✅ |
| JD | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 2 `associate (Cao đẳng)` | 0.500 | 0.500 | ✅ |
| JD | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 3 `bachelor (Đại học)` | 0.750 | 0.750 | ✅ |
| JD | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Thạc sĩ` | 4 `master (Thạc sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Master` | 4 `master (Thạc sĩ)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `Master` | 4 `master (Thạc sĩ)` | 1 `high_school (THPT)` | 0.250 | 0.250 | ✅ |
| JD | `Master` | 4 `master (Thạc sĩ)` | 2 `associate (Cao đẳng)` | 0.500 | 0.500 | ✅ |
| JD | `Master` | 4 `master (Thạc sĩ)` | 3 `bachelor (Đại học)` | 0.750 | 0.750 | ✅ |
| JD | `Master` | 4 `master (Thạc sĩ)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Master` | 4 `master (Thạc sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 1 `high_school (THPT)` | 0.200 | 0.200 | ✅ |
| JD | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 2 `associate (Cao đẳng)` | 0.400 | 0.400 | ✅ |
| JD | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 3 `bachelor (Đại học)` | 0.600 | 0.600 | ✅ |
| JD | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 4 `master (Thạc sĩ)` | 0.800 | 0.800 | ✅ |
| JD | `Tiến sĩ` | 5 `phd (Tiến sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `PhD` | 5 `phd (Tiến sĩ)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `PhD` | 5 `phd (Tiến sĩ)` | 1 `high_school (THPT)` | 0.200 | 0.200 | ✅ |
| JD | `PhD` | 5 `phd (Tiến sĩ)` | 2 `associate (Cao đẳng)` | 0.400 | 0.400 | ✅ |
| JD | `PhD` | 5 `phd (Tiến sĩ)` | 3 `bachelor (Đại học)` | 0.600 | 0.600 | ✅ |
| JD | `PhD` | 5 `phd (Tiến sĩ)` | 4 `master (Thạc sĩ)` | 0.800 | 0.800 | ✅ |
| JD | `PhD` | 5 `phd (Tiến sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |
| JD | `Doctor` | 5 `phd (Tiến sĩ)` | 0 `(none/không có)` | 0.500 | 0.500 | ✅ |
| JD | `Doctor` | 5 `phd (Tiến sĩ)` | 1 `high_school (THPT)` | 0.200 | 0.200 | ✅ |
| JD | `Doctor` | 5 `phd (Tiến sĩ)` | 2 `associate (Cao đẳng)` | 0.400 | 0.400 | ✅ |
| JD | `Doctor` | 5 `phd (Tiến sĩ)` | 3 `bachelor (Đại học)` | 0.600 | 0.600 | ✅ |
| JD | `Doctor` | 5 `phd (Tiến sĩ)` | 4 `master (Thạc sĩ)` | 0.800 | 0.800 | ✅ |
| JD | `Doctor` | 5 `phd (Tiến sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | ✅ |

**Kết quả: 144/144 tổ hợp khớp tuyệt đối
(100.0%).**

### A.4 Property-based tests

| Property | Mô tả bất biến | Kết quả | Chi tiết |
| --- | --- | --- | --- |
| P1 — Cận trên (cap ở 1.0) | Bằng cấp cao hơn yêu cầu không được cộng điểm vượt 1.0 | ✅ PASS | OK — không có vi phạm trong 30 tổ hợp (jd_level 1..5 x cv_level 0..5) |
| P2 — Đơn điệu không giảm theo cv_level | cv_level tăng (1→5, jd_level cố định) → D4 không được giảm | ✅ PASS | OK — đơn điệu trên cả 5 giá trị jd_level |
| P3 — Bất biến với thứ tự education[] | Xáo trộn thứ tự 5 bằng cấp trong CV (mọi hoán vị) không được đổi D4 (lấy max=PHD), trên mọi jd_level | ✅ PASS | OK — 720 phép kiểm tra (5!=120 hoán vị x 6 jd_level) đều nhất quán |
| P4 — OTHER ≡ high_school (numeric=1) | Degree 'other' và 'high_school' cùng numeric=1 → phải cho D4 giống hệt nhau | ✅ PASS | OK — khớp trên cả 5 giá trị jd_level |

**Kết quả: 4/4 property PASS.** (P3 tự nó đã kiểm
720 phép hoán vị — xem chi tiết cột "Chi tiết").

### A.5 Kết luận Phần A

Trên tổng cộng **366 test case correctness** (A.1 + A.2 + A.3,
toàn bộ exhaustive) cộng 4 property test, `score_education()`
cài đặt **đúng 100%** đặc tả công thức: 366/366 tổ hợp
khớp tuyệt đối, 4/4 property PASS — bao gồm cả khi
CV/JD ghi bằng cấp bằng tiếng Việt (A.3), đúng với ngữ cảnh sử dụng thực tế
của sản phẩm. Bao gồm cả 2 trường hợp biên dễ cài sai (JD không yêu cầu →
1.0 bất kể CV; CV không có bằng → 0.5 trung lập, không phải 0.0 — tức
"thiếu dữ liệu không đồng nghĩa với không đạt"), cận trên chặn đúng ở 1.0,
và tính `max` trên `education[]` — cả khi CV có 1 bằng lẫn nhiều bằng cùng
lúc — không phụ thuộc thứ tự phần tử. Đây là bằng chứng **hình thức, đầy đủ**
(exhaustive trên toàn bộ không gian đầu vào rời rạc của D4, không phải suy
diễn từ mẫu) — không gian đầu vào **số** của D4 chỉ có 2 biến số (bậc CV cao
nhất, bậc JD yêu cầu, 36 tổ hợp) nên phần mở rộng ở A.2/A.3 đã phủ
kín mọi cách một tổ hợp số đó có thể được **biểu diễn** trong dữ liệu thực
(nhiều bằng cùng lúc, tên tiếng Việt) — thêm case ngẫu nhiên nữa trên cùng
2 biến số đó sẽ không mang thêm thông tin mới.

## PHẦN B — Đúng thực tế (validity)

**Phương pháp:** D4 dùng **tỉ lệ** bậc học vấn ($L_{cv}/L_{jd}$), nhưng
$L$ là thang **thứ tự** (ordinal) — bản thân mục 4.8 của báo cáo đã lưu ý đây
là "giả định đơn giản hóa có ý thức". Để kiểm chứng mức độ hợp lý của giả
định này, ta so D4 với một **nhãn proxy độc lập** mô phỏng trực giác tuyển
dụng phổ biến, dựa trên **khoảng cách bậc** thay vì **tỉ lệ bậc**: thiếu đúng
1 bậc → vẫn cân nhắc (0.65), thiếu 2 bậc → yếu (0.3), thiếu ≥3 bậc → gần như
loại (0.1). Đây là nhãn có lý giải domain, **không phải dữ liệu khảo sát HR
thật** (ngoài phạm vi thu thập được của đồ án) — hạn chế này được nêu tường
minh, không dùng để khẳng định "đã kiểm chứng với người dùng thật".

### B.1 Toàn bộ điểm so sánh (jd_level 1..5 × cv_level 0..5, 30 điểm)

| jd_level | cv_level | D4 (công thức) | Nhãn proxy HR (khoảng cách bậc) | \|D4 − human\| |
| --- | --- | --- | --- | --- |
| 1 `high_school (THPT)` | 0 `(none/không có)` | 0.500 | 0.500 | 0.000 |
| 1 `high_school (THPT)` | 1 `high_school (THPT)` | 1.000 | 1.000 | 0.000 |
| 1 `high_school (THPT)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | 0.000 |
| 1 `high_school (THPT)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | 0.000 |
| 1 `high_school (THPT)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | 0.000 |
| 1 `high_school (THPT)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | 0.000 |
| 2 `associate (Cao đẳng)` | 0 `(none/không có)` | 0.500 | 0.500 | 0.000 |
| 2 `associate (Cao đẳng)` | 1 `high_school (THPT)` | 0.500 | 0.650 | 0.150 |
| 2 `associate (Cao đẳng)` | 2 `associate (Cao đẳng)` | 1.000 | 1.000 | 0.000 |
| 2 `associate (Cao đẳng)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | 0.000 |
| 2 `associate (Cao đẳng)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | 0.000 |
| 2 `associate (Cao đẳng)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | 0.000 |
| 3 `bachelor (Đại học)` | 0 `(none/không có)` | 0.500 | 0.500 | 0.000 |
| 3 `bachelor (Đại học)` | 1 `high_school (THPT)` | 0.333 | 0.300 | 0.033 |
| 3 `bachelor (Đại học)` | 2 `associate (Cao đẳng)` | 0.667 | 0.650 | 0.017 |
| 3 `bachelor (Đại học)` | 3 `bachelor (Đại học)` | 1.000 | 1.000 | 0.000 |
| 3 `bachelor (Đại học)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | 0.000 |
| 3 `bachelor (Đại học)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | 0.000 |
| 4 `master (Thạc sĩ)` | 0 `(none/không có)` | 0.500 | 0.500 | 0.000 |
| 4 `master (Thạc sĩ)` | 1 `high_school (THPT)` | 0.250 | 0.100 | 0.150 |
| 4 `master (Thạc sĩ)` | 2 `associate (Cao đẳng)` | 0.500 | 0.300 | 0.200 |
| 4 `master (Thạc sĩ)` | 3 `bachelor (Đại học)` | 0.750 | 0.650 | 0.100 |
| 4 `master (Thạc sĩ)` | 4 `master (Thạc sĩ)` | 1.000 | 1.000 | 0.000 |
| 4 `master (Thạc sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | 0.000 |
| 5 `phd (Tiến sĩ)` | 0 `(none/không có)` | 0.500 | 0.500 | 0.000 |
| 5 `phd (Tiến sĩ)` | 1 `high_school (THPT)` | 0.200 | 0.100 | 0.100 |
| 5 `phd (Tiến sĩ)` | 2 `associate (Cao đẳng)` | 0.400 | 0.100 | 0.300 |
| 5 `phd (Tiến sĩ)` | 3 `bachelor (Đại học)` | 0.600 | 0.300 | 0.300 |
| 5 `phd (Tiến sĩ)` | 4 `master (Thạc sĩ)` | 0.800 | 0.650 | 0.150 |
| 5 `phd (Tiến sĩ)` | 5 `phd (Tiến sĩ)` | 1.000 | 1.000 | 0.000 |

### B.2 Chỉ số tổng hợp

| Chỉ số | Giá trị | Ý nghĩa |
| --- | --- | --- |
| Spearman ρ (D4 vs nhãn proxy) | 0.9730 | Thứ hạng phù hợp có khớp không (D4 có sắp đúng thứ tự các ứng viên theo mức phù hợp học vấn không) |
| MAE (D4 vs nhãn proxy) | 0.0500 | Giá trị tuyệt đối lệch bao nhiêu trên thang 0-1 |
| Accuracy phân loại "đạt yêu cầu" (ngưỡng 0.7) | 0.9333 | Nếu dùng D4 để quyết định nhị phân "đạt/không đạt học vấn" thì khớp với nhãn proxy bao nhiêu % |
| Confusion matrix | TP=15 FP=2 TN=13 FN=0 | Chi tiết theo ngưỡng 0.7 |

### B.3 5 điểm lệch nhiều nhất (D4 vs nhãn proxy)

| jd_level | cv_level | D4 | Nhãn proxy | Lệch |
| --- | --- | --- | --- | --- |
| 5 `phd (Tiến sĩ)` | 2 `associate (Cao đẳng)` | 0.400 | 0.100 | 0.300 |
| 5 `phd (Tiến sĩ)` | 3 `bachelor (Đại học)` | 0.600 | 0.300 | 0.300 |
| 4 `master (Thạc sĩ)` | 2 `associate (Cao đẳng)` | 0.500 | 0.300 | 0.200 |
| 2 `associate (Cao đẳng)` | 1 `high_school (THPT)` | 0.500 | 0.650 | 0.150 |
| 5 `phd (Tiến sĩ)` | 4 `master (Thạc sĩ)` | 0.800 | 0.650 | 0.150 |

### B.4 Kết luận Phần B

Spearman ρ = 0.973 cho thấy D4 **sắp đúng thứ tự** gần như tuyệt đối —
ứng viên có bậc học vấn cao hơn (so với cùng 1 yêu cầu JD) luôn được D4 chấm
điểm không thấp hơn, khớp trực giác HR. Đây là thuộc tính quan trọng nhất
với vai trò của D4 trong hệ (xếp hạng ứng viên), và **đã được PHẦN A chứng
minh hình thức** ở property P2.

Tuy nhiên MAE = 0.050 cho thấy **giá trị tuyệt đối** lệch đáng kể ở các
tổ hợp yêu cầu bậc cao (jd_level lớn): xem B.3, các trường hợp lệch nhiều
nhất đều rơi vào `jd=phd` hoặc `jd=master` với CV thấp hơn 2-4 bậc — do
D4 tính theo **tỉ lệ** ($3/5=0.6$ cho bachelor/phd) trong khi trực giác HR
theo **khoảng cách** (3 bậc dưới phd → gần như loại, 0.1). Nói cách khác:
**D4 đúng về thứ hạng nhưng là một phép đo thô về độ lớn** khi khoảng yêu
cầu-thực tế lớn — đúng như giả định đơn giản hóa đã tự nhận trong mục 4.8,
và ở đây được **định lượng** thay vì chỉ nêu định tính.

**Hạn chế của thực nghiệm này:** nhãn proxy dựa trên lý giải domain của
người viết, không phải khảo sát HR thật (xem đề xuất "Precision/Recall của
D2" và nDCG/Spearman với nhãn HR thật ở
[`docs/thesis_report.md` mục 6.2](thesis_report.md#62-chỉ-số-đánh-giá-đề-xuất-chưa-thực-hiện)
— cùng phương pháp luận, nhưng cho D4 thay vì toàn hệ). Kết luận "đúng thứ
hạng, thô về độ lớn" nên được đọc như một **giả thuyết có cơ sở định lượng**,
cần xác nhận thêm bằng dữ liệu HR thật nếu đưa vào phần kết luận chính thức
của đồ án.

## Tổng kết

| | Kết quả |
| --- | --- |
| Đúng cài đặt (Phần A) | 366/366 test case correctness khớp tuyệt đối (36 đơn-bằng + 186 đa-bằng + 144 tiếng Việt) + 4/4 property PASS → **100% correctness trên toàn bộ không gian đầu vào rời rạc, kể cả dữ liệu tiếng Việt** |
| Đúng thực tế (Phần B) | Spearman ρ=0.973 (thứ hạng khớp cao) · MAE=0.050 (giá trị tuyệt đối lệch ở khoảng cách bậc lớn) · Accuracy phân loại=0.933 @ngưỡng 0.7 |

---
*Tái tạo báo cáo này: `python scripts/d4_education_experiment.py`*
