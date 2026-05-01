"""Ground recommendations to Phase 2 candidates; fuzzy repair and backfill."""

from __future__ import annotations

from typing import Dict, List, Sequence, Set, Tuple

from recommender.common.models import RestaurantRecord
from recommender.phase3.parser import ParsedRecommendation


def _by_name_casefold(records: Sequence[RestaurantRecord]) -> Dict[str, RestaurantRecord]:
    """First wins on duplicate lowered names."""
    m: Dict[str, RestaurantRecord] = {}
    for r in records:
        key = r.name.strip().casefold()
        if key and key not in m:
            m[key] = r
    return m


def reconcile_to_candidates(
    parsed: Sequence[ParsedRecommendation],
    candidates: Sequence[RestaurantRecord],
    *,
    top_k: int,
) -> Tuple[List[RestaurantRecord], List[str]]:
    """Return ordered unique restaurants and parallel explanations (same length).

    Unknown IDs try exact case-insensitive name match against candidates.
    After parsed rows are exhausted, backfill from remaining candidates in input order.
    """
    id_map: Dict[str, RestaurantRecord] = {r.id: r for r in candidates}
    name_map = _by_name_casefold(candidates)

    chosen: List[RestaurantRecord] = []
    explanations: List[str] = []
    seen_ids: Set[str] = set()

    for row in parsed:
        if len(chosen) >= top_k:
            break
        rec = id_map.get(row.restaurant_id)
        if rec is None:
            rec = name_map.get(row.restaurant_id.strip().casefold())
        if rec is None:
            continue
        if rec.id in seen_ids:
            continue
        seen_ids.add(rec.id)
        chosen.append(rec)
        expl = row.explanation or "Matches your preferences among the shortlisted venues."
        explanations.append(expl)

    template = "High rating and match for your filters among the shortlisted venues."
    for r in candidates:
        if len(chosen) >= top_k:
            break
        if r.id in seen_ids:
            continue
        seen_ids.add(r.id)
        chosen.append(r)
        explanations.append(template)

    return chosen, explanations
