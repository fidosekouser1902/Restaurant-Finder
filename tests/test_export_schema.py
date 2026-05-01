import json

from recommender.phase1.export_schema import build_canonical_schema_document, write_canonical_schema
from recommender.phase1.schema import SCHEMA_VERSION


def test_build_matches_schema_version():
    doc = build_canonical_schema_document()
    assert doc["schema_version"] == SCHEMA_VERSION
    assert doc["json_schema"]["properties"]["cost_tier"]["enum"] == ["low", "medium", "high"]


def test_write_roundtrip(tmp_path):
    p = tmp_path / "out.json"
    write_canonical_schema(p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION
    assert len(data["column_mapping"]) == len(build_canonical_schema_document()["column_mapping"])
