"""Restaurant recommender — Phase 1 ingestion, Phase 2 filtering (public API)."""

from __future__ import annotations

from typing import Any

from recommender.common.errors import DatasetSchemaError, PreferenceValidationError
from recommender.common.models import CostTier, RestaurantRecord
from recommender.phase1.config import DatasetConfig
from recommender.phase1.schema import RAW_COLUMN_MAP, get_schema_version
from recommender.phase2.filter_engine import FilterConfig, FilterResult, filter_restaurants, pack_candidates_for_llm
from recommender.phase2.preferences import UserPreferences

__all__ = [
    "CostTier",
    "DatasetConfig",
    "DatasetSchemaError",
    "FilterConfig",
    "FilterResult",
    "PreferenceValidationError",
    "RestaurantRecord",
    "RAW_COLUMN_MAP",
    "UserPreferences",
    "filter_restaurants",
    "get_schema_version",
    "load_dataset",
    "materialize_restaurants",
    "pack_candidates_for_llm",
    "recommend",
    "RecommendationItem",
    "RecommendationResult",
    "GroqLLMConfig",
    "GroqChatClient",
    "validate_corpus",
]


def __getattr__(name: str) -> Any:
    if name == "load_dataset":
        from recommender.phase1.loader import load_dataset as fn

        return fn
    if name == "materialize_restaurants":
        from recommender.phase1.loader import materialize_restaurants as fn

        return fn
    if name == "validate_corpus":
        from recommender.phase1.validate import validate_corpus as vc

        return vc
    if name == "recommend":
        from recommender.phase3.engine import recommend as fn

        return fn
    if name == "RecommendationItem":
        from recommender.phase3.engine import RecommendationItem as t

        return t
    if name == "RecommendationResult":
        from recommender.phase3.engine import RecommendationResult as t

        return t
    if name == "GroqLLMConfig":
        from recommender.phase3.config import GroqLLMConfig as t

        return t
    if name == "GroqChatClient":
        from recommender.phase3.client import GroqChatClient as t

        return t
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
