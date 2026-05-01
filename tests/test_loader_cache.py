import json
from pathlib import Path

from recommender.common.models import CostTier, RestaurantRecord
from recommender.phase1.config import DatasetConfig
from recommender.phase1.loader import _dict_to_record, _meta_path, _record_to_dict, _write_parquet_cache
from recommender.phase1.normalize import row_to_restaurant


def test_record_roundtrip_dict(tmp_path: Path):
    cfg = DatasetConfig()
    raw = {
        "name": "Test Cafe",
        "listed_in(city)": "Delhi",
        "location": "Connaught Place",
        "cuisines": "Italian",
        "rate": "4.5/5",
        "approx_cost(for two people)": "1200",
        "votes": 10,
    }
    rec = row_to_restaurant(raw, cfg)
    d = _record_to_dict(rec)
    back = _dict_to_record(d)
    assert back == rec


def test_parquet_cache_write_and_meta(tmp_path: Path):
    cfg = DatasetConfig(dataset_name="ManikaSaini/zomato-restaurant-recommendation", revision=None)
    rows = [
        RestaurantRecord(
            id="abc",
            name="R",
            city="Delhi",
            neighborhood="CP",
            cuisines=["italian"],
            rating=4.0,
            cost_for_two=500,
            cost_tier=CostTier.MEDIUM,
            votes=5,
            raw_fields={},
        )
    ]
    path = tmp_path / "out.parquet"
    _write_parquet_cache(path, rows, cfg)
    assert path.is_file()
    meta = json.loads(_meta_path(path).read_text(encoding="utf-8"))
    assert meta["schema_version"]
    assert meta["row_count"] == 1
