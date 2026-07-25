"""
Application configuration — loads from .env via pydantic-settings.

Three LLM providers are supported, switchable via .env (LLM_PROVIDER).
Embedding is Gemini-only (gemini-embedding-001).
"""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Single source of truth for which scoring dimensions exist. Anything that
# needs to know "what are the 5 D's" (HR weight-override validation in
# app/api/score.py, the defaults below) reads this instead of repeating the
# name list.
SCORE_DIMENSIONS: tuple[str, ...] = ("semantic", "skills", "experience", "education", "location")


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

    # ---- Embedding provider (Gemini only) ----
    gemini_embed_model: str = "gemini-embedding-001"          # 3072-dim

    # ---- Scoring ----
    cosine_min: float = 0.0    # no stretch — raw cosine used as-is (override via COSINE_MIN)
    cosine_max: float = 1.0    # no stretch — raw cosine used as-is (override via COSINE_MAX)

    default_weight_semantic:   float = 0.30
    default_weight_skills:     float = 0.35
    default_weight_experience: float = 0.20
    default_weight_education:  float = 0.10
    default_weight_location:   float = 0.05   # D5 — was "keywords", replaced by location+work-mode score

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def default_weights(self) -> dict[str, float]:
        return {name: getattr(self, f"default_weight_{name}") for name in SCORE_DIMENSIONS}

    @model_validator(mode="after")
    def _check_default_weights_sum_to_one(self) -> "Settings":
        total = sum(self.default_weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"DEFAULT_WEIGHT_* must sum to 1.0, got {total:.4f} — check .env "
                f"({self.default_weights})"
            )
        return self


settings = Settings()
