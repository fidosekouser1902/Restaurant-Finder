"""Paths relative to this repository (editable / dev checkout layout)."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Directory that contains ``src/`` (the git project root when installed editable)."""
    # This file: <root>/src/recommender/common/paths.py
    return Path(__file__).resolve().parent.parent.parent.parent


def project_hf_home() -> Path:
    """Hugging Face cache root inside the project: ``<root>/.cache/huggingface``."""
    return project_root() / ".cache" / "huggingface"


def default_normalized_parquet_path() -> Path:
    """Default location for normalized Parquet written by Phase 1 (optional use)."""
    return project_root() / ".cache" / "zomato_normalized.parquet"
