import pytest

from recommender.common.errors import PreferenceValidationError
from recommender.common.models import CostTier, RestaurantRecord
from recommender.phase2.filter_engine import (
    FilterConfig,
    filter_restaurants,
    pack_candidates_for_llm,
)
from recommender.phase2.preferences import UserPreferences


def _rec(**kw) -> RestaurantRecord:
    defaults = dict(
        id="x",
        name="N",
        city="Indiranagar",
        neighborhood="Indiranagar",
        cuisines=["north indian"],
        rating=4.2,
        cost_for_two=600,
        cost_tier=CostTier.MEDIUM,
        votes=100,
        raw_fields={"address": "Bangalore MG Road"},
    )
    defaults.update(kw)
    return RestaurantRecord(**defaults)


CORPUS = (
    _rec(id="1", name="Alpha", cuisines=["italian", "continental"], rating=4.5, cost_tier=CostTier.HIGH),
    _rec(id="2", name="Beta", cuisines=["chinese"], rating=4.0, cost_tier=CostTier.MEDIUM, city="Banashankari"),
    _rec(id="3", name="Gamma", cuisines=["italian"], rating=3.8, cost_tier=CostTier.LOW),
    _rec(id="4", name="Delta", cuisines=["mexican"], rating=None, cost_tier=CostTier.MEDIUM),
)


def test_parse_preferences_ok():
    p = UserPreferences.from_mapping(
        {
            "location": "Bangalore",
            "budget_for_two_inr": 1000,
            "cuisines": ["Italian"],
            "min_rating": 4.0,
            "extras": "quiet",
        }
    )
    assert p.location == "Bangalore"
    assert p.max_cost_for_two_inr == 1000
    assert p.cuisines == ("italian",)
    assert p.min_rating == 4.0


def test_parse_budget_inr_invalid():
    with pytest.raises(PreferenceValidationError):
        UserPreferences.from_mapping(
            {"location": "Delhi", "budget_for_two_inr": 0, "cuisines": [], "min_rating": 3.0}
        )


def test_parse_min_rating_range():
    with pytest.raises(PreferenceValidationError):
        UserPreferences.from_mapping(
            {"location": "Delhi", "budget_for_two_inr": 500, "cuisines": [], "min_rating": 6.0}
        )


def test_parse_cuisines_rejects_single_string():
    with pytest.raises(PreferenceValidationError):
        UserPreferences.from_mapping(
            {"location": "Delhi", "budget_for_two_inr": 500, "cuisines": "Italian", "min_rating": 3.0}
        )


def test_filter_location_and_cuisine():
    prefs = UserPreferences(
        location="Banashankari",
        max_cost_for_two_inr=1000,
        cuisines=("chinese",),
        min_rating=3.5,
    )
    res = filter_restaurants(prefs, CORPUS, config=FilterConfig(k_min=1, max_candidates=10))
    assert len(res.candidates) == 1
    assert res.candidates[0].name == "Beta"
    assert res.relaxations_applied == ()


def test_filter_excludes_null_rating():
    prefs = UserPreferences(
        location=None,
        max_cost_for_two_inr=1000,
        cuisines=("mexican",),
        min_rating=4.0,
    )
    res = filter_restaurants(prefs, CORPUS, config=FilterConfig(k_min=1, max_candidates=10))
    assert len(res.candidates) == 0


def test_relaxation_lowers_min_rating():
    """Only Gamma matches italian + budget; need rating relax for k_min=2."""
    small = (
        _rec(id="a", name="A", cuisines=["italian"], rating=4.2, cost_tier=CostTier.MEDIUM),
        _rec(id="b", name="B", cuisines=["italian"], rating=3.6, cost_tier=CostTier.MEDIUM),
    )
    prefs = UserPreferences(
        location=None,
        max_cost_for_two_inr=1000,
        cuisines=("italian",),
        min_rating=4.0,
    )
    res = filter_restaurants(
        prefs,
        small,
        config=FilterConfig(k_min=2, max_candidates=10, min_rating_floor=3.5, rating_relax_step=0.5),
    )
    assert len(res.candidates) >= 2
    assert "lowered_min_rating" in res.relaxations_applied


def test_pack_candidates_for_llm_shape():
    prefs = UserPreferences(
        location=None,
        max_cost_for_two_inr=5000,
        cuisines=(),
        min_rating=0.0,
    )
    res = filter_restaurants(prefs, CORPUS[:2], config=FilterConfig(k_min=1, max_candidates=5))
    packed = pack_candidates_for_llm(res.candidates)
    assert packed[0]["id"]
    assert packed[0]["cost_tier"] in ("low", "medium", "high")
