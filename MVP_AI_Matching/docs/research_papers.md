# Research Papers — AI CV/JD Matching System

> Tổng hợp cơ sở lý thuyết cho từng thành phần **đang có trong code**
> (`app/services/`). Mọi mục "Validate component" đều trỏ tới file/hàm cụ thể.
> Cập nhật: 2026-07-31

**Ký hiệu nguồn:**
`✅` link đã xác minh · `📖` sách/bài báo kinh điển (tra thư viện, không có
arXiv) · `🌐` tài nguyên/tiêu chuẩn trực tuyến

---

## Nhóm 1 — Multi-dimensional Weighted Scoring (kiến trúc D1–D5)

> Xác nhận kiến trúc core: kết hợp nhiều chiều điểm số có trọng số cho kết quả
> tốt hơn bất kỳ chiều đơn lẻ nào.

### [1] Multiple Attribute Decision Making: Methods and Applications
- **Tác giả:** Ching-Lai Hwang, Kwangsun Yoon
- **Nguồn:** 📖 Springer-Verlag, Lecture Notes in Economics and Mathematical Systems, Vol. 186, 1981
- **Link:** https://link.springer.com/book/10.1007/978-3-642-48318-9
- **Phương pháp:** Formalize bài toán ra quyết định đa tiêu chí (MADM). Mô hình
  **Simple Additive Weighting (SAW/WSM)**: $\text{score} = \sum w_i d_i$ với
  $\sum w_i = 1$. Điều kiện áp dụng: mọi tiêu chí phải **cùng thang đo, cùng
  chiều tốt/xấu, và độc lập ưu tiên (preferential independence)**.
- **Validate component:** `scorer.py::calculate_score` — `final = Σ(Dᵢ × Wᵢ) × 100`,
  mọi $D_i \in [0,1]$, `config.py::_check_default_weights_sum_to_one` ép $\sum W_i = 1$.
- **Dùng để trả lời phản biện:** vì sao mọi chiều phải normalize về [0,1] trước
  khi cộng; vì sao D1 **cố ý loại skills** khỏi text embed (tránh vi phạm giả
  định độc lập giữa D1 và D2 → trọng số hiệu dụng bị thổi phồng).

### [2] The Analytic Hierarchy Process
- **Tác giả:** Thomas L. Saaty
- **Nguồn:** 📖 McGraw-Hill, 1980
- **Phương pháp:** Rút trọng số từ chuyên gia bằng **so sánh cặp (pairwise
  comparison)** + kiểm tra **consistency ratio**.
- **Validate component:** `config.py` — bộ trọng số mặc định 30/35/20/10/5 là
  **prior theo domain**, và hệ thống cho HR ghi đè per-job qua
  `ScoreRequest.weights`. AHP là câu trả lời chuẩn cho câu hỏi *"vì sao chọn
  đúng những con số này?"*.

### [3] AI-driven Semantic Similarity-based Job Matching Framework
- **Nguồn:** ✅ ScienceDirect — Information Sciences (2025)
- **Link:** https://www.sciencedirect.com/science/article/pii/S0020025525008643
- **Phương pháp:** Weighted aggregation của nhiều attribute similarities → single
  compatibility score. Trọng số xác định theo domain expertise; critical dims
  (skills, exp) đóng góp nhiều hơn.
- **Validate component:** `scorer.py` — cấu trúc 5 chiều + phân bổ trọng số.

### [4] Resume-Job Compatibility Scoring Using Graph Neural Networks and Large Language Models
- **Nguồn:** ✅ ACM ICIT IoT & Smart City (2024)
- **Link:** https://dl.acm.org/doi/full/10.1145/3787330.3787359
- **Phương pháp:** Bipartite graph với nodes = skill/education/experience
  entities, edges mang numeric proficiency weights. Aggregated weighted score.
- **Validate component:** `schemas.py::RequiredSkill.weight` (1–3) — numeric
  weighting per skill.

### [5] Improved Candidate-Career Matching via Comparative Semantic Resume Analysis
- **Nguồn:** ✅ Advances in Science, Technology and Engineering Systems Journal
- **Link:** https://www.astesj.com/v09/i01/p03/
- **Phương pháp:** Empirically-determined attribute weights, multi-criteria
  aggregation.
- **Validate component:** Toàn bộ scoring architecture, tunable weights per job.

### [6] A Comprehensive Survey of Artificial Intelligence Techniques for Talent Analytics
- **Tác giả:** Chuan Qin, Le Zhang, Feng Zhu, et al.
- **Nguồn:** ✅ arXiv preprint, 2023
- **Link:** https://arxiv.org/abs/2307.03195
- **Phương pháp:** Survey toàn diện về AI trong HR. Validate rằng
  multi-dimensional scoring kết hợp semantic matching là hướng state-of-the-art.
- **Validate component:** Justify tổng thể approach của đồ án.

### [7] Person-Job Fit: Adapting the Right Talent for the Right Job with Joint Representation Learning
- **Tác giả:** Chen Zhu, Hengshu Zhu, Hui Xiong, Chao Ma, et al.
- **Nguồn:** ✅ ACM TMIS Vol. 9, No. 3, 2018
- **Links:** https://arxiv.org/abs/1810.04040 · https://dl.acm.org/doi/10.1145/3234465
- **Phương pháp:** PJFNN — bipartite neural network học joint representation từ
  lịch sử ứng tuyển. Paper đầu tiên formalize bài toán **Person-Job Fit**.
- **Validate component:** Định nghĩa bài toán. **Đối chiếu:** PJFNN cần
  *labeled hiring history* để train — đồ án này chọn hướng **zero-shot +
  rule-based** vì không có dữ liệu tuyển dụng gán nhãn tiếng Việt.

---

## Nhóm 2 — Dense Embedding + Cosine Similarity (D1 Semantic, W=0.30)

> Xác nhận `embedder.py` + `scorer.py::cosine_sim` / `normalize_cosine`.

### [8] Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks
- **Tác giả:** Nils Reimers, Iryna Gurevych
- **Nguồn:** ✅ EMNLP-IJCNLP 2019, pages 3982–3992
- **Links:** https://arxiv.org/abs/1908.10084 · https://aclanthology.org/D19-1410/
- **Phương pháp:** Kiến trúc **bi-encoder Siamese**, fine-tune BERT bằng NLI để
  sentence embedding so sánh được bằng cosine. Giảm thời gian tìm cặp tương đồng
  nhất trong 10.000 câu từ **65 giờ (cross-encoder) xuống 5 giây**.
- **Validate component:** `embedder.py` — lý do precompute `cv_embedding` /
  `jd_embedding` **một lần lúc parse** rồi lưu DB, thay vì cross-encoder chạy
  lại mỗi cặp CV↔JD. Với 1 job có N ứng viên, bi-encoder là O(N) embedding +
  O(N) dot product; cross-encoder là O(N) forward pass đầy đủ.

### [9] A Survey of Text Similarity Approaches
- **Tác giả:** Wael H. Gomaa, Aly A. Fahmy
- **Nguồn:** ✅ International Journal of Computer Applications, Vol. 68, No. 13, 2013
- **Link:** https://www.semanticscholar.org/paper/A-Survey-of-Text-Similarity-Approaches-Gomaa-Fahmy/5b5ca878c534aee3882a038ef9e82f46e102131b
- **Phương pháp:** Phân loại độ đo text similarity: **String-based** (edit
  distance, Jaro-Winkler), **Corpus-based** (cosine TF-IDF, LSA),
  **Knowledge-based** (WordNet).
- **Validate component:** Bản đồ lý thuyết của cả hệ: D1 = corpus-based,
  Layer 3 của D2 = string-based, Layer 1/2 của D2 = knowledge-based. **Ba nhóm
  này bổ sung nhau chứ không thay thế nhau** — đây là luận điểm trung tâm cho
  kiến trúc hybrid.

### [10] How Contextual are Contextualized Word Representations?
- **Tác giả:** Kawin Ethayarajh
- **Nguồn:** ✅ EMNLP 2019
- **Link:** https://arxiv.org/abs/1909.00512
- **Phương pháp:** Chứng minh embedding của transformer bị **anisotropy** — các
  vector nằm trong một **hình nón hẹp** của không gian, nên cosine giữa 2 văn
  bản bất kỳ hiếm khi tiến gần 0.
- **Validate component:** `scorer.py::normalize_cosine` — **cơ sở lý thuyết duy
  nhất chính đáng** cho việc kéo giãn (stretch) $[r_{min}, r_{max}] \to [0,1]$.
  Cấu hình hiện tại `COSINE_MIN=0.0 / COSINE_MAX=1.0` (không kéo giãn) là lựa
  chọn thận trọng; nếu đo được khoảng cosine thực tế của `gemini-embedding-001`
  trên tập CV/JD thì có thể chỉnh 2 hằng số này qua `.env` mà không sửa code.

### [11] Matryoshka Representation Learning
- **Tác giả:** Aditya Kusupati, Gantavya Bhatt, Aniket Rege, et al.
- **Nguồn:** ✅ NeurIPS 2022
- **Link:** https://arxiv.org/abs/2205.13147
- **Phương pháp:** Huấn luyện embedding sao cho **prefix của vector vẫn là một
  embedding hợp lệ** → có thể cắt 3072 → 1536 → 768 chiều mà chất lượng suy
  giảm rất ít.
- **Validate component:** `embedder.py` — trả lời câu hỏi *"3072 chiều có thừa
  không? Lưu 12KB/CV có lãng phí không?"*: `gemini-embedding-001` là model theo
  hướng MRL, cho phép **đánh đổi chiều ↔ chi phí lưu trữ/tìm kiếm** về sau mà
  không phải re-embed toàn bộ corpus.

### [12] MTEB: Massive Text Embedding Benchmark
- **Tác giả:** Niklas Muennighoff, Nouamane Tazi, Loïc Magne, Nils Reimers
- **Nguồn:** ✅ EACL 2023
- **Link:** https://arxiv.org/abs/2210.07316
- **Phương pháp:** Benchmark chuẩn so sánh embedding model trên 8 nhóm task
  (retrieval, STS, clustering...). Cho thấy **không có model nào thắng mọi
  task** — phải chọn theo task cụ thể.
- **Validate component:** Cơ sở phương pháp luận để chọn/đổi embedding provider.
  **Cũng là điểm cần thừa nhận:** hệ hiện dùng embedding *đối xứng* (kiểu STS)
  cho một bài toán *bất đối xứng* (CV dài ↔ JD ngắn); hướng cải tiến là dùng
  `task_type` `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` mà API Gemini hỗ trợ.

### [13] Zero-Shot Resume–Job Matching with LLMs via Structured Prompting and Semantic Embeddings
- **Nguồn:** ✅ MDPI Electronics (2025)
- **Link:** https://www.mdpi.com/2079-9292/14/24/4960
- **Phương pháp:** Structured prompting + sentence embeddings + cosine
  similarity, đạt 87% accuracy **không cần fine-tune**.
- **Validate component:** Toàn bộ hướng zero-shot của đồ án (`parser.py` +
  `embedder.py`) — bằng chứng rằng không fine-tune vẫn đạt kết quả dùng được.

### [14] Resume2Vec: Transforming ATS with Intelligent Resume Embeddings
- **Nguồn:** ✅ MDPI Electronics (2025)
- **Link:** https://www.mdpi.com/2079-9292/14/4/794
- **Phương pháp:** BERT/RoBERTa/DistilBERT encodings + cosine similarity. Cải
  thiện **+15.85% nDCG** và **+15.94% RBO** so với baseline keyword matching.
- **Validate component:** `embedder.py` — lý do dùng transformer embedding thay
  TF-IDF/keyword; đồng thời là **nguồn chỉ số đánh giá** (nDCG, RBO) cho chương
  kiểm thử.

### [15] ConFit v2: Improving Resume-Job Matching via Hypothetical Resume Embedding
- **Nguồn:** ✅ ACL Findings (2025)
- **Link:** https://arxiv.org/html/2502.12361v1
- **Phương pháp:** LLM embeddings + cosine compatibility score, **hard-negative
  mining** để cải thiện ranking.
- **Validate component:** Hướng phát triển của D1 — nếu muốn fine-tune embedding
  cho domain tuyển dụng thì hard-negative mining là kỹ thuật bắt buộc (không
  thể chỉ dùng positive pairs).

---

## Nhóm 3 — LLM-based Information Extraction (Stage 2 Parsing)

> Xác nhận `parser.py` + `llm_client.py`: dùng LLM để parse CV/JD ra JSON có
> cấu trúc thay vì rule-based NER.

### [16] Chain-of-Thought Prompting Elicits Reasoning in Large Language Models
- **Tác giả:** Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, et al.
- **Nguồn:** ✅ NeurIPS 2022
- **Link:** https://arxiv.org/abs/2201.11903
- **Phương pháp:** Cung cấp bước reasoning trung gian trong prompt cải thiện
  đáng kể chất lượng output trên task phức tạp.
- **Validate component:** `parser.py::CV_EXTRACT_PROMPT` / `JD_EXTRACT_PROMPT` —
  prompt mô tả **rõ ràng schema JSON + quy tắc chuyển đổi ngày tháng + quy tắc
  chuẩn hóa tên skill** thay vì chỉ ra lệnh chung chung.

### [17] Large Language Models for Generative Information Extraction: A Survey
- **Nguồn:** ✅ Frontiers of Computer Science — Springer Nature (2024)
- **Link:** https://link.springer.com/article/10.1007/s11704-024-40555-y
- **Phương pháp:** Survey xác nhận LLM-based IE vượt trội NER truyền thống cho
  văn bản phi cấu trúc.
- **Validate component:** Lựa chọn LLM thay pipeline NER cho CV — CV có định
  dạng cực kỳ đa dạng, rule-based không tổng quát hóa được.

### [18] Layout-Aware Parsing Meets Efficient LLMs: A Unified, Scalable Framework for Resume Information Extraction
- **Nguồn:** ✅ arXiv, 2025 (deployed tại Alibaba HR platform)
- **Link:** https://arxiv.org/abs/2510.09722
- **Phương pháp:** Layout parser (chuẩn hóa format đa dạng) + LLM extractor.
- **Validate component:** `pdf_extractor.py::extract_text_smart_layout` +
  `parser.py` — xác nhận **layout-aware trước, LLM sau** là thứ tự đúng.

### [19] Smart-Hiring: An Explainable End-to-End Pipeline for CV Information Extraction and Job Matching
- **Nguồn:** ✅ arXiv, 2024
- **Link:** https://arxiv.org/html/2511.02537v1
- **Phương pháp:** PDF → LLM parse → structured JSON → matching, **explainable**.
- **Validate component:** Toàn bộ pipeline `parse-cv` → `score` → `evaluate`.

### [20] Augmented Fine-Tuned LLMs for Enhanced Recruitment Automation
- **Nguồn:** ✅ arXiv, 2024
- **Link:** https://arxiv.org/html/2509.06196v1
- **Phương pháp:** Standardized JSON schema cho consistency & scalability.
- **Validate component:** `schemas.py` — thiết kế `ParsedCV`/`ParsedJD` + validator
  chuẩn hóa (`_normalize_degree`, `_coerce_exp`, `_filter_empty_entries`).

---

## Nhóm 4 — Skill Ontology & Entity Resolution (D2 Layer 1)

> Xác nhận `skill_data.json` (9.524 entry) + `skill_matcher.py::resolve_canonical`.
> **Đây là tầng "canonical hóa hai phía": đưa tên skill của CV và của JD về
> cùng một dạng chuẩn rồi mới so.**

### [21] ESCO — European Skills, Competences, Qualifications and Occupations
- **Nguồn:** 🌐 European Commission
- **Link:** https://esco.ec.europa.eu/
- **Nội dung:** Ontology chính thức của EU: ~13.900 kỹ năng, đa ngôn ngữ, có
  quan hệ phân cấp và liên kết skill↔occupation.
- **Đối chiếu với hệ thống:** Đây là **phương án thay thế đã cân nhắc và không
  chọn** cho Layer 1. Lý do: ESCO mạnh ở kỹ năng nghề nghiệp tổng quát nhưng
  **độ phủ long-tail công nghệ IT kém** (không có "NestJS", "Redux Toolkit",
  "Tailwind CSS"). Stack Overflow tags do chính cộng đồng developer bảo trì nên
  phủ đúng lớp từ vựng mà CV/JD ngành IT thực sự dùng.

### [22] O*NET — Occupational Information Network
- **Nguồn:** 🌐 U.S. Department of Labor
- **Link:** https://www.onetonline.org/
- **Nội dung:** Chuẩn vàng trong nghiên cứu talent analytics; taxonomy
  skill/knowledge/ability theo nghề.
- **Đối chiếu:** Cùng lý do với ESCO — mức trừu tượng quá cao so với nhu cầu
  khớp "PostgreSQL" ↔ "Postgres".

### [23] A Novel Approach for Job Matching and Skill Recommendation Using Transformers and O*NET
- **Nguồn:** ✅ ScienceDirect (2025)
- **Link:** https://www.sciencedirect.com/science/article/pii/S2214579625000048
- **Phương pháp:** Trích skill bằng NLP → **map về entity của O\*NET** → so khớp.
- **Validate component:** `skill_matcher.py::resolve_canonical` — xác nhận
  nguyên tắc **"chuẩn hóa về canonical entity trước khi so khớp"**. Đồ án dùng
  cùng nguyên tắc, khác ở chỗ nguồn ontology là Stack Overflow tag synonyms.

### [24] NLPnorth @ TalentCLEF 2025: Comparing Discriminative, Contrastive, and Prompt-Based Methods for Skill Matching
- **Nguồn:** ✅ arXiv (2025)
- **Link:** https://arxiv.org/pdf/2506.19058
- **Phương pháp:** So sánh các phương pháp skill matching. Kết luận: matching
  theo ngữ cảnh/ngữ nghĩa vượt trội exact keyword matching.
- **Validate component:** Lý do D2 **không dừng ở Layer 0** (exact match) mà
  phải có thêm canonical hóa, entailment và fuzzy.

### [25] An Introduction to Duplicate Detection / Entity Resolution
- **Tác giả:** Felix Naumann, Melanie Herschel
- **Nguồn:** 📖 Morgan & Claypool, Synthesis Lectures on Data Management, 2010
- **Phương pháp:** Lý thuyết **entity resolution**: nhiều *surface form* cùng
  trỏ về một *thực thể*; giải bằng chuẩn hóa + so khớp + phân cụm.
- **Validate component:** `build_skill_data.py` — 5.536 ánh xạ *synonym →
  canonical* chính là một **synonym ring** kinh điển (cùng mô hình với redirect
  của Wikipedia, hay thesaurus theo chuẩn ISO 25964).

---

## Nhóm 5 — Knowledge Graph & Transitive Closure (D2 Layer 2)

> Xác nhận `skill_implies.json` (1.504 key / 1.707 cạnh) +
> `close_implies.py::transitive_closure`. **Đây là phần có hàm lượng thuật toán
> cao nhất của D2.**

### [26] A Theorem on Boolean Matrices
- **Tác giả:** Stephen Warshall
- **Nguồn:** 📖 Journal of the ACM, Vol. 9, No. 1, 1962, pages 11–12
- **Phương pháp:** Thuật toán kinh điển tính **bao đóng bắc cầu (transitive
  closure)** của quan hệ nhị phân, độ phức tạp $O(V^3)$.
- **Validate component:** `close_implies.py::transitive_closure`. Code dùng
  **lặp tới điểm bất động (fixpoint iteration)** thay vì Warshall thuần: đồ thị
  thưa (1.504 đỉnh / 1.707 cạnh) nên lặp tới hội tụ rẻ hơn $O(V^3)$, và tính dừng
  được bảo đảm vì toán tử mở rộng là **đơn điệu trên một dàn hữu hạn** (định lý
  điểm bất động Kleene) — đồ thị implies là **DAG**, không có chu trình.
- **Ý nghĩa thiết kế:** vật chất hóa (materialize) closure **offline** để
  runtime chỉ cần **tra hash O(1)**, không duyệt đồ thị khi chấm điểm — đánh đổi
  không gian ↔ thời gian kinh điển.

### [27] RDF Schema 1.1 — `rdfs:subClassOf` semantics
- **Nguồn:** 🌐 W3C Recommendation, 2014
- **Link:** https://www.w3.org/TR/rdf-schema/
- **Phương pháp:** Định nghĩa hình thức quan hệ **subsumption** và luật suy diễn
  bắc cầu; phân biệt **forward chaining (materialization)** với **backward
  chaining (suy diễn lúc query)**.
- **Validate component:** `skill_implies.json` chính là một tập luật subsumption
  ("biết Django ⟹ biết Python"), và `close_implies.py` là bước **forward
  chaining materialization**. Quan hệ này **phản đối xứng**: Django ⟹ Python
  nhưng Python ⇏ Django — `test_D_entailment_does_not_leak` kiểm tra đúng tính
  chất này.

### [28] WordNet: An Electronic Lexical Database
- **Tác giả:** Christiane Fellbaum (ed.)
- **Nguồn:** 📖 MIT Press, 1998
- **Phương pháp:** Mạng từ vựng với quan hệ **hypernym/hyponym** (is-a) — mô
  hình lý thuyết của mọi taxonomy "X là trường hợp đặc biệt của Y".
- **Validate component:** Cơ sở khái niệm cho `skill_implies.json`; cũng là lý
  do quan hệ implies phải **một chiều**.

### [29] Knowledge Acquisition Bottleneck (hệ chuyên gia)
- **Tác giả:** Edward Feigenbaum và cộng sự (thuật ngữ kinh điển của lĩnh vực
  expert systems, thập niên 1980)
- **Phương pháp/vấn đề:** Hệ dựa-luật bị giới hạn bởi chi phí **con người viết
  luật**; đảm bảo được *soundness* (luật viết ra là đúng) nhưng không đảm bảo
  được *completeness* (đủ luật).
- **Validate component:** **Hạn chế phải tự nêu** của Layer 2: 1.504 quy tắc là
  viết tay. Kiểm soát chất lượng hiện tại = test tự động
  (`test_L1_implies_transitively_closed`, `test_L2/L3_implies_*_canonical`,
  `test_D_entailment_does_not_leak`). Hướng mở rộng: bootstrap luật từ
  co-occurrence của tag trên Stack Overflow.

---

## Nhóm 6 — Fuzzy String Matching (D2 Layer 3)

> Xác nhận `skill_matcher.py::_fuzzy_best_match`, ngưỡng **0.85**.

### [30] Pattern Matching: The Gestalt Approach (Ratcliff/Obershelp)
- **Tác giả:** John W. Ratcliff, David E. Metzener
- **Nguồn:** 📖 Dr. Dobb's Journal, Vol. 13, No. 7, July 1988, pages 46–51
- **Implement:** https://docs.python.org/3/library/difflib.html#difflib.SequenceMatcher
- **Phương pháp:** Tìm đệ quy các khối khớp chung dài nhất;
  $\text{ratio}(a,b) = \dfrac{2M}{|a| + |b|}$ với $M$ = tổng độ dài khối khớp.
  **Không phải Levenshtein** — đây là điểm hay bị gọi nhầm tên.
- **Validate component:** `_LAYER3_FUZZY_THRESHOLD = 0.85`.
- **Số liệu thực đo trên ngưỡng đang dùng:**

  | Cặp | ratio | Kết quả |
  | --- | --- | --- |
  | `postgresql` / `postgres` | 0.889 | ✅ khớp đúng |
  | `nodejs` / `node.js` | 0.923 | ✅ khớp đúng |
  | `java` / `javascript` | 0.571 | ✅ đúng khi **không** khớp |
  | `sql` / `mysql` | 0.750 | ✅ đúng khi **không** khớp |
  | `n3` / `n4` | 0.500 | (đã chặn riêng bằng tầng proficiency) |
  | `angular` / `angularjs` | **0.875** | ⚠️ **khớp nhầm** — 2 framework khác nhau |

- **Hạn chế đã biết:** cặp `angular`/`angularjs` vượt ngưỡng dù là hai canonical
  **khác nhau** trong `skill_data.json`. Đây là đánh đổi precision–recall cố hữu
  của ngưỡng cứng. Hướng khắc phục: chặn Layer 3 khi **cả hai phía đều resolve
  được ra canonical hợp lệ nhưng khác nhau**.

### [31] Binary Codes Capable of Correcting Deletions, Insertions and Reversals
- **Tác giả:** Vladimir I. Levenshtein
- **Nguồn:** 📖 Soviet Physics Doklady, Vol. 10, No. 8, 1966, pages 707–710
- **Phương pháp:** Edit distance — chi phí chèn/xóa/thay tối thiểu.
- **Validate component:** **Phương án so sánh**, không dùng. Cần biết để trả lời
  *"sao không dùng Levenshtein?"*: Ratcliff/Obershelp cho ratio đã chuẩn hóa
  theo độ dài (tiện đặt ngưỡng), có sẵn trong stdlib, và ưu tiên **khối chung
  liên tục** — hợp với biến thể chính tả của tên công nghệ hơn là chi phí thao
  tác từng ký tự.

---

## Nhóm 7 — Ordinal Measurement (D2 tầng phụ + D4)

> Xác nhận `skill_matcher.py::_PROFICIENCY_PATTERNS` (JLPT/HSK/TOPIK/IELTS/
> TOEIC/TOEFL/CEFR) và `schemas.py::DegreeLevel.numeric`.

### [32] On the Theory of Scales of Measurement
- **Tác giả:** Stanley S. Stevens
- **Nguồn:** 📖 Science, Vol. 103, No. 2684, 1946, pages 677–680
- **Phương pháp:** Phân loại 4 thang đo — **nominal, ordinal, interval, ratio**
  — và quy định **phép toán nào hợp lệ trên thang nào**.
- **Validate component:**
  - Chứng chỉ ngôn ngữ (JLPT N5→N1, CEFR A1→C2, HSK 1→9) là **thang thứ tự**.
    Trên thang này phép **so sánh $\geq$ là hợp lệ** (N2 thỏa yêu cầu N3) nhưng
    **cộng/trung bình là vô nghĩa** — code chỉ so sánh, không cộng. ✅
  - Chỉ so **trong cùng framework**: IELTS 6.5 vs TOEIC 800 không có phép quy
    đổi có cơ sở đo lường → `_match_proficiency` trả `None` nếu khác framework.
  - **Điểm phải tự thừa nhận:** `DegreeLevel.numeric` (1–5) và
    `RequiredSkill.weight` (1–3) là thang **thứ tự** nhưng được dùng như thang
    **tỉ lệ** trong phép chia/nhân. Đây là giả định đơn giản hóa có ý thức, cần
    nêu rõ trong báo cáo chứ không giấu.

### [33] Common European Framework of Reference for Languages (CEFR)
- **Nguồn:** 🌐 Council of Europe
- **Link:** https://www.coe.int/en/web/common-european-framework-reference-languages
- **Nội dung:** Thang A1–C2 chuẩn hóa trình độ ngôn ngữ.
- **Validate component:** `_CEFR_RANK` trong `skill_matcher.py`. Lưu ý: các bảng
  quy đổi CEFR ↔ IELTS/TOEIC là **xấp xỉ và gây tranh cãi** — đó là lý do hệ
  thống **không** quy đổi chéo framework.

---

## Nhóm 8 — Document Processing (Stage 1)

### [34] An Overview of the Tesseract OCR Engine
- **Tác giả:** Raymond W. Smith (HP Labs)
- **Nguồn:** ✅ ICDAR 2007, Vol. 2, pages 629–633, IEEE
- **Link:** https://www.semanticscholar.org/paper/An-Overview-of-the-Tesseract-OCR-Engine-Smith/89d9aae7e0c8b6edd56d0d79b277c07b7ab66fda
- **Phương pháp:** adaptive thresholding → connected component analysis →
  line/word finding → nhận dạng.
- **Validate component:** `pdf_extractor.py::ocr_pdf_with_tesseract` — rasterize
  200 DPI, `lang="eng+vie"`.

### [35] PubLayNet: Largest Dataset Ever for Document Layout Analysis
- **Tác giả:** Xu Zhong, Jianbin Tang, Antonio Jimeno-Yepes (IBM Research)
- **Nguồn:** ✅ ICDAR 2019, pages 1015–1022
- **Link:** https://arxiv.org/abs/1908.07836
- **Phương pháp:** Dataset 1 triệu+ trang PDF có annotation layout; chứng minh
  bài toán **phát hiện bố cục nhiều cột** là bài toán riêng biệt và quan trọng.
- **Validate component:** `extract_text_smart_layout` — heuristic `center_x`
  (left < 45%, right > 55%, cần ≥2 block mỗi bên) là bản **rút gọn không cần
  training** của cùng ý tưởng. **Hạn chế cần nêu:** heuristic ngưỡng cứng, không
  xử lý được layout 3 cột hay bố cục bất đối xứng.

---

## Nhóm 9 — Explainability, Fairness & Pháp lý

> Nhóm này **không validate một dòng code cụ thể** mà biện minh cho **lựa chọn
> kiến trúc tổng thể**: vì sao 70% trọng số nằm ở các chiều tất định, và vì sao
> `evaluator.py` cố ý **không** đưa ra nhãn recommendation.

### [36] EU Artificial Intelligence Act — Regulation (EU) 2024/1689
- **Nguồn:** 🌐 European Union
- **Link:** https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- **Nội dung:** Xếp AI dùng cho **tuyển dụng và sàng lọc ứng viên** vào nhóm
  **rủi ro cao (high-risk, Annex III)** — kèm nghĩa vụ minh bạch, ghi log, và
  giám sát của con người.
- **Validate component:** `evaluator.py` trả `skill_details[]` với
  `matched_layer`/`matched_via` (truy vết từng điểm về đúng skill nào trong CV);
  `score.py` trả `weights_used`; **không có** trường `recommendation`.

### [37] GDPR — Regulation (EU) 2016/679, Article 22
- **Nguồn:** 🌐 European Union
- **Link:** https://eur-lex.europa.eu/eli/reg/2016/679/oj
- **Nội dung:** Quyền **không bị áp một quyết định hoàn toàn dựa trên xử lý tự
  động** khi quyết định đó gây ảnh hưởng đáng kể.
- **Validate component:** Thiết kế "human-in-the-loop": hệ thống **xếp hạng và
  giải thích**, HR **quyết định**.

### [38] Man is to Computer Programmer as Woman is to Homemaker? Debiasing Word Embeddings
- **Tác giả:** Tolga Bolukbasi, Kai-Wei Chang, James Zou, Venkatesh Saligrama, Adam Kalai
- **Nguồn:** ✅ NeurIPS 2016
- **Link:** https://arxiv.org/abs/1607.06520
- **Phương pháp:** Chứng minh word embedding kế thừa **thiên lệch giới** từ
  corpus huấn luyện.
- **Validate component:** **Rủi ro đã nhận diện** của D1 — chiều duy nhất dùng
  mô hình học sâu, và cũng là chiều duy nhất không giải thích được. Giảm thiểu:
  D1 chỉ chiếm **0.30**; D2–D5 hoàn toàn tất định và kiểm toán được. Trường hợp
  thực tế để dẫn chứng: công cụ sàng lọc CV của Amazon bị hủy bỏ năm 2018 vì
  thiên lệch giới học từ dữ liệu tuyển dụng lịch sử.

---

## Nhóm 10 — Đánh giá & Kiểm thử

### [39] Cumulated Gain-based Evaluation of IR Techniques
- **Tác giả:** Kalervo Järvelin, Jaana Kekäläinen
- **Nguồn:** 📖 ACM Transactions on Information Systems, Vol. 20, No. 4, 2002, pages 422–446
- **Phương pháp:** Định nghĩa **DCG/nDCG** — chỉ số chuẩn đánh giá xếp hạng khi
  nhãn liên quan có **nhiều mức**, có tính tới **vị trí** trong danh sách.
- **Validate component:** Chỉ số đề xuất cho chương kiểm thử: **nDCG@10** giữa
  ranking của hệ thống và ranking do HR gán nhãn. Cùng chỉ số mà [14] Resume2Vec
  dùng → so sánh được với văn liệu.

### [40] A Coefficient of Agreement for Nominal Scales
- **Tác giả:** Jacob Cohen
- **Nguồn:** 📖 Educational and Psychological Measurement, Vol. 20, No. 1, 1960, pages 37–46
- **Phương pháp:** **Cohen's kappa** — đo độ đồng thuận giữa 2 người gán nhãn,
  đã hiệu chỉnh cho phần đồng thuận ngẫu nhiên.
- **Validate component:** Nếu xây gold set bằng cách nhờ nhiều HR chấm cùng một
  tập CV, phải báo cáo kappa để chứng minh nhãn **đủ tin cậy làm chuẩn**.

---

## Map: Component → Papers

| Component trong code | Papers |
| --- | --- |
| `pdf_extractor.py` — smart layout | [35] PubLayNet, [18] Layout-Aware LLM |
| `pdf_extractor.py` — OCR fallback | [34] Tesseract |
| `parser.py` — prompt design | [16] Chain-of-Thought, [17] LLM-IE Survey |
| `parser.py` / `schemas.py` — JSON schema | [20] Standardized schema, [19] Smart-Hiring |
| `llm_client.py` — provider abstraction | [17], [19] |
| `embedder.py` — bi-encoder, precompute | [8] SBERT, [12] MTEB |
| `embedder.py` — 3072 chiều | [11] Matryoshka |
| `scorer.py::cosine_sim` | [8], [9] Text Similarity Survey |
| `scorer.py::normalize_cosine` | [10] Anisotropy |
| **D1** Semantic (0.30) — narrative-only embed | [1] MADM (độc lập tiêu chí), [13], [14], [15] |
| **D2** Skills (0.35) — Layer 0/1 canonical | [21] ESCO, [22] O\*NET, [23] O\*NET matching, [25] Entity Resolution |
| **D2** — trọng số 3 tier skill của JD (3/2/1) | [1] MADM (trọng số tiêu chí), [2] AHP |
| **D2** — Layer 2 entailment + closure | [26] Warshall, [27] RDFS, [28] WordNet, [29] KA bottleneck |
| **D2** — Layer 3 fuzzy | [30] Ratcliff/Obershelp, [31] Levenshtein (đối chiếu) |
| **D2** — tầng proficiency ordinal | [32] Stevens, [33] CEFR |
| **D2** — vì sao 4 tầng thay vì exact | [24] TalentCLEF, [9] |
| **D3** Experience (0.20) | [1], [3], [5] |
| **D4** Education (0.10) | [1], [32] (thang thứ tự) |
| **D5** Location (0.05) | [1] (trọng số phụ), OSM/OSRM (công cụ) |
| `scorer.py::calculate_score` — Σ(Dᵢ×Wᵢ) | [1] Hwang & Yoon, [2] Saaty, [3], [4] |
| `config.py` — HR chỉnh weights per-job | [2] AHP, [5] |
| `evaluator.py` — explainable output | [19], [36] EU AI Act, [37] GDPR Art. 22 |
| `evaluator.py` — không có recommendation | [36], [37] |
| Rủi ro thiên lệch của D1 | [38] Debiasing Word Embeddings |
| Chương kiểm thử & đánh giá | [39] nDCG, [40] Cohen's kappa, [14] (nDCG/RBO baseline) |

---

## Ghi chú về các cơ chế **đã bị gỡ bỏ**

Những paper từng được trích để biện minh cho các cơ chế sau **không còn áp
dụng** — code hiện tại không có chúng nữa:

| Cơ chế cũ | Thay bằng | Ghi chú |
| --- | --- | --- |
| Category partial credit (0.3–0.5× khi cùng nhóm frontend/backend/...) | Cascade 4 tầng, chấm **nhị phân** | Hệ số 0.3–0.5 không có cơ sở hiệu chỉnh và không giải thích được cho HR |
| Fuzzy partial credit (0.9× thay vì 1.0) | Fuzzy = full credit ở Layer 3 | Điểm bộ phận làm mờ ranh giới "có/không có kỹ năng" |
| D5 Keywords (string match trên `cv_raw_text`) | D5 Location + Work Mode (Nominatim + OSRM) | Keyword trùng lặp tín hiệu với D1/D2 |
| Fallback haversine cho D5 | Trả điểm trung lập 0.5 | Đường chim bay không phản ánh giao thông đô thị |
| `preferred_skills` chỉ hiển thị, không tính vào D2 | D2 tính trên **cả 3 tier** (`required` / `preferred` / `nice_to_have`) với trọng số giảm dần 3–2–1 | Thứ bậc ưu tiên của nhà tuyển dụng nên biểu diễn bằng **trọng số**, không phải bằng ranh giới cứng tính/không-tính — vẫn nằm trong khuôn khổ SAW [1] |

Trong báo cáo, nên trình bày các thay đổi này ở mục **"Quá trình cải tiến thiết
kế"** — chúng thể hiện năng lực đánh giá lại lựa chọn kỹ thuật, chứ không nên
giấu đi.
