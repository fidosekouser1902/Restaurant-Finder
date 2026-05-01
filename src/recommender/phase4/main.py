"""Run the Phase 4 API with Uvicorn (``python -m recommender.phase4.main``)."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("RECOMMENDER_API_HOST", "127.0.0.1")
    port = int(os.environ.get("RECOMMENDER_API_PORT", "8000"))
    reload = os.environ.get("RECOMMENDER_API_RELOAD", "").lower() in ("1", "true", "yes")
    uvicorn.run(
        "recommender.phase4.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
