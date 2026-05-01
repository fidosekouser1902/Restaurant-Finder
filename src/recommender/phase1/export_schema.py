"""Write machine-readable canonical schema JSON under ``schemas/canonical_schema.json``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from recommender.common.paths import project_root
from recommender.phase1.schema import RAW_COLUMN_MAP, SCHEMA_VERSION

DEFAULT_DATASET_ID = "ManikaSaini/zomato-restaurant-recommendation"


def build_canonical_schema_document() -> Dict[str, Any]:
    """Single artifact: HF mapping + JSON Schema for ``RestaurantRecord``."""
    return {
        "$comment": "Regenerate from code: python -m recommender.phase1.export_schema",
        "schema_version": SCHEMA_VERSION,
        "source_dataset": {
            "huggingface_id": DEFAULT_DATASET_ID,
            "split": "train",
        },
        "column_mapping": [
            {"hf_column": name, "canonical_use": description}
            for name, description in sorted(RAW_COLUMN_MAP.items())
        ],
        "json_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "RestaurantRecord",
            "description": "Normalized restaurant row after Phase 1 ingestion.",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "id",
                "name",
                "city",
                "neighborhood",
                "cuisines",
                "rating",
                "cost_for_two",
                "cost_tier",
                "votes",
                "raw_fields",
            ],
            "properties": {
                "id": {
                    "type": "string",
                    "description": "16-char hex prefix of SHA-256(name|city|neighborhood|sorted cuisines).",
                },
                "name": {"type": "string", "description": "Trimmed, title-cased from HF name."},
                "city": {
                    "type": "string",
                    "description": "From listed_in(city); normalized via city aliases (e.g. Bengaluru→Bangalore).",
                },
                "neighborhood": {"type": "string", "description": "From location."},
                "cuisines": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Comma-split HF cuisines; deduped; lowercased tokens.",
                },
                "rating": {
                    "type": ["number", "null"],
                    "description": "Parsed from rate (e.g. 4.1/5); null if missing/unparseable.",
                },
                "cost_for_two": {
                    "type": ["integer", "null"],
                    "description": "INR digits from approx_cost(for two people); null if missing.",
                },
                "cost_tier": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Derived from cost_for_two vs DatasetConfig thresholds; MEDIUM if cost unknown.",
                },
                "votes": {
                    "type": ["integer", "null"],
                    "description": "From HF votes when integer-parseable.",
                },
                "raw_fields": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Subset of HF columns (url, address, rest_type, …); values may be string or other.",
                },
            },
        },
        "validation_rules": {
            "has_required_fields": "Truthy normalized name AND city (Phase 1 minimum bar).",
        },
    }


def default_schema_output_path() -> Path:
    return project_root() / "schemas" / "canonical_schema.json"


def write_canonical_schema(path: Path | None = None) -> Path:
    out = path or default_schema_output_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = build_canonical_schema_document()
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Write schemas/canonical_schema.json from code.")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: <repo>/schemas/canonical_schema.json)",
    )
    ns = p.parse_args(argv)
    written = write_canonical_schema(ns.output)
    print(str(written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
