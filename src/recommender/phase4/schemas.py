"""Pydantic models for Phase 4 HTTP API (OpenAPI / request validation)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from recommender.common.limits import MAX_RECOMMENDATION_TOP_K


class RecommendRequest(BaseModel):
    """JSON body aligned with Phase 2 preference contract (architecture §2.2)."""

    location: Optional[str] = Field(
        default=None,
        description="Locality/area from dataset (matches neighborhood, city, or address substring); omit or null for all areas.",
    )
    budget_for_two_inr: int = Field(
        ...,
        gt=0,
        le=1_000_000,
        description="Maximum approximate cost for two (INR). Restaurants above this are excluded.",
    )
    cuisines: List[str] = Field(
        default_factory=list,
        description="Optional. Empty = any cuisine.",
    )
    min_rating: float = Field(..., ge=0.0, le=5.0)
    extras: str = Field(default="", description="Free text for LLM context.")
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=MAX_RECOMMENDATION_TOP_K,
        description=(
            f"How many ranked recommendations to return (at most {MAX_RECOMMENDATION_TOP_K}). "
            "Omit to use `RECOMMENDER_TOP_K` / Phase 3 config default."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "budget_for_two_inr": 1200,
                    "cuisines": ["Italian"],
                    "min_rating": 4.0,
                    "location": "Bangalore",
                    "extras": "quiet dinner",
                }
            ]
        }
    }


class LocalitiesResponse(BaseModel):
    """Distinct neighborhood / locality names from the loaded corpus (Zomato ``location`` → ``neighborhood``)."""

    localities: List[str]


class FilterFunnelMeta(BaseModel):
    total_after_location: int
    total_after_cuisine: int
    total_after_budget: int
    total_after_rating: int


class RecommendationOut(BaseModel):
    id: str
    name: str
    city: str
    neighborhood: str
    cuisines: List[str]
    rating: Optional[float]
    cost_for_two: Optional[int]
    cost_tier: str
    explanation: str
    rank: int


class RecommendResponse(BaseModel):
    recommendations: List[RecommendationOut]
    summary: Optional[str]
    model_id: str
    prompt_version: str
    fallback_used: bool
    relaxations_applied: List[str]
    truncated: bool
    filter_funnel: FilterFunnelMeta


class ErrorDetail(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    corpus_size: int
