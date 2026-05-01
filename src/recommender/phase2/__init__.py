"""Phase 2 — user preferences and deterministic filtering."""

from recommender.phase2.filter_engine import (
    FilterConfig,
    FilterResult,
    filter_restaurants,
    pack_candidates_for_llm,
)
from recommender.phase2.preferences import UserPreferences

__all__ = [
    "FilterConfig",
    "FilterResult",
    "UserPreferences",
    "filter_restaurants",
    "pack_candidates_for_llm",
]
