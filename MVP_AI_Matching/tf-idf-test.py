#!/usr/bin/env python3
"""
Interactive CLI smoke test for the TF-IDF matching endpoint.

Run standalone (does NOT import app.* — talks to the running server over
HTTP, exactly like the .NET backend does):

    python tf-idf-test.py
    python tf-idf-test.py --base-url http://localhost:8000

Flow:
  1. GET  /health           — confirm the server is up
  2. Read JD text + CV URL(s) from stdin
  3. POST /ai/tfidf-score   — jd_text + cv_urls -> ranked TF-IDF cosine similarity scores
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

BAR_WIDTH = 20


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


def score_color(value: float) -> str:
    if value >= 60:
        return GREEN
    if value >= 30:
        return YELLOW
    return RED


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


def tfidf_score(client: httpx.Client, jd_text: str, cv_urls: list[str]) -> list[dict]:
    print(f"\nCalling POST /ai/tfidf-score with {len(cv_urls)} CV URL(s) ...")
    resp = client.post(
        "/ai/tfidf-score",
        json={"jd_text": jd_text, "cv_urls": cv_urls},
        timeout=180.0,
    )
    resp.raise_for_status()
    return resp.json()["results"]


def print_summary_table(results: list[dict]) -> None:
    headers = ["Rank", "CV", "TF-IDF Score"]
    rows = []
    for r in results:
        name = r["url"].rsplit("/", 1)[-1]
        if r.get("error"):
            rows.append([str(r.get("rank") or "-"), name, colorize(f"ERROR: {r['error']}", RED)])
        else:
            score = r["tfidf_score"]
            rows.append([str(r["rank"]), name, colorize(f"{score:.2f}", score_color(score))])

    widths = [max(len(h), *(len(_strip_ansi(r[c])) for r in rows)) for c, h in enumerate(headers)] if rows else [len(h) for h in headers]

    def fmt_row(cells: list[str]) -> str:
        parts = []
        for c, cell in enumerate(cells):
            pad = " " * max(0, widths[c] - len(_strip_ansi(cell)))
            parts.append(cell + pad)
        return "  ".join(parts)

    print(f"\n{'=' * 60}")
    print(colorize("TF-IDF Candidate Ranking", BOLD))
    print(f"{'=' * 60}")
    print(colorize(fmt_row(headers), BOLD))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt_row(row))


def _strip_ansi(text: str) -> str:
    for code in (RESET, BOLD, GREEN, YELLOW, RED):
        text = text.replace(code, "")
    return text


def print_result(index: int, result: dict) -> None:
    name = result["url"].rsplit("/", 1)[-1]
    sep = "─" * 60
    print(f"\n{sep}")
    print(f"  #{index}  {name}")
    print(sep)

    if result.get("error"):
        print(f"  {colorize('ERROR', RED)}: {result['error']}")
        return

    score = result["tfidf_score"]
    print(f"  {'TF-IDF Score':<15} [{bar(score)}]  {score:5.2f}")


def main() -> None:
    ap = argparse.ArgumentParser(description="TF-IDF JD/CV matching smoke test")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                     help=f"AI service base URL (default: {DEFAULT_BASE_URL})")
    args = ap.parse_args()

    with httpx.Client(base_url=args.base_url) as client:
        if not check_server(client):
            sys.exit(1)

        jd_text = read_jd_text()
        cv_urls = read_cv_urls()

        results = tfidf_score(client, jd_text, cv_urls)
        results_sorted = sorted(
            results, key=lambda r: (r.get("rank") is None, r.get("rank") or 0)
        )

        print_summary_table(results_sorted)

        for i, result in enumerate(results_sorted, start=1):
            print_result(i, result)

        print(f"\n{'=' * 60}\nDone.")


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPStatusError as e:
        print(f"\nRequest failed: {e.response.status_code} {e.response.text}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
