from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from recommender.common.errors import DatasetSchemaError
from recommender.common.models import CostTier, RestaurantRecord
from recommender.common.paths import project_hf_home
from recommender.phase1.config import DatasetConfig
from recommender.phase1.normalize import row_to_restaurant
from recommender.phase1.schema import SCHEMA_VERSION

logger = logging.getLogger(__name__)


def _use_project_hf_home() -> bool:
    """When True (default), set ``HF_HOME`` to ``<repo>/.cache/huggingface`` if unset."""
    raw = os.environ.get("RECOMMENDER_USE_PROJECT_CACHE", "1")
    return raw.strip().lower() not in ("0", "false", "no", "off")


def ensure_project_huggingface_home() -> None:
    """Pin Hugging Face downloads to **this repo** via ``HF_HOME`` (respects existing ``HF_HOME``).

    Must run **before** importing ``datasets`` / ``huggingface_hub`` so caches resolve under the project.
    This module calls it once at import time; you may call again (idempotent).

    Controlled by ``RECOMMENDER_USE_PROJECT_CACHE`` (default ``1``). Disable with ``0``/``false``.
    """
    if not _use_project_hf_home():
        return
    home = project_hf_home()
    home.mkdir(parents=True, exist_ok=True)
    before = os.environ.get("HF_HOME")
    chosen = os.environ.setdefault("HF_HOME", str(home))
    if before is None:
        if not logging.root.handlers:
            logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logger.info(
            "Project-local Hugging Face cache: HF_HOME=%s "
            "(datasets in …/datasets, hub in …/hub). RECOMMENDER_USE_PROJECT_CACHE=0 uses ~/.cache.",
            chosen,
        )


# Set HF_HOME before huggingface_hub constants are snapshot at first import.
ensure_project_huggingface_home()

from datasets import Dataset, load_dataset as hf_load_dataset

# Columns expected from ``ManikaSaini/zomato-restaurant-recommendation`` train split.
_EXPECTED_HF_COLUMNS = frozenset(
    {
        "url",
        "address",
        "name",
        "online_order",
        "book_table",
        "rate",
        "votes",
        "phone",
        "location",
        "rest_type",
        "dish_liked",
        "cuisines",
        "approx_cost(for two people)",
        "reviews_list",
        "menu_item",
        "listed_in(type)",
        "listed_in(city)",
    }
)


def load_dataset(config: DatasetConfig) -> Iterator[RestaurantRecord]:
    """Load Hugging Face Zomato dataset and yield normalized ``RestaurantRecord`` rows.

    If ``config.normalized_cache_path`` is set and ``config.prefer_cache`` is True,
    reads Parquet when a sidecar ``.meta.json`` matches ``SCHEMA_VERSION`` and dataset revision.

    After a **non-streaming** Hugging Face load, writes Parquet when ``normalized_cache_path`` is set.

    ``streaming=True`` reads the Hub iterable without loading the entire split into memory; Parquet cache
    is **not** written in streaming mode (set ``streaming=False`` to build ``.parquet`` in one pass).
    """
    cache_path = config.normalized_cache_path
    if cache_path and config.prefer_cache:
        cached = _try_load_parquet_cache(Path(cache_path), config)
        if cached is not None:
            logger.info("Loaded %s normalized rows from cache %s", len(cached), cache_path)
            yield from cached
            return

    if config.streaming:
        if cache_path and not config.prefer_cache:
            logger.warning(
                "streaming=True skips writing normalized Parquet (%s); set prefer_cache to read "
                "an existing cache, or streaming=False to materialize and write.",
                cache_path,
            )
        yield from _stream_from_huggingface(config)
        return

    rows = _load_from_huggingface(config)
    if cache_path:
        _write_parquet_cache(Path(cache_path), rows, config)
    yield from rows


def materialize_restaurants(config: DatasetConfig) -> List[RestaurantRecord]:
    """Load all configured rows into a list (avoid for production-scale unless memory allows)."""
    return list(load_dataset(config))


def _meta_path(parquet_path: Path) -> Path:
    return parquet_path.with_suffix(parquet_path.suffix + ".meta.json")


def _try_load_parquet_cache(parquet_path: Path, config: DatasetConfig) -> Optional[List[RestaurantRecord]]:
    meta_file = _meta_path(parquet_path)
    if not parquet_path.is_file() or not meta_file.is_file():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if meta.get("schema_version") != SCHEMA_VERSION:
        return None
    if meta.get("dataset_name") != config.dataset_name:
        return None
    if config.revision is not None and meta.get("revision") != config.revision:
        return None
    ds = hf_load_dataset("parquet", data_files=str(parquet_path), split="train")
    return [_dict_to_record(dict(row)) for row in ds]


def _write_parquet_cache(parquet_path: Path, rows: List[RestaurantRecord], config: DatasetConfig) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    records = [_record_to_dict(r) for r in rows]
    Dataset.from_list(records).to_parquet(str(parquet_path))
    meta = {
        "schema_version": SCHEMA_VERSION,
        "dataset_name": config.dataset_name,
        "revision": config.revision,
        "row_count": len(rows),
    }
    _meta_path(parquet_path).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Wrote normalized cache %s (%s rows)", parquet_path, len(rows))


def _record_to_dict(r: RestaurantRecord) -> Dict[str, Any]:
    return {
        "id": r.id,
        "name": r.name,
        "city": r.city,
        "neighborhood": r.neighborhood,
        "cuisines_json": json.dumps(r.cuisines),
        "rating": r.rating,
        "cost_for_two": r.cost_for_two,
        "cost_tier": r.cost_tier.value,
        "votes": r.votes,
        "raw_fields_json": json.dumps(r.raw_fields, default=str),
    }


def _dict_to_record(d: Dict[str, Any]) -> RestaurantRecord:
    cuisines = json.loads(d["cuisines_json"])
    raw_fields = json.loads(d["raw_fields_json"])
    return RestaurantRecord(
        id=d["id"],
        name=d["name"],
        city=d["city"],
        neighborhood=d["neighborhood"],
        cuisines=cuisines,
        rating=d.get("rating"),
        cost_for_two=d.get("cost_for_two"),
        cost_tier=CostTier(d["cost_tier"]),
        votes=d.get("votes"),
        raw_fields=raw_fields,
    )


def _column_names_from_dataset(ds: Any) -> Optional[List[str]]:
    cols = getattr(ds, "column_names", None)
    if cols:
        return list(cols)
    features = getattr(ds, "features", None)
    if features is not None:
        try:
            return list(features.keys())
        except AttributeError:
            pass
    return None


def _validate_columns(columns: Optional[List[str]], strict: bool) -> None:
    if not columns:
        return
    keyset = set(columns)
    missing = _EXPECTED_HF_COLUMNS - keyset
    if not missing:
        return
    msg = (
        "Dataset columns missing vs expected Phase 1 schema "
        f"(missing={sorted(missing)}); update recommender.phase1.loader._EXPECTED_HF_COLUMNS or RAW_COLUMN_MAP."
    )
    if strict:
        raise DatasetSchemaError(msg)
    logger.warning("%s Mapping may fail for some rows.", msg)


def _hf_load_kw(config: DatasetConfig, streaming: bool) -> Dict[str, Any]:
    kw: Dict[str, Any] = {
        "split": config.split,
        "trust_remote_code": config.trust_remote_code,
        "streaming": streaming,
    }
    if config.revision is not None:
        kw["revision"] = config.revision
    if config.cache_dir is not None:
        kw["cache_dir"] = config.cache_dir
    return kw


def _stream_from_huggingface(config: DatasetConfig) -> Iterator[RestaurantRecord]:
    ds = hf_load_dataset(config.dataset_name, **_hf_load_kw(config, streaming=True))
    _validate_columns(_column_names_from_dataset(ds), strict=config.strict_columns)

    limit = config.max_rows
    valid_count = 0
    seen = 0
    for row in ds:
        if limit is not None and seen >= limit:
            break
        raw = dict(row)
        rec = row_to_restaurant(raw, config)
        if rec.has_required_fields():
            valid_count += 1
        seen += 1
        yield rec

    logger.info(
        "Streamed %s rows from %s (split=%s); %s pass has_required_fields()",
        seen,
        config.dataset_name,
        config.split,
        valid_count,
    )


def _load_from_huggingface(config: DatasetConfig) -> List[RestaurantRecord]:
    ds = hf_load_dataset(config.dataset_name, **_hf_load_kw(config, streaming=False))
    _validate_columns(ds.column_names, strict=config.strict_columns)

    out: List[RestaurantRecord] = []
    limit = config.max_rows
    for i, row in enumerate(ds):
        if limit is not None and i >= limit:
            break
        raw = dict(row)
        rec = row_to_restaurant(raw, config)
        out.append(rec)

    valid = sum(1 for r in out if r.has_required_fields())
    logger.info(
        "Loaded %s rows from %s (split=%s); %s pass has_required_fields()",
        len(out),
        config.dataset_name,
        config.split,
        valid,
    )
    return out
