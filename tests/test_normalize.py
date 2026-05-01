import pytest

from recommender.common.models import CostTier
from recommender.phase1.config import DatasetConfig
from recommender.phase1.normalize import (
    normalize_city,
    parse_cost_inr,
    parse_rating,
    row_to_restaurant,
    split_cuisines,
    stable_restaurant_id,
)


def test_parse_rating_fraction():
    assert parse_rating("4.1/5") == pytest.approx(4.1)
    assert parse_rating("NEW") is None


def test_parse_cost_inr():
    assert parse_cost_inr("800") == 800
    assert parse_cost_inr("1,200") == 1200


def test_split_cuisines():
    assert split_cuisines("North Indian, Mughlai, Chinese") == [
        "north indian",
        "mughlai",
        "chinese",
    ]


def test_normalize_city_alias():
    assert normalize_city("bengaluru") == "Bangalore"


def test_stable_id_deterministic():
    a = stable_restaurant_id("Jalsa", "Bangalore", "Banashankari", ["north indian"])
    b = stable_restaurant_id("Jalsa", "Bangalore", "Banashankari", ["north indian"])
    assert a == b


def test_row_to_restaurant_sample():
    raw = {
        "name": "Jalsa",
        "listed_in(city)": "Banashankari",
        "location": "Banashankari",
        "cuisines": "North Indian, Mughlai, Chinese",
        "rate": "4.1/5",
        "approx_cost(for two people)": "800",
        "votes": 775,
    }
    cfg = DatasetConfig()
    r = row_to_restaurant(raw, cfg)
    assert r.name == "Jalsa"
    assert r.city == "Banashankari"
    assert r.neighborhood == "Banashankari"
    assert r.rating == pytest.approx(4.1)
    assert r.cost_for_two == 800
    assert r.cost_tier == CostTier.MEDIUM
    assert r.votes == 775
    assert r.has_required_fields()


def test_cost_tier_thresholds():
    cfg = DatasetConfig(cost_low_max_inr=400, cost_medium_max_inr=1000)
    raw_low = {"name": "A", "listed_in(city)": "Delhi", "cuisines": "C", "approx_cost(for two people)": "300"}
    assert row_to_restaurant(raw_low, cfg).cost_tier == CostTier.LOW
    raw_high = {**raw_low, "approx_cost(for two people)": "2000"}
    assert row_to_restaurant(raw_high, cfg).cost_tier == CostTier.HIGH
