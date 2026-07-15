"""
Stage 3 — Dense Embedding (Tạo vector nhúng cho văn bản)

File này chịu trách nhiệm chuyển văn bản (CV hoặc JD) thành một vector số
thực (dense vector) để dùng cho D1 — điểm số ngữ nghĩa (semantic score) khi
so khớp CV với JD bằng cosine similarity (xem scorer.py::cosine_sim).

Provider embedding duy nhất được hỗ trợ: Gemini (model gemini-embedding-001,
3072 chiều, trả phí). Client được chạy trong thread executor (asyncio
run_in_executor) để không làm nghẽn event loop của FastAPI (vì SDK là hàm
đồng bộ/blocking).
"""

from __future__ import annotations

import asyncio

from openai import OpenAI

from app.config import settings


# ---------------------------------------------------------------------------
# Lazy singleton — chỉ khởi tạo client khi thực sự cần dùng lần đầu
# ---------------------------------------------------------------------------

_gemini_embed_client = None


def _get_gemini_embed() -> OpenAI:
    """
    Trả về client gọi Gemini dùng chung (singleton), tạo mới nếu chưa có.

    Gemini không có SDK embedding riêng ở đây — ta tận dụng client OpenAI
    trỏ vào endpoint tương thích OpenAI của Google
    (generativelanguage.googleapis.com/v1beta/openai/) để tái sử dụng cùng
    một interface .embeddings.create(...). Nếu thiếu GEMINI_API_KEY sẽ raise lỗi.
    """
    global _gemini_embed_client
    if _gemini_embed_client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set in .env")
        _gemini_embed_client = OpenAI(
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    return _gemini_embed_client


def _embed_sync(text: str) -> list[float]:
    """Gọi API embeddings của Gemini cho 1 đoạn text, trả về vector 3072 chiều."""
    client = _get_gemini_embed()
    response = client.embeddings.create(
        model=settings.gemini_embed_model,
        input=text,
    )
    return response.data[0].embedding


# ---------------------------------------------------------------------------
# Public async API — hàm public để các module khác (parser, main, ...) gọi
# ---------------------------------------------------------------------------

async def embed(text: str) -> list[float]:
    """
    Tính embedding cho một đoạn text (bất đồng bộ), trả về vector 3072 chiều.

    Vì SDK embedding là hàm đồng bộ (blocking), hàm này đẩy việc gọi thực sự
    (_embed_sync) sang một thread executor để không chặn event loop của
    FastAPI, cho phép server tiếp tục xử lý các request khác song song.
    """
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")
    return await asyncio.get_running_loop().run_in_executor(None, _embed_sync, text)


def embedding_dim() -> int:
    """Trả về số chiều (dimension) của vector do gemini-embedding-001 tạo ra."""
    return 3072
