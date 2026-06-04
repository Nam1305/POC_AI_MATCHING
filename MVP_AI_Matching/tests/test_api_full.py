"""
Full API integration test — chạy qua toàn bộ 5 endpoint theo pipeline thực tế.

Cách chạy (từ MVP_AI_Matching/):
    python tests/test_api_full.py

Yêu cầu:
    pip install requests
    Server đang chạy: python -m uvicorn app.main:app --port 8000
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

BASE = "http://localhost:8000/ai"
CV_PATH = Path(__file__).parent.parent.parent / "POC_CV_Matching" / "CVs" / "backend_developer_1.pdf"
JD_PATH = Path(__file__).parent.parent / "sample_data" / "jd_sample.txt"

# ─── ANSI colors ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}[OK]{RESET}   {msg}")
def fail(msg): print(f"  {RED}[FAIL]{RESET} {msg}")
def step(msg): print(f"\n{CYAN}=== {msg} ==={RESET}")
def warn(msg): print(f"  {YELLOW}[WARN]{RESET} {msg}")


def assert_range(val, lo, hi, label):
    if val is not None and lo <= val <= hi:
        ok(f"{label} = {val:.1f}  (in [{lo}, {hi}])")
    else:
        fail(f"{label} = {val}  NOT in [{lo}, {hi}]")


def assert_len(lst, expected, label):
    n = len(lst) if lst else 0
    if n == expected:
        ok(f"{label} length = {expected}")
    else:
        fail(f"{label} length = {n}, expected {expected}")


def post(path, **kwargs):
    """Thin wrapper that always raises on non-2xx."""
    r = requests.post(f"{BASE}{path}", timeout=120, **kwargs)
    if not r.ok:
        body = ""
        try:
            body = json.dumps(r.json(), indent=2)
        except Exception:
            body = r.text[:500]
        raise RuntimeError(f"HTTP {r.status_code} on {path}:\n{body}")
    return r.json()


# ── Step 0 — Health ─────────────────────────────────────────────────────────
def step0_health():
    step("Step 0 — Health check")
    r = requests.get("http://localhost:8000/health", timeout=5)
    if r.ok and r.json().get("status") == "ok":
        ok("Server is up")
    else:
        fail("Server not reachable")
        print(f"\n  → Start server: python -m uvicorn app.main:app --reload")
        sys.exit(1)


# ── Step 1 — Parse JD ───────────────────────────────────────────────────────
def step1_parse_jd():
    step("Step 1 — POST /ai/parse-jd")
    jd_text = JD_PATH.read_text(encoding="utf-8")
    print(f"  JD file: {JD_PATH.name}  ({len(jd_text)} chars)")

    result = post("/parse-jd", json={"jd_text": jd_text})

    pjd = result["parsed_jd"]
    emb = result["embedding"]
    ok(f"Title: {pjd.get('title', '—')}")
    ok(f"Required skills: {len(pjd.get('required_skills', []))}")
    ok(f"Min exp years: {pjd.get('min_experience_years', '—')}")
    assert_len(emb, 384, "JD embedding")

    return result


# ── Step 2 — Parse CV ───────────────────────────────────────────────────────
def step2_parse_cv():
    step("Step 2 — POST /ai/parse-cv  (file upload)")
    path = CV_PATH
    if not path.exists():
        path = CV_PATH.parent / "ai_engineer_1.pdf"
    print(f"  Uploading: {path.name}  ({path.stat().st_size // 1024} KB)")

    with open(path, "rb") as f:
        # requests handles multipart boundary correctly
        result = post("/parse-cv", files={"cv_file": (path.name, f, "application/pdf")})

    raw = result.get("cv_raw_text", "")
    pcv = result.get("parsed_cv", {})
    emb = result.get("embedding", [])

    ok(f"cv_raw_text: {len(raw)} chars")
    ok(f"Skills found: {pcv.get('skills', [])[:5]}")
    ok(f"Work experience: {len(pcv.get('work_experience', []))} entries")
    ok(f"Education: {len(pcv.get('education', []))} entries")
    assert_len(emb, 384, "CV embedding")

    if len(raw) < 100:
        fail("cv_raw_text too short — PDF parsing issue")
    else:
        ok("Text extraction successful")

    return result


# ── Step 3 — Score ──────────────────────────────────────────────────────────
def step3_score(cv_result, jd_result):
    step("Step 3 — POST /ai/score")

    body = {
        "parsed_cv":    cv_result["parsed_cv"],
        "parsed_jd":    jd_result["parsed_jd"],
        "cv_embedding": cv_result["embedding"],
        "jd_embedding": jd_result["embedding"],
        "cv_raw_text":  cv_result["cv_raw_text"],
    }
    result = post("/score", json=body)

    fs = result["final_score"]
    s  = result["scores"]
    assert_range(fs, 0, 100, "final_score")
    assert_range(s["semantic"],   0, 100, "D1 semantic")
    assert_range(s["skills"],     0, 100, "D2 skills")
    assert_range(s["experience"], 0, 100, "D3 experience")
    assert_range(s["education"],  0, 100, "D4 education")
    assert_range(s["keywords"],   0, 100, "D5 keywords")

    # Display score card
    bar = lambda v: ("█" * int(v / 10)).ljust(10)
    print()
    print(f"  ┌──────────────────────────────────────────┐")
    print(f"  │  Final Score : {fs:>6.1f} / 100               │")
    print(f"  │  D1 Semantic : {s['semantic']:>5.1f}%  {bar(s['semantic'])}  │")
    print(f"  │  D2 Skills   : {s['skills']:>5.1f}%  {bar(s['skills'])}  │")
    print(f"  │  D3 Exp      : {s['experience']:>5.1f}%  {bar(s['experience'])}  │")
    print(f"  │  D4 Education: {s['education']:>5.1f}%  {bar(s['education'])}  │")
    print(f"  │  D5 Keywords : {s['keywords']:>5.1f}%  {bar(s['keywords'])}  │")
    print(f"  └──────────────────────────────────────────┘")

    return result


# ── Step 4 — Recalculate ────────────────────────────────────────────────────
def step4_recalculate(score_result):
    step("Step 4 — POST /ai/recalculate  (no LLM, pure math)")

    original_scores = score_result["scores"]
    body = {
        "applications": [
            {"id": "app-001", "scores": original_scores},
            {"id": "app-002", "scores": {"semantic": 70.0, "skills": 80.0,
                                          "experience": 60.0, "education": 100.0, "keywords": 50.0}},
            {"id": "app-003", "scores": {"semantic": 85.0, "skills": 55.0,
                                          "experience": 90.0, "education": 50.0, "keywords": 75.0}},
        ],
        # Shift emphasis to skills
        "weights": {"semantic": 0.20, "skills": 0.50,
                    "experience": 0.15, "education": 0.10, "keywords": 0.05},
    }
    result = post("/recalculate", json=body)

    results = result["results"]
    assert_len(results, 3, "Recalculate results")
    for r in results:
        assert_range(r["final_score"], 0, 100, f"  app {r['id']} score")

    orig = score_result["final_score"]
    new  = next(r["final_score"] for r in results if r["id"] == "app-001")
    if orig != new:
        ok(f"Score changed after weight shift: {orig} → {new}")
    else:
        warn(f"Score unchanged ({orig}) — weights may give same result for this CV")

    return result


# ── Step 5 — NL Search ──────────────────────────────────────────────────────
def step5_search(cv_result, score_result):
    step("Step 5 — POST /ai/search  (NL query)")

    import random, math
    random.seed(42)

    def rand_emb(dim=384):
        raw = [random.gauss(0, 1) for _ in range(dim)]
        norm = math.sqrt(sum(x*x for x in raw)) or 1.0
        return [x / norm for x in raw]

    mock_cv_frontend = {
        "skills": ["React", "JavaScript", "CSS", "TypeScript"],
        "work_experience": [{"company": "FE Corp", "role": "Frontend Developer",
                             "months": 24, "end": "present", "is_current": True,
                             "tech_stack": ["React", "JavaScript"], "description": "Built SPAs"}],
        "education": [{"institution": "FPT", "degree": "bachelor", "major": "IT"}],
        "projects": [], "certifications": [], "languages": [], "awards": [],
        "skill_details": [], "contact": {}, "candidate_name": None, "summary": None,
    }
    mock_cv_ml = {
        "skills": ["Python", "TensorFlow", "pandas", "Machine Learning"],
        "work_experience": [{"company": "AI Lab", "role": "ML Engineer",
                             "months": 36, "end": "present", "is_current": True,
                             "tech_stack": ["Python", "TensorFlow"],
                             "description": "ML pipelines and model training"}],
        "education": [{"institution": "Bach Khoa", "degree": "master", "major": "CS"}],
        "projects": [], "certifications": [], "languages": [], "awards": [],
        "skill_details": [], "contact": {}, "candidate_name": None, "summary": None,
    }

    query = "Find .NET developer with at least 1 year experience"
    print(f"  Query: '{query}'")

    body = {
        "query": query,
        "top_n_reasons": 2,
        "applications": [
            {"id": "real-cv", "cv_embedding": cv_result["embedding"],
             "final_score": score_result["final_score"], "parsed_cv": cv_result["parsed_cv"]},
            {"id": "mock-frontend", "cv_embedding": rand_emb(),
             "final_score": 65.0, "parsed_cv": mock_cv_frontend},
            {"id": "mock-ml", "cv_embedding": rand_emb(),
             "final_score": 72.0, "parsed_cv": mock_cv_ml},
        ],
    }
    result = post("/search", json=body)

    ok(f"query_parsed: {json.dumps(result.get('query_parsed', {}), ensure_ascii=False)}")
    results = result.get("results", [])
    ok(f"Results returned: {len(results)}")
    print()
    for i, r in enumerate(results, 1):
        reason = r.get("match_reason") or "(no reason)"
        print(f"  #{i}  {r['id']:<20}  combined={r['combined_score']:>6.1f}  "
              f"sim={r['similarity_score']:.3f}  → {reason}")

    return result


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"{CYAN}{'='*55}")
    print(f"  Full API Test — {BASE}")
    print(f"{'='*55}{RESET}")

    failed_steps = []

    step0_health()

    jd_result = cv_result = score_result = None

    try:
        jd_result = step1_parse_jd()
    except Exception as e:
        fail(f"parse-jd: {e}")
        failed_steps.append("parse-jd")

    try:
        cv_result = step2_parse_cv()
    except Exception as e:
        fail(f"parse-cv: {e}")
        failed_steps.append("parse-cv")

    if jd_result and cv_result:
        try:
            score_result = step3_score(cv_result, jd_result)
        except Exception as e:
            fail(f"score: {e}")
            failed_steps.append("score")

        if score_result:
            try:
                step4_recalculate(score_result)
            except Exception as e:
                fail(f"recalculate: {e}")
                failed_steps.append("recalculate")

            try:
                step5_search(cv_result, score_result)
            except Exception as e:
                fail(f"search: {e}")
                failed_steps.append("search")
    else:
        warn("Skipping steps 3-5 because steps 1 or 2 failed.")

    # Summary
    print(f"\n{CYAN}{'='*55}{RESET}")
    if not failed_steps:
        print(f"{GREEN}  ALL STEPS PASSED{RESET}")
    else:
        print(f"{RED}  FAILED STEPS: {', '.join(failed_steps)}{RESET}")
    print(f"{CYAN}{'='*55}{RESET}\n")

    # Exit code: 0 = all pass, 1 = some failed
    sys.exit(0 if not failed_steps else 1)


if __name__ == "__main__":
    main()
