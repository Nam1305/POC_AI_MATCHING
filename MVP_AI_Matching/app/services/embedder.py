"""
Stage 3 — Dense Embedding

Converts text into a dense vector for D1 semantic scoring + NL search.
Provider selected via .env EMBED_PROVIDER:

  - openai                : text-embedding-3-small   (1536-dim, paid)
  - sentence_transformer  : all-MiniLM-L6-v2         (384-dim,  local, free)
  - gemini                : gemini-embedding-001       (3072-dim, paid)

Both providers run in a thread executor so FastAPI's event loop stays responsive.
The vector dim is consistent across CV/JD as long as the provider doesn't change.
"""

from __future__ import annotations

import asyncio

from openai import OpenAI

from app.config import settings


# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------

_openai_client = None
_st_model = None
_gemini_embed_client = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not set in .env")
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _get_sentence_transformer():
    """Lazy import to avoid loading heavy torch deps when using OpenAI."""
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        print(f"Loading embedding model: {settings.st_embed_model} ...")
        _st_model = SentenceTransformer(settings.st_embed_model)
    return _st_model


def _get_gemini_embed() -> OpenAI:
    global _gemini_embed_client
    if _gemini_embed_client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set in .env")
        _gemini_embed_client = OpenAI(
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    return _gemini_embed_client


# ---------------------------------------------------------------------------
# Provider-specific embed (sync)
# ---------------------------------------------------------------------------

def _embed_openai(text: str) -> list[float]:
    client = _get_openai()
    response = client.embeddings.create(
        model=settings.openai_embed_model,
        input=text,
    )
    return response.data[0].embedding


def _embed_st(text: str) -> list[float]:
    model = _get_sentence_transformer()
    return model.encode(text, normalize_embeddings=True).tolist()


def _embed_gemini(text: str) -> list[float]:
    client = _get_gemini_embed()
    response = client.embeddings.create(
        model=settings.gemini_embed_model,
        input=text,
    )
    return response.data[0].embedding


def _embed_sync(text: str) -> list[float]:
    if settings.embed_provider == "openai":
        return _embed_openai(text)
    if settings.embed_provider == "gemini":
        return _embed_gemini(text)
    return _embed_st(text)


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def embed(text: str) -> list[float]:
    """
    Compute embedding for a single text. Returns:
      - 1536-dim list[float] if EMBED_PROVIDER=openai
      - 384-dim  list[float] if EMBED_PROVIDER=sentence_transformer
      - 3072-dim list[float] if EMBED_PROVIDER=gemini
    """
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")
    return await asyncio.get_running_loop().run_in_executor(None, _embed_sync, text)


def embedding_dim() -> int:
    """Return the dimension produced by the active provider."""
    if settings.embed_provider == "openai":
        return 1536
    if settings.embed_provider == "gemini":
        return 3072
    return 384
