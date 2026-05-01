"""Phase 2 — deterministic filtering, relaxation, ranking, and LLM-ready packing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from recommender.common.models import RestaurantRecord
from recommender.phase1.normalize import normalize_whitespace
from recommender.phase2.preferences import UserPreferences


@dataclass(frozen=True)
class FilterConfig:
    """Tuning for relaxation and output size (Phase 2)."""

    k_min: int = 5
    k_target: int = 20
    max_candidates: int = 30
    min_rating_floor: float = 2.5
    rating_relax_step: float = 0.5
    #: When relaxing budget, add this many INR to the user's max cost-for-two cap each step.
    budget_relax_step_inr: int = 400
    #: Stop widening the INR cap at this ceiling (avoids unbounded relaxation).
    budget_relax_ceiling_inr: int = 250_000


@dataclass(frozen=True)
class FilterResult:
    """Outcome of ``filter_restaurants`` (per architecture §2.6)."""

    candidates: Tuple[RestaurantRecord, ...]
    total_after_location: int
    total_after_cuisine: int
    total_after_budget: int
    total_after_rating: int
    relaxations_applied: Tuple[str, ...]
    truncated: bool
    preferences: UserPreferences


def pack_candidates_for_llm(records: Sequence[RestaurantRecord]) -> List[Dict[str, Any]]:
    """Compact dicts for Phase 3 prompts (grounding payload)."""
    out: List[Dict[str, Any]] = []
    for r in records:
        out.append(
            {
                "id": r.id,
                "name": r.name,
                "city": r.city,
                "neighborhood": r.neighborhood,
                "cuisines": list(r.cuisines),
                "rating": r.rating,
                "cost_for_two": r.cost_for_two,
                "cost_tier": r.cost_tier.value,
                "votes": r.votes,
            }
        )
    return out


def _location_matches(rec: RestaurantRecord, query: str) -> bool:
    """Substring match on city, neighborhood, or raw address (Phase 1 ``raw_fields``)."""
    q = normalize_whitespace(query).lower()
    if not q:
        return True
    city = rec.city.lower()
    hood = rec.neighborhood.lower()
    addr = str(rec.raw_fields.get("address") or "").lower()
    if q in city or q in hood or q in addr:
        return True
    if city in q or hood in q:
        return True
    return False


def _cuisine_matches(rec: RestaurantRecord, wanted: Sequence[str]) -> bool:
    if not wanted:
        return True
    for w in wanted:
        if not w:
            continue
        for c in rec.cuisines:
            if w in c or c in w:
                return True
    return False


def _budget_matches_inr(rec: RestaurantRecord, max_cost_inr: int) -> bool:
    """True when approximate cost for two is known and within the user's INR ceiling."""
    if rec.cost_for_two is None:
        return False
    return rec.cost_for_two <= max_cost_inr


def _rating_matches(rec: RestaurantRecord, min_rating: float) -> bool:
    if rec.rating is None:
        return False
    return rec.rating >= min_rating


def _run_pipeline(
    corpus: Sequence[RestaurantRecord],
    *,
    apply_location: bool,
    location_query: Optional[str],
    cuisines: Sequence[str],
    max_cost_inr: int,
    min_rating: float,
) -> Tuple[List[RestaurantRecord], int, int, int, int]:
    if apply_location and location_query:
        after_loc = [r for r in corpus if _location_matches(r, location_query)]
    else:
        after_loc = list(corpus)

    after_cuisine = [r for r in after_loc if _cuisine_matches(r, cuisines)]
    after_budget = [r for r in after_cuisine if _budget_matches_inr(r, max_cost_inr)]
    after_rating = [r for r in after_budget if _rating_matches(r, min_rating)]

    return (
        after_rating,
        len(after_loc),
        len(after_cuisine),
        len(after_budget),
        len(after_rating),
    )


def _rank_pre_llm(records: Sequence[RestaurantRecord]) -> List[RestaurantRecord]:
    """Deterministic sort: higher rating, more votes, then name."""

    def key(r: RestaurantRecord) -> Tuple[float, int, str]:
        rating = r.rating if r.rating is not None else -1.0
        votes = r.votes if r.votes is not None else 0
        return (-rating, -votes, r.name.lower())

    return sorted(records, key=key)


@dataclass
class _MutableFilterParams:
    apply_location: bool
    location_query: Optional[str]
    cuisines: List[str]
    max_cost_inr: int
    min_rating: float
    did_relax_location: bool = False
    did_drop_secondary_cuisine: bool = False

    @classmethod
    def from_preferences(cls, prefs: UserPreferences) -> _MutableFilterParams:
        loc_q = prefs.location
        apply_loc = bool(loc_q)
        return cls(
            apply_location=apply_loc,
            location_query=loc_q,
            cuisines=list(prefs.cuisines),
            max_cost_inr=prefs.max_cost_for_two_inr,
            min_rating=prefs.min_rating,
        )


def _next_relaxation(p: _MutableFilterParams, cfg: FilterConfig) -> Optional[str]:
    if p.apply_location and not p.did_relax_location:
        return "removed_location_filter"
    if len(p.cuisines) > 1 and not p.did_drop_secondary_cuisine:
        return "kept_primary_cuisine_only"
    if p.min_rating > cfg.min_rating_floor + 1e-9:
        return "lowered_min_rating"
    next_cap = min(cfg.budget_relax_ceiling_inr, p.max_cost_inr + cfg.budget_relax_step_inr)
    if next_cap > p.max_cost_inr:
        return "increased_budget_cap_inr"
    return None


def _apply_relaxation(label: str, p: _MutableFilterParams, cfg: FilterConfig) -> None:
    if label == "removed_location_filter":
        p.apply_location = False
        p.location_query = None
        p.did_relax_location = True
    elif label == "kept_primary_cuisine_only":
        p.cuisines = p.cuisines[:1]
        p.did_drop_secondary_cuisine = True
    elif label == "lowered_min_rating":
        p.min_rating = max(cfg.min_rating_floor, p.min_rating - cfg.rating_relax_step)
    elif label == "increased_budget_cap_inr":
        p.max_cost_inr = min(
            cfg.budget_relax_ceiling_inr,
            p.max_cost_inr + cfg.budget_relax_step_inr,
        )


def filter_restaurants(
    preferences: UserPreferences,
    corpus: Iterable[RestaurantRecord],
    *,
    config: Optional[FilterConfig] = None,
) -> FilterResult:
    """Apply Phase 2 pipeline with relaxation until ``k_min`` candidates or no moves left.

    Always returns records drawn from ``corpus`` only (grounded list).
    """
    cfg = config or FilterConfig()
    rows = [r for r in corpus if r.has_required_fields()]
    relaxations: List[str] = []
    params = _MutableFilterParams.from_preferences(preferences)

    while True:
        candidates, n_loc, n_cuis, n_budget, n_rate = _run_pipeline(
            rows,
            apply_location=params.apply_location,
            location_query=params.location_query,
            cuisines=params.cuisines,
            max_cost_inr=params.max_cost_inr,
            min_rating=params.min_rating,
        )
        if len(candidates) >= cfg.k_min:
            break
        step = _next_relaxation(params, cfg)
        if step is None:
            break
        _apply_relaxation(step, params, cfg)
        relaxations.append(step)

    ranked = _rank_pre_llm(candidates)
    truncated = len(ranked) > cfg.max_candidates
    capped = ranked[: cfg.max_candidates]

    return FilterResult(
        candidates=tuple(capped),
        total_after_location=n_loc,
        total_after_cuisine=n_cuis,
        total_after_budget=n_budget,
        total_after_rating=n_rate,
        relaxations_applied=tuple(relaxations),
        truncated=truncated,
        preferences=preferences,
    )
