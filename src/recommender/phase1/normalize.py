from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

from recommender.common.models import CostTier, RestaurantRecord
from recommender.phase1.config import DatasetConfig

# Common Indian city synonyms for user-facing consistency (extend as needed).
_CITY_ALIASES = {
    "bengaluru": "Bangalore",
    "bangalore": "Bangalore",
    "gurugram": "Gurgaon",
    "gurgaon": "Gurgaon",
    "new delhi": "Delhi",
    "ncr": "Delhi",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
}


def normalize_whitespace(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def normalize_city(city: str) -> str:
    s = normalize_whitespace(city.strip())
    if not s:
        return ""
    key = s.lower()
    if key in _CITY_ALIASES:
        return _CITY_ALIASES[key]
    return s.title()


def split_cuisines(raw: Optional[str]) -> List[str]:
    if not raw or not str(raw).strip():
        return []
    parts = re.split(r"\s*,\s*", str(raw))
    out: List[str] = []
    for p in parts:
        t = normalize_whitespace(p).lower()
        if t:
            out.append(t)
    # Dedupe preserving order
    seen = set()
    uniq: List[str] = []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


_RATE_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*/\s*5")


def parse_rating(raw: Optional[Any]) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in {"nan", "new", "-", "none"}:
        return None
    m = _RATE_PATTERN.match(s)
    if m:
        return float(m.group(1))
    try:
        return float(s)
    except ValueError:
        return None


def parse_cost_inr(raw: Optional[Any]) -> Optional[int]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in {"nan", "-"}:
        return None
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return None
    return int(digits)


def classify_cost_tier(cost: Optional[int], config: DatasetConfig) -> CostTier:
    if cost is None:
        return CostTier.MEDIUM
    low_max, med_max = config.cost_tier_bounds()
    if cost <= low_max:
        return CostTier.LOW
    if cost <= med_max:
        return CostTier.MEDIUM
    return CostTier.HIGH


def stable_restaurant_id(name: str, city: str, neighborhood: str, cuisines: Iterable[str]) -> str:
    """Stable surrogate ID — architecture: hash of name + location + cuisine."""
    cuis = ",".join(sorted(cuisines))
    payload = f"{normalize_whitespace(name)}|{normalize_city(city)}|{normalize_whitespace(neighborhood)}|{cuis}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def row_to_restaurant(raw: Dict[str, Any], config: DatasetConfig) -> RestaurantRecord:
    """Map one Hugging Face row dict to ``RestaurantRecord``."""
    name_raw = raw.get("name") or ""
    name = normalize_whitespace(str(name_raw)).title() if name_raw else ""

    city_raw = raw.get("listed_in(city)")
    city = normalize_city(str(city_raw or ""))

    neighborhood_raw = raw.get("location") or ""
    neighborhood = normalize_whitespace(str(neighborhood_raw))

    cuisines = split_cuisines(raw.get("cuisines"))
    rating = parse_rating(raw.get("rate"))
    cost_for_two = parse_cost_inr(raw.get("approx_cost(for two people)"))
    cost_tier = classify_cost_tier(cost_for_two, config)

    votes: Optional[int] = None
    v = raw.get("votes")
    if v is not None:
        try:
            votes = int(v)
        except (TypeError, ValueError):
            votes = None

    rid = stable_restaurant_id(name, city, neighborhood, cuisines)

    extra_keys = (
        "url",
        "address",
        "online_order",
        "book_table",
        "phone",
        "rest_type",
        "dish_liked",
        "reviews_list",
        "menu_item",
        "listed_in(type)",
    )
    raw_fields: Dict[str, Any] = {k: raw.get(k) for k in extra_keys if k in raw}

    return RestaurantRecord(
        id=rid,
        name=name,
        city=city,
        neighborhood=neighborhood,
        cuisines=cuisines,
        rating=rating,
        cost_for_two=cost_for_two,
        cost_tier=cost_tier,
        votes=votes,
        raw_fields=raw_fields,
    )
