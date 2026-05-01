"""Phase 4 API tests (in-memory corpus + mock LLM; no Hugging Face)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from recommender.common.models import CostTier, RestaurantRecord
from recommender.phase3.client import ChatCompleter
from recommender.phase4.app import create_app


def _tiny_corpus() -> tuple[RestaurantRecord, ...]:
    return (
        RestaurantRecord(
            id="a1",
            name="Roma",
            city="Bangalore",
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
            city="Bangalore",
            neighborhood="Koramangala",
            cuisines=["italian", "continental"],
            rating=4.2,
            cost_for_two=900,
            cost_tier=CostTier.HIGH,
            votes=5,
            raw_fields={},
        ),
        RestaurantRecord(
            id="c3",
            name="Spice Hub",
            city="Delhi",
            neighborhood="Connaught Place",
            cuisines=["north indian"],
            rating=4.0,
            cost_for_two=600,
            cost_tier=CostTier.MEDIUM,
            votes=20,
            raw_fields={},
        ),
    )


class _FakeGroq(ChatCompleter):
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def complete(
        self,
        messages,
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        return json.dumps(self._payload)


@pytest.fixture
def client_mock_llm():
    payload = {
        "summary": "Italian picks in Bangalore.",
        "recommendations": [
            {"rank": 1, "restaurant_id": "b2", "explanation": "Great variety."},
            {"rank": 2, "restaurant_id": "a1", "explanation": "High rating."},
        ],
    }
    app = create_app(
        corpus=_tiny_corpus(),
        llm_client=_FakeGroq(payload),
        load_env_file=False,
        enable_cors=False,
    )
    with TestClient(app) as tc:
        yield tc


def test_health_reports_corpus_size():
    app = create_app(corpus=_tiny_corpus(), load_env_file=False, enable_cors=False)
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "corpus_size": 3}


def test_ui_root_serves_html():
    app = create_app(corpus=_tiny_corpus(), load_env_file=False, enable_cors=False, serve_ui=True)
    with TestClient(app) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        body = r.text
        assert "Restaurant recommender" in body
        assert "/api/v1/recommend" in body


def test_ui_disabled_skips_root():
    app = create_app(corpus=_tiny_corpus(), load_env_file=False, enable_cors=False, serve_ui=False)
    with TestClient(app) as client:
        assert client.get("/").status_code == 404


def test_localities_endpoint_returns_sorted_neighborhoods():
    app = create_app(corpus=_tiny_corpus(), load_env_file=False, enable_cors=False)
    with TestClient(app) as client:
        r = client.get("/api/v1/localities")
        assert r.status_code == 200
        locs = r.json()["localities"]
        assert locs == sorted(locs, key=str.lower)
        assert "Indiranagar" in locs
        assert "Koramangala" in locs
        assert "Connaught Place" in locs


def test_recommend_top_k_above_max_returns_422(client_mock_llm):
    r = client_mock_llm.post(
        "/api/v1/recommend",
        json={
            "budget_for_two_inr": 1500,
            "cuisines": ["Italian"],
            "min_rating": 4.0,
            "location": "Bangalore",
            "extras": "",
            "top_k": 13,
        },
    )
    assert r.status_code == 422


def test_recommend_top_k_limits_count(client_mock_llm):
    r = client_mock_llm.post(
        "/api/v1/recommend",
        json={
            "budget_for_two_inr": 1500,
            "cuisines": ["Italian"],
            "min_rating": 4.0,
            "location": "Bangalore",
            "extras": "",
            "top_k": 1,
        },
    )
    assert r.status_code == 200
    assert len(r.json()["recommendations"]) == 1


def test_recommend_validation_zero_budget_returns_422(client_mock_llm):
    r = client_mock_llm.post(
        "/api/v1/recommend",
        json={
            "budget_for_two_inr": 0,
            "cuisines": [],
            "min_rating": 4.0,
            "location": "Bangalore",
        },
    )
    assert r.status_code == 422


def test_recommend_happy_path_mock_llm(client_mock_llm):
    r = client_mock_llm.post(
        "/api/v1/recommend",
        json={
            "budget_for_two_inr": 1500,
            "cuisines": ["Italian"],
            "min_rating": 4.0,
            "location": "Bangalore",
            "extras": "date night",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["fallback_used"] is False
    assert data["summary"] == "Italian picks in Bangalore."
    assert len(data["recommendations"]) == 2
    assert data["recommendations"][0]["id"] == "b2"
    assert data["recommendations"][0]["explanation"]
    assert data["recommendations"][0]["rating"] == 4.2
    assert data["recommendations"][0]["cost_tier"] == "high"
    assert isinstance(data["relaxations_applied"], list)
    assert "filter_funnel" in data
    assert data["filter_funnel"]["total_after_location"] >= 1
