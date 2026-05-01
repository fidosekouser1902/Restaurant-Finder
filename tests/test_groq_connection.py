"""Live Groq connectivity checks (loads repo ``.env``; requires network)."""

from __future__ import annotations

import pytest

from recommender.common.models import CostTier, RestaurantRecord
from recommender.phase2.preferences import UserPreferences
from recommender.phase3.client import GroqChatClient
from recommender.phase3.config import GroqLLMConfig
from recommender.phase3.engine import recommend
from recommender.phase3.env import load_dotenv_if_present


@pytest.fixture(scope="module", autouse=True)
def _load_dotenv_once():
    """Pick up ``GROQ_API_KEY`` from project root ``.env`` before assertions."""
    load_dotenv_if_present()


def test_groq_config_loaded_from_env():
    cfg = GroqLLMConfig.try_from_env(load_env_file=False)
    assert cfg is not None, "GROQ_API_KEY missing after .env load — check .env at repo root"
    assert len(cfg.api_key) >= 10, "API key looks too short"


def test_groq_minimal_chat_completion():
    cfg = GroqLLMConfig.try_from_env(load_env_file=False)
    if cfg is None:
        pytest.fail("No Groq config; add GROQ_API_KEY to .env")
    client = GroqChatClient(cfg)
    text = client.complete(
        [{"role": "user", "content": 'Respond with exactly one word: OK'}],
        model=cfg.model,
        temperature=0.0,
        max_tokens=16,
    )
    assert "OK" in text.upper(), f"Unexpected model reply: {text[:200]!r}"


def test_recommend_pipeline_calls_groq_without_fallback():
    cfg = GroqLLMConfig.try_from_env(load_env_file=False)
    if cfg is None:
        pytest.fail("No Groq config")

    prefs = UserPreferences(
        location=None,
        max_cost_for_two_inr=2000,
        cuisines=("italian",),
        min_rating=3.5,
        extras="family dinner",
    )
    candidates = (
        RestaurantRecord(
            id="t1",
            name="Test Bistro",
            city="Bangalore",
            neighborhood="Indiranagar",
            cuisines=["italian", "continental"],
            rating=4.4,
            cost_for_two=700,
            cost_tier=CostTier.MEDIUM,
            votes=42,
            raw_fields={},
        ),
        RestaurantRecord(
            id="t2",
            name="Test Diner",
            city="Bangalore",
            neighborhood="Koramangala",
            cuisines=["north indian"],
            rating=4.1,
            cost_for_two=500,
            cost_tier=CostTier.MEDIUM,
            votes=10,
            raw_fields={},
        ),
    )
    result = recommend(
        prefs,
        candidates,
        llm_config=cfg,
        load_env_file=False,
        top_k=2,
    )
    assert result.fallback_used is False, "LLM path failed — check key, model id, and network"
    assert len(result.items) >= 1
    ids = {r.id for r in candidates}
    for item in result.items:
        assert item.restaurant.id in ids
        assert item.explanation.strip()
