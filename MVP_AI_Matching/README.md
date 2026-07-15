# AI Service — CV/JD Matching Microservice

Stateless FastAPI service that powers a .NET-based hiring platform with AI-driven CV parsing, JD parsing, multi-dimensional scoring, and LLM-generated candidate evaluations.

## Architecture

```
ReactJS  ──→  .NET API  ──→  PostgreSQL
                  ↕ HTTP (Docker internal network)
            Python AI Service (this repo)
              - stateless: no DB, no auth
              - 4 endpoints under /ai
```

## Endpoints

| Method | Path | Purpose | LLM? |
|--------|------|---------|------|
| POST | `/ai/parse-jd` | JD text → structured JSON + embedding | ✅ |
| POST | `/ai/parse-cv` | CV URL(s) (S3/R2, PDF/DOCX) → structured JSON + embedding | ✅ |
| POST | `/ai/score` | CV ↔ JD → 5-dimension score + evaluation (narrative optional) | ❌ (✅ if `include_narrative=true`) |
| POST | `/ai/evaluate` | CV ↔ JD → qualitative HR narrative (skills/experience/education breakdown) | ✅ |
| GET | `/health` | Health check | ❌ |
| GET | `/docs` | Swagger UI | ❌ |

## Scoring Dimensions

| ID | Name | Method | Tech |
|----|------|--------|------|
| D1 | Semantic | Cosine similarity of embeddings, stretched over `[COSINE_MIN, COSINE_MAX]` | numpy |
| D2 | Skills | Weighted skill overlap — exact / implied (e.g. react → javascript) / fuzzy / category match | `skill_matcher.py` |
| D3 | Experience | `cv_years / jd_min_years`, capped at 1.0 | arithmetic |
| D4 | Education | `cv_degree_level / jd_required_degree_level`, capped at 1.0 | enum mapping |
| D5 | Location | Driving-time estimate (OSRM route on geocoded lat/lng) × work-mode fit (onsite/hybrid/remote) | Nominatim + OSRM |

`final_score = Σ(Di × Wi) × 100`, weights configurable per-request (`weights` field on `/ai/score`) or via `DEFAULT_WEIGHT_*` in `.env`.

## Setup

### 1. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env to set API keys
```

Embedding always uses Gemini (`gemini-embedding-001`), regardless of which `LLM_PROVIDER` you pick — so `GEMINI_API_KEY` is required in every setup.

**Free dev stack:**
```
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...             # still required for embeddings
```

**Production stack:**
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
# or: ./run.sh start   (./run.sh stop to kill it)
```

Open `http://localhost:8000/docs` for Swagger.

### 4. Docker Deployment

```bash
docker-compose up --build
```

## Project Structure

```
MVP_AI_Matching/
├── app/
│   ├── main.py                  FastAPI app + router mounts
│   ├── config.py                pydantic-settings (loads .env, SCORE_DIMENSIONS)
│   ├── schemas.py                Pydantic models (ParsedCV, ParsedJD, CVJobEvaluation, ...)
│   ├── api/                     HTTP endpoints (parse, score, evaluate)
│   └── services/
│       ├── pdf_extractor.py       PDF/DOCX text extraction (+ OCR fallback)
│       ├── llm_client.py          Shared LLM client (anthropic/gemini/groq)
│       ├── parser.py              LLM-based CV/JD → structured JSON (+ geocoding)
│       ├── embedder.py            Gemini embeddings
│       ├── scorer.py              5-dimension scoring engine (D1-D5)
│       ├── skill_matcher.py       Skill alias/implied/fuzzy/category matching
│       ├── skill_data.py          Skill alias + category data
│       ├── skill_implies.py       Skill implication graph (e.g. react → javascript)
│       ├── evaluator.py           LLM narrative + qualitative evaluation
│       └── location_service.py    Geocoding + driving-time (Nominatim/OSRM)
├── tests/                       pytest unit tests (parser, scorer, evaluator — no LLM/network)
├── scripts/                     offline generation of the skill-implication data
├── quick_test.py                CLI smoke test against a running server
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── run.sh                       start/stop helper for local uvicorn
```

## Testing

```bash
pytest -v
```

All tests are self-contained unit tests (LLM calls and geocoding are monkeypatched) — no API keys or network access needed.

## Manual Smoke Test

Against a running server (mirrors the real .NET integration flow: health → parse-jd → parse-cv → score):

```bash
python quick_test.py --base-url http://localhost:8000
```

## How .NET Calls This Service

After R2 upload, .NET fires an HTTP call to `http://ai-service:8000/ai/parse-cv` with the CV's R2 URL(s). The AI service downloads, parses, and embeds each CV, returning structured JSON that .NET persists to PostgreSQL. Scoring is then triggered separately via `/ai/score`, and a qualitative narrative can be requested either inline (`include_narrative=true`) or standalone via `/ai/evaluate`.
