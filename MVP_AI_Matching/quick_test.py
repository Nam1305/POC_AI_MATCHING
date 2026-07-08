#!/usr/bin/env python3
"""
Interactive CLI smoke test for the AI service.

Run standalone (does NOT import app.* — talks to the running server over
HTTP, exactly like the .NET backend does):

    python app/scripts/quick_test.py
    python app/scripts/quick_test.py --base-url http://localhost:8000

Flow (mirrors the .NET integration):
  1. GET  /health                 — confirm the server is up
  2. POST /ai/parse-jd            — jd_text -> parsed_jd + jd_embedding
  3. POST /ai/parse-cv            — cv_urls -> [cv_raw_text, parsed_cv, cv_embedding]
  4. POST /ai/score  (per CV)     — parsed_cv + parsed_jd + embeddings -> final_score + evaluation
"""

from __future__ import annotations

import argparse
import sys

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"

BAR_WIDTH = 20


def recommendation_color(recommendation: str) -> str:
    rec = recommendation.upper()
    if "STRONG" in rec or "EXCELLENT" in rec:
        return GREEN
    if "POSSIBLE" in rec or "GOOD" in rec:
        return YELLOW
    if "POOR" in rec or "NOT" in rec or "REJECT" in rec:
        return RED
    return RESET


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


def bar(value: float, width: int = BAR_WIDTH) -> str:
    value = max(0.0, min(100.0, value))
    filled = round(width * value / 100)
    return "█" * filled + "░" * (width - filled)


def check_server(client: httpx.Client) -> bool:
    try:
        resp = client.get("/health", timeout=5.0)
        resp.raise_for_status()
        print(f"Server is up: {resp.json()}")
        return True
    except httpx.HTTPError as e:
        print(f"Server is NOT reachable at {client.base_url}: {e}")
        return False


def read_jd_text() -> str:
    print("\nPaste the JD text below. Finish with an empty line, then Ctrl+D (or Ctrl+Z on Windows):")
    lines: list[str] = []
    try:
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
    except EOFError:
        pass
    text = "\n".join(lines).strip()
    if not text:
        print("No JD text entered. Aborting.")
        sys.exit(1)
    return text


def read_cv_urls() -> list[str]:
    print("\nEnter CV URL(s), one per line. Empty line to finish:")
    urls: list[str] = []
    while True:
        try:
            url = input(f"  CV URL #{len(urls) + 1}: ").strip()
        except EOFError:
            break
        if not url:
            break
        urls.append(url)
    if not urls:
        print("No CV URLs entered. Aborting.")
        sys.exit(1)
    return urls


def parse_jd(client: httpx.Client, jd_text: str) -> dict:
    print("\nCalling POST /ai/parse-jd ...")
    resp = client.post("/ai/parse-jd", json={"jd_text": jd_text}, timeout=120.0)
    resp.raise_for_status()
    return resp.json()


def parse_cvs(client: httpx.Client, cv_urls: list[str]) -> list[dict]:
    print(f"\nCalling POST /ai/parse-cv with {len(cv_urls)} URL(s) ...")
    resp = client.post("/ai/parse-cv", json={"cv_urls": cv_urls}, timeout=180.0)
    resp.raise_for_status()
    return resp.json()["results"]


def score_cv(client: httpx.Client, parsed_cv: dict, parsed_jd: dict,
             cv_embedding: list[float], jd_embedding: list[float]) -> dict:
    resp = client.post(
        "/ai/score",
        json={
            "parsed_cv":    parsed_cv,
            "parsed_jd":    parsed_jd,
            "cv_embedding": cv_embedding,
            "jd_embedding": jd_embedding,
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()


def print_summary_table(results: list[tuple[str, dict]]) -> None:
    headers = ["#", "CV", "Final", "Skills", "Exp", "Edu", "Semantic", "Recommendation"]
    rows = []
    for i, (url, score_result) in enumerate(results, start=1):
        name = url.rsplit("/", 1)[-1]
        scores = score_result["scores"]
        rows.append([
            str(i),
            name,
            f"{score_result['final_score']:.1f}",
            f"{scores.get('skills', 0):.1f}",
            f"{scores.get('experience', 0):.1f}",
            f"{scores.get('education', 0):.1f}",
            f"{scores.get('semantic', 0):.1f}",
            score_result["evaluation"]["recommendation"],
        ])

    widths = [max(len(h), *(len(r[c]) for r in rows)) for c, h in enumerate(headers)] if rows else [len(h) for h in headers]

    def fmt_row(cells: list[str], colorize_last: bool = False) -> str:
        parts = []
        for c, cell in enumerate(cells):
            pad = " " * max(0, widths[c] - len(cell))
            if colorize_last and c == len(cells) - 1:
                parts.append(colorize(cell, recommendation_color(cell)) + pad)
            else:
                parts.append(cell + pad)
        return "  ".join(parts)

    print(f"\n{'=' * 70}")
    print(colorize("Candidate Summary", BOLD))
    print(f"{'=' * 70}")
    print(colorize(fmt_row(headers), BOLD))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt_row(row, colorize_last=True))


def print_result(index: int, url: str, score_result: dict) -> None:
    name = url.rsplit("/", 1)[-1]
    sep = "─" * 74

    print(f"\n{sep}")
    print(f"  #{index}  {name}")
    print(sep)

    scores = score_result["scores"]
    metrics = [
        ("Final Score", score_result["final_score"]),
        ("Skills", scores.get("skills", 0)),
        ("Experience", scores.get("experience", 0)),
        ("Education", scores.get("education", 0)),
        ("Semantic", scores.get("semantic", 0)),
        ("Keywords", scores.get("keywords", 0)),
    ]
    for label, value in metrics:
        print(f"  {label:<15} [{bar(value)}]  {value:5.1f}")

    ev = score_result["evaluation"]
    print()
    print(f"  {'Recommendation':<15}  {colorize(ev['recommendation'], recommendation_color(ev['recommendation']))}")
    print(f"  {'Experience':<15}  {ev['experience_verdict']}  —  {ev['experience_detail']}")
    print(f"  {'Education':<15}  {ev['education_verdict']}")
    print(f"  {'Seniority':<15}  {ev['seniority_match']}  —  {ev['seniority_detail']}")

    print()
    print(f"  {'Skill match rate':<20} {ev['skill_match_rate']}%")
    if ev["missing_must_have"]:
        print(f"  Missing (must-have): {', '.join(ev['missing_must_have'])}")
    print(f"  Missing (preferred): {', '.join(ev['missing_preferred'])}")
    print(f"  Bonus skills:        {', '.join(ev['bonus_skills'])}")

    print()
    print("  Narrative:")
    for line in ev["narrative"].splitlines():
        print(f"    {line}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Interactive AI-service smoke test")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                     help=f"AI service base URL (default: {DEFAULT_BASE_URL})")
    args = ap.parse_args()

    with httpx.Client(base_url=args.base_url) as client:
        if not check_server(client):
            sys.exit(1)

        jd_text = read_jd_text()
        cv_urls = read_cv_urls()

        jd_result = parse_jd(client, jd_text)
        parsed_jd = jd_result["parsed_jd"]
        jd_embedding = jd_result["jd_embedding"]
        print(f"Parsed JD title: {parsed_jd.get('title')}")

        cv_results = parse_cvs(client, cv_urls)

        scored: list[tuple[str, dict]] = []
        for cv in cv_results:
            if cv.get("error"):
                print(f"\n[FAILED] {cv['url']}: {cv['error']}")
                continue

            score_result = score_cv(
                client,
                parsed_cv=cv["parsed_cv"],
                parsed_jd=parsed_jd,
                cv_embedding=cv["cv_embedding"],
                jd_embedding=jd_embedding,
            )
            scored.append((cv["url"], score_result))

        scored.sort(key=lambda pair: pair[1]["final_score"], reverse=True)

        print_summary_table(scored)

        for i, (url, score_result) in enumerate(scored, start=1):
            print_result(i, url, score_result)

        print(f"\n{'=' * 70}\nDone.")


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPStatusError as e:
        print(f"\nRequest failed: {e.response.status_code} {e.response.text}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)