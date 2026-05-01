"""Groq OpenAI-compatible chat client."""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Protocol

import httpx

from recommender.phase3.config import GroqLLMConfig

logger = logging.getLogger(__name__)


class ChatCompleter(Protocol):
    """Thin interface so tests can mock LLM responses without HTTP."""

    def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        ...


class GroqChatClient:
    """POST ``/chat/completions`` to Groq."""

    def __init__(self, config: GroqLLMConfig) -> None:
        self._c = config

    def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        url = f"{self._c.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self._c.api_key}",
            "Content-Type": "application/json",
        }
        last_exc: Exception | None = None
        attempts = max(1, self._c.max_retries + 1)
        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=120.0) as http:
                    resp = http.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    return str(data["choices"][0]["message"]["content"])
            except (httpx.HTTPError, KeyError, json.JSONDecodeError) as e:
                last_exc = e
                logger.warning("Groq request failed attempt %s/%s: %s", attempt + 1, attempts, e)
        assert last_exc is not None
        raise last_exc
