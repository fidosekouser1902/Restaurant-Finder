"""CLI and helpers to verify Phase 1 ingestion (counts, validation rules)."""

from __future__ import annotations

import argparse
import logging
import sys

from recommender.phase1.config import DatasetConfig
from recommender.phase1.loader import load_dataset
from recommender.phase1.schema import get_schema_version

logger = logging.getLogger(__name__)


def validate_corpus(
    config: DatasetConfig,
    *,
    min_valid: int = 0,
) -> dict:
    """Iterate the corpus under ``config`` and return totals.

    Raises ``AssertionError`` if ``min_valid`` > 0 and valid count is below it.
    """
    total = 0
    valid = 0
    for r in load_dataset(config):
        total += 1
        if r.has_required_fields():
            valid += 1

    stats = {
        "total_rows": total,
        "rows_passing_validation": valid,
        "schema_version": get_schema_version(),
    }
    if min_valid > 0 and valid < min_valid:
        raise AssertionError(
            f"Expected at least {min_valid} rows with has_required_fields(); got {valid} "
            f"(total_iterated={total})."
        )
    return stats


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Validate Phase 1 Zomato dataset ingestion.")
    p.add_argument(
        "--min-valid",
        type=int,
        default=0,
        help="Exit 1 if fewer rows pass has_required_fields() (e.g. 1000)",
    )
    p.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Maximum rows to scan (omit for full split)",
    )
    p.add_argument(
        "--streaming",
        action="store_true",
        help="Stream from Hub instead of loading the full split into memory",
    )
    ns = p.parse_args(argv)

    overrides: dict = {"streaming": ns.streaming}
    if ns.max_rows is not None:
        overrides["max_rows"] = ns.max_rows
    config = DatasetConfig.from_env(**overrides)
    logger.info(
        "Validating corpus dataset=%s split=%s streaming=%s max_rows=%s",
        config.dataset_name,
        config.split,
        config.streaming,
        config.max_rows,
    )
    try:
        stats = validate_corpus(config, min_valid=ns.min_valid)
    except AssertionError as e:
        logger.error("%s", e)
        return 1
    print(
        "schema_version={schema_version}\n"
        "total_rows={total_rows}\n"
        "rows_passing_validation={rows_passing_validation}".format(**stats),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
