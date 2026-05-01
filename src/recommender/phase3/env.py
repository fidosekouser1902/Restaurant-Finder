"""Load ``.env`` from the repository root when ``python-dotenv`` is available."""

from __future__ import annotations

from pathlib import Path


def load_dotenv_if_present(path: Path | None = None) -> bool:
    """Load env vars from ``path`` (default: ``<repo>/.env``). Returns True if file was loaded."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    target = path
    if target is None:
        from recommender.common.paths import project_root

        target = project_root() / ".env"
    if not target.is_file():
        return False
    load_dotenv(target)
    return True
