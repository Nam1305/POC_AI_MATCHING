# Research Papers — AI CV/JD Matching System

> Tổng hợp các paper xác nhận phương pháp sử dụng trong MVP_AI_Matching
> Cập nhật: 2026-06-16

---

## Nhóm 1 — Multi-dimensional Weighted Scoring

> Xác nhận kiến trúc core: kết hợp nhiều chiều điểm số có trọng số (skills, experience, education, semantics) cho kết quả tốt hơn bất kỳ chiều đơn lẻ nào.

### [1] AI-driven Semantic Similarity-based Job Matching Framework
- **Nguồn:** ScienceDirect — Information Sciences (2025)
- **Link:** https://www.sciencedirect.com/science/article/pii/S0020025525008643
- **Phương pháp:** Weighted aggregation của nhiều attribute similarities → single compatibility score. Trọng số xác định theo domain expertise, critical dims (skills, exp) đóng góp nhiều hơn.
- **Validate component:** `scorer.py` — final_score = Σ(Dᵢ × Wᵢ) × 100

### [2] Resume-Job Compatibility Scoring Using Graph Neural Networks and Large Language Models
- **Nguồn:** ACM ICIT IoT & Smart City (2024)
- **Link:** https://dl.acm.org/doi/full/10.1145/3787330.3787359
- **Phương pháp:** Bipartite graph với nodes = skill/education/experience entities, edges mang numeric proficiency weights ("basic", "expert"). Aggregated weighted score cho compatibility.
- **Validate component:** Cấu trúc 5 dimensions D1–D5, numeric weighting per skill

### [3] Improved Candidate-Career Matching via Comparative Semantic Resume Analysis
- **Nguồn:** Advances in Science, Technology and Engineering Systems Journal
- **Link:** https://www.astesj.com/v09/i01/p03/
- **Phương pháp:** Empirically-determined attribute weights, multi-criteria aggregation. Semantic models capture contextual similarity giữa multi-word skill phrases.
- **Validate component:** Toàn bộ scoring architecture, tunable weights per job

---

## Nhóm 2 — Dense Embedding + Cosine Similarity (D1 Semantic)

> Xác nhận cách tính `cosine_sim(cv_embedding, jd_embedding)` cho chiều Semantic 30%.

### [4] Zero-Shot Resume–Job Matching with LLMs via Structured Prompting and Semantic Embeddings
- **Nguồn:** MDPI Electronics (2025)
- **Link:** https://www.mdpi.com/2079-9292/14/24/4960
- **Phương pháp:** Chain-of-Thought prompting + sentence embeddings (nomic-embed-text, google-embedding-gemma) + cosine similarity. Đạt 87% accuracy.
- **Validate component:** `embedder.py` + D1 semantic scoring

### [5] Resume2Vec: Transforming ATS with Intelligent Resume Embeddings
- **Nguồn:** MDPI Electronics (2025)
- **Link:** https://www.mdpi.com/2079-9292/14/4/794
- **Phương pháp:** BERT / RoBERTa / DistilBERT encodings + cosine similarity. Cải thiện +15.85% nDCG và +15.94% RBO so với baseline keyword matching.
- **Validate component:** `embedder.py` — lý do dùng transformer embeddings thay TF-IDF

### [6] ConFit v2: Improving Resume-Job Matching via Hypothetical Resume Embedding
- **Nguồn:** ACL Findings (2025)
- **Link:** https://arxiv.org/html/2502.12361v1
- **Phương pháp:** GPT-4o-mini embeddings + cosine similarity compatibility score, hard-negative mining để cải thiện ranking.
- **Validate component:** Lựa chọn OpenAI embedding (text-embedding-3-small) cho production

### [7] Learning Effective Representations for Person-Job Fit by Feature Fusion
- **Nguồn:** arXiv (2020) — baseline chuẩn của lĩnh vực
- **Link:** https://arxiv.org/pdf/2006.07017
- **Phương pháp:** CNN/RNN/Attention/BERT representations + cosine similarity cho person-job fit score. Paper gốc định nghĩa bài toán Person-Job Fit.
- **Validate component:** Toàn bộ matching approach, cosine similarity as scoring backbone

---

## Nhóm 3 — LLM-based Information Extraction / CV Parsing

> Xác nhận việc dùng LLM để parse CV/JD ra structured JSON thay vì rule-based NER.

### [8] Layout-Aware Parsing Meets Efficient LLMs: A Unified, Scalable Framework for Resume Information Extraction
- **Nguồn:** arXiv (2024)
- **Link:** https://arxiv.org/html/2510.09722v1
- **Phương pháp:** LLM extract structured key-value từ CV PDF với layout awareness. Focus on efficiency & scalability cho production recruitment systems.
- **Validate component:** `pdf_extractor.py` (layout detection) + `parser.py` (LLM extraction)

### [9] Smart-Hiring: An Explainable End-to-End Pipeline for CV Information Extraction and Job Matching
- **Nguồn:** arXiv (2024)
- **Link:** https://arxiv.org/html/2511.02537v1
- **Phương pháp:** PDF → LLM parse → structured JSON → matching. Explainable pipeline tương tự kiến trúc MVP.
- **Validate component:** Toàn bộ pipeline: `parse-cv` → `score` → `search`

### [10] Augmented Fine-Tuned LLMs for Enhanced Recruitment Automation
- **Nguồn:** arXiv (2024)
- **Link:** https://arxiv.org/html/2509.06196v1
- **Phương pháp:** LLM tạo synthetic dataset JSON format chuẩn cho resume parsing, standardized schema cho consistency & scalability.
- **Validate component:** `schemas.py` — ParsedCV / ParsedJD JSON schema design

### [11] Large Language Models for Generative Information Extraction: A Survey
- **Nguồn:** Frontiers of Computer Science — Springer Nature (2024)
- **Link:** https://link.springer.com/article/10.1007/s11704-024-40555-y
- **Phương pháp:** Survey toàn diện, xác nhận LLM-based IE vượt trội NER truyền thống cho unstructured documents.
- **Validate component:** Lựa chọn Anthropic Claude / Groq Llama thay NER pipeline

---

## Nhóm 4 — Fuzzy Skill Matching + Category-level Credit (D2 Skills)

> Xác nhận cách khớp kỹ năng 3 tầng: exact match → fuzzy match → category credit.

### [12] Resume Screening and Career Matching Model Based on Fuzzy Natural Language Processing
- **Nguồn:** SAGE Journals (2025)
- **Link:** https://journals.sagepub.com/doi/abs/10.1177/14727978251366558
- **Phương pháp:** Fuzzy logic + semantic analysis = multi-dimensional semantic understanding framework. Tối ưu intelligent matching giữa talents và positions.
- **Validate component:** D2 skill scoring — fuzzy matching (SequenceMatcher ≥ 0.85)

### [13] A Novel Approach for Job Matching and Skill Recommendation Using Transformers and O*NET
- **Nguồn:** ScienceDirect (2025)
- **Link:** https://www.sciencedirect.com/science/article/pii/S2214579625000048
- **Phương pháp:** NLP tools extract skills → map to O*NET entities → Jaccard Similarity. Xác nhận category-level skill mapping.
- **Validate component:** Skill alias normalization + category-level partial credit (0.3–0.5×)

### [14] NLPnorth @ TalentCLEF 2025: Comparing Discriminative, Contrastive, and Prompt-Based Methods for Skill Matching
- **Nguồn:** arXiv (2025)
- **Link:** https://arxiv.org/pdf/2506.19058
- **Phương pháp:** So sánh các phương pháp skill matching. Kết luận: contextual/semantic matching > keyword exact matching.
- **Validate component:** Lý do dùng fuzzy + category thay vì pure exact match

---

## Nhóm 5 — Natural Language Search + Re-ranking (nl_search)

> Xác nhận pipeline: NL query → embed → vector search → re-rank → LLM explain.

### [15] Scaling Up Efficient Small Language Models Serving for Semantic Job Search
- **Nguồn:** arXiv (2024)
- **Link:** https://arxiv.org/pdf/2510.22101
- **Phương pháp:** NL intent understanding → dense retrieval → re-ranking. LinkedIn-scale semantic job search, shift từ keyword sang intent.
- **Validate component:** `nl_search.py` — query parse → embed → re-rank pipeline

### [16] From Text to Talent: A Pipeline for Extracting Insights from Candidate Profiles
- **Nguồn:** arXiv (2025)
- **Link:** https://arxiv.org/html/2503.17438v1
- **Phương pháp:** NL query → embedding → ranked candidate retrieval + match explanation. Tương tự chính xác flow của `/ai/search`.
- **Validate component:** `nl_search.py` — combined_score × 0.4 + similarity × 0.6 + LLM explain

---

## Map: Component → Papers

| Component trong hệ thống | Papers xác nhận |
|--------------------------|-----------------|
| `pdf_extractor.py` (PyMuPDF + OCR) | [8] Layout-Aware Parsing LLMs |
| `parser.py` (LLM → JSON) | [8], [9], [10], [11] |
| `embedder.py` (dense vectors) | [4], [5], [6], [7] |
| `scorer.py` D1 Semantic 30% | [4] 87% accuracy, [5] +15.85% nDCG |
| `scorer.py` D2 Skills 35% (fuzzy) | [12], [13], [14] |
| `scorer.py` D3 Experience 20% | [1], [2], [3] |
| `scorer.py` D4 Education 10% | [2] GNN nodes, [3] multi-criteria |
| `scorer.py` D5 Keywords 5% | [3] keyword weighting |
| `nl_search.py` (re-rank + explain) | [15], [16] |
| Kiến trúc multi-dim weighted scoring | [1], [2], [3] |
| Lựa chọn LLM (Claude/Groq) | [9], [10], [11] |
| Lựa chọn OpenAI / SentenceTransformer | [5], [6] |
