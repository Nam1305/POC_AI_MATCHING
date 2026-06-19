"""
Provider-agnostic LLM client — shared by parser and nl_search.

Exposes two call modes:
  call_llm_json(prompt, text)  → parsed JSON dict  (for structured extraction)
  call_llm_text(prompt)        → raw text string    (for free-form generation)
"""

from __future__ import annotations

import asyncio
import json

import anthropic
from openai import OpenAI

from app.config import settings


# ---------------------------------------------------------------------------
# Lazy singleton clients
# ---------------------------------------------------------------------------

_anthropic_client: anthropic.Anthropic | None = None
_groq_client: OpenAI | None = None
_gemini_client: OpenAI | None = None


def get_anthropic() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
        _anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def get_groq() -> OpenAI:
    global _groq_client
    if _groq_client is None:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY not set in .env")
        _groq_client = OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _groq_client


def get_gemini() -> OpenAI:
    global _gemini_client
    if _gemini_client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set in .env")
        _gemini_client = OpenAI(
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    return _gemini_client


# ---------------------------------------------------------------------------
# Sync helpers
# ---------------------------------------------------------------------------

def call_llm_json_sync(prompt: str, text: str) -> dict:
    """Call configured LLM provider with prompt+text, return parsed JSON dict."""
    full_prompt = prompt + text

    if settings.llm_provider == "anthropic":
        client = get_anthropic()
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            temperature=0,
            messages=[{"role": "user", "content": full_prompt}],
        )
        content = response.content[0].text.strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        return json.loads(content)

    if settings.llm_provider == "gemini":
        client = get_gemini()
        response = client.chat.completions.create(
            model=settings.gemini_model,
            messages=[{"role": "user", "content": full_prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return json.loads(response.choices[0].message.content)

    client = get_groq()
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": full_prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


def call_llm_text_sync(
    prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> str:
    """Call configured LLM provider with a complete prompt, return raw text."""
    if settings.llm_provider == "anthropic":
        client = get_anthropic()
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

    if settings.llm_provider == "gemini":
        # Gemini 2.5 Flash uses internal thinking tokens that count toward
        # the max_tokens budget, leaving almost no room for visible output.
        # Omitting max_tokens lets the model auto-allocate its thinking budget.
        client = get_gemini()
        resp = client.chat.completions.create(
            model=settings.gemini_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()

    client = get_groq()
    resp = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Async wrappers (SDKs are sync — push to thread executor)
# ---------------------------------------------------------------------------

async def call_llm_json(prompt: str, text: str) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: call_llm_json_sync(prompt, text))


async def call_llm_text(
    prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: call_llm_text_sync(prompt, temperature, max_tokens)
    )
