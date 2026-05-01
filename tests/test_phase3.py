import json
import os

import pytest

from recommender.common.models import CostTier, RestaurantRecord
from recommender.phase2.preferences import UserPreferences
from recommender.phase3.client import ChatCompleter
from recommender.phase3.engine import recommend
from recommender.phase3.parser import parse_llm_response
from recommender.phase3.reconcile import reconcile_to_candidates


class _FakeGroq(ChatCompleter):
    def __init__(self, response_json: dict):
        self._payload = response_json

    def complete(
        self,
        messages,
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        return json.dumps(self._payload)


def _prefs() -> UserPreferences:
    return UserPreferences(
        location="Bangalore",
        max_cost_for_two_inr=2500,
        cuisines=("italian",),
        min_rating=4.0,
        extras="",
    )


def _candidates():
    return (
        RestaurantRecord(
            id="a1",
            name="Roma",
            city="Indiranagar",
            neighborhood="Indiranagar",
            cuisines=["italian"],
            rating=4.5,
            cost_for_two=800,
            cost_tier=CostTier.MEDIUM,
            votes=10,
            raw_fields={},
        ),
        RestaurantRecord(
            id="b2",
            name="Venice",
            city="Koramangala",
            neighborhood="Koramangala",
            cuisines=["italian", "continental"],
            rating=4.2,
            cost_for_two=900,
            cost_tier=CostTier.HIGH,
            votes=5,
            raw_fields={},
        ),
    )


def test_parse_llm_response_roundtrip():
    payload = {
        "summary": "Good Italian nearby.",
        "recommendations": [
            {"rank": 1, "restaurant_id": "a1", "explanation": "Strong rating."},
            {"rank": 2, "restaurant_id": "b2", "explanation": "Solid backup."},
        ],
    }
    summary, rows = parse_llm_response(json.dumps(payload))
    assert summary == "Good Italian nearby."
    assert [r.restaurant_id for r in rows] == ["a1", "b2"]


def test_parse_llm_response_markdown_fence():
    inner = '{"summary": null, "recommendations": [{"rank": 1, "restaurant_id": "x", "explanation": "y"}]}'
    raw = f"```json\n{inner}\n```"
    summary, rows = parse_llm_response(raw)
    assert rows[0].restaurant_id == "x"


def test_reconcile_name_fallback():
    from recommender.phase3.parser import ParsedRecommendation

    cands = _candidates()
    parsed = [
        ParsedRecommendation(1, "roma", "by name"),
    ]
    recs, expls = reconcile_to_candidates(parsed, cands, top_k=2)
    assert recs[0].name == "Roma"
    assert "by name" in expls[0]


def test_recommend_mock_llm():
    payload = {
        "summary": "Two picks.",
        "recommendations": [
            {"rank": 1, "restaurant_id": "b2", "explanation": "Nice variety."},
            {"rank": 2, "restaurant_id": "a1", "explanation": "Classic."},
        ],
    }
    client = _FakeGroq(payload)
    result = recommend(
        _prefs(),
        _candidates(),
        client=client,
        load_env_file=False,
        top_k=2,
    )
    assert not result.fallback_used
    assert len(result.items) == 2
    assert result.items[0].restaurant.id == "b2"
    assert result.summary == "Two picks."


def test_recommend_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = recommend(_prefs(), _candidates(), load_env_file=False, top_k=2)
    assert result.fallback_used
    assert len(result.items) == 2


@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="Set GROQ_API_KEY for live Groq smoke test.")
def test_recommend_live_groq_smoke():
    prefs = _prefs()
    out = recommend(prefs, _candidates(), load_env_file=True, top_k=2)
    assert len(out.items) >= 1
    ids = {r.id for r in _candidates()}
    for it in out.items:
        assert it.restaurant.id in ids
