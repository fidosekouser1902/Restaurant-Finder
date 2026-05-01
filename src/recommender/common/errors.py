"""Errors for ingestion, preferences, and corpus loading."""


class DatasetSchemaError(ValueError):
    """Raised when the Hugging Face table is missing columns required for Phase 1 mapping."""


class PreferenceValidationError(ValueError):
    """Raised when user preference JSON fails validation (Phase 2)."""
