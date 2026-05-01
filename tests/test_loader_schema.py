"""Loader schema guards and HF integration wiring (mocked)."""

from unittest.mock import patch

import pytest

from recommender.common.errors import DatasetSchemaError
from recommender.phase1.config import DatasetConfig
from recommender.phase1.loader import _EXPECTED_HF_COLUMNS, load_dataset

_SAMPLE_ROW = {
    "url": "",
    "address": "",
    "name": "Cafe",
    "online_order": "No",
    "book_table": "No",
    "rate": "4.0/5",
    "votes": 10,
    "phone": "",
    "location": "Area",
    "rest_type": "Casual",
    "dish_liked": "",
    "cuisines": "Italian",
    "approx_cost(for two people)": "600",
    "reviews_list": "",
    "menu_item": "",
    "listed_in(type)": "Delivery",
    "listed_in(city)": "Delhi",
}


class _StubHubDataset:
    """Minimal Duck-typing Hugging Face ``Dataset`` with ``column_names`` and row iteration."""

    def __init__(self, column_names: list[str], rows: list[dict]):
        self.column_names = column_names
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


@patch("recommender.phase1.loader.hf_load_dataset")
def test_strict_columns_raises_when_hub_schema_incomplete(mock_hf):
    incomplete_cols = ["name"]
    mock_hf.return_value = _StubHubDataset(incomplete_cols, [])

    config = DatasetConfig(strict_columns=True, max_rows=10)
    with pytest.raises(DatasetSchemaError):
        list(load_dataset(config))


@patch("recommender.phase1.loader.hf_load_dataset")
def test_relaxed_columns_logs_warning_when_columns_missing(mock_hf, caplog):
    import logging

    caplog.set_level(logging.WARNING)
    cols = sorted(_EXPECTED_HF_COLUMNS - {"votes"})
    mock_hf.return_value = _StubHubDataset(cols, [_SAMPLE_ROW])

    config = DatasetConfig(strict_columns=False, max_rows=1)
    list(load_dataset(config))
    assert "missing" in caplog.text.lower()
