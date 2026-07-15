"""
LLM Client — lớp client dùng chung cho mọi lời gọi LLM trong service.

File này là điểm truy cập LLM duy nhất, được parser.py (trích xuất CV/JD)
và evaluator.py (sinh nhận xét cho HR) tái sử dụng, để không phải lặp lại
logic chọn provider/gọi API ở nhiều nơi.

Nhà cung cấp LLM được chọn qua .env LLM_PROVIDER:
  - anthropic : Claude              (chất lượng cao, dùng cho production)
  - gemini    : Google Gemini       (qua endpoint tương thích OpenAI)
  - groq      : Groq (Llama)        (miễn phí, dùng để dev/fallback)

Expose 2 chế độ gọi:
  call_llm_json(prompt, text)  → trả về dict đã parse từ JSON (dùng để trích xuất có cấu trúc, ví dụ parse CV/JD)
  call_llm_text(prompt)        → trả về chuỗi text thô          (dùng để sinh văn bản tự do, ví dụ nhận xét ứng viên)

Vì SDK của các provider đều là hàm đồng bộ (blocking), các hàm public đều có
bản async wrapper chạy hàm sync trong thread executor để không chặn event
loop của FastAPI.
"""

from __future__ import annotations

import asyncio
import json

import anthropic
from openai import OpenAI

from app.config import settings


# ---------------------------------------------------------------------------
# Lazy singleton clients — chỉ khởi tạo khi thực sự cần dùng lần đầu
# ---------------------------------------------------------------------------

_anthropic_client: anthropic.Anthropic | None = None
_groq_client: OpenAI | None = None
_gemini_client: OpenAI | None = None


def get_anthropic() -> anthropic.Anthropic:
    """
    Trả về client Anthropic (Claude) dùng chung (singleton), tạo mới nếu
    chưa có. Raise lỗi ngay nếu thiếu ANTHROPIC_API_KEY trong .env.
    """
    global _anthropic_client
    if _anthropic_client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
        _anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def get_groq() -> OpenAI:
    """
    Trả về client Groq dùng chung (singleton), tạo mới nếu chưa có.
    Groq expose API tương thích OpenAI nên tái sử dụng luôn class OpenAI,
    chỉ trỏ base_url khác. Raise lỗi ngay nếu thiếu GROQ_API_KEY.
    """
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
    """
    Trả về client Gemini dùng chung (singleton), tạo mới nếu chưa có.
    Cũng dùng class OpenAI trỏ vào endpoint tương thích OpenAI của Google.
    Raise lỗi ngay nếu thiếu GEMINI_API_KEY.
    """
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
# Sync helpers — hàm gọi LLM thực sự (đồng bộ/blocking)
# ---------------------------------------------------------------------------

def call_llm_json_sync(prompt: str, text: str) -> dict:
    """
    Gọi LLM (theo provider cấu hình trong .env) với prompt + text (ví dụ
    prompt hướng dẫn trích xuất + nội dung CV/JD), trả về dict đã parse
    từ JSON do LLM sinh ra.

    Với Anthropic: dùng temperature=0 (kết quả ổn định, không sáng tạo) và
    tự bóc tách nếu LLM lỡ bọc JSON trong code fence (```json ... ```).
    Với Gemini/Groq: dùng response_format={"type": "json_object"} để ép
    model trả JSON hợp lệ trực tiếp, không cần bóc tách thủ công.
    """
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
    """
    Gọi LLM (theo provider cấu hình trong .env) với một prompt hoàn chỉnh,
    trả về text thô (không parse JSON) — dùng cho sinh văn bản tự do như
    đoạn nhận xét ứng viên (narrative) trong evaluator.py.
    """
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
# Các hàm public thực sự được gọi từ parser.py / evaluator.py
# ---------------------------------------------------------------------------

async def call_llm_json(prompt: str, text: str) -> dict:
    """
    Bản async của call_llm_json_sync — chạy lời gọi LLM (blocking) trong
    thread executor để không chặn event loop của FastAPI. Dùng khi cần kết
    quả có cấu trúc (JSON), ví dụ trích xuất CV/JD trong parser.py.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: call_llm_json_sync(prompt, text))


async def call_llm_text(
    prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> str:
    """
    Bản async của call_llm_text_sync — chạy lời gọi LLM (blocking) trong
    thread executor để không chặn event loop của FastAPI. Dùng khi cần văn
    bản tự do, ví dụ đoạn nhận xét ứng viên trong evaluator.py.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: call_llm_text_sync(prompt, temperature, max_tokens)
    )
