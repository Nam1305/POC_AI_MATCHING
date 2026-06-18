"""
Application configuration — loads from .env via pydantic-settings.

Two LLM providers + two embedding providers are supported. Switch via
.env (LLM_PROVIDER, EMBED_PROVIDER) without code changes.
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- Server ----
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # ---- LLM provider ----
    llm_provider: Literal["anthropic", "groq", "gemini"] = "gemini"

    anthropic_api_key: str = ""
    anthropic_model:   str = "claude-sonnet-4-6"

    groq_api_key: str = ""
    groq_model:   str = "llama-3.1-8b-instant"

    gemini_api_key: str = ""
    gemini_model:   str = "gemini-2.5-flash"

    # ---- Embedding provider ----
    embed_provider: Literal["openai", "sentence_transformer", "gemini"] = "gemini"

    openai_api_key:     str = ""
    openai_embed_model: str = "text-embedding-3-small"     # 1536-dim

    st_embed_model: str = "all-MiniLM-L6-v2"               # 384-dim, local

    gemini_embed_model: str = "gemini-embedding-001"          # 3072-dim

    # ---- Scoring ----
    cosine_min: float = 0.55    # gemini-embedding-001 real-world floor (unrelated fields)
    cosine_max: float = 0.90    # gemini-embedding-001 real-world ceiling (same-stack match)

    default_weight_semantic:   float = 0.30
    default_weight_skills:     float = 0.35
    default_weight_experience: float = 0.20
    default_weight_education:  float = 0.10
    default_weight_keywords:   float = 0.05

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def default_weights(self) -> dict[str, float]:
        return {
            "semantic":   self.default_weight_semantic,
            "skills":     self.default_weight_skills,
            "experience": self.default_weight_experience,
            "education":  self.default_weight_education,
            "keywords":   self.default_weight_keywords,
        }


settings = Settings()
