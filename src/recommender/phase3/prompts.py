"""Versioned prompt templates for Phase 3."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from recommender.phase2.preferences import UserPreferences

PROMPT_VERSION = "v2"

_OUTPUT_SCHEMA_HINT = """
Respond with a single JSON object only (no markdown fences), exactly in this shape:
{
  "summary": "One short sentence overview for the user (may acknowledge constraints).",
  "recommendations": [
    {
      "rank": 1,
      "restaurant_id": "<must match an id from the candidates array>",
      "explanation": "1-3 sentences why this pick fits the user."
    }
  ]
}
Include at most {top_k} entries in recommendations, ordered by rank starting at 1.
Every restaurant_id MUST be copied from the candidates list — never invent venues.
"""


def build_chat_messages(
    preferences: UserPreferences,
    candidates: List[Dict[str, Any]],
    *,
    top_k: int,
) -> List[Dict[str, str]]:
    """OpenAI-style messages for Groq chat completions."""
    cuisine_note = (
        "any cuisine (user did not specify)"
        if not preferences.cuisines
        else ", ".join(preferences.cuisines)
    )
    prefs_payload = {
        "locality_or_area": preferences.location or "any locality",
        "max_budget_inr_for_two": preferences.max_cost_for_two_inr,
        "cuisine_preferences": cuisine_note,
        "min_rating": preferences.min_rating,
        "extras": preferences.extras or None,
    }
    user_body = {
        "user_preferences": prefs_payload,
        "candidates": candidates,
        "instructions": _OUTPUT_SCHEMA_HINT.replace("{top_k}", str(top_k)).strip(),
    }
    system = (
        "You are a restaurant recommendation assistant for India. "
        "You receive user preferences and a JSON array of candidate restaurants. "
        "The user states a maximum budget in INR for approximate cost for two (max_budget_inr_for_two); "
        "respect that constraint when reasoning and explaining — candidates are already filtered to fit it unless noted. "
        "Cuisine preferences may be empty meaning any cuisine; still explain fit using rating, cost, and locality/city. "
        "You must ONLY recommend restaurants that appear in the candidates array, using their exact \"id\" values. "
        "If none are a perfect fit, say so briefly in summary but still choose the best options from the list."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_body, ensure_ascii=False)},
    ]
