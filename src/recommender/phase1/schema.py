"""Schema versioning and documented raw → canonical column mapping.

Source dataset: ``ManikaSaini/zomato-restaurant-recommendation`` on Hugging Face.
Train split columns (verified): see ``RAW_COLUMN_MAP``.
"""

from __future__ import annotations

# Bump when ``RestaurantRecord`` fields or normalization semantics change.
SCHEMA_VERSION = "1.0.0"


def get_schema_version() -> str:
    """Return canonical schema version string for debugging and compatibility checks."""
    return SCHEMA_VERSION


# Explicit mapping: Hugging Face column name → purpose in our pipeline.
RAW_COLUMN_MAP = {
    "url": "raw_fields only — listing URL",
    "address": "raw_fields — full address",
    "name": "RestaurantRecord.name (title-cased)",
    "online_order": "raw_fields",
    "book_table": "raw_fields",
    "rate": "RestaurantRecord.rating — parsed from strings like 4.1/5",
    "votes": "RestaurantRecord.votes",
    "phone": "raw_fields",
    "location": "RestaurantRecord.neighborhood (area within city)",
    "rest_type": "raw_fields — Casual Dining, etc.",
    "dish_liked": "raw_fields",
    "cuisines": "RestaurantRecord.cuisines — split list, lowercased",
    "approx_cost(for two people)": "RestaurantRecord.cost_for_two + cost_tier",
    "reviews_list": "raw_fields — long text",
    "menu_item": "raw_fields",
    "listed_in(type)": "raw_fields — Buffet, Delivery, …",
    "listed_in(city)": "RestaurantRecord.city — normalized metro / zone for filtering",
}
