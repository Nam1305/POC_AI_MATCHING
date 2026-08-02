# CẨM NANG BẢO VỆ ĐỒ ÁN — PHẦN AI SERVICE

> Tài liệu này đi **theo đúng luồng dữ liệu của AI**: file CV/JD thô → text sạch →
> JSON có cấu trúc → vector embedding → 5 điểm thành phần D1–D5 → điểm tổng +
> nhận xét cho HR.
>
> Mỗi chặng gồm 4 phần cố định:
> - **① Nói gì** — lời thoại ngắn gọn, đủ ý để trình bày trong 1–2 phút
> - **② Cơ chế thật trong code** — con số, ngưỡng, file/dòng để chỉ tận nơi khi hội đồng hỏi
> - **③ Vì sao thiết kế như vậy** — lý do bảo vệ được, không phải "em làm cho tiện"
> - **④ Câu hỏi phản biện + cách trả lời** — kể cả câu bẫy
>
> Tài liệu chi tiết học thuật: [docs/thesis_report.md](docs/thesis_report.md) ·
> Danh mục 40 tài liệu tham khảo: [docs/research_papers.md](docs/research_papers.md)

---

## MỤC LỤC

- [0. Bản đồ 60 giây — mở đầu buổi bảo vệ](#0-bản-đồ-60-giây--mở-đầu-buổi-bảo-vệ)
- [1. Kiến trúc & vị trí của AI service](#1-kiến-trúc--vị-trí-của-ai-service)
- [2. CHẶNG 1 — Tiền xử lý tài liệu (PDF/DOCX → text sạch)](#2-chặng-1--tiền-xử-lý-tài-liệu-pdfdocx--text-sạch)
- [3. CHẶNG 2 — Trích xuất JSON bằng LLM (text → ParsedCV / ParsedJD)](#3-chặng-2--trích-xuất-json-bằng-llm-text--parsedcv--parsedjd)
- [4. CHẶNG 3 — Embedding (text → vector 3072 chiều)](#4-chặng-3--embedding-text--vector-3072-chiều)
- [5. CHẶNG 4 — Chấm điểm 5 chiều](#5-chặng-4--chấm-điểm-5-chiều)
  - [5.1 D1 — Semantic](#51-d1--semantic-ngữ-nghĩa--w--030)
  - [5.2 D2 — Skills](#52-d2--skills-kỹ-năng--w--035--phần-nặng-thuật-toán-nhất)
  - [5.3 D3 — Experience](#53-d3--experience-kinh-nghiệm--w--020)
  - [5.4 D4 — Education](#54-d4--education-học-vấn--w--010)
  - [5.5 D5 — Location](#55-d5--location--work-mode-vị-trí--w--005)
- [6. CHẶNG 5 — Tổng hợp điểm & nhận xét cho HR](#6-chặng-5--tổng-hợp-điểm--nhận-xét-cho-hr)
- [7. Bảng số liệu bắt buộc thuộc lòng](#7-bảng-số-liệu-bắt-buộc-thuộc-lòng)
- [8. Ngân hàng câu hỏi phản biện](#8-ngân-hàng-câu-hỏi-phản-biện--trả-lời-mẫu)
- [9. Điểm yếu tự nhận (chủ động nêu trước)](#9-điểm-yếu-tự-nhận--nên-chủ-động-nêu-trước-khi-bị-hỏi)
- [10. Checklist việc phải làm TRƯỚC buổi bảo vệ](#10-checklist-việc-phải-làm-trước-buổi-bảo-vệ)
- [11. Kịch bản demo 5 phút](#11-kịch-bản-demo-5-phút)

---

## 0. Bản đồ 60 giây — mở đầu buổi bảo vệ

Học thuộc đoạn này, nói trước khi vào chi tiết. Nó định khung cho toàn bộ phần
phản biện phía sau:

> "AI service của em là một microservice FastAPI **không trạng thái** (stateless:
> không database, không authentication), được backend .NET gọi qua HTTP nội bộ.
> Nó làm 3 việc: **đọc hiểu CV/JD**, **biến chúng thành dữ liệu có cấu trúc**, và
> **chấm điểm mức độ phù hợp giữa một CV với một JD**.
>
> Điểm mấu chốt về mặt thiết kế: em **không** để một mô hình AI duy nhất quyết
> định điểm số. Hệ thống là **hybrid** — lai giữa hai trường phái. LLM và embedding
> (học sâu) chỉ đảm nhiệm phần *đọc hiểu ngôn ngữ*, chiếm **30%** trọng số điểm.
> **70%** trọng số còn lại nằm ở các quy tắc **tất định** (deterministic) viết bằng
> Python thuần: so khớp kỹ năng theo từ điển tri thức, so số năm kinh nghiệm, so
> bằng cấp, tính thời gian di chuyển. Nghĩa là với cùng một cặp CV–JD, phần lớn
> điểm số luôn tái lập được và **truy vết được từng điểm đến từ đâu**.
>
> Lý do của lựa chọn này không phải kỹ thuật mà là **trách nhiệm**: tuyển dụng là
> lĩnh vực rủi ro cao, hệ thống phải giải thích được vì sao ứng viên A xếp trên
> ứng viên B."

**Ba từ khóa để hội đồng nhớ:** *hybrid* — *giải thích được (explainable)* — *tách bạch tín hiệu (không đếm trùng)*.

---

## 1. Kiến trúc & vị trí của AI service

### ① Nói gì

```
ReactJS  ──→  .NET API  ──→  PostgreSQL (lưu parsed_cv, parsed_jd, embedding, score)
                  ↕  HTTP (mạng nội bộ Docker)
          Python AI Service  ←── stateless, 4 endpoint dưới /ai
                  ↓
       Gemini / Claude / Groq (LLM + embedding)  ·  Nominatim + OSRM (bản đồ)
```

| Endpoint | Việc nó làm | Có gọi LLM? | Thời gian |
| --- | --- | --- | --- |
| `POST /ai/parse-jd` | text JD → JSON có cấu trúc + vector | ✅ 1 call | ~3–5s |
| `POST /ai/parse-cv` | URL file CV (S3/R2) → text + JSON + vector | ✅ 1–3 call | ~5–10s |
| `POST /ai/score` | CV + JD (đã parse) → 5 điểm + điểm tổng | ❌ (mặc định) | ~1ms + I/O bản đồ |
| `POST /ai/evaluate` | CV + JD → đoạn nhận xét tiếng Việt cho HR | ✅ 1 call | ~3–5s |

### ② Cơ chế thật trong code

- Router: [app/main.py](app/main.py) · Cấu hình: [app/config.py](app/config.py)
- **Stateless nghĩa là**: AI service không lưu gì cả. Vector, JSON, điểm số đều
  trả về cho .NET và .NET lưu vào PostgreSQL. Service có thể scale ngang, restart
  bất kỳ lúc nào, không mất dữ liệu.
- **Tách công việc đắt và công việc rẻ**: parse (đắt, gọi LLM) chạy **1 lần** khi
  upload CV / đăng tin. Score (rẻ, ~1ms) chạy **N lần** — mỗi ứng viên × mỗi job.

### ③ Vì sao thiết kế như vậy

Nếu nhét AI vào thẳng .NET thì mỗi lần chấm điểm lại phải parse lại CV → tốn tiền
LLM gấp N lần và chậm gấp hàng nghìn lần. Kiến trúc **precompute** (tính trước) này
là chuẩn mực của các hệ retrieval: vector và JSON được tính **một lần tại thời
điểm parse**, sau đó mọi phép chấm điểm chỉ là số học trên dữ liệu đã có.

### ④ Câu hỏi phản biện

**"Sao không dùng Python luôn cho cả backend?"**
→ Backend đã có nghiệp vụ .NET (auth, phân quyền, quản lý tin tuyển dụng, thanh
toán). Tách AI thành service riêng cho phép: deploy độc lập, scale riêng phần tốn
CPU (OCR/embedding), đổi nhà cung cấp LLM mà không đụng backend, và team backend
không cần biết Python.

**"Service không có authentication thì có nguy hiểm không?"**
→ Có, và em đã cân nhắc. Hiện tại nó chỉ lắng nghe trên **mạng nội bộ Docker**,
không expose ra Internet — chỉ container .NET gọi được. Nếu triển khai thật, cần
thêm: API key giữa 2 service, và **whitelist domain** cho `/ai/parse-cv` vì
endpoint này nhận URL tùy ý rồi tải về (nguy cơ SSRF — kẻ tấn công đưa URL nội bộ
để service tự tải về hộ). Đây là hạn chế em ghi nhận, không phải bỏ sót.

---

## 2. CHẶNG 1 — Tiền xử lý tài liệu (PDF/DOCX → text sạch)

📁 [app/services/pdf_extractor.py](app/services/pdf_extractor.py) · [app/api/parse.py](app/api/parse.py)

### ① Nói gì

> "Trước khi AI đọc được CV, em phải biến file PDF/Word thành text sạch. Nghe đơn
> giản nhưng đây là chặng dễ hỏng nhất: CV là loại tài liệu có **bố cục tự do
> nhất** mà người ta có thể tạo ra — 2 cột, bảng, icon, ảnh scan. Em xử lý bằng 4
> bước: tải file → trích xuất theo block có nhận diện bố cục → **tự chấm điểm chất
> lượng** text vừa lấy được → nếu chất lượng kém thì tự động chuyển sang OCR."

### ② Cơ chế thật trong code

**Bước 1 — Tải file** ([parse.py:163](app/api/parse.py#L163))
- Nhận `cv_url` (1 file) hoặc `cv_urls` (tối đa **50 file/request**), tải **song
  song** bằng `asyncio.gather`.
- Retry **3 lần**, giãn cách tăng dần (1.5s → 3s → 4.5s), timeout 30s.
- Đoán tên file theo thứ tự: header `Content-Disposition` → đoạn cuối URL →
  suy từ `Content-Type`.
- **Lỗi từng file không làm hỏng cả lô**: file nào lỗi thì phần tử đó trong mảng
  `results` mang `error`, các file khác vẫn xử lý bình thường.

**Bước 2 — Trích xuất theo bố cục** ([pdf_extractor.py:66](app/services/pdf_extractor.py#L66))

Đây là điểm kỹ thuật đáng nói nhất của chặng này. PyMuPDF trả về các **block** text
kèm tọa độ `(x0, y0, x1, y1)`. Nếu chỉ đọc từ trên xuống dưới thì CV 2 cột sẽ bị
**trộn lẫn**: dòng "React, Node.js" ở cột trái dính vào dòng "Công ty ABC" ở cột
phải → LLM đọc ra nội dung vô nghĩa.

Cách phát hiện 2 cột:
```
left_count  = số block có tâm nằm bên trái  45% chiều rộng trang
right_count = số block có tâm nằm bên phải  55% chiều rộng trang
is_two_col  = (left_count >= 2) AND (right_count >= 2)
```
Nếu là 2 cột, thứ tự đọc là: **header (16% chiều cao trên cùng) → cột phải → cột
trái**. Cột phải trước vì mẫu CV 2 cột phổ biến đặt nội dung chính (kinh nghiệm,
dự án) bên phải, còn cột trái là thanh phụ (kỹ năng, liên hệ).

**Bước 3 — Chấm điểm chất lượng, thang 0–100** ([pdf_extractor.py:141](app/services/pdf_extractor.py#L141))

| Tín hiệu nghi ngờ | Trừ | Ý nghĩa |
| --- | --- | --- |
| Text < 100 ký tự | −60 | Gần như chắc chắn là PDF ảnh |
| < 30 từ | −30 | Nội dung không đáng kể |
| Tỷ lệ ký tự rác `�` > 2% | −20 | Lỗi font/encoding |
| Độ dài từ trung bình < 2 hoặc > 15 | −15 | Từ có nghĩa thường dài 4–8 ký tự |

**Bước 4 — OCR dự phòng** ([pdf_extractor.py:188](app/services/pdf_extractor.py#L188))
- Kích hoạt khi **điểm chất lượng < 60**.
- Render từng trang PDF thành ảnh ở **200 DPI**, chạy Tesseract với gói ngôn ngữ
  **`eng+vie`** (đọc được cả tiếng Việt có dấu).
- Chi phí: +2–5 giây mỗi trang → nên chỉ chạy khi thật cần, đó là lý do phải có
  bước chấm điểm chất lượng ở giữa.

**Bước 5 — Làm sạch** ([pdf_extractor.py:246](app/services/pdf_extractor.py#L246)):
bỏ ký tự null, gộp nhiều space/tab thành một, gộp 3+ dòng trống thành tối đa 2.

### ③ Vì sao thiết kế như vậy

- **Vì sao có bước chấm điểm chất lượng thay vì luôn OCR?** OCR đắt và chậm gấp
  hàng chục lần. 90% CV là PDF gốc có text layer sạch. Chấm điểm chất lượng là
  một **cổng lọc rẻ tiền** để chỉ trả giá OCR cho đúng 10% cần thiết.
- **Vì sao không dùng model layout detection có huấn luyện (như PubLayNet)?** Vì
  cần GPU, cần thời gian inference, và bài toán ở đây chỉ có 2 lớp bố cục phổ
  biến. Heuristic 45%/55% giải quyết được đa số với chi phí gần bằng 0. Em ghi
  nhận đây là đánh đổi, và nêu hướng nâng cấp trong phần hạn chế.

### ④ Câu hỏi phản biện

**"Heuristic 45%/55% có cơ sở khoa học không? Sao không phải 40/60?"**
→ Thành thật: đây là **ngưỡng thực nghiệm**, không phải hằng số lý thuyết. Ý tưởng
là chừa một "vùng đệm" 10% ở giữa trang để các block nằm vắt ngang tâm (như tiêu
đề mục trải dài) không bị gán nhầm vào cột nào. Hạn chế đã biết: **không xử lý
được CV 3 cột hoặc 2 cột lệch tỷ lệ**. Hướng nâng cấp là model layout detection
kiểu PubLayNet.

**"CV scan chữ viết tay thì sao?"**
→ Tesseract đọc chữ in tốt, chữ viết tay thì rất kém. Trường hợp đó text sẽ ra
rác, LLM ở chặng sau trả về JSON gần như rỗng, và ứng viên nhận điểm thấp bất
công. Đây là hạn chế thật — hướng xử lý là cảnh báo cho HR khi `cv_raw_text` quá
ngắn để HR đọc tay.

**"Sao không dùng thư viện parse CV có sẵn?"**
→ Các thư viện đó dựa trên regex/template cố định, hỏng ngay khi gặp mẫu CV lạ và
gần như không hỗ trợ tiếng Việt. Kiến trúc của em đặt phần "hiểu nội dung" vào
LLM (chặng 2) nên chặng này **chỉ cần lấy đúng text theo đúng thứ tự đọc** — một
bài toán hẹp hơn nhiều và dễ đảm bảo hơn.

---

## 3. CHẶNG 2 — Trích xuất JSON bằng LLM (text → ParsedCV / ParsedJD)

📁 [app/services/parser.py](app/services/parser.py) · [app/services/llm_client.py](app/services/llm_client.py) · [app/schemas.py](app/schemas.py)

### ① Nói gì

> "Chặng này biến text tự do thành **JSON có cấu trúc chặt** để các bước sau tính
> toán được. Em dùng LLM vì CV không có định dạng chuẩn — cùng một ý 'kinh nghiệm
> 3 năm' có thể viết bằng 50 cách khác nhau, regex không kham nổi.
>
> Nhưng em **không tin LLM một cách mù quáng**. Có 4 lớp kiểm soát: prompt ràng
> buộc rất chi tiết, ép model trả JSON, sửa JSON hỏng, và cuối cùng **validate
> bằng Pydantic** — mọi thứ LLM trả về đều phải đi qua schema mới được vào hệ
> thống. Đặc biệt, **mọi phép tính số học em giành lại cho Python**, không giao
> cho LLM."

### ② Cơ chế thật trong code

**(a) Chọn nhà cung cấp LLM — 3 lựa chọn thay thế được** ([llm_client.py](app/services/llm_client.py))

| Provider | Model mặc định | Dùng khi nào |
| --- | --- | --- |
| `gemini` | `gemini-2.5-flash` | Mặc định — rẻ, nhanh, có JSON mode |
| `anthropic` | `claude-sonnet-4-6` | Production — chất lượng trích xuất cao nhất |
| `groq` | `llama-3.1-8b-instant` | Dev — miễn phí |

Chuyển đổi chỉ bằng 1 biến môi trường `LLM_PROVIDER`. **Điểm cần nhấn**: dù chọn
provider nào thì **embedding luôn là Gemini** — vì vector phải được sinh bởi *cùng
một model* thì mới so sánh được với nhau (xem chặng 3).

**(b) Prompt là "hợp đồng" chứ không phải lời gợi ý**

Prompt trích xuất CV ([parser.py:42](app/services/parser.py#L42)) dài ~90 dòng, ghi rõ:
- **Khung JSON mẫu** kèm mô tả từng trường.
- **Bảng quy đổi ngày tháng** — bao gồm cả định dạng tiếng Việt:
  `"Tháng 3/2021"` / `"T3/2021"` → `"2021-03"`; `"Hiện tại"` / `"Nay"` / `"Đến nay"` → `"present"`.
- **Quy tắc chuẩn hóa tên kỹ năng**: `"ReactJS"` → `"React"`, `"NodeJS"` → `"Node.js"`,
  `"K8s"` → `"Kubernetes"`; bỏ số phiên bản (`"Python 3.10"` → `"Python"`); tách kỹ
  năng ghép (`"HTML/CSS"` → 2 mục riêng); thêm công nghệ cha (`"AWS S3"` → thêm `"AWS"`).
- **Quy tắc chống bịa (hallucination)** cho địa chỉ: chỉ lấy địa chỉ ở khối liên
  hệ đầu CV, **cấm** suy ra từ đầu số điện thoại, từ địa chỉ trường học hay công
  ty cũ. `willing_to_relocate` chỉ `true` khi CV nói thẳng, **cấm suy diễn**.

Prompt trích xuất JD ([parser.py:198](app/services/parser.py#L198)) còn chặt hơn vì
JD do backend .NET **ghép từ các trường trong database**:
- **Trường có cấu trúc thắng văn xuôi**: dòng `"Work Type: Hybrid"` do nhà tuyển
  dụng chọn từ dropdown → tin tuyệt đối, không suy từ đoạn mô tả.
- **3 danh sách kỹ năng đã phân tầng sẵn** (`Required` / `Preferred` / `Nice to
  Have`) → copy **nguyên văn**, cấm phân loại lại.
- **Quy tắc chống trùng lặp**: khi quét thêm kỹ năng từ đoạn văn xuôi, phải đối
  chiếu với cả 3 danh sách trước; nếu đã có (kể cả biến thể chính tả) thì **không
  thêm lần nữa**. Đây là hàng rào duy nhất chống việc một kỹ năng bị **đếm hai
  lần ở hai tầng khác nhau**.
- **Quy tắc học vấn ngược trực giác**: dòng `"Education: THPT, Thạc sĩ, Tiến sĩ"`
  là **multi-select "chấp nhận bằng nào cũng được"**, nên phải lấy mức **THẤP
  NHẤT** (`high_school`) làm sàn, không phải mức cao nhất.
- **Loại trừ khối Benefits**: mục phúc lợi hay ghi "phụ cấp tiếng Nhật N1/N2" —
  đó là tiền thưởng, không phải yêu cầu tuyển dụng.

**(c) Ba lớp bảo vệ chất lượng đầu ra**

1. **Ép định dạng JSON**: Gemini/Groq dùng `response_format={"type":"json_object"}`;
   Anthropic tự bóc code fence ```` ```json ````. Tất cả đặt **`temperature=0`** —
   tham số điều khiển độ ngẫu nhiên, đặt 0 nghĩa là "luôn chọn phương án khả dĩ
   nhất", cho kết quả ổn định nhất có thể.
2. **Sửa JSON hỏng** ([llm_client.py:42](app/services/llm_client.py#L42)): thử
   `json.loads` → nếu lỗi thì regex bỏ dấu phẩy thừa trước `}`/`]` → nếu vẫn lỗi
   thì dùng thư viện `json_repair`. Chỉ khi cả 3 đều thất bại mới báo lỗi.
3. **Retry theo tính đầy đủ** ([parser.py:456](app/services/parser.py#L456)): sau
   lần parse đầu, kiểm tra 2 trường quan trọng nhất — `work_experience` và
   `skills`. Nếu rỗng → gọi lại bằng **prompt ngắn, chỉ tập trung vào đúng phần
   thiếu**. Nếu thiếu cả hai thì 2 lần gọi chạy **song song** qua `asyncio.gather`
   nên không cộng dồn thời gian. Nếu retry cũng thất bại thì **giữ nguyên kết quả
   cũ**, không ghi đè bằng dữ liệu rỗng.

**(d) Python giành lại mọi phép tính — điểm cần nhấn mạnh**

| Việc | Ai làm | Vì sao |
| --- | --- | --- |
| Đọc chuỗi ngày `"Tháng 3/2021"` | LLM | Cần hiểu ngôn ngữ |
| Tính số tháng giữa 2 mốc | **Python** ([schemas.py:121](app/schemas.py#L121)) | LLM tính số học hay sai |
| Tổng số năm kinh nghiệm | **Python** ([schemas.py:357](app/schemas.py#L357)) | Phải **gộp khoảng thời gian chồng lấn** |
| Quy đổi bằng cấp thành số | **Python** ([schemas.py:96](app/schemas.py#L96)) | Cần bảng ánh xạ cố định |

Riêng phần tổng số năm kinh nghiệm dùng thuật toán **merge interval**
([schemas.py:63](app/schemas.py#L63)): nếu ứng viên làm freelance song song với
full-time từ 2021-01 đến 2022-01, hệ thống chỉ tính **12 tháng**, không phải 24.
Nếu để LLM cộng, nó gần như chắc chắn cộng thành 24.

**(e) Pydantic — hàng rào cuối cùng** ([app/schemas.py](app/schemas.py))

- **Ép kiểu mềm**: LLM trả `null` thay vì `[]` → tự chuyển thành `[]` thay vì crash.
- **Chuẩn hóa bằng cấp**: `"Bachelor of Science"`, `"BSc"`, `"Cử nhân"` → cùng ra `bachelor`.
- **Chuẩn hóa thành phố**: `"HCM"`, `"Saigon"`, `"Hồ Chí Minh"` → `"Ho Chi Minh"`.
- **Xóa bản ghi ma** ([schemas.py:320](app/schemas.py#L320)): LLM đôi khi bịa ra
  `{role: "Internship/Fresher", company: "", description: ""}`. Quy tắc giữ lại:
  phải có tên công ty, HOẶC có chức danh kèm ít nhất một chi tiết thật (mô tả
  hoặc ngày bắt đầu).
- **Danh sách chặn "kỹ năng giả"** ([schemas.py:255](app/schemas.py#L255)): ~45 cụm
  như `"teamwork"`, `"problem solving"`, `"communication"`, `"programming
  fundamentals"` bị **loại khỏi yêu cầu của JD**. Lý do rất cụ thể: những cụm này
  **không bao giờ xuất hiện dưới dạng token khớp được trong CV**, nên nếu giữ lại
  thì **mọi ứng viên đều thiếu chúng** → điểm D2 của tất cả bị kéo xuống một cách
  vô nghĩa.

**(f) Geocode một lần tại thời điểm parse** ([parser.py:428](app/services/parser.py#L428))

Địa chỉ được chuyển thành tọa độ **ngay khi parse**, không phải mỗi lần chấm điểm
— cùng triết lý với embedding. Lỗi geocode trả `(None, None)`, **không bao giờ làm
hỏng cả lời gọi parse**.

### ③ Vì sao thiết kế như vậy

- **Vì sao LLM chứ không phải NER/regex?** Bài toán này là *information extraction
  trên văn bản không có cấu trúc, đa ngôn ngữ, đa định dạng*. Mô hình NER truyền
  thống cần dữ liệu gán nhãn cho từng loại trường; LLM làm được **zero-shot** chỉ
  bằng mô tả schema. Đổi lại là chi phí và tính không tất định — nên phải có 4
  lớp kiểm soát ở trên.
- **Vì sao `temperature=0` cho trích xuất nhưng `0.4` cho nhận xét?** Trích xuất
  là bài toán có **một đáp án đúng** → cần tái lập được. Viết nhận xét cho HR là
  bài toán **sinh văn bản** → cần chút biến thiên để câu văn tự nhiên, không lặp
  khuôn.
- **Vì sao trường có cấu trúc thắng văn xuôi?** Vì `"Work Type: Hybrid"` là nhà
  tuyển dụng **chọn từ dropdown** — đó là dữ liệu, còn đoạn văn mô tả là văn
  quảng cáo. Tin dữ liệu, không tin quảng cáo.

### ④ Câu hỏi phản biện

**"LLM có bịa thông tin (hallucinate) không? Làm sao kiểm soát?"**
→ Có, và em xử lý ở 3 tầng: (1) **prompt** cấm suy diễn ở đúng chỗ nguy hiểm nhất
là địa chỉ và ý định chuyển việc; (2) **Pydantic** xóa các bản ghi rỗng/ma; (3)
**kiến trúc**: LLM chỉ *đọc và sắp xếp*, không được *tính toán* và **không được
chấm điểm**. Toàn bộ 5 chiều điểm đều do Python thuần tính từ JSON — nghĩa là dù
LLM có bịa thì cái nó bịa vẫn phải **hiện ra trong JSON để người kiểm tra thấy
được**, chứ không giấu được trong điểm số.

**"`temperature=0` thì kết quả có tuyệt đối tái lập không?"**
→ **Không tuyệt đối** — em nói thẳng điểm này. `temperature=0` chỉ làm giảm ngẫu
nhiên ở khâu lấy mẫu token, nhưng hạ tầng inference của nhà cung cấp (batching,
GPU floating-point non-determinism) vẫn có thể cho ra khác biệt nhỏ giữa 2 lần
gọi. Đó chính là **một lý do nữa** để 70% trọng số điểm nằm ở phần tất định: phần
biến thiên của LLM bị giới hạn ở khâu trích xuất, không lan vào công thức tính điểm.

**"Chi phí một lần parse là bao nhiêu?"**
→ Mỗi CV: 1–3 lần gọi LLM (thường 1) + 1 lần embedding. Với Gemini Flash thì chi
phí ở mức phần nghìn đô mỗi CV. Quan trọng hơn là **parse chỉ chạy 1 lần**; sau
đó chấm điểm cho vô số job đều miễn phí vì chỉ là số học.

**"Nếu nhà cung cấp LLM chết thì sao?"**
→ Có 3 provider thay thế được qua 1 biến môi trường. Hạn chế: hiện **chưa có
fallback tự động** khi provider lỗi giữa chừng — đây là việc em ghi nhận cần bổ
sung.

---

## 4. CHẶNG 3 — Embedding (text → vector 3072 chiều)

📁 [app/services/embedder.py](app/services/embedder.py) · [schemas.py:394](app/schemas.py#L394) (CV) · [schemas.py:587](app/schemas.py#L587) (JD)

> ⚠️ **Đây là phần hội đồng chắc chắn hỏi sâu** — 4 câu trong
> [QUESTIONARE.md](QUESTIONARE.md) đều thuộc chặng này. Đọc kỹ mục ④.

### ① Nói gì

> "Embedding là biến một đoạn văn bản thành một **dãy số** — ở đây là 3072 số thực
> — sao cho hai đoạn văn **có ý nghĩa gần nhau** thì hai dãy số cũng nằm gần nhau
> trong không gian. Nhờ đó máy so được 'Backend Developer' với 'Server-side
> Engineer' là gần nghĩa, dù **không có một từ nào trùng nhau**. Đây là thứ mà so
> khớp từ khóa không bao giờ làm được."

### ② Cơ chế thật trong code

- Model: **`gemini-embedding-001`**, **3072 chiều**, gọi qua endpoint tương thích
  OpenAI của Google.
- Client là hàm **đồng bộ (blocking)** nên được đẩy sang thread riêng
  (`run_in_executor`) để không chặn event loop của FastAPI.

**Nội dung đưa vào embedding được chọn lọc rất có chủ đích:**

| | ✅ Đưa vào | ❌ **Cố ý loại bỏ** |
| --- | --- | --- |
| **CV** | `summary`, `"role at company: description"` (**job mới nhất trước**), `"Project: tên + mô tả"`, học vấn, chứng chỉ, ngôn ngữ | **toàn bộ `skills[]` và mọi `tech_stack[]`** |
| **JD** | `title`, `responsibilities`, `"minimum N years"`, `"Education: X or above"` | **toàn bộ `required_skills` / `preferred_skills` / `nice_to_have_skills`** |

Quyết định này được đánh dấu trong code bằng hằng số
`EMBED_TEXT_VERSION = "v2-no-skills"` ([schemas.py:292](app/schemas.py#L292)) —
để nếu sau này đổi nội dung embed thì không ai vô tình so một vector kiểu cũ với
một vector kiểu mới.

### ③ Vì sao thiết kế như vậy — **luận điểm quan trọng nhất của cả đồ án**

> **Nếu tên kỹ năng vừa nằm trong text được embed (D1), vừa được so khớp ở D2, thì
> cùng một tín hiệu bị tính hai lần.** Trọng số thực tế của "kỹ năng" sẽ là
> 0.30 + 0.35 = **0.65**, trong khi tài liệu thiết kế nói là 0.35 — hệ thống *nói
> một đằng làm một nẻo*.

Mô hình cộng có trọng số (Simple Additive Weighting) đòi hỏi các tiêu chí **độc
lập ưu tiên** với nhau. Vì vậy em phân vai dứt khoát:

- **D1 chỉ đo "sự phù hợp về câu chuyện nghề nghiệp"** — vai trò, phạm vi trách
  nhiệm, bối cảnh nghiệp vụ. Ứng viên này *làm nghề gì*?
- **D2 chỉ đo "sự phù hợp về công cụ"** — ứng viên này *dùng công nghệ gì*?

Chi tiết nhỏ nhưng đáng nói: kinh nghiệm làm việc được **sắp xếp job gần nhất
trước** khi ghép text, để vector nghiêng về bối cảnh nghề nghiệp *hiện tại* thay
vì các công việc từ nhiều năm trước.

### ④ Trả lời 4 câu trong QUESTIONARE.md

#### **Câu 1 — "Tại sao chọn model embedding này?"**

Bốn lý do, xếp theo mức độ quan trọng:

1. **Chất lượng đa ngôn ngữ.** CV ở Việt Nam trộn lẫn tiếng Việt và tiếng Anh
   trong cùng một câu ("Phát triển API bằng Spring Boot"). `gemini-embedding-001`
   được huấn luyện đa ngôn ngữ và đưa cả hai thứ tiếng vào **cùng một không gian
   vector**, nên câu tiếng Việt và câu tiếng Anh cùng nghĩa vẫn gần nhau. Các
   model chỉ mạnh tiếng Anh (như `text-embedding-ada-002` đời cũ) làm việc này kém hơn.
2. **Xếp hạng cao trên MTEB** — bộ benchmark chuẩn ngành cho embedding, đo trên
   nhiều tác vụ (truy hồi, phân loại, tương đồng ngữ nghĩa) chứ không chỉ một tác vụ.
3. **Đồng bộ hạ tầng.** Dự án đã dùng Gemini làm LLM mặc định → cùng một API key,
   cùng một endpoint, giảm điểm hỏng. Và quan trọng: **embedding luôn cố định là
   Gemini kể cả khi LLM đổi sang Claude/Groq**, vì hai vector chỉ so sánh được với
   nhau khi cùng do một model sinh ra.
4. **Vận hành được ngay.** Đây là API có sẵn, không cần GPU, không cần tự host —
   phù hợp phạm vi đồ án. Em có cân nhắc chạy model mã nguồn mở tự host
   (Sentence-BERT), nhưng đánh đổi là phải có GPU và chất lượng tiếng Việt kém hơn.

#### **Câu 2 — "Tại sao lại là 3072 chiều?"**

Trả lời trung thực và mạch lạc:

> "3072 **không phải là con số em chọn** — đó là số chiều đầu ra mặc định của
> `gemini-embedding-001`, do kiến trúc mạng của model quy định. Câu hỏi đúng hơn
> là: *3072 chiều có ý nghĩa gì và có nên giảm không?*"

- **Số chiều là "sức chứa ngữ nghĩa".** Mỗi chiều là một trục ẩn mà mô hình học
  được trong quá trình huấn luyện (không có nghĩa tường minh kiểu "chiều 5 là độ
  trang trọng"). Càng nhiều chiều thì càng phân biệt được nhiều sắc thái tinh vi,
  nhưng tốn bộ nhớ và tính toán hơn.
- **Chi phí thực tế**: 3072 số thực × 4 byte ≈ **12 KB mỗi CV**. Với 10.000 CV là
  ~120 MB — hoàn toàn nằm trong khả năng của PostgreSQL + pgvector.
- **Có thể giảm được.** Model này hỗ trợ **Matryoshka Representation Learning** —
  kỹ thuật huấn luyện sao cho có thể **cắt bớt đuôi vector** (lấy 768 hoặc 1536
  chiều đầu) mà chỉ mất rất ít chất lượng. Ở quy mô đồ án chưa cần tối ưu nên em
  giữ nguyên 3072; nếu lên hàng triệu CV thì đây là nút vặn có sẵn.
- **Lưu ý bắt buộc**: **CV và JD phải cùng số chiều và cùng model**. So một vector
  3072 chiều với một vector 768 chiều là vô nghĩa về mặt toán học.

> 💡 Nếu hội đồng hỏi "sao trong tài liệu ghi 3071?" → đó là lỗi đánh máy trong
> [QUESTIONARE.md](QUESTIONARE.md); con số đúng là **3072**, kiểm tra được ở
> [embedder.py:78](app/services/embedder.py#L78).

#### **Câu 3 — "Cosine similarity hoạt động như thế nào?"**

Giải thích theo 3 tầng, dùng tầng nào tùy độ sâu câu hỏi:

**Tầng trực giác:** Coi mỗi văn bản là một **mũi tên** trong không gian. Cosine đo
**góc giữa hai mũi tên**, không quan tâm chúng dài bao nhiêu. Cùng hướng → giống
nghĩa. Vuông góc → không liên quan.

**Tầng công thức** ([scorer.py:40](app/services/scorer.py#L40)):
```
                    A · B              Σ(aᵢ × bᵢ)
cos(A, B) = ───────────────── = ──────────────────────────
                 ‖A‖ × ‖B‖        √(Σaᵢ²) × √(Σbᵢ²)
```
- Tử số là **tích vô hướng**: nhân từng cặp thành phần tương ứng rồi cộng lại.
  Hai vector cùng "mạnh" ở cùng những chiều → tử số lớn.
- Mẫu số là **tích độ dài hai vector** — bước chuẩn hóa này khiến kết quả **không
  phụ thuộc độ dài văn bản**.
- Kết quả nằm trong `[-1, 1]`: **1** = cùng hướng hoàn toàn, **0** = không liên
  quan, **−1** = ngược hướng. Với embedding văn bản, giá trị hầu như luôn dương.

**Tầng "vì sao là cosine chứ không phải khoảng cách Euclid":** vì cosine **bỏ qua
độ dài vector**, mà độ dài lại tương quan với **độ dài văn bản**. Một CV 3 trang và
một JD 10 dòng sẽ cho hai vector rất chênh nhau về độ dài dù cùng nói về một nghề.
Dùng Euclid thì CV dài luôn bị "phạt"; dùng cosine thì chỉ so **hướng ngữ nghĩa**.
(Về mặt toán học: trên các vector đã chuẩn hóa về độ dài 1, hai đại lượng này
tương đương nhau qua công thức `d² = 2(1 − cos)` — nên cosine là lựa chọn tự nhiên
và rẻ hơn.)

**Trong code**: `numpy` tính bằng `np.dot(a,b) / (norm(a) * norm(b))`, có bảo vệ
chia cho 0. Với 3072 chiều, phép này mất **micro-giây**.

#### **Câu 4 — "Model embedding hoạt động như thế nào?"**

Giải thích 5 bước, đủ sâu để thuyết phục mà không sa vào toán:

1. **Tokenization** — văn bản bị cắt thành các mảnh nhỏ (token), mỗi mảnh khoảng
   một từ hoặc một phần từ.
2. **Embedding lookup** — mỗi token được tra thành một vector khởi điểm. Ở bước
   này `"bank"` trong "river bank" và "投資 bank" vẫn giống hệt nhau.
3. **Các lớp Transformer + cơ chế self-attention** — đây là trái tim. Mỗi token
   được phép "nhìn" tất cả token khác trong câu và **cập nhật biểu diễn của mình
   theo ngữ cảnh**. Sau vài chục lớp như vậy, `"Java"` trong "Java Spring Boot" và
   `"Java"` trong "du lịch đảo Java" đã có vector **khác hẳn nhau**. Đây là điều
   mà các phương pháp cũ như TF-IDF hay Word2Vec không làm được.
4. **Pooling** — gộp N vector token thành **một** vector duy nhất đại diện cả đoạn
   (thường lấy trung bình có trọng số).
5. **Huấn luyện contrastive** — model được dạy bằng hàng triệu **cặp câu**: cặp
   cùng nghĩa thì bị "kéo lại gần", cặp khác nghĩa bị "đẩy ra xa". Chính bước này
   tạo ra tính chất mà em khai thác: **khoảng cách hình học = khoảng cách ngữ nghĩa**.

Kiến trúc mà em dùng là **bi-encoder** (theo Sentence-BERT của Reimers & Gurevych,
2019): CV và JD được mã hóa **độc lập** thành 2 vector rồi mới so sánh. Ưu điểm
quyết định: **vector CV tính một lần rồi lưu lại**, so với 1000 JD chỉ tốn 1000
phép nhân vô hướng. Nếu dùng cross-encoder (nhét cả CV và JD vào model cùng lúc,
chính xác hơn) thì phải chạy model 1000 lần — không khả thi cho hệ thống thực.

### ④b Câu hỏi phản biện khác

**"Vì sao loại bỏ skills khỏi text embed? Nghe như bỏ phí thông tin."**
→ Xem mục ③ ở trên — đây là câu trả lời mạnh nhất của em, **hãy chủ động nói
trước khi bị hỏi**. Thông tin không bị bỏ phí, nó được xử lý ở D2 với công cụ phù
hợp hơn (từ điển tri thức chính xác) thay vì bị làm nhòe trong vector.

**"Gửi CV lên API của Google có vi phạm quyền riêng tư không?"**
→ Câu hỏi rất chính đáng và em ghi nhận đây là **hạn chế thật**. Về mặt kỹ thuật,
đầu vào embedding đã là text đã lọc (không có số điện thoại/email), nhưng vẫn
chứa tên và lịch sử làm việc. Hướng xử lý trong môi trường thật: (1) hợp đồng xử
lý dữ liệu với nhà cung cấp, (2) thông báo và lấy đồng ý của ứng viên, (3) nếu
yêu cầu cao thì chuyển sang model tự host trong hạ tầng nội bộ.

**"Embedding có thiên lệch (bias) không?"**
→ Có — đây là rủi ro đã được ghi nhận trong nghiên cứu (Bolukbasi et al., 2016:
embedding học được cả định kiến giới trong dữ liệu huấn luyện). Đó là **lý do
kiến trúc** để D1 chỉ chiếm **0.30** và không có quyền quyết định một mình: 70%
điểm nằm ở các quy tắc tất định mà con người đọc và kiểm tra được.

---

## 5. CHẶNG 4 — Chấm điểm 5 chiều

📁 [app/services/scorer.py](app/services/scorer.py)

### Khung tổng thể — 3 nguyên tắc xuyên suốt phải nhớ

```
final_score = ( D1×0.30 + D2×0.35 + D3×0.20 + D4×0.10 + D5×0.05 ) × 100
```

| Nguyên tắc | Nội dung | Áp dụng ở |
| --- | --- | --- |
| **Thiếu dữ liệu → 0.5 (trung lập)** | Ứng viên **không bị phạt** vì hệ thống trích xuất/geocode thất bại | D1 (thiếu vector), D4 (CV không ghi bằng), D5 (thiếu tọa độ / OSRM lỗi) |
| **JD không yêu cầu → 1.0 (đủ điểm)** | Không có yêu cầu thì không thể không đạt | D2 (JD không nêu kỹ năng), D3 (không yêu cầu số năm), D4 (không yêu cầu bằng) |
| **Vượt yêu cầu → chặn trần ở 1.0** | Tiến sĩ ứng tuyển vị trí cần cử nhân **không** được cộng thêm điểm | D3, D4 |

> **Cách nói nguyên tắc thứ 3 cho hay:** "Điểm số đo *mức độ đáp ứng yêu cầu*, chứ
> không đo *ứng viên giỏi đến đâu*. 10 năm kinh nghiệm cho vị trí cần 2 năm không
> làm ứng viên phù hợp hơn — thậm chí evaluator sẽ gắn cờ `over_qualified` để cảnh
> báo HR về rủi ro ứng viên nhanh nghỉ việc."

Trọng số có thể **HR tùy chỉnh cho từng tin tuyển dụng** qua trường `weights` trong
request ([score.py:45](app/api/score.py#L45)), có kiểm tra chặt: phải đủ đúng 5
khóa, mỗi giá trị trong `[0,1]`, và **tổng phải bằng 1.0**.

---

### 5.1 D1 — Semantic (ngữ nghĩa) — W = 0.30

**Công thức** ([scorer.py:47](app/services/scorer.py#L47)):
```
raw = cosine_sim(cv_embedding, jd_embedding)
D1  = clamp( (raw − COSINE_MIN) / (COSINE_MAX − COSINE_MIN),  0,  1 )
```

**② Chi tiết cần biết**
- Mặc định hiện tại `COSINE_MIN=0.0`, `COSINE_MAX=1.0` → **không kéo giãn**, D1
  chính là cosine thô.
- Thiếu 1 trong 2 vector → **D1 = 0.5** (trung lập).

**③ Vì sao có cơ chế kéo giãn (stretch)?**
Trong thực tế, cosine giữa hai văn bản tiếng người **hiếm khi xuống dưới ~0.5** —
kể cả hai văn bản chẳng liên quan gì (hiện tượng **anisotropy**: các vector embedding
có xu hướng dồn về một vùng hẹp của không gian, Ethayarajh 2019). Nghĩa là dải
điểm hữu ích thực tế có thể chỉ là `[0.6, 0.9]`. Cơ chế kéo giãn cho phép ánh xạ
đúng dải đó về `[0,1]` để D1 **dùng hết thang điểm** thay vì mọi ứng viên đều được
70–85 điểm và không phân biệt được ai hơn ai.

**④ Câu hỏi phản biện**

**"Sao hiện tại lại để 0.0/1.0, tức là tắt tính năng đó?"**
→ Vì để hiệu chỉnh đúng `COSINE_MIN`/`COSINE_MAX` cần **dữ liệu thật**: chạy trên
một tập CV–JD đủ lớn, xem phân phối cosine thực tế rơi vào đâu (ví dụ lấy phân vị
5% và 95%) rồi mới đặt ngưỡng. Em **chưa có gold set** nên chọn để giá trị trung
tính thay vì bịa ra một con số. Hai tham số đã sẵn sàng trong `.env`, chỉ cần chỉnh
khi có dữ liệu — **đây là quyết định có ý thức, không phải bỏ sót**.

**"Cosine 0.75 nghĩa là gì? Phù hợp 75%?"**
→ **Không.** Cosine là một đại lượng **thứ tự (ordinal)**, không phải tỷ lệ phần
trăm. Nó chỉ có ý nghĩa khi **so sánh tương đối giữa các ứng viên trên cùng một
JD**: ứng viên có cosine 0.80 gần với JD hơn ứng viên có 0.75. Diễn giải "phù hợp
75%" là sai về mặt đo lường — đây cũng chính là lý do phải có cơ chế kéo giãn.

---

### 5.2 D2 — Skills (kỹ năng) — W = 0.35 — **phần nặng thuật toán nhất**

📁 [app/services/skill_matcher.py](app/services/skill_matcher.py) (490 dòng) +
[app/data/skill_data.json](app/data/skill_data.json) + [app/data/skill_implies.json](app/data/skill_implies.json)

### ① Nói gì

> "Đây là chiều có trọng số cao nhất và cũng là phần em đầu tư nhiều nhất. Bài
> toán nghe đơn giản — CV có kỹ năng JD đòi hay không — nhưng thực tế đầy bẫy:
> JD ghi 'ReactJS', CV ghi 'React'; JD đòi 'JavaScript', CV chỉ ghi 'React' (mà
> biết React thì đương nhiên biết JavaScript); JD đòi 'JLPT N3', CV có 'JLPT N2'
> (N2 cao hơn N3 nên phải tính là đạt, dù hai chuỗi khác nhau).
>
> Em giải bằng một **thác 4 tầng** cộng một tầng phụ, chạy tuần tự, **dừng ngay ở
> tầng đầu tiên khớp được**."

### ② Cơ chế thật trong code

**(a) Gom kỹ năng từ CV — không chỉ mục "Skills"** ([skill_matcher.py:220](app/services/skill_matcher.py#L220))

Nguồn: `skills[]` + `work_experience[].tech_stack` + `projects[].tech_stack` +
`languages` + `certifications`.

Với ngôn ngữ/chứng chỉ còn có bước **tách chuỗi con**: `"Japanese - JLPT N3"` được
tách thành `{"japanese - jlpt n3", "japanese", "jlpt n3"}` để yêu cầu `"JLPT N3"`
của JD khớp được vào đúng mảnh đó.

Toàn bộ việc chuẩn hóa CV chạy **đúng 1 lần** rồi lưu vào `CVContext`
([skill_matcher.py:318](app/services/skill_matcher.py#L318)) — nếu JD có 20 yêu cầu
thì không phải chuẩn hóa lại 20 lần.

**(b) Thác 4 tầng** ([skill_matcher.py:337](app/services/skill_matcher.py#L337))

| Tầng | Cơ chế | Ví dụ khớp được | Chi phí |
| --- | --- | --- | --- |
| **Layer 0** — Direct | So chuỗi trực tiếp sau khi lowercase | `"Python"` ↔ `"python"` | rẻ nhất |
| **Layer 1** — Identity | Chuẩn hóa **cả hai phía** về tên chuẩn qua `skill_data.json` rồi so | `"ReactJS"` ↔ `"React.js"` (cùng ra `reactjs`) | rẻ |
| **Layer 2** — Entailment | "Biết X thì tất yếu biết Y", tra `skill_implies.json` | JD đòi `JavaScript`, CV có `React` → **đạt** | rẻ (đã dựng sẵn) |
| **Layer 3** — Fuzzy | `SequenceMatcher` ≥ **0.85** trên chuỗi thô | `"Postgresql"` ↔ `"PostgreSQL"`, `"pythonn"` ↔ `"Python"` | đắt nhất |
| **Tầng phụ** — Proficiency | So **thứ bậc** trong cùng hệ chứng chỉ | JD đòi `JLPT N3`, CV có `JLPT N2` → **đạt** | rẻ |

**Thứ tự các tầng là có chủ ý**: chính xác nhất trước, lỏng nhất sau. Layer 3 (fuzzy)
đặt **cuối cùng** vì nó vừa tốn kém vừa dễ khớp nhầm — chỉ chạy khi 3 tầng chính
xác đều trượt.

**(c) Chi tiết tầng canonicalization (Layer 1)** ([skill_matcher.py:77](app/services/skill_matcher.py#L77))

Vấn đề: LLM trả `"ASP.NET Core"` (Title Case, có dấu cách) nhưng dữ liệu của em
theo chuẩn tag Stack Overflow (`"asp.net-core"`: chữ thường, dấu cách → gạch nối).
Hàm `to_stackoverflow_format` sinh ra **danh sách biến thể** theo thứ tự ưu tiên:
```
"ASP.NET Core" → ["asp.net core", "asp.net-core", "asp.netcore",
                  "aspnet core", "aspnet-core", "aspnetcore"]
"Node.js"      → ["node.js", "nodejs", ...]
```
rồi thử từng cái cho đến khi tra được. Biến thể thừa vô hại vì dừng ở cái đầu tiên khớp.

**(d) Nguồn gốc dữ liệu tri thức — hội đồng rất hay hỏi**

| File | Quy mô | Nguồn |
| --- | --- | --- |
| `skill_data.json` | **9.524 mục** (3.988 tên chuẩn + 5.536 từ đồng nghĩa) | Crawl từ **API Stack Exchange**: lấy toàn bộ tag của Stack Overflow + bảng synonym chính thức của cộng đồng ([crawl_so_tags.py](app/data/crawl_so_tags.py), [build_skill_data.py](app/data/build_skill_data.py)), sau đó bổ sung tay các domain còn thiếu (AI/Python, DevOps, QA, IT support) |
| `skill_implies.json` | **1.504 khóa / 1.707 cạnh** | **Viết tay** — đây là tri thức chuyên gia, không crawl được |

**Cấu trúc `skill_data.json`** là một dict phẳng `{tag: canonical | null}`, trong đó
`null` nghĩa là **"chính key này đã là tên chuẩn"**, không phải "bỏ qua". Đây là mô
hình **synonym ring** kinh điển trong entity resolution.

**Bao đóng bắc cầu (transitive closure)** — chi tiết thuật toán đáng khoe:
Đồ thị implies là một **DAG** (đồ thị có hướng không chu trình). Nếu chỉ lưu cạnh
trực tiếp `nestjs → typescript` và `typescript → javascript`, thì lúc chạy phải
duyệt đồ thị để biết `nestjs → javascript`. Thay vì vậy, em chạy **trước một lần**
script [close_implies.py](app/data/close_implies.py) để **làm phẳng toàn bộ quan hệ
gián tiếp vào file** (kỹ thuật *materialization*, họ hàng với thuật toán Warshall
1962). Kết quả: lúc chạy chỉ cần **một phép tra bảng O(1)**, không duyệt đồ thị.

Có hẳn một nhóm test (nhóm **L** trong `test_d2_skills.py`) đóng vai **bất biến dữ
liệu**: nếu ai sửa tay `skill_implies.json` mà quên chạy lại `close_implies.py`
thì test **fail ngay**, thay vì để hệ thống âm thầm bỏ sót suy luận.

**(e) Tầng phụ proficiency — vì sao phải tách riêng** ([skill_matcher.py:165](app/services/skill_matcher.py#L165))

Hỗ trợ 7 hệ: **JLPT, HSK, TOPIK, IELTS, TOEIC, TOEFL, CEFR**.

Lý do phải xử lý riêng, không dùng 4 tầng trên được:
- **Không so exact được**: JD đòi N3, CV có N2 → hai chuỗi khác nhau nhưng N2
  **cao hơn** nên phải tính đạt.
- **Fuzzy thì nguy hiểm chết người**: `"N4"` và `"N3"` giống nhau tới **86% ký tự**
  (vượt ngưỡng 0.85!) nhưng N4 **thấp hơn** N3 → nếu để fuzzy xử lý sẽ cho đạt
  **sai**. Vì vậy code **chặn Layer 3 với mọi token là chứng chỉ ngôn ngữ**
  ([skill_matcher.py:362](app/services/skill_matcher.py#L362)) và bắt buộc đi qua
  tầng proficiency.
- JLPT có **thứ tự ngược** (N1 giỏi nhất) nên rank được tính `6 − số`.

**(f) OR-group — "A hoặc B đều được"** ([skill_matcher.py:411](app/services/skill_matcher.py#L411))

JD ghi *"React, TypeScript, hoặc Vue"* → LLM gộp thành **một** yêu cầu:
`{skill: "React", alternatives: ["TypeScript", "Vue"]}`. Chỉ cần khớp **một** trong
ba là đủ điểm cho cả nhóm. Nếu tách thành 3 yêu cầu riêng thì ứng viên biết React
sẽ bị trừ điểm vì "thiếu TypeScript và Vue" — **hoàn toàn sai ý JD**.

Khi nhiều alternative cùng khớp, hệ thống chọn cái khớp ở **tầng sớm nhất** (bảng
`_LAYER_RANK`: layer0=5 > layer1=4 > layer2=3 > layer3=2 > proficiency=1) để
`matched_via` trả về bằng chứng đáng tin nhất.

**(g) Công thức tính điểm — 3 tầng yêu cầu, chấm nhị phân** ([skill_matcher.py:425](app/services/skill_matcher.py#L425))

```
        Σ (wᵢ × mᵢ)
D2 = ─────────────────        mᵢ ∈ {0, 1}   ← nhị phân, KHÔNG có điểm một phần
           Σ wᵢ
```

| Tầng yêu cầu của JD | Trọng số wᵢ | Ghi chú |
| --- | --- | --- |
| `required_skills` | **`req.weight` ∈ {1,2,3}** do LLM gán | Kỹ năng từ danh sách tag "Required Skills:" luôn = **3** |
| `preferred_skills` | **2** (hằng số) | Danh sách phẳng, cả tầng dùng chung 1 trọng số |
| `nice_to_have_skills` | **1** (hằng số) | Tầng thấp nhất |

JD không nêu kỹ năng nào ở cả 3 tầng → **D2 = 1.0**.

### ③ Vì sao thiết kế như vậy

**Vì sao chấm nhị phân (0 hoặc 1) thay vì cho điểm một phần?**
Đây là một **thay đổi thiết kế có chủ ý** so với bản trước (bản cũ cho 1.0 khớp
chính xác / 0.9 fuzzy / 0.3–0.5 cùng nhóm). Ba lý do:

1. **Các hệ số 0.9 và 0.3–0.5 không có cơ sở hiệu chỉnh** — chúng được chọn tùy ý
   và không có cách nào đo được là đúng hay sai.
2. **Không giải thích được cho HR.** Câu "ứng viên được 0.4 điểm cho Vue vì biết
   React" là câu không bảo vệ được trước nhà tuyển dụng.
3. **Nhị phân + entailment tường minh chuyển tri thức từ "hệ số ma thuật" sang
   "quy tắc kiểm toán được".** Bây giờ mỗi điểm đều truy vết được: khớp qua tầng
   nào (`matched_layer`) và nhờ kỹ năng cụ thể nào trong CV (`matched_via`). Nếu
   HR không đồng ý với một suy luận, họ chỉ cần sửa một dòng trong
   `skill_implies.json` — chứ không phải chỉnh một hệ số mờ ám.

**Vì sao đưa cả 3 tầng yêu cầu vào D2 thay vì chỉ tính required?**
Vì JD phân tầng là để **phân biệt ứng viên**. Nếu chỉ tính `required`, hai ứng viên
cùng đạt hết yêu cầu bắt buộc sẽ **bằng điểm nhau tuyệt đối**, dù một người có
thêm toàn bộ kỹ năng ưu tiên. Đưa cả 3 tầng vào với trọng số giảm dần (3 / 2 / 1)
khiến thiếu kỹ năng ưu tiên vẫn kéo điểm xuống — **nhưng nhẹ hơn** thiếu kỹ năng
bắt buộc. Đúng với ý nghĩa của việc phân tầng.

### ④ Câu hỏi phản biện

**"Vì sao ngưỡng fuzzy là 0.85?"**
→ Đây là ngưỡng thực nghiệm, chọn **cao có chủ ý** để ưu tiên **precision hơn
recall**: chỉ bắt biến thể chính tả/định dạng, không gộp nhầm hai kỹ năng khác
nhau. Ví dụ kiểm chứng: `"Java"` vs `"JavaScript"` chỉ đạt ~0.55 → **không khớp**
(đúng). Nhưng em **thừa nhận một ca sai đã biết**: `"angular"` vs `"angularjs"`
đạt 0.875 → khớp, trong khi thực tế đây là **hai framework khác hẳn nhau**. Hướng
sửa: chặn Layer 3 khi cả hai phía đều tra ra tên chuẩn hợp lệ nhưng **khác nhau**
— vì khi đó ta đã *biết chắc* chúng là hai thực thể riêng biệt.

**"1.504 quy tắc implies viết tay — làm sao đảm bảo đầy đủ?"**
→ **Không đảm bảo được, và em nói thẳng điều đó.** Đây chính là *knowledge
acquisition bottleneck* — nút thắt kinh điển của mọi hệ chuyên gia (đã có nghiên
cứu từ những năm 1980). Tính chất của bộ quy tắc này là: **có tính đúng đắn
(soundness)** — mọi quy tắc đã viết đều đúng; **không có tính đầy đủ
(completeness)** — chắc chắn còn thiếu quy tắc. Hệ quả thực tế của việc thiếu là
**bỏ sót một trận khớp đáng lẽ có** (false negative), chứ **không** tạo ra khớp
sai. Đó là kiểu lỗi an toàn hơn nhiều trong tuyển dụng. Hướng mở rộng: bootstrap
tự động từ **thống kê đồng xuất hiện tag trên Stack Overflow** (những tag hay đi
cùng nhau là ứng viên cho quan hệ implies), sau đó cho người duyệt.

**"Quan hệ implies có bị dùng ngược chiều không? Biết JavaScript đâu có nghĩa là biết React."**
→ Đúng, và đồ thị của em **có hướng một chiều**: `react → javascript` **không** kéo
theo `javascript → react`. Nhóm test **D** trong `test_d2_skills.py` kiểm tra đúng
việc này ("không rò rỉ chiều ngược").

**"D2 có phạt ứng viên có quá nhiều kỹ năng thừa không?"**
→ **Không, và đây là chủ ý.** D2 là độ đo **bất đối xứng**: chỉ đo "CV đáp ứng bao
nhiêu phần yêu cầu của JD", không đo chiều ngược lại. Kỹ năng thừa được báo cáo
riêng cho HR qua trường `bonus_skills` để họ tự đánh giá — chứ không tự động cộng
hay trừ điểm.

---

### 5.3 D3 — Experience (kinh nghiệm) — W = 0.20

**Công thức** ([scorer.py:105](app/services/scorer.py#L105)):
```
D3 = min( tổng_số_năm_CV / số_năm_JD_yêu_cầu , 1.0 )
JD không yêu cầu → 1.0
```

**② Chi tiết cần biết**
- `tổng_số_năm_CV` = `total_exp_months / 12`, trong đó `total_exp_months` được tính
  bằng **merge interval** ([schemas.py:63](app/schemas.py#L63)) — công việc chồng
  lấn thời gian **chỉ đếm một lần**.
- Ngày `"present"` được quy về **tháng hiện tại**; ngày thiếu/không đọc được cũng
  fallback về tháng hiện tại.

**③ Vì sao KHÔNG có hệ số "độ liên quan" hay "độ gần đây"?**

Đây là câu hội đồng rất hay hỏi: *"3 năm làm kế toán có bằng 3 năm làm backend không?"*

Câu trả lời chuẩn bị sẵn:
> "Về mặt hệ thống thì **không bằng**, nhưng sự khác biệt đó **đã được D1 và D2 xử
> lý rồi**. D1 so ngữ nghĩa mô tả công việc — kế toán và backend cho cosine thấp.
> D2 so kỹ năng — kế toán không có Java, Spring. Nếu em nhân thêm một hệ số 'độ
> liên quan' vào D3 nữa thì cùng một tín hiệu 'có liên quan hay không' bị **tính
> đến ba lần** trong công thức cộng có trọng số — chính là lỗi mà em đã cẩn thận
> tránh khi loại skills khỏi text embed ở D1. **D3 cố tình chỉ đo một thứ duy
> nhất: số lượng thời gian.**"

**④ Câu hỏi phản biện**

**"Ứng viên 1.9 năm cho JD đòi 2 năm bị 0.95 điểm — có quá khắt khe không?"**
→ Ở phần chấm điểm thì đúng là tuyến tính như vậy. Nhưng ở phần **nhận xét cho
HR**, evaluator dùng ngưỡng mềm hơn: đạt **≥ 80%** yêu cầu đã được xếp verdict
`sufficient` ([evaluator.py:133](app/services/evaluator.py#L133)). Nghĩa là điểm số
phản ánh mức độ liên tục, còn nhận xét cho người đọc thì khoan dung hơn.

**"Có tính kinh nghiệm từ project/thực tập không?"**
→ Prompt yêu cầu LLM trích **mọi loại kinh nghiệm** kể cả thực tập và part-time.
Project cá nhân không có mốc thời gian nên không vào D3, nhưng vẫn đóng góp vào
**D1** (mô tả project nằm trong text embed) và **D2** (`projects[].tech_stack` là
nguồn kỹ năng).

---

### 5.4 D4 — Education (học vấn) — W = 0.10

**Công thức** ([scorer.py:123](app/services/scorer.py#L123)):
```
D4 = min( bậc_bằng_CV / bậc_bằng_JD_yêu_cầu , 1.0 )
JD không yêu cầu       → 1.0
CV không ghi bằng cấp  → 0.5  (trung lập, không phạt vì thiếu dữ liệu)
```

**② Bảng quy đổi bậc** ([schemas.py:96](app/schemas.py#L96)):
`high_school=1` · `associate=2` · `bachelor=3` · `master=4` · `phd=5` · **`other=1`**

Ví dụ: JD đòi cử nhân (3), CV có cao đẳng (2) → D4 = 2/3 = 0.67.
JD đòi cử nhân (3), CV có thạc sĩ (4) → min(4/3, 1) = **1.0** (không cộng thêm).

**③ Vì sao trọng số chỉ 0.10?**
Vì trong ngành phần mềm, **bằng cấp là tín hiệu yếu** so với kỹ năng thực tế và
kinh nghiệm. Đặt trọng số thấp là một tuyên bố về giá trị: hệ thống không muốn
loại một lập trình viên giỏi vì họ học cao đẳng.

**④ Câu hỏi phản biện**

**"Vì sao `other = 1`, bằng với trung học phổ thông?"**
→ Đây là lựa chọn **thận trọng có ý thức**. `other` là những trường hợp không xếp
được vào 5 bậc chuẩn (chứng chỉ nghề, bootcamp, khóa học trực tuyến). Nếu gán cao
thì tạo lỗ hổng — bất kỳ chứng chỉ nào cũng thành "tương đương đại học". Nếu gán 0
thì phạt nặng hơn cả người không ghi gì. Gán 1 = coi như "có nền tảng cơ bản".
Em ghi nhận đây là điểm có thể tranh luận.

**"Phép chia bậc bằng cấp có hợp lệ về mặt toán học không?"**
→ Câu hỏi rất sắc, và em trả lời thẳng: **về lý thuyết đo lường thì không hoàn
toàn hợp lệ**. Theo phân loại thang đo của Stevens (1946), bằng cấp là **thang thứ
tự (ordinal)** — ta biết thạc sĩ > cử nhân, nhưng **không có cơ sở nói "thạc sĩ
bằng 4/3 cử nhân"**. Phép chia chỉ hợp lệ trên **thang tỷ lệ (ratio)**. Em dùng
phép chia như một **giả định đơn giản hóa** để có một hàm đơn điệu tăng, trơn,
trong `[0,1]` — và em **nêu rõ giả định này** thay vì giấu đi. Nếu cần chặt chẽ
hơn thì nên thay bằng **ma trận so sánh cặp rút ra bằng AHP** (Saaty, 1980) — dùng
đánh giá của chuyên gia để định lượng khoảng cách giữa các bậc.

---

### 5.5 D5 — Location + Work Mode (vị trí) — W = 0.05

📁 [scorer.py:149](app/services/scorer.py#L149) · [app/services/location_service.py](app/services/location_service.py)

**Luồng quyết định, theo đúng thứ tự trong code:**
```
1. JD là remote                     → 1.0   (làm từ xa thì vị trí vô nghĩa)
2. CV ghi rõ sẵn sàng chuyển chỗ ở  → 1.0
3. Thiếu lat/lng ở 1 trong 2 phía   → 0.5   (trung lập)
4. Gọi OSRM lấy thời gian lái xe t (phút)
     lỗi → nghỉ 0.5s → thử lại 1 lần → vẫn lỗi → 0.5
5. T_max = 45 phút (onsite)  hoặc  75 phút (hybrid)
6. D5 = max(0, 1 − t / T_max)
```

**② Chi tiết cần biết**
- **Geocode** (địa chỉ → tọa độ) dùng **Nominatim** của OpenStreetMap, chạy **tại
  thời điểm parse**, không phải lúc chấm điểm. Có 2 lượt thử: chuỗi đầy đủ +
  `", Vietnam"`, nếu trượt thì chỉ lấy đoạn cuối (thường là tên thành phố).
  Bắt buộc gửi `User-Agent` mô tả ứng dụng — không có thì Nominatim chặn 403.
- **Routing** (2 tọa độ → thời gian lái xe) dùng **OSRM**, chạy **tại thời điểm
  chấm điểm** vì nó phụ thuộc vào *cặp* CV–JD.
- Timeout 5s cho cả hai API.
- JD phía .NET lưu `address` và `city` ở **2 cột riêng**, nên parser phải **ghép
  lại** `"raw_address, city"` trước khi geocode để Nominatim đủ ngữ cảnh.

**③ Vì sao dùng thời gian lái xe thay vì so tên thành phố (bản trước) hay khoảng cách đường chim bay?**
- So tên thành phố quá thô: hai người cùng ở "Hà Nội" nhưng một người ở Đông Anh,
  một người cách văn phòng 800m — hoàn toàn khác nhau về khả năng đi làm hằng ngày.
- Khoảng cách đường chim bay bỏ qua địa hình và mạng lưới đường. Ở Việt Nam, cách
  nhau 5km qua sông có thể mất 40 phút.
- **Thời gian di chuyển là đại lượng ứng viên thật sự cảm nhận** — nó là thứ quyết
  định người ta có nhận việc và trụ lại được hay không.
- `T_max` khác nhau theo hình thức làm việc vì **hybrid chỉ lên văn phòng 2–3
  buổi/tuần**, nên người ta chịu đựng được quãng đường xa hơn (75 phút thay vì 45).

**④ Câu hỏi phản biện**

**"Vì sao 45 và 75 phút? Có nghiên cứu nào không?"**
→ Đây là **ngưỡng thực nghiệm dựa trên bối cảnh giao thông đô thị Việt Nam**, không
phải hằng số từ nghiên cứu. Ý tưởng: 45 phút mỗi chiều là ngưỡng chịu đựng thông
thường cho việc đi làm hằng ngày; hybrid nhân hệ số lên vì tần suất thấp hơn. Cả
hai là hằng số trong code, chỉnh được dễ dàng, và với **trọng số chỉ 0.05** thì
sai lệch ở đây ảnh hưởng rất nhỏ tới điểm cuối.

**"Sao trọng số D5 chỉ 0.05 mà lại tốn gọi mạng lúc chấm điểm — không phải là đắt so với giá trị không?"**
→ **Đây là câu hỏi sắc nhất về D5 và em nên chủ động nêu trước.** Đúng là có vấn
đề về khả năng mở rộng: chấm 100 ứng viên cho một job thì gọi OSRM 100 lần, mỗi
lần timeout 5s + có thể retry. Ba hướng xử lý em đã xác định: (1) **cache theo cặp
tọa độ** — cùng một văn phòng thì mọi ứng viên chỉ cần tính route một lần cho mỗi
điểm xuất phát; (2) **self-host OSRM** để bỏ giới hạn của server demo công cộng;
(3) tính D5 **theo lô, không đồng bộ**. Hiện tại chưa cài vì service đang giữ
nguyên tắc **stateless (không cache, không DB)** — một sự đánh đổi có ý thức giữa
tính đơn giản của kiến trúc và hiệu năng ở quy mô lớn.

**"Dùng server demo công cộng của OSRM/Nominatim có ổn cho production không?"**
→ **Không.** Cả hai đều là dịch vụ cộng đồng miễn phí, có giới hạn tần suất, không
cam kết SLA, và chính sách sử dụng cấm dùng cho tải lớn. Đây là lựa chọn phù hợp
cho **phạm vi đồ án**; lên production bắt buộc phải self-host OSRM (dữ liệu OSM
Việt Nam chỉ vài GB) hoặc mua dịch vụ có SLA. Em ghi nhận rõ điều này.

**"Nếu API bản đồ chết thì cả hệ thống chấm điểm chết theo?"**
→ Không. Mọi lời gọi đều bọc `try/except` và **fallback về 0.5 trung lập**. Chấm
điểm vẫn chạy bình thường, chỉ mất độ chính xác của một chiều chiếm 5%.

---

## 6. CHẶNG 5 — Tổng hợp điểm & nhận xét cho HR

📁 [app/api/score.py](app/api/score.py) · [app/services/evaluator.py](app/services/evaluator.py)

### ① Nói gì

> "Bước cuối gộp 5 chiều thành một điểm 0–100 và song song đó tạo ra **phần giải
> thích** cho HR: kỹ năng nào khớp, kỹ năng nào thiếu, thiếu ở tầng bắt buộc hay
> tầng ưu tiên, kinh nghiệm/học vấn có đạt không. Với những hồ sơ HR muốn xem kỹ
> thì có thêm một đoạn **nhận xét tiếng Việt** do LLM viết."

### ② Cơ chế thật trong code

**(a) Hai việc chạy song song** ([score.py:77](app/api/score.py#L77)):
`calculate_score` (đẩy sang thread vì thuần CPU) và `evaluate_cv_for_job` (async)
chạy đồng thời qua `asyncio.gather`.

**(b) `include_narrative` — công tắc chi phí.** Mặc định `false`: `/score` chỉ chạy
Python thuần (~1ms), **không tốn LLM**. Chỉ khi HR bấm xem chi tiết mới bật lên
hoặc gọi `/ai/evaluate` riêng. Đây là thiết kế quan trọng: chấm điểm hàng loạt phải
rẻ, giải thích chi tiết mới đắt.

**(c) Evaluator dùng CHUNG một nguồn với scorer** ([evaluator.py:52](app/services/evaluator.py#L52)).
Cả hai đều gọi `matcher.evaluate_tiers(jd, ctx)`. Đây là chi tiết kỹ thuật đáng nói:
nó đảm bảo `skill_match_rate` hiển thị cho HR **luôn khớp với điểm D2 dùng để xếp
hạng**. Nếu viết 2 công thức riêng thì sớm muộn chúng sẽ lệch nhau và HR sẽ thấy
"khớp 80% mà điểm kỹ năng chỉ 65" — mất hoàn toàn niềm tin vào hệ thống.

**(d) Phân loại kỹ năng thiếu vào 3 nhóm** ([evaluator.py:62](app/services/evaluator.py#L62)):
`missing_must_have` (tầng required, weight ≥ 3) · `missing_preferred` (tầng
preferred, hoặc required nhưng weight < 3) · `missing_nice_to_have`.
Cộng thêm `bonus_skills` — kỹ năng CV có mà JD không nêu (so trên dạng chuẩn hóa
để `"React"` không bị coi là thừa khi JD đòi `"React.js"`), giới hạn 8 mục.

**(e) Verdict kinh nghiệm** ([evaluator.py:105](app/services/evaluator.py#L105)):
`not_required` · `over_qualified` (≥ **2×** yêu cầu) · `sufficient` (≥ **80%**) ·
`insufficient`. Verdict học vấn: `not_required` / `exceeds` / `meets` / `below`.

**(f) LLM chỉ "viết văn", không "phán xét"** ([evaluator.py:181](app/services/evaluator.py#L181)).
Điểm này phải nhấn mạnh: **mọi con số trong prompt đều do Python tính sẵn** — tỷ lệ
khớp, danh sách kỹ năng thiếu, số năm kinh nghiệm. LLM chỉ nhận bảng dữ liệu đó và
diễn đạt thành đoạn văn ~10 câu.

Và prompt **cấm LLM đưa ra khuyến nghị hành động** ("nên phỏng vấn" / "nên loại"):
> *"...KHÔNG đưa ra khuyến nghị hành động — quyết định đó do HR tự đánh giá dựa trên
> điểm số hệ thống đã tính, không phải bạn."*

### ③ Vì sao cấm LLM đưa khuyến nghị — **luận điểm về đạo đức, nên nói**

Hai lý do:
1. **Tránh mâu thuẫn nội bộ.** Nếu LLM viết "ứng viên rất tiềm năng, nên phỏng vấn"
   trong khi điểm hệ thống là 45/100, HR không biết tin cái nào. Hệ thống phải nói
   **một tiếng nói duy nhất**.
2. **Trách nhiệm pháp lý.** Tuyển dụng thuộc nhóm **rủi ro cao** theo EU AI Act
   (Annex III), và GDPR Điều 22 cho phép cá nhân **từ chối bị quyết định hoàn toàn
   tự động**. Hệ thống của em được thiết kế ở vai trò **hỗ trợ ra quyết định**, đưa
   thông tin và điểm số có giải thích — **con người vẫn là người quyết định**. Việc
   cấm LLM ra khuyến nghị không phải chi tiết vụn vặt, nó là **cách hiện thực hóa
   nguyên tắc "human-in-the-loop" ở tầng code**.

---

## 7. Bảng số liệu bắt buộc thuộc lòng

| Hạng mục | Con số | Nơi kiểm chứng |
| --- | --- | --- |
| Trọng số D1/D2/D3/D4/D5 | **0.30 / 0.35 / 0.20 / 0.10 / 0.05** (tổng = 1.0, có validator kiểm tra) | [config.py:47](app/config.py#L47) |
| Số chiều embedding | **3072** | [embedder.py:78](app/services/embedder.py#L78) |
| Model embedding | `gemini-embedding-001` | [config.py:41](app/config.py#L41) |
| LLM mặc định / production | `gemini-2.5-flash` / `claude-sonnet-4-6` | [config.py:29](app/config.py#L29) |
| Ngưỡng kích hoạt OCR | chất lượng **< 60**/100 | [pdf_extractor.py:51](app/services/pdf_extractor.py#L51) |
| OCR: DPI / ngôn ngữ | **200 DPI** / `eng+vie` | [pdf_extractor.py:188](app/services/pdf_extractor.py#L188) |
| Phát hiện 2 cột | **45% / 55%**, header **16%** chiều cao | [pdf_extractor.py:105](app/services/pdf_extractor.py#L105) |
| Ngưỡng fuzzy Layer 3 | **0.85** | [skill_matcher.py:120](app/services/skill_matcher.py#L120) |
| Từ điển kỹ năng | **9.524** mục (3.988 chuẩn + 5.536 đồng nghĩa) | `app/data/skill_data.json` |
| Đồ thị suy luận kỹ năng | **1.504** khóa / **1.707** cạnh (đã đóng bắc cầu) | `app/data/skill_implies.json` |
| Trọng số 3 tầng kỹ năng | required **1–3** · preferred **2** · nice_to_have **1** | [skill_matcher.py:281](app/services/skill_matcher.py#L281) |
| Hệ chứng chỉ ngôn ngữ hỗ trợ | **7**: JLPT, HSK, TOPIK, IELTS, TOEIC, TOEFL, CEFR | [skill_matcher.py:169](app/services/skill_matcher.py#L169) |
| Bậc bằng cấp | HS=1, CĐ=2, ĐH=3, ThS=4, TS=5, other=1 | [schemas.py:96](app/schemas.py#L96) |
| Ngưỡng đi làm D5 | **45 phút** (onsite) / **75 phút** (hybrid) | [scorer.py:190](app/services/scorer.py#L190) |
| Danh sách chặn kỹ năng giả | **~45** cụm soft skill | [schemas.py:255](app/schemas.py#L255) |
| Giới hạn CV mỗi request | **50** | [parse.py:25](app/api/parse.py#L25) |
| Bộ test | **194 test**, chạy **~1 giây**, hoàn toàn offline | `tests/` |
| Tốc độ chấm điểm | **~1ms** (thuần Python + numpy) | [scorer.py:201](app/services/scorer.py#L201) |
| Tốc độ parse | CV ~5–10s · JD ~3–5s | — |

---

## 8. Ngân hàng câu hỏi phản biện & trả lời mẫu

### Nhóm A — Câu hỏi về tổng thể

**A1. "Hệ thống này khác gì so với việc lọc CV bằng từ khóa như các ATS truyền thống?"**
→ Ba khác biệt: (1) **Hiểu ngữ nghĩa** — D1 khớp được "Backend Developer" với
"Server-side Engineer" dù không trùng từ nào; (2) **Suy luận kỹ năng** — D2 Layer 2
biết "biết React thì biết JavaScript", ATS từ khóa không biết; (3) **Điểm nhiều
chiều có giải thích** thay vì một quyết định đậu/rớt hộp đen.

**A2. "Vì sao là 5 chiều mà không phải 3 hay 10?"**
→ 5 chiều tương ứng đúng **5 nhóm tiêu chí độc lập** mà nhà tuyển dụng thật sự dùng
khi sàng lọc: *làm nghề gì* (D1), *dùng công cụ gì* (D2), *bao lâu rồi* (D3), *học
hành thế nào* (D4), *có đi làm được không* (D5). Nguyên tắc của mô hình cộng có
trọng số là các tiêu chí phải **độc lập ưu tiên** — thêm chiều thứ 6 mà nó chồng
lấn với chiều có sẵn thì sẽ gây đếm trùng tín hiệu, đúng cái lỗi em cẩn thận tránh
suốt cả hệ thống.

**A3. "Bộ trọng số 30/35/20/10/5 lấy ở đâu ra? Có hiệu chỉnh thực nghiệm không?"**
→ **Chưa hiệu chỉnh thực nghiệm — em nói thẳng.** Chúng phản ánh **thứ tự ưu tiên
của nghiệp vụ tuyển dụng**: kỹ năng quan trọng nhất, rồi đến sự phù hợp nghề
nghiệp, kinh nghiệm, học vấn, và vị trí là yếu tố phụ. Có một ràng buộc thiết kế
rõ ràng đứng sau: **giữ chiều duy nhất không giải thích được (D1) ở mức 0.30 để
70% điểm nằm ở phần tất định**. Để hiệu chỉnh đúng cần **gold set** do HR gán nhãn
rồi chạy **ablation study** — đặt lần lượt từng $W_i = 0$ và đo nDCG@10 để biết mỗi
chiều đóng góp bao nhiêu. Đây là **hướng phát triển tiếp theo rõ ràng nhất** của đồ án.

**A4. "Vì sao không dùng một model học sâu end-to-end học thẳng từ dữ liệu?"**
→ Ba lý do: (1) **Không có dữ liệu huấn luyện** — cần hàng chục nghìn cặp CV–JD có
nhãn "tuyển/không tuyển", đó là dữ liệu độc quyền của các công ty lớn; (2) **Không
giải thích được** — mô hình end-to-end cho ra một con số không truy vết được, không
chấp nhận được trong lĩnh vực rủi ro cao; (3) **Không sửa được** — muốn hệ thống
hiểu một kỹ năng mới, với kiến trúc của em chỉ cần thêm một dòng JSON; với model
end-to-end thì phải huấn luyện lại.

**A5. "Làm sao chứng minh hệ thống chấm đúng?"**
→ Trả lời trung thực theo hai tầng: (1) **Đã chứng minh được**: 194 unit test
chứng minh **từng tầng hoạt động đúng đặc tả** — kể cả các bất biến của chính dữ
liệu tri thức; (2) **Chưa chứng minh được**: chất lượng **xếp hạng end-to-end** so
với đánh giá của HR thật. Việc đó cần gold set và các chỉ số nDCG@10, Precision@k,
Spearman ρ, cùng Cohen's kappa để kiểm tra độ tin cậy của chính bộ nhãn. Em xác
định đây là giới hạn của phạm vi đồ án và đã thiết kế sẵn phương pháp đánh giá.

### Nhóm B — Câu hỏi kỹ thuật sâu (đã trả lời chi tiết trong các chặng)

| Câu hỏi | Xem mục |
| --- | --- |
| Tại sao chọn model embedding này? | [§4 ④ Câu 1](#câu-1--tại-sao-chọn-model-embedding-này) |
| Tại sao 3072 chiều? | [§4 ④ Câu 2](#câu-2--tại-sao-lại-là-3072-chiều) |
| Cosine similarity hoạt động thế nào? | [§4 ④ Câu 3](#câu-3--cosine-similarity-hoạt-động-như-thế-nào) |
| Model embedding hoạt động thế nào? | [§4 ④ Câu 4](#câu-4--model-embedding-hoạt-động-như-thế-nào) |
| Vì sao loại skills khỏi text embed? | [§4 ③](#③-vì-sao-thiết-kế-như-vậy--luận-điểm-quan-trọng-nhất-của-cả-đồ-án) |
| Vì sao D2 chấm nhị phân? | [§5.2 ③](#③-vì-sao-thiết-kế-như-vậy-2) |
| Vì sao D3 không xét độ liên quan? | [§5.3 ③](#③-vì-sao-không-có-hệ-số-độ-liên-quan-hay-độ-gần-đây) |
| Chia bậc bằng cấp có hợp lệ không? | [§5.4 ④](#④-câu-hỏi-phản-biện-4) |
| Ngưỡng 45/75 phút ở đâu ra? | [§5.5 ④](#④-câu-hỏi-phản-biện-5) |
| LLM bịa thông tin thì sao? | [§3 ④](#④-câu-hỏi-phản-biện-1) |

### Nhóm C — Câu hỏi về đạo đức, pháp lý, vận hành

**C1. "Hệ thống có thể phân biệt đối xử không?"**
→ Rủi ro có thật và em đã tính đến ở 3 tầng: (1) **Kiến trúc** — chiều duy nhất có
thể kế thừa định kiến từ dữ liệu huấn luyện (D1) bị giới hạn ở 0.30; (2) **Dữ
liệu** — hệ thống không trích xuất và không dùng tuổi, giới tính, ảnh chân dung,
tình trạng hôn nhân (xem schema `ParsedCV` — không có trường nào như vậy); (3)
**Quy trình** — LLM bị cấm đưa khuyến nghị tuyển/loại, HR là người quyết định cuối.
Hạn chế còn lại: **tên riêng vẫn nằm trong text được embed**, mà tên có thể mang
tín hiệu giới tính/vùng miền — hướng khắc phục là loại tên khỏi text embed.

**C2. "Ứng viên có quyền biết vì sao mình bị điểm thấp không?"**
→ Về mặt kỹ thuật thì **có** và đây là ưu điểm của kiến trúc: hệ thống trả về điểm
từng chiều, danh sách kỹ năng thiếu theo từng tầng, verdict kinh nghiệm/học vấn, và
với D2 còn truy được **khớp qua tầng nào, nhờ kỹ năng nào** (`matched_layer`,
`matched_via`). Việc có công bố cho ứng viên hay không là **quyết định nghiệp vụ**
của phía .NET, nhưng dữ liệu để giải thích thì đã có sẵn.

**C3. "Chi phí vận hành thực tế?"**
→ Chỉ có **parse** tốn tiền (1–3 lần gọi LLM + 1 lần embedding mỗi CV, chạy **một
lần duy nhất**). **Chấm điểm gần như miễn phí** — ~1ms Python thuần, không gọi LLM.
Nhận xét narrative là tùy chọn, chỉ bật khi HR cần. Đây chính là lý do kiến trúc
tách "parse một lần / chấm điểm N lần".

**C4. "Hệ thống chịu tải được bao nhiêu?"**
→ Chấm điểm thì rất khỏe (~1ms/cặp, thuần CPU). Nút thắt nằm ở: (1) **rate limit
của nhà cung cấp LLM** khi parse hàng loạt; (2) **OSRM lúc chấm điểm** — đã phân
tích ở [§5.5](#④-câu-hỏi-phản-biện-5); (3) **OCR** ngốn CPU. Mọi lời gọi SDK đồng bộ
đều được đẩy sang thread executor nên event loop của FastAPI không bị chặn, và
service stateless nên **scale ngang được** bằng cách chạy thêm container.

---

## 9. Điểm yếu tự nhận — nên chủ động nêu trước khi bị hỏi

> **Chiến thuật quan trọng:** nêu trước 3–4 điểm yếu ngay trong phần trình bày.
> Hội đồng đánh giá cao người **hiểu giới hạn công trình của mình**, và việc nêu
> trước sẽ **vô hiệu hóa** phần lớn câu hỏi công kích.

| # | Điểm yếu | Bản chất | Câu trả lời / hướng khắc phục |
| --- | --- | --- | --- |
| 1 | **Chưa có gold set do HR gán nhãn** | Chưa đo được chất lượng xếp hạng end-to-end | Đã thiết kế sẵn phương pháp: nDCG@10, Precision@k, Spearman ρ, Cohen's kappa, ablation study |
| 2 | **Trọng số 30/35/20/10/5 chưa hiệu chỉnh thực nghiệm** | Dựa trên ưu tiên nghiệp vụ + ràng buộc "70% tất định" | Ablation study khi có gold set; đồng thời HR đã chỉnh được per-job |
| 3 | **1.504 quy tắc implies viết tay** | Knowledge acquisition bottleneck — có soundness, không có completeness | Lỗi do thiếu là **false negative** (an toàn hơn); bootstrap từ co-occurrence tag SO |
| 4 | **`angular` khớp nhầm `angularjs` ở Layer 3** (ratio 0.875) | Đánh đổi precision–recall của một ngưỡng cứng | Chặn Layer 3 khi cả hai phía tra ra canonical hợp lệ nhưng **khác nhau** |
| 5 | **Nominatim/OSRM là server demo công cộng** | Rate limit, không SLA, chính sách cấm tải lớn | Self-host OSRM (dữ liệu OSM VN chỉ vài GB) + cache theo cặp tọa độ |
| 6 | **D5 gọi mạng ngay trong vòng chấm điểm** | N ứng viên = N lời gọi HTTP | Cache theo cặp tọa độ / tính theo lô bất đồng bộ |
| 7 | **Thang thứ tự dùng như thang tỷ lệ** (bằng cấp, weight kỹ năng) | Giả định đơn giản hóa về đo lường (Stevens 1946) | Nêu rõ giả định; muốn chặt hơn thì rút trọng số bằng AHP |
| 8 | **Heuristic 2 cột dùng ngưỡng cứng 45/55%** | Không xử lý được layout 3 cột / lệch tỷ lệ | Model layout detection có huấn luyện (hướng PubLayNet) |
| 9 | **Gửi nội dung CV lên API bên thứ ba** | Quyền riêng tư dữ liệu ứng viên | Hợp đồng xử lý dữ liệu + lấy đồng ý; hoặc self-host model embedding |
| 10 | **Chưa có fallback tự động khi LLM provider lỗi** | Điểm hỏng đơn (single point of failure) | Đã có 3 provider thay thế được qua config, cần thêm logic tự chuyển |
| 11 | **AI service không có authentication** | Phụ thuộc hoàn toàn vào cách ly mạng Docker | API key giữa 2 service + whitelist domain cho `/parse-cv` (chống SSRF) |
| 12 | **Embedding đối xứng cho bài toán bất đối xứng** (CV dài ↔ JD ngắn) | Model kiểu STS không tối ưu cho truy hồi | Dùng `task_type` `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` của API Gemini |

---

## 10. Checklist việc phải làm TRƯỚC buổi bảo vệ

### 🔴 Ưu tiên cao — sửa ngay

- [ ] **Sửa 2 test đang fail.** Chạy `pytest` hiện cho **192 pass / 2 fail**. Nếu
      hội đồng chạy thử mà thấy suite đỏ thì rất mất điểm, dù nguyên nhân chỉ là
      **test cũ chưa cập nhật theo thiết kế mới**, không phải lỗi code:

  | Test | Kỳ vọng cũ | Hành vi hiện tại | Cách sửa |
  | --- | --- | --- | --- |
  | `tests/test_scorer.py::test_score_skills_typo_no_longer_fuzzy_matched` | `"pythonn"` **không** khớp `"Python"` → D2 = 0.0 | Khớp qua Layer 3 (ratio 0.923) → D2 = 1.0 | Viết lại thành khẳng định fuzzy **có** bắt được lỗi chính tả |
  | `tests/test_d2_skills.py::test_J9_ui_ux_compound_term` | `xfail(strict=True)`: `"UI/UX testing"` không khớp | Đã khớp qua Layer 3 → **XPASS** | Bỏ đánh dấu `xfail`, đổi thành test khớp bình thường |

  > Nếu hội đồng hỏi tại sao từng có: đây là bằng chứng tốt cho thấy **test bám sát
  > thay đổi thiết kế** — Layer 3 fuzzy được thêm lại **sau** khi 2 test này viết ra.

- [ ] **Sửa comment lỗi thời trong [schemas.py:506-509](app/schemas.py#L506)**, đang
      ghi `nice_to_have_skills` là *"Display-only... never affects D2 scoring"*.
      **Sai với code hiện tại** — `evaluate_tiers` đã tính cả 3 tầng vào D2 với
      trọng số 1. Nếu giám khảo đọc code và bắt được chỗ này thì rất khó đỡ.

- [ ] **Sửa lỗi đánh máy "3071" → "3072"** trong [QUESTIONARE.md](QUESTIONARE.md).

### 🟡 Ưu tiên trung bình — nên có

- [ ] Chuẩn bị **1 cặp CV–JD mẫu** đã chạy sẵn, in ra JSON kết quả để chiếu — tránh
      demo trực tiếp phụ thuộc mạng/API key.
- [ ] Chuẩn bị **1 ví dụ thể hiện được sức mạnh của Layer 2**: JD đòi `JavaScript`,
      CV chỉ ghi `React` → vẫn khớp, và chỉ rõ `matched_via: "react"`.
- [ ] Chuẩn bị **1 ví dụ proficiency**: JD đòi `JLPT N3`, CV có `"Japanese - JLPT N2"`
      → khớp; đồng thời giải thích vì sao fuzzy sẽ làm sai ca `N4` vs `N3`.
- [ ] Chạy `pytest -v` một lần ngay trước buổi bảo vệ, chụp màn hình kết quả xanh.
- [ ] Thuộc **3 con số**: 5 chiều · 3072 chiều · 9.524 kỹ năng.

### 🟢 Nếu còn thời gian

- [ ] Vẽ **1 sơ đồ khối duy nhất** cho toàn bộ luồng (file → text → JSON → vector →
      D1-D5 → điểm) — slide này sẽ được chiếu suốt buổi.
- [ ] Chuẩn bị số liệu so sánh: cùng một JD, chấm 3 CV có mức phù hợp khác nhau
      rõ rệt, để chứng minh hệ thống **phân biệt được**.
- [ ] Thử chạy ablation thủ công trên vài cặp (đặt từng $W_i = 0$) để có ít nhất
      **quan sát định tính** về đóng góp của từng chiều.

---

## 11. Kịch bản demo 5 phút

| Phút | Nội dung | Điểm cần nói khi đang chiếu |
| --- | --- | --- |
| 0:00–0:30 | Mở Swagger `http://localhost:8000/docs` | "4 endpoint, service stateless" |
| 0:30–1:30 | `POST /ai/parse-jd` với một JD thật | Chỉ vào `required_skills` có `weight` và `alternatives` → **"đây là OR-group, JD ghi 'React hoặc Vue' thì chỉ cần một"** |
| 1:30–2:30 | `POST /ai/parse-cv` với URL một CV | Chỉ vào `work_experience[].months` → **"số này do Python tính, không phải LLM"**; chỉ vào `candidate_location.lat/lng` → **"geocode một lần tại đây, không tính lại lúc chấm điểm"** |
| 2:30–4:00 | `POST /ai/score` | Chỉ vào `scores` **từng chiều** → **"không phải một con số hộp đen"**; chỉ vào `evaluation.missing_must_have` vs `missing_preferred` → **"phân biệt được thiếu bắt buộc và thiếu ưu tiên"**; nhấn **"toàn bộ bước này ~1ms, không gọi LLM"** |
| 4:00–5:00 | `POST /ai/evaluate` | Đoạn nhận xét tiếng Việt → **"mọi con số trong đoạn này do Python tính, LLM chỉ diễn đạt; và nó bị cấm đưa ra khuyến nghị tuyển hay loại — quyết định là của HR"** |

**Phương án dự phòng:** nếu mạng/API lỗi, chuyển sang chạy `pytest -v` để chứng
minh 194 test chạy offline trong ~1 giây, rồi chiếu JSON kết quả đã lưu sẵn.

---

## PHỤ LỤC — Bản đồ file nhanh (khi cần chỉ tận nơi)

| Câu hỏi về | Mở file |
| --- | --- |
| Bố cục PDF, OCR, làm sạch text | [app/services/pdf_extractor.py](app/services/pdf_extractor.py) |
| Prompt trích xuất CV/JD, retry, geocode | [app/services/parser.py](app/services/parser.py) |
| Chọn provider LLM, sửa JSON hỏng | [app/services/llm_client.py](app/services/llm_client.py) |
| Schema, validate, tính tháng, denylist soft skill | [app/schemas.py](app/schemas.py) |
| Embedding, nội dung được embed | [app/services/embedder.py](app/services/embedder.py) + `build_embed_text()` trong schemas |
| Công thức D1–D5, tổng hợp điểm | [app/services/scorer.py](app/services/scorer.py) |
| Thác 4 tầng, proficiency, OR-group, 3 tier | [app/services/skill_matcher.py](app/services/skill_matcher.py) |
| Geocode + routing | [app/services/location_service.py](app/services/location_service.py) |
| Nhận xét cho HR, prompt narrative | [app/services/evaluator.py](app/services/evaluator.py) |
| Trọng số mặc định, validator tổng = 1.0 | [app/config.py](app/config.py) |
| Sinh dữ liệu kỹ năng, đóng bắc cầu | [app/data/](app/data/) |
| Test | [tests/](tests/) |
