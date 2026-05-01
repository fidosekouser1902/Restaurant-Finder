from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_optional_int(name: str) -> Optional[int]:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return int(raw)


def _env_truthy(name: str) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return False
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")


@dataclass
class DatasetConfig:
    """Externalized settings for Phase 1 ingestion (env-overridable via ``from_env``)."""

    dataset_name: str = "ManikaSaini/zomato-restaurant-recommendation"
    split: str = "train"
    revision: Optional[str] = None
    trust_remote_code: bool = False

    #: Hugging Face Arrow cache directory (HF hub download). Mirrors common ``HF_HOME`` workflows;
    #: also honours ``RECOMMENDER_DATASET_CACHE_DIR`` in ``from_env``.
    cache_dir: Optional[str] = None

    #: If set and ``prefer_cache`` is True, load normalized Parquet when metadata matches.
    normalized_cache_path: Optional[str] = None
    prefer_cache: bool = False

    #: INR thresholds for ``approx_cost(for two people)`` → CostTier (inclusive upper bounds).
    #: Default: low ≤ 400, medium ≤ 1000, else high (typical Zomato India bands).
    cost_low_max_inr: int = field(default_factory=lambda: _env_int("RECOMMENDER_COST_LOW_MAX_INR", 400))
    cost_medium_max_inr: int = field(default_factory=lambda: _env_int("RECOMMENDER_COST_MEDIUM_MAX_INR", 1000))

    #: Limit rows for tests or debugging (None = all).
    max_rows: Optional[int] = None

    #: Stream from Hub without materializing full split into RAM (no Parquet cache write — see loader).
    streaming: bool = False

    #: If True, missing expected HF columns raises ``DatasetSchemaError`` instead of logging a warning.
    strict_columns: bool = False

    def cost_tier_bounds(self) -> Tuple[int, int]:
        """Returns (low_max, medium_max) inclusive upper limits for low and medium tiers."""
        return (self.cost_low_max_inr, self.cost_medium_max_inr)

    @classmethod
    def from_env(cls, **kwargs: Any) -> DatasetConfig:
        """Merge optional environment defaults with explicit ``kwargs`` (kwargs win).

        Supported env vars:
        - ``RECOMMENDER_DATASET_NAME``, ``RECOMMENDER_DATASET_REVISION``, ``RECOMMENDER_DATASET_SPLIT``
        - ``RECOMMENDER_MAX_ROWS``, ``RECOMMENDER_PREFER_CACHE`` (truthy strings)
        - ``RECOMMENDER_NORMALIZED_CACHE_PATH``, ``RECOMMENDER_STREAMING`` (truthy)
        - ``RECOMMENDER_STRICT_COLUMNS`` (truthy)
        - ``DATASET_CACHE_DIR`` or ``RECOMMENDER_DATASET_CACHE_DIR`` → ``cache_dir``
        - ``RECOMMENDER_USE_PROJECT_CACHE`` — ``0``/``false`` disables default project-local ``HF_HOME`` (see loader).
        """
        base: Dict[str, Any] = {}
        name = os.environ.get("RECOMMENDER_DATASET_NAME")
        if name:
            base["dataset_name"] = name
        rev = os.environ.get("RECOMMENDER_DATASET_REVISION")
        if rev:
            base["revision"] = rev
        spl = os.environ.get("RECOMMENDER_DATASET_SPLIT")
        if spl:
            base["split"] = spl
        mr = _env_optional_int("RECOMMENDER_MAX_ROWS")
        if mr is not None:
            base["max_rows"] = mr
        ncp = os.environ.get("RECOMMENDER_NORMALIZED_CACHE_PATH")
        if ncp:
            base["normalized_cache_path"] = ncp
        if _env_truthy("RECOMMENDER_PREFER_CACHE"):
            base["prefer_cache"] = True
        if _env_truthy("RECOMMENDER_STREAMING"):
            base["streaming"] = True
        if _env_truthy("RECOMMENDER_STRICT_COLUMNS"):
            base["strict_columns"] = True
        cache = os.environ.get("DATASET_CACHE_DIR") or os.environ.get("RECOMMENDER_DATASET_CACHE_DIR")
        if cache:
            base["cache_dir"] = cache
        merged = {**base, **kwargs}
        return cls(**merged)
