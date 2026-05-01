"""Orchestrate Phase 2 filter + Phase 3 recommend for the HTTP layer."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Tuple

from recommender.common.errors import PreferenceValidationError
from recommender.common.models import RestaurantRecord
from recommender.phase2.filter_engine import FilterConfig, FilterResult, filter_restaurants
from recommender.phase2.preferences import UserPreferences
from recommender.phase3.client import ChatCompleter
from recommender.phase3.engine import recommend
from recommender.phase4.schemas import FilterFunnelMeta, RecommendationOut, RecommendResponse


def preferences_from_request_body(body: Mapping[str, Any]) -> UserPreferences:
    """Map validated API body to ``UserPreferences`` (re-validates business rules)."""
    return UserPreferences.from_mapping(body)


def run_recommendation(
    preferences: UserPreferences,
    corpus: Sequence[RestaurantRecord],
    *,
    filter_config: FilterConfig,
    llm_client: Optional[ChatCompleter] = None,
    load_env_file: bool = True,
    top_k: Optional[int] = None,
) -> Tuple[RecommendResponse, FilterResult]:
    filtered = filter_restaurants(preferences, corpus, config=filter_config)
    rec_result = recommend(
        preferences,
        filtered.candidates,
        client=llm_client,
        load_env_file=load_env_file,
        top_k=top_k,
    )
    rows = [
        RecommendationOut(
            id=item.restaurant.id,
            name=item.restaurant.name,
            city=item.restaurant.city,
            neighborhood=item.restaurant.neighborhood,
            cuisines=list(item.restaurant.cuisines),
            rating=item.restaurant.rating,
            cost_for_two=item.restaurant.cost_for_two,
            cost_tier=item.restaurant.cost_tier.value,
            explanation=item.explanation,
            rank=item.rank,
        )
        for item in rec_result.items
    ]
    funnel = FilterFunnelMeta(
        total_after_location=filtered.total_after_location,
        total_after_cuisine=filtered.total_after_cuisine,
        total_after_budget=filtered.total_after_budget,
        total_after_rating=filtered.total_after_rating,
    )
    response = RecommendResponse(
        recommendations=rows,
        summary=rec_result.summary,
        model_id=rec_result.model_id,
        prompt_version=rec_result.prompt_version,
        fallback_used=rec_result.fallback_used,
        relaxations_applied=list(filtered.relaxations_applied),
        truncated=filtered.truncated,
        filter_funnel=funnel,
    )
    return response, filtered


def parse_preferences_safe(body: Mapping[str, Any]) -> UserPreferences:
    """Raise ``PreferenceValidationError`` with clear messages for HTTP 400."""
    try:
        return preferences_from_request_body(body)
    except PreferenceValidationError:
        raise
    except Exception as e:
        raise PreferenceValidationError(str(e)) from e
