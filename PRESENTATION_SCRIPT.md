# 🎯 AI Matching Engine — Presentation Script

---

## 📋 TABLE OF CONTENTS

1. **Full Architecture Overview** (5 mins)
2. **The 3-Stage Pipeline** (2 mins)
3. **Stage 1: Pre-Processing Data** (8 mins)
4. **Stage 2: Dense Embeddings** (3 mins)
5. **Stage 3: Multi-Dimensional Scoring** (12 mins)
6. **Key Insights & Conclusion** (2 mins)

---

## 🏗️ PART 1: FULL ARCHITECTURE OVERVIEW (5 mins)

### What is this system?

We're building an **AI-powered CV-JD Matching Engine** that automatically evaluates the compatibility between a candidate's CV and a job description.

**Goal:** Given a CV and a JD, output a match score (0-100) with detailed breakdown.

### Why is this important?

- **For HR/Recruiters:** Automated candidate screening, consistency, time-saving
- **For Candidates:** Fair evaluation, detailed feedback on where they stand
- **For Companies:** Data-driven hiring, reduce bias, better matching

### The High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI AI Service                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  INPUT: CV file (PDF/text) + JD text                            │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Stage 1      │  │ Stage 2      │  │ Stage 3      │           │
│  │ PARSING      │→ │ EMBEDDING    │→ │ SCORING      │           │
│  │              │  │              │  │              │           │
│  │ LLM-based    │  │ Neural net   │  │ Pure math    │           │
│  │ extraction   │  │ (transformer)│  │ (no LLM)     │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│         ↓                  ↓                  ↓                   │
│      JSON data      Dense vectors      5D Scores                 │
│      (structured)   (384-1536 dims)    + Final Score (0-100)    │
│                                                                   │
│  OUTPUT: Match score with detailed breakdown                     │
│          (semantic, skills, experience, education, keywords)    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Three separate stages** — each can be optimized independently
2. **No LLM in Stage 3 (Scoring)** — pure Python math for speed & consistency
3. **Stateless microservice** — can scale horizontally
4. **Provider flexibility** — swap embedding or LLM providers via .env

---

## ⚙️ PART 2: THE 3-STAGE PIPELINE (2 mins)

### Quick Overview

| Stage | Input | Process | Output | Cost |
|-------|-------|---------|--------|------|
| **1: Parse** | Raw CV/JD text | LLM extracts structured data | JSON (skills, experience, education, keywords) | 💰 LLM cost |
| **2: Embed** | Parsed text | Neural net vectorizes | Dense vectors (384-1536 dims) | 💰 Embed API cost |
| **3: Score** | CV + JD embeddings + parsed data | Math & heuristics | 5D scores + final match (0-100) | ✅ Free (local) |

### Why this architecture?

- **Separation of concerns** — clean boundaries between LLM, embedding, and scoring
- **Cost efficient** — expensive LLM work happens once, scoring is cheap
- **Testable** — each stage has clear inputs/outputs
- **Flexible** — can swap providers without rewriting logic

---

## 🔍 PART 3: STAGE 1 — PRE-PROCESSING DATA (8 mins)

### What is Pre-Processing?

Raw CV/JD text is **unstructured** and **messy**. We need to convert it into clean, **structured JSON** for downstream processing.

**Example:**
```
Raw CV (messy):
"Senior Full-Stack Developer at TechCorp (2020-2023)
Led development of microservices using Node.js, React, PostgreSQL.
Key achievements: reduced API latency by 40%, mentored 5 junior devs.
Skills: JavaScript, TypeScript, React, Node.js, Docker, AWS..."

↓ PARSING ↓

Structured JSON:
{
  "work_experience": [{
    "company": "TechCorp",
    "role": "Senior Full-Stack Developer",
    "start": "2020-01",
    "end": "2023-01",
    "months": 36,
    "tech_stack": ["nodejs", "react", "postgresql", "docker", "aws"],
    "description": "Led development of microservices... reduced latency by 40%..."
  }],
  "skills": ["javascript", "typescript", "react", "nodejs", ...],
  "education": [{
    "institution": "Tech University",
    "degree": "bachelor",
    "major": "Computer Science"
  }]
}
```

### How does parsing work?

**Step 1: Extract CV/JD text**

```
POST /ai/parse-cv
{
  "cv_file": <PDF or text file>,
}

POST /ai/parse-jd
{
  "jd_text": "Senior Developer at Company X..."
}
```

**Step 2: Send to LLM (Claude or Llama)**

We use **structured prompts** with clear JSON output format. The prompt tells the LLM:
- What to extract (skills, experience, education, projects, etc.)
- What format to use (JSON schema)
- Edge cases (what if no degree? what if date is missing?)

**Example prompt structure:**
```
"Extract information from the CV text below.
Return ONLY valid JSON. No explanation, no markdown fences.

JSON structure:
{
  "name": "...",
  "skills": ["skill1", "skill2", ...],
  "work_experience": [
    {
      "company": "...",
      "role": "...",
      "start": "YYYY-MM",
      "end": "YYYY-MM or present",
      "tech_stack": [...],
      "description": "..."
    }
  ],
  "education": [
    {
      "institution": "...",
      "degree": "high_school | associate | bachelor | master | phd | other",
      "major": "..."
    }
  ],
  ...
}"
```

**Step 3: Data Validation & Auto-Retry**

After LLM returns JSON, we validate it:
- ✅ All required fields present?
- ✅ Correct data types?
- ✅ Critical fields (work_experience, skills) non-empty?

If validation fails, we **auto-retry with focused prompts**:
```
Example: If work_experience is missing, retry with:
"Focus ONLY on the employment/work history section.
Extract ALL jobs: full-time, part-time, internships, freelance."
```

**Why auto-retry?** Because sometimes the first parse misses critical info, but a focused retry is often successful.

**Step 4: Date Calculation**

Once we have structured data, we calculate **months of experience** locally (not asking LLM):

```python
def _diff_months(start: "2020-06", end: "2023-03") → int:
    return (2023 - 2020) * 12 + (3 - 6) = 33 months
```

Why? **Accuracy** — dates are deterministic, no need to ask LLM.

**Step 5: Degree Level Normalization**

Map arbitrary degree strings to a canonical enum:

```
"Bachelor of Software Engineering" → DegreeLevel.BACHELOR (numeric: 3)
"Master of Business Admin" → DegreeLevel.MASTER (numeric: 4)
"High School Diploma" → DegreeLevel.HIGH_SCHOOL (numeric: 1)
```

This numeric mapping is crucial for **scoring** later.

### What gets extracted?

**CV Structure:**
```json
{
  "name": "John Doe",
  "summary": "Professional summary...",
  "skills": ["Python", "React", "PostgreSQL", ...],
  "work_experience": [
    {
      "company": "Company A",
      "role": "Senior Developer",
      "start": "2022-01",
      "end": "present",
      "is_current": true,
      "months": 24,
      "tech_stack": ["Python", "Django", "PostgreSQL"],
      "description": "Key responsibilities and achievements..."
    },
    ...
  ],
  "education": [
    {
      "institution": "University of X",
      "degree": "bachelor",
      "degree_raw": "B.Sc. in Computer Science",
      "major": "Computer Science"
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "tech_stack": ["Tech1", "Tech2"],
      "description": "What the project does..."
    }
  ],
  "certifications": ["AWS Solutions Architect", ...],
  "languages": ["English - Fluent", "Vietnamese - Native"]
}
```

**JD Structure:**
```json
{
  "title": "Senior Full-Stack Engineer",
  "description": "Job description text...",
  "min_experience_years": 5,
  "required_skills": [
    {"skill": "Python", "weight": 3},
    {"skill": "React", "weight": 3},
    {"skill": "PostgreSQL", "weight": 2},
    {"skill": "Docker", "weight": 1}
  ],
  "required_degree_level": 3,  // Bachelor
  "keywords": ["agile", "CI/CD", "microservices"],
  "seniority": "senior"
}
```

### Key Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| **LLM hallucination** | Focused auto-retry, validation checks |
| **Missing dates** | Use empty string, fallback to year-only |
| **Fuzzy skill names** | Normalize via alias map (handled in Scoring stage) |
| **Multi-language** | Claude handles this well out-of-box |
| **PDF parsing** | Pre-convert to text before sending to LLM |

---

## 💡 PART 4: STAGE 2 — DENSE EMBEDDINGS (3 mins)

### What is an embedding?

A **dense vector** (list of 300-1500 numbers) that represents the semantic meaning of text.

```
Text: "Senior Python Developer with 5 years of experience"
                        ↓ Embedding ↓
Vector: [-0.123, 0.456, 0.789, -0.234, 0.567, ...]  (384-1536 dimensions)
```

**Why dense vectors?**
- Capture semantic relationships (similar texts → similar vectors)
- Enable **cosine similarity** comparison (how similar are two texts?)
- Work with transformer models

### How embeddings work in this system

**Step 1: Prepare text**
```python
cv_text = "Senior Python Developer... Docker, Kubernetes, PostgreSQL...
           5 years experience at TechCorp..."

jd_text = "We're hiring a Senior Backend Engineer with Python and cloud experience..."
```

**Step 2: Send to embedding provider**

Three options (via `.env EMBED_PROVIDER`):

| Provider | Model | Dimensions | Cost | Speed |
|----------|-------|-----------|------|-------|
| **sentence_transformer** | all-MiniLM-L6-v2 | 384 | Free ✅ | Fast (local) |
| **openai** | text-embedding-3-small | 1536 | Paid | API call |
| **gemini** | gemini-embedding-001 | 3072 | Paid | API call |

We default to **sentence_transformer** because it's free and runs locally.

**Step 3: Get dense vectors**
```python
cv_embedding = [0.12, -0.45, 0.78, ...]  # 384 numbers
jd_embedding = [0.11, -0.46, 0.80, ...]  # 384 numbers
```

**Step 4: Compute similarity**

```python
similarity = cosine_similarity(cv_embedding, jd_embedding)
# Result: 0.82 (range -1 to 1, typically 0-1 for text)
```

This becomes **D1: Semantic Score** later.

### Why embeddings matter

- **Semantic understanding** — catches meaning beyond exact keyword match
- **Flexibility** — handles paraphrasing, synonyms
- **Quantifiable** — enables scoring

---

## 🎯 PART 5: STAGE 3 — MULTI-DIMENSIONAL SCORING (12 mins)

### The Problem

How do we compare a CV and JD **fairly**?

- ❌ Pure semantic similarity (embedding only) → missing specific requirements
- ❌ Pure keyword matching → brittle, no context
- ❌ Single number score → no transparency

**Solution:** **5-dimensional scoring system**

### The 5 Dimensions

Each dimension evaluates a **different aspect** of CV-JD match:

```
Final Score = (D1×0.25 + D2×0.30 + D3×0.20 + D4×0.10 + D5×0.05) × 100
                ─────────────────────────────────────────────────────────
                              Default weights (tunable)
```

---

### **D1: Semantic Similarity** (25% weight)

**What:** How semantically similar are the CV and JD?

**How:**
```python
cosine_similarity = cosine(cv_embedding, jd_embedding)
# Result: 0.55–0.90 range for relevant matches

normalized = (raw - 0.55) / (0.90 - 0.55)
# Stretch [0.55, 0.90] → [0, 1]
# Below 0.55 → unrelated fields
# Above 0.90 → same tech stack
```

**Example:**
- CV: "Senior Python Developer, 5 years, microservices, Docker, AWS"
- JD: "Python Backend Engineer, cloud-native experience, Docker"
- Similarity: 0.85 → **D1 = 100**

---

### **D2: Skills Matching** (30% weight) ⭐ Most Important

**What:** How well do the candidate's skills match JD requirements?

**Why 30%?** Because skills are the most direct indicator of capability.

**How (3-tier matching):**

**Tier 1: Exact Match**
```
CV skill: "Python" (normalized)
JD skill: "Python" (normalized)
→ Full weight (1.0)
```

**Tier 2: Fuzzy Match** (handles typos & variants)
```
CV skill: "Reactjs" 
JD skill: "React"
Similarity: 92% > 85% threshold
→ 90% weight (0.9)
```

**Tier 3: Category Match** (partial credit for related skills)
```
JD requires: "Angular"
CV has: "React", "Vue" (both frontend)
Same category (frontend) with 2 overlaps
→ 40% weight (0.3–0.5 scale)
```

**Example Calculation:**
```
JD required skills:
├─ Python (weight: 3) — MUST HAVE
├─ Django (weight: 2)
└─ Docker (weight: 1)
Total weight: 6

CV skills: Python ✅, Flask (not Django, but backend category), Docker ✅

Matched weight:
├─ Python: 3 (exact match)
├─ Django: 2 × 0.4 = 0.8 (category match — Flask is also backend)
└─ Docker: 1 (exact match)
Total matched: 3 + 0.8 + 1 = 4.8

D2 = 4.8 / 6 = 0.80 (80%)
```

**Skill Aliases (handles ecosystem variants):**
- "JS" ↔ "JavaScript" ↔ "ES6" → all normalize to "javascript"
- "K8s" ↔ "kubernetes" → "kubernetes"
- "Postgres" ↔ "PostgreSQL" → "postgresql"
- "ts" ↔ "TypeScript" → "typescript"

**Categories (for partial credit):**
- **Frontend:** React, Vue, Angular, JavaScript, TypeScript, HTML, CSS, Tailwind
- **Backend:** Django, Flask, FastAPI, Spring, Express, NestJS, ASP.NET
- **Database:** MySQL, PostgreSQL, MongoDB, Redis, Elasticsearch
- **Cloud:** AWS, GCP, Azure
- **DevOps:** Docker, Kubernetes, CI/CD, Jenkins, Terraform
- **ML:** TensorFlow, PyTorch, Keras, Scikit-learn

---

### **D3: Experience Relevance** (20% weight)

**What:** Does the candidate have enough relevant experience?

**How:**

**Base Score:**
```python
base = min(cv_total_years / jd_required_years, 1.0)

Example:
CV: 5 years experience
JD: "3+ years required"
base = min(5/3, 1.0) = 1.0
```

**Then Apply Modifiers:**

| Modifier | Effect | Example |
|----------|--------|---------|
| **Domain Relevance** | +0.20 if work history overlaps JD keywords | CV has "microservices" experience, JD mentions "microservices" → +0.20 |
| **Recency** | +0.10 if latest job < 3 months ago (current) | Last job still active → +0.10 |
| **Employment Gap** | -0.10 if latest job ended > 12 months ago | Last job: 18 months ago → -0.10 |
| **Over-qualification** | -0.05 if cv_years > 2 × jd_required | CV: 8 years, JD: 3 years → -0.05 |

**Example Calculation:**
```
CV: 6 years total, last job is current, domain overlap exists
JD: "5+ years required"

base = min(6/5, 1.0) = 1.0
modifiers:
  + domain relevance: +0.20
  + current job: +0.10
  − over-qualification: −0.05
                        ─────
  total modifiers: +0.25

D3 = clamp(1.0 + 0.25, 0, 1.0) = 1.0 (capped at 1.0)
```

---

### **D4: Education Match** (10% weight)

**What:** Does the candidate's education meet the requirement?

**How (simplest dimension):**
```python
D4 = min(cv_degree_level / jd_required_degree_level, 1.0)
```

**Degree Mapping:**
| Level | Value | Examples |
|-------|-------|----------|
| **High School** | 1 | High School Diploma |
| **Associate** | 2 | Associate Degree |
| **Bachelor** | 3 | B.Sc., B.A., Bachelor |
| **Master** | 4 | M.Sc., MBA, Master |
| **PhD** | 5 | PhD, Doctorate |

**Examples:**
```
CV: Bachelor (3), JD requires: Bachelor (3)
D4 = 3/3 = 1.0 ✅

CV: Master (4), JD requires: Bachelor (3)
D4 = 4/3 = 1.33 → capped at 1.0 ✅ (over-qualified is OK)

CV: High School (1), JD requires: Master (4)
D4 = 1/4 = 0.25 ❌ (under-qualified)
```

---

### **D5: Keywords & Specific Requirements** (5% weight)

**What:** Are specific keywords/requirements mentioned in the CV?

**How (3-level matching):**

**Level 1: Exact Substring Match**
```
JD keyword: "CI/CD"
CV text: "...implemented CI/CD pipelines using Jenkins..."
Match found → Score: 1.0
```

**Level 2: Word-Boundary Match**
```
JD keyword: "agile"
CV text: "...following agile methodology and scrum practices..."
Word "agile" found → Score: 1.0
```

**Level 3: Multi-word Phrase (all subwords present)**
```
JD keyword: "microservices architecture"
CV text: "...worked on microservices... AWS architecture design..."
Both "microservices" and "architecture" present → Score: 0.7 (partial credit)
```

**Final Score:**
```
D5 = average of all keyword scores

Example:
Keywords: ["CI/CD", "Docker", "Kubernetes", "Agile"]
CV matches:
├─ CI/CD: found (1.0)
├─ Docker: found (1.0)
├─ Kubernetes: NOT found (0.0)
└─ Agile: found (1.0)

D5 = (1 + 1 + 0 + 1) / 4 = 0.75 (75%)
```

---

### **Putting It All Together**

**Example Final Scoring:**

```
Candidate: "John Doe"
CV Analysis:
├─ D1 (Semantic):    0.85 (vectors are similar)
├─ D2 (Skills):      0.80 (80% skill overlap)
├─ D3 (Experience):  1.00 (5+ years, active, relevant)
├─ D4 (Education):   1.00 (Bachelor, required Bachelor)
└─ D5 (Keywords):    0.75 (75% keywords present)

Weights (default):
├─ semantic:   0.25
├─ skills:     0.30
├─ experience: 0.20
├─ education:  0.10
└─ keywords:   0.05

Calculation:
final = (0.85×0.25 + 0.80×0.30 + 1.00×0.20 + 1.00×0.10 + 0.75×0.05) × 100
      = (0.2125 + 0.240 + 0.200 + 0.100 + 0.0375) × 100
      = 0.79 × 100
      = 79.0 / 100
```

**Output:**
```json
{
  "final_score": 79.0,
  "scores": {
    "semantic":   85.0,
    "skills":     80.0,
    "experience": 100.0,
    "education":  100.0,
    "keywords":   75.0
  }
}
```

### Business Rules (Hard Constraints)

We also apply **penalties** for deal-breakers:

```python
if enforce_must_have:
    # Missing critical skills (weight ≥ 3)
    for each missing must-have skill:
        penalty += 0.20 (max -0.70 total)
    
    # Insufficient experience
    if cv_years < 0.8 × jd_required_years:
        penalty += 0.30

final_score *= (1 - penalty)
```

**Why?** Because missing a critical skill shouldn't just reduce score — it should be a strong red flag.

---

## 🎓 PART 6: KEY INSIGHTS & CONCLUSION (2 mins)

### What Makes This System Effective?

1. **Multi-dimensional** — doesn't rely on single metric
2. **Transparent** — each dimension is explainable
3. **Tunable** — weights can be adjusted per client need
4. **Fast & Cheap** — no LLM in scoring stage
5. **Extensible** — can add dimensions (culture fit, location, etc.)

### Why Not Just Use One Number?

```
❌ Bad: "Your match score is 75%"
   → Where did 75 come from? No insight.

✅ Good: 
   "Match Score: 75%
    ├─ Semantic fit: 85% ✅ (strong alignment)
    ├─ Skills: 80% ✅ (good overlap)
    ├─ Experience: 100% ✅ (meets requirement)
    ├─ Education: 100% ✅ (exceeds requirement)
    └─ Keywords: 75% ⚠️  (missing some specifics)"
```

This transparency builds trust with both recruiters and candidates.

### Real-World Tuning

Different industries have different needs:

**Data Science roles:**
- Increase `education` weight (advanced degree common)
- Increase `keywords` weight (specific tools matter)

**Startup positions:**
- Decrease `education` weight (experience over credentials)
- Increase `semantic` weight (culture & innovation mindset)

**Enterprise roles:**
- Increase `experience` weight (stability & proven track record)
- Increase `education` weight (formal credentials valued)

---

## 🚀 TAKEAWAYS

1. **AI ≠ just LLM** — Our system uses LLM for parsing, neural nets for embedding, and pure math for scoring. Different tools for different jobs.

2. **Pre-processing is critical** — Spending effort to get clean, structured data upfront pays dividends in scoring quality.

3. **Explainability matters** — Multi-dimensional scoring beats a black box, even if the black box might be slightly more "accurate."

4. **Flexibility is valuable** — By separating stages, we can swap components, adjust weights, add new dimensions without rewriting everything.

5. **Transparent scoring = better outcomes** — Candidates understand what they need to improve; recruiters can set clear expectations.

---

## ❓ Q&A DISCUSSION POINTS

**Q: Why not just use LLM to score?**
A: LLM is expensive, non-deterministic, and hard to debug. Math is fast, predictable, and transparent.

**Q: What if a CV doesn't have a degree?**
A: D4 defaults to 0.5, doesn't penalize heavily. Other dimensions can compensate. Final score depends on other factors.

**Q: Can we customize weights per client?**
A: Yes! Each client can have their own weight config. AdaptiveWeights class even suggests weights based on JD characteristics.

**Q: How do we handle tech stack evolution?**
A: Skill aliases are easy to update. If "WebAssembly" becomes important, just add it to ALIASES dict. No retraining needed.

**Q: What about non-technical candidates?**
A: System still works — just fewer technical skills. Education & experience dimensions carry more weight.

---

## 📊 DEMO / WALKTHROUGH

**Show live API call:**

```bash
POST /ai/score
{
  "parsed_cv": { ... },
  "parsed_jd": { ... },
  "cv_embedding": [0.12, -0.45, ...],
  "jd_embedding": [0.11, -0.46, ...]
}

Response:
{
  "final_score": 79.0,
  "scores": {
    "semantic": 85.0,
    "skills": 80.0,
    "experience": 100.0,
    "education": 100.0,
    "keywords": 75.0
  }
}
```

**Or show screenshots of:**
- CV parsing result (JSON structure)
- Embedding vectors (visual similarity chart)
- Score breakdown (bar chart of 5 dimensions)

---

## 📚 APPENDIX: TECHNICAL REFERENCES

**Key Files:**
- [scorer.py](MVP_AI_Matching/app/services/scorer.py) — All 5 dimensions + scoring logic
- [parser.py](MVP_AI_Matching/app/services/parser.py) — LLM extraction
- [embedder.py](MVP_AI_Matching/app/services/embedder.py) — Embedding providers
- [schemas.py](MVP_AI_Matching/app/schemas.py) — Data models

**API Endpoints:**
- `POST /ai/parse-cv` — Parse CV file
- `POST /ai/parse-jd` — Parse JD text
- `POST /ai/score` — Score CV vs JD

**Configuration (.env):**
```
LLM_PROVIDER=claude|groq
EMBED_PROVIDER=sentence_transformer|openai|gemini
OPENAI_API_KEY=...
GEMINI_API_KEY=...
```

---

**END OF PRESENTATION SCRIPT**

