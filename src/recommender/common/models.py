from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CostTier(str, Enum):
    """Discrete budget bucket derived from approximate cost for two (INR)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class RestaurantRecord:
    """Canonical restaurant row used by filtering and LLM phases.

    Mapping from Hugging Face `ManikaSaini/zomato-restaurant-recommendation`:
    - ``city`` ← ``listed_in(city)`` (normalized for user queries like Delhi / Bangalore).
    - ``neighborhood`` ← ``location`` (area within city).
    - ``cuisines`` ← split ``cuisines`` string.
    - ``rating`` ← parsed ``rate`` (e.g. ``4.1/5``).
    - ``cost_for_two`` ← parsed ``approx_cost(for two people)``.
    - ``cost_tier`` ← thresholds on ``cost_for_two`` (see ``DatasetConfig``).
    - ``id`` ← stable hash when source has no explicit ID.

    Extra source columns are preserved in ``raw_fields`` for later phases (votes, rest_type, etc.).
    """

    id: str
    name: str
    city: str
    neighborhood: str
    cuisines: List[str]
    rating: Optional[float]
    cost_for_two: Optional[int]
    cost_tier: CostTier
    votes: Optional[int] = None
    raw_fields: Dict[str, Any] = field(default_factory=dict)

    def has_required_fields(self) -> bool:
        """True when row has normalized name and city (minimum bar for filtering)."""
        return bool(self.name and self.city)
