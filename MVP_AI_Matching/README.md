# AI Service — CV/JD Matching Microservice

Stateless FastAPI service that powers a .NET-based hiring platform with AI-driven CV parsing, JD parsing, multi-dimensional scoring, and natural-language candidate search.

## Architecture

```
ReactJS  ──→  .NET API  ──→  PostgreSQL
                  ↕ HTTP (Docker internal network)
            Python AI Service (this repo)
              - stateless: no DB, no auth
              - 5 endpoints under /ai
```

## Endpoints

| Method | Path | Purpose | LLM? |
|--------|------|---------|------|
| POST | `/ai/parse-jd` | JD text → structured JSON + embedding | ✅ |
| POST | `/ai/parse-cv` | CV file (PDF/DOCX) → structured JSON + embedding | ✅ |
| POST | `/ai/score` | CV ↔ JD → 5-dimension score + final score | ❌ |
| POST | `/ai/recalculate` | Re-apply new weights to existing scores | ❌ |
| POST | `/ai/search` | Natural-language query → ranked candidates | ✅ |
| GET | `/health` | Health check | ❌ |
| GET | `/docs` | Swagger UI | ❌ |

## Scoring Dimensions

| ID | Name | Method | Tech |
|----|------|--------|------|
| D1 | Semantic | Cosine similarity of embeddings | numpy |
| D2 | Skills | Weighted skill overlap (incl. tech_stack) | Python sets |
| D3 | Experience | `cv_years / jd_min_years`, capped 1.0 | arithmetic |
| D4 | Education | `cv_degree_level / jd_degree_level` | enum mapping |
| D5 | Keywords | Substring overlap on raw CV text | string match |

`final_score = Σ(Di × Wi) × 100`

## Setup

### 1. Install Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env to set API keys
```

**Free dev stack (no payment required):**
```
LLM_PROVIDER=groq
EMBED_PROVIDER=sentence_transformer
GROQ_API_KEY=gsk_...
```

**Production stack:**
```
LLM_PROVIDER=anthropic
EMBED_PROVIDER=openai
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
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
│   ├── main.py              FastAPI app + router mounts
│   ├── config.py            pydantic-settings (loads .env)
│   ├── schemas.py           Pydantic models (ParsedCV, ParsedJD)
│   ├── api/                 HTTP endpoints (thin wrappers)
│   └── services/            Business logic (PDF, LLM, embed, score)
├── tests/                   pytest unit + integration tests
├── sample_data/             Manual testing inputs
├── requirements.txt
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

## Testing

```bash
# Unit tests
pytest tests/test_scorer.py -v

# Integration (needs API keys)
pytest tests/test_integration.py -v
```

## How .NET Calls This Service

After R2 upload, .NET fires an HTTP call to `http://ai-service:8000/ai/parse-cv` with the CV bytes. The AI service returns parsed JSON + embedding, which .NET persists to PostgreSQL. Scoring is then triggered separately via `/ai/score`.

See `Plan.md` (parent folder) for full end-to-end flow diagrams.
