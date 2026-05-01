"""Phase 3 — Groq LLM ranking and explanations."""

from recommender.phase3.client import ChatCompleter, GroqChatClient
from recommender.phase3.config import GroqLLMConfig
from recommender.phase3.engine import RecommendationItem, RecommendationResult, recommend

__all__ = [
    "ChatCompleter",
    "GroqChatClient",
    "GroqLLMConfig",
    "RecommendationItem",
    "RecommendationResult",
    "recommend",
]
