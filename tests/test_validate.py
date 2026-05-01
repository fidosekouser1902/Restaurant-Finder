from unittest.mock import patch

import pytest

from recommender.phase1.config import DatasetConfig
from recommender.phase1.validate import validate_corpus


class _Tiny:
    """Minimal RestaurantRecord duck for mocking load_dataset yields."""

    def __init__(self, ok=True):
        self._ok = ok

    def has_required_fields(self):
        return self._ok


def test_validate_corpus_min_valid():
    with patch("recommender.phase1.validate.load_dataset", return_value=[_Tiny(True)] * 5):
        stats = validate_corpus(DatasetConfig(), min_valid=0)
        assert stats["total_rows"] == 5
        assert stats["rows_passing_validation"] == 5


def test_validate_corpus_asserts_when_below_min():
    with patch("recommender.phase1.validate.load_dataset", return_value=[_Tiny(False), _Tiny(True)]):
        with pytest.raises(AssertionError):
            validate_corpus(DatasetConfig(), min_valid=5)


def test_dataset_config_from_env_merge(monkeypatch):
    monkeypatch.setenv("RECOMMENDER_MAX_ROWS", "42")
    monkeypatch.setenv("RECOMMENDER_PREFER_CACHE", "true")
    monkeypatch.setenv("RECOMMENDER_STREAMING", "1")
    monkeypatch.setenv("DATASET_CACHE_DIR", "/tmp/hf")
    c = DatasetConfig.from_env(streaming=False)  # explicit wins
    assert c.max_rows == 42
    assert c.prefer_cache is True
    assert c.streaming is False
    assert c.cache_dir == "/tmp/hf"
