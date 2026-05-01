"""Phase 2 — typed user preferences and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from recommender.common.errors import PreferenceValidationError
from recommender.phase1.normalize import normalize_city, normalize_whitespace


def _parse_budget_for_two_inr(raw: Any) -> int:
    """Max approximate cost for two (INR) the user is willing to pay — hard ceiling for filtering."""
    if raw is None:
        raise PreferenceValidationError(
            "budget_for_two_inr is required (positive integer INR, max cost for two)."
        )
    try:
        v = int(raw)
    except (TypeError, ValueError):
        raise PreferenceValidationError(f"budget_for_two_inr must be a whole number (INR); got {raw!r}.")
    if v <= 0:
        raise PreferenceValidationError("budget_for_two_inr must be greater than zero.")
    if v > 1_000_000:
        raise PreferenceValidationError("budget_for_two_inr is too large (max 1,000,000 INR).")
    return v


def _normalize_cuisine_tokens(items: Any) -> Tuple[str, ...]:
    """Empty list or omit → no cuisine constraint (any cuisine)."""
    if items is None:
        return ()
    if isinstance(items, (str, bytes)):
        raise PreferenceValidationError("cuisines must be a JSON array of strings, not a single string.")
    if not isinstance(items, (list, tuple)):
        raise PreferenceValidationError("cuisines must be a list of strings.")
    out: list[str] = []
    for x in items:
        if not isinstance(x, str):
            raise PreferenceValidationError("Each cuisine must be a string.")
        t = normalize_whitespace(x).lower()
        if t:
            out.append(t)
    return tuple(out)


def _parse_location(raw: Any) -> str | None:
    if raw is None:
        return None
    s = normalize_whitespace(str(raw))
    if not s:
        return None
    return normalize_city(s)


def _parse_min_rating(raw: Any) -> float:
    if raw is None:
        raise PreferenceValidationError("min_rating is required.")
    try:
        v = float(raw)
    except (TypeError, ValueError):
        raise PreferenceValidationError(f"min_rating must be a number; got {raw!r}.")
    if v < 0.0 or v > 5.0:
        raise PreferenceValidationError("min_rating must be between 0 and 5.")
    return v


@dataclass(frozen=True)
class UserPreferences:
    """Validated API payload for Phase 2 filtering.

    - ``location`` ``None`` means no location constraint (all cities).
    - ``cuisines`` empty means **any cuisine** (optional constraint).
    - ``max_cost_for_two_inr`` — restaurants must have ``cost_for_two <=`` this value (unknown cost excluded).
    - ``extras`` is carried for Phase 3 only (not used in deterministic filters).
    """

    location: str | None
    max_cost_for_two_inr: int
    cuisines: Tuple[str, ...]
    min_rating: float
    extras: str = ""

    @staticmethod
    def from_mapping(data: Mapping[str, Any]) -> UserPreferences:
        """Build from JSON-like dict (e.g. FastAPI body)."""
        if not isinstance(data, Mapping):
            raise PreferenceValidationError("Preferences must be a JSON object.")

        loc = _parse_location(data.get("location"))
        raw_budget = data.get("budget_for_two_inr")
        if raw_budget is None:
            raw_budget = data.get("budget_max_inr")
        max_inr = _parse_budget_for_two_inr(raw_budget)
        cuisines = _normalize_cuisine_tokens(data.get("cuisines"))
        min_rating = _parse_min_rating(data.get("min_rating"))

        extras_raw = data.get("extras", "") or ""
        if not isinstance(extras_raw, str):
            extras_raw = str(extras_raw)

        return UserPreferences(
            location=loc,
            max_cost_for_two_inr=max_inr,
            cuisines=cuisines,
            min_rating=min_rating,
            extras=extras_raw.strip(),
        )
