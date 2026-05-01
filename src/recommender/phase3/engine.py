"""Orchestrate Groq call, parse, reconcile, and fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from recommender.common.limits import MAX_RECOMMENDATION_TOP_K
from recommender.common.models import RestaurantRecord
from recommender.phase2.filter_engine import pack_candidates_for_llm
from recommender.phase2.preferences import UserPreferences
from recommender.phase3.client import ChatCompleter, GroqChatClient
from recommender.phase3.config import GroqLLMConfig
from recommender.phase3.parser import parse_llm_response
from recommender.phase3.prompts import PROMPT_VERSION, build_chat_messages
from recommender.phase3.reconcile import reconcile_to_candidates

logger = logging.getLogger(__name__)

# When no ``top_k`` arg and no Groq config, use this (matches ``GroqLLMConfig.top_k`` default).
_DEFAULT_TOP_K = 10


@dataclass(frozen=True)
class RecommendationItem:
    restaurant: RestaurantRecord
    explanation: str
    rank: int


@dataclass(frozen=True)
class RecommendationResult:
    items: Tuple[RecommendationItem, ...]
    summary: Optional[str]
    model_id: str
    prompt_version: str
    fallback_used: bool


def _fallback_result(
    candidates: Sequence[RestaurantRecord],
    *,
    top_k: int,
    summary: Optional[str] = None,
) -> RecommendationResult:
    template = "Ranked using ratings and votes on your shortlist (LLM unavailable or parse error)."
    items: List[RecommendationItem] = []
    for i, r in enumerate(candidates[:top_k], start=1):
        items.append(RecommendationItem(restaurant=r, explanation=template, rank=i))
    return RecommendationResult(
        items=tuple(items),
        summary=summary or "Here are top picks from your filtered list.",
        model_id="deterministic_fallback",
        prompt_version=PROMPT_VERSION,
        fallback_used=True,
    )


def recommend(
    preferences: UserPreferences,
    candidates: Sequence[RestaurantRecord],
    *,
    llm_config: Optional[GroqLLMConfig] = None,
    client: Optional[ChatCompleter] = None,
    load_env_file: bool = True,
    top_k: Optional[int] = None,
) -> RecommendationResult:
    """Call Groq (unless ``client`` injects a mock), parse JSON, reconcile IDs, or fallback.

    If ``GROQ_API_KEY`` is missing and no ``client`` is passed, returns deterministic fallback immediately.
    """
    cfg = llm_config if llm_config is not None else GroqLLMConfig.try_from_env(load_env_file=load_env_file)
    k = top_k if top_k is not None else (cfg.top_k if cfg else _DEFAULT_TOP_K)
    k = min(k, MAX_RECOMMENDATION_TOP_K)

    if not candidates:
        return RecommendationResult(
            items=tuple(),
            summary="No restaurants matched your filters.",
            model_id="none",
            prompt_version=PROMPT_VERSION,
            fallback_used=True,
        )

    if client is None and cfg is None:
        logger.info("No GROQ_API_KEY; using deterministic fallback.")
        return _fallback_result(candidates, top_k=k)

    packed = pack_candidates_for_llm(list(candidates))
    messages = build_chat_messages(preferences, packed, top_k=k)

    model_id = "llama-3.3-70b-versatile"
    temperature = 0.5
    max_tokens = 1200
    if cfg is not None:
        model_id = cfg.model
        temperature = cfg.temperature
        max_tokens = cfg.max_tokens
    # Longer shortlists need more completion budget for K explanations.
    if max_tokens < 350 + 85 * k:
        max_tokens = min(4096, 350 + 85 * k)

    if client is not None:
        active_client = client
    else:
        assert cfg is not None
        active_client = GroqChatClient(cfg)

    try:
        raw = active_client.complete(
            messages,
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        summary, parsed = parse_llm_response(raw)
        recs, expls = reconcile_to_candidates(parsed, candidates, top_k=k)
        items = tuple(
            RecommendationItem(restaurant=r, explanation=e, rank=i)
            for i, (r, e) in enumerate(zip(recs, expls), start=1)
        )
        # Grounding invariant: every restaurant must be from candidates set
        allowed = {r.id for r in candidates}
        for it in items:
            if it.restaurant.id not in allowed:
                logger.error("Grounding violation for id=%s; falling back.", it.restaurant.id)
                return _fallback_result(candidates, top_k=k)

        return RecommendationResult(
            items=items,
            summary=summary,
            model_id=model_id,
            prompt_version=PROMPT_VERSION,
            fallback_used=False,
        )
    except Exception as e:
        logger.warning("Phase 3 LLM path failed; fallback. (%s)", e)
        return _fallback_result(candidates, top_k=k)
