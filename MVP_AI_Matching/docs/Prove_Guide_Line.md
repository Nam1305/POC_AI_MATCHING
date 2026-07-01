# Hướng dẫn chứng minh trọng số W1–W5

> Tài liệu này mô tả 3 con đường để tìm ra hoặc chứng minh tính hợp lý của bộ trọng số trong `app/services/scorer.py`.

---

## Trọng số hiện tại

```python
# DEFAULT_WEIGHTS_WITH_ROLE
W1  semantic   = 0.25
W2  skills     = 0.30
W3  experience = 0.20
W4  education  = 0.10
W5  keywords   = 0.05
W6  role_fit   = 0.10
# Σ = 1.00
```

---

## Con đường 1 — Entropy Weighting (Nhanh nhất, ~2 ngày, không cần data mới)

**Ý tưởng:** Chiều nào phân biệt CV tốt/xấu nhất (variance cao) → weight cao. Tính từ data `result_test/` có sẵn.

### Bước 1: Thu thập điểm D1–D5 từ batch test

```python
import json, os

dimension_scores = []  # list of [d1, d2, d3, d4, d5]
for f in os.listdir("result_test/"):
    data = json.load(open(f"result_test/{f}"))
    s = data["scores"]
    dimension_scores.append([
        s["semantic"]   / 100,
        s["skills"]     / 100,
        s["experience"] / 100,
        s["education"]  / 100,
        s["keywords"]   / 100,
    ])
```

### Bước 2: Tính entropy weights

```python
import numpy as np

matrix = np.array(dimension_scores)  # shape (N, 5)
N = matrix.shape[0]

# Normalize từng cột
p = matrix / (matrix.sum(axis=0) + 1e-9)

# Shannon entropy
entropy = -(p * np.log(p + 1e-9)).sum(axis=0) / np.log(N)

# Diversity = discriminating power
diversity = 1 - entropy

# Weights
weights = diversity / diversity.sum()
labels = ["semantic", "skills", "experience", "education", "keywords"]
for k, w in zip(labels, weights):
    print(f"{k:12s}: {w:.4f}")
```

### Bước 3: So sánh với current weights

```
current:  semantic=0.25, skills=0.30, experience=0.20, education=0.10, keywords=0.05
entropy:  ???  ← điền kết quả tính được
```

Nếu `entropy weights ≈ current weights` → **validated**.

**Paper tham khảo:**
- [An Information Entropy Weighting Method Combined with TOPSIS](https://www.researchgate.net/publication/256457451_An_Information_Entropy_Weighting_Method_Combined_to_TOPSIS_Approach_for_Ranking_Consulting_Firms)
- [Objective Methods for MCDM Weights: Entropy, CRITIC, SD (DMAME)](https://dmame-journal.org/index.php/dmame/article/view/194)

---

## Con đường 2 — AHP (Chặt chẽ về lý thuyết, ~1 tuần, cần HR expert)

**Ý tưởng:** Hỏi 3–5 recruiter "Tiêu chí A quan trọng hơn B bao nhiêu lần?", tính eigenvector → đó là trọng số.

### Bước 1: Phỏng vấn expert, điền ma trận 5×5

Dùng thang Saaty: **1** = ngang nhau, **3** = hơi quan trọng hơn, **5** = rõ ràng hơn, **7** = rất hơn, **9** = tuyệt đối hơn.

```
Câu hỏi mẫu:
- "Skills match quan trọng hơn Education level bao nhiêu lần?" → 5
- "Experience quan trọng hơn Keywords bao nhiêu lần?"          → 7
- "Semantic similarity quan trọng hơn Keywords bao nhiêu lần?" → 5
... (10 cặp cho 5 tiêu chí)
```

### Bước 2: Xây và giải ma trận

```python
import numpy as np

# Ma trận so sánh cặp (5×5)
# Hàng/cột: [semantic, skills, experience, education, keywords]
A = np.array([
    [1,   1/2,  1/2,  3,   5  ],   # semantic
    [2,   1,    3/2,  5,   7  ],   # skills
    [2,   2/3,  1,    3,   5  ],   # experience
    [1/3, 1/5,  1/3,  1,   3  ],   # education
    [1/5, 1/7,  1/5,  1/3, 1  ],   # keywords
])

# Tính eigenvector chính
eigenvalues, eigenvectors = np.linalg.eig(A)
max_idx = np.argmax(eigenvalues.real)
w = eigenvectors[:, max_idx].real
w = w / w.sum()  # normalize

# Kiểm tra Consistency Ratio (phải < 0.10)
lambda_max = eigenvalues[max_idx].real
n = 5
CI = (lambda_max - n) / (n - 1)
RI = {3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24}[n]
CR = CI / RI

print(f"Weights: {dict(zip(['semantic','skills','experience','education','keywords'], w))}")
print(f"CR = {CR:.4f} {'✅ OK' if CR < 0.10 else '❌ Cần điều chỉnh lại ma trận'}")
```

### Bước 3: Nếu CR < 0.10 → weights AHP hợp lệ

So sánh kết quả với current weights. Khoảng cách nhỏ → **current weights được confirm**.

**Paper tham khảo:**
- [AHP-Powered LLM Reasoning for Multi-Criteria Evaluation (EMNLP 2024)](https://aclanthology.org/2024.findings-emnlp.101.pdf)
- [Job Recommendation System Based on AHP and K-means (ACM 2021)](https://dl.acm.org/doi/fullHtml/10.1145/3474963.3474978)
- [Analytic Hierarchy Process (Wikipedia)](https://en.wikipedia.org/wiki/Analytic_hierarchy_process)

---

## Con đường 3 — Regression từ Labeled Data (Mạnh nhất, ~4 tuần)

**Ý tưởng:** Học W trực tiếp từ dữ liệu (CV, JD, recruiter_score), tối ưu MSE.

### Bước 1: Tạo labeled dataset

**Option A — Synthetic labels bằng LLM (nhanh):**

```python
# Với mỗi cặp (CV, JD), gọi Claude/GPT:
prompt = """
Bạn là HR expert. Đánh giá mức độ phù hợp của CV này với JD này.
Cho điểm 0-100. Chỉ trả về số nguyên.

JD: {jd_text}
CV: {cv_text}
"""
# Thu thập recruiter_score_i cho 200+ cặp
```

**Option B — Recruiter thực tế (chắc hơn):** ~50 cặp là đủ để validate.

### Bước 2: Thu thập dimension scores

```python
# Với mỗi cặp (i): tính D1..D5 bằng hệ thống hiện tại (calculate_score)
X = []  # shape (N, 5) — dimension scores (0–100)
y = []  # shape (N,)   — recruiter labels (0–100)
```

### Bước 3: Tối ưu trọng số

```python
from scipy.optimize import minimize
import numpy as np

X = np.array(X)  # (N, 5)
y = np.array(y)  # (N,)

def loss(w):
    pred = X @ w
    return np.mean((pred - y) ** 2)

constraints = [{'type': 'eq', 'fun': lambda w: w.sum() - 1}]
bounds = [(0, 1)] * 5
w0 = np.array([0.25, 0.30, 0.20, 0.10, 0.05])  # khởi tạo = current weights

result = minimize(loss, w0, method='SLSQP',
                  bounds=bounds, constraints=constraints)
learned_w = result.x
print(dict(zip(['semantic', 'skills', 'experience', 'education', 'keywords'], learned_w)))
```

### Bước 4: Đánh giá

```python
from scipy.stats import spearmanr

pred_current = X @ np.array([0.25, 0.30, 0.20, 0.10, 0.05])
pred_learned = X @ learned_w

corr_current, _ = spearmanr(pred_current, y)
corr_learned, _ = spearmanr(pred_learned, y)

print(f"Spearman (current weights): {corr_current:.4f}")
print(f"Spearman (learned weights): {corr_learned:.4f}")
# Nếu corr_current ≈ corr_learned → current weights validated
```

**Paper tham khảo:**
- [Machine Learned Resume-Job Matching Solution — LinkedIn (arxiv 2016)](https://arxiv.org/abs/1607.07657)
- [RankPO: Preference Optimization for Job-Talent Matching (arxiv 2025)](https://arxiv.org/abs/2503.10723)

---

## Sensitivity Analysis (Bổ sung cho mọi con đường)

Chứng minh rằng thay đổi nhỏ ±0.05 không làm thay đổi ranking đáng kể.

```python
from itertools import product
from scipy.stats import spearmanr
import numpy as np

base_w = np.array([0.25, 0.30, 0.20, 0.10, 0.05])
base_scores = X @ base_w

correlations = []
for deltas in product([-0.05, 0, 0.05], repeat=5):
    w = base_w + np.array(deltas)
    if any(w < 0):
        continue
    w = w / w.sum()
    corr, _ = spearmanr(X @ w, base_scores)
    correlations.append(corr)

print(f"Min Spearman vs base: {min(correlations):.4f}")
# Nếu > 0.95 → weights ROBUST
```

**Kết quả kỳ vọng:** Min Spearman > 0.95 → xếp hạng ổn định dù thay đổi trọng số nhỏ.

**Paper tham khảo:**
- [PeopleSearchBench: Multi-Dimensional Benchmark (2026)](https://arxiv.org/pdf/2603.27476)

---

## Tóm tắt lộ trình

| Con đường | Thời gian | Cần gì | Kết quả |
|-----------|:---------:|--------|---------|
| **Entropy Weighting** | 2 ngày | `result_test/` có sẵn | Objective, data-driven |
| **AHP** | 1 tuần | 3–5 HR expert | Lý thuyết chặt chẽ, defensible |
| **Regression** | 3–4 tuần | 100–300 labeled pairs | Empirical, mạnh nhất |
| **Sensitivity Analysis** | 1 ngày | Không cần gì thêm | Chứng minh robustness |

**Đề xuất:** Bắt đầu với **Entropy** (ngay hôm nay) + **Sensitivity Analysis** để có kết quả nhanh. Sau đó làm **AHP** để có bằng chứng lý thuyết cho báo cáo/paper.