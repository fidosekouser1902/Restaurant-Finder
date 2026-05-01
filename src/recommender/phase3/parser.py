"""Parse JSON recommendation payloads from LLM output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


@dataclass(frozen=True)
class ParsedRecommendation:
    rank: int
    restaurant_id: str
    explanation: str


def _strip_markdown_fence(text: str) -> str:
    s = text.strip()
    if not s.startswith("```"):
        return s
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```\s*$", "", s)
    return s.strip()


def parse_llm_response(raw: str) -> Tuple[Optional[str], List[ParsedRecommendation]]:
    """Parse model output into summary + structured recommendations."""
    blob = json.loads(_strip_markdown_fence(raw))
    if not isinstance(blob, dict):
        raise ValueError("LLM JSON root must be an object.")
    summary = blob.get("summary")
    if summary is not None and not isinstance(summary, str):
        summary = str(summary)

    raw_list = blob.get("recommendations")
    if raw_list is None:
        return summary, []
    if not isinstance(raw_list, list):
        raise ValueError("recommendations must be a JSON array.")

    out: List[ParsedRecommendation] = []
    for i, row in enumerate(raw_list):
        if not isinstance(row, dict):
            continue
        rid = row.get("restaurant_id")
        if rid is None:
            continue
        expl = row.get("explanation") or ""
        rank_raw = row.get("rank")
        try:
            rank = int(rank_raw) if rank_raw is not None else i + 1
        except (TypeError, ValueError):
            rank = i + 1
        out.append(
            ParsedRecommendation(
                rank=rank,
                restaurant_id=str(rid).strip(),
                explanation=str(expl).strip(),
            )
        )
    out.sort(key=lambda x: x.rank)
    return summary, out
