"""Groq / LLM configuration (Phase 3)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from recommender.common.limits import MAX_RECOMMENDATION_TOP_K
from recommender.phase3.env import load_dotenv_if_present


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class GroqLLMConfig:
    """Runtime settings for Groq OpenAI-compatible chat completions."""

    api_key: str
    model: str = "llama-3.3-70b-versatile"
    base_url: str = "https://api.groq.com/openai/v1"
    temperature: float = 0.5
    max_tokens: int = 1200
    max_retries: int = 2
    top_k: int = 10

    @staticmethod
    def try_from_env(*, load_env_file: bool = True) -> Optional[GroqLLMConfig]:
        """Return config if ``GROQ_API_KEY`` is set after optional ``.env`` load; else None."""
        if load_env_file:
            load_dotenv_if_present()
        key = (os.environ.get("GROQ_API_KEY") or "").strip()
        if not key:
            return None
        model = (os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile").strip()
        base = (os.environ.get("GROQ_BASE_URL") or "https://api.groq.com/openai/v1").strip().rstrip("/")
        return GroqLLMConfig(
            api_key=key,
            model=model,
            base_url=base,
            temperature=_env_float("GROQ_TEMPERATURE", 0.5),
            max_tokens=_env_int("GROQ_MAX_TOKENS", 1200),
            max_retries=_env_int("GROQ_MAX_RETRIES", 2),
            top_k=min(_env_int("RECOMMENDER_TOP_K", 10), MAX_RECOMMENDATION_TOP_K),
        )

    @staticmethod
    def require_from_env(*, load_env_file: bool = True) -> GroqLLMConfig:
        cfg = GroqLLMConfig.try_from_env(load_env_file=load_env_file)
        if cfg is None:
            raise ValueError("GROQ_API_KEY is not set (add it to .env or the environment).")
        return cfg
