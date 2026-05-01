"""Phase 4 — FastAPI application shell (corpus lifecycle + ``POST /api/v1/recommend``)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from recommender.common.errors import PreferenceValidationError
from recommender.common.models import RestaurantRecord
from recommender.phase1.config import DatasetConfig
from recommender.phase1.loader import materialize_restaurants
from recommender.phase2.filter_engine import FilterConfig
from recommender.phase3.client import ChatCompleter
from recommender.phase4.schemas import HealthResponse, LocalitiesResponse, RecommendRequest, RecommendResponse
from recommender.phase4.service import parse_preferences_safe, run_recommendation

logger = logging.getLogger(__name__)

_PHASE4_DIR = Path(__file__).resolve().parent
_UI_INDEX = _PHASE4_DIR / "web" / "index.html"


def _filter_config_from_env() -> FilterConfig:
    def _i(name: str, default: int) -> int:
        raw = os.environ.get(name)
        if raw is None or raw.strip() == "":
            return default
        return int(raw)

    def _f(name: str, default: float) -> float:
        raw = os.environ.get(name)
        if raw is None or raw.strip() == "":
            return default
        return float(raw)

    return FilterConfig(
        k_min=_i("RECOMMENDER_FILTER_K_MIN", 5),
        k_target=_i("RECOMMENDER_FILTER_K_TARGET", 20),
        max_candidates=_i("RECOMMENDER_MAX_CANDIDATES", 30),
        min_rating_floor=_f("RECOMMENDER_MIN_RATING_FLOOR", 2.5),
        rating_relax_step=_f("RECOMMENDER_RATING_RELAX_STEP", 0.5),
        budget_relax_step_inr=_i("RECOMMENDER_BUDGET_RELAX_STEP_INR", 400),
        budget_relax_ceiling_inr=_i("RECOMMENDER_BUDGET_RELAX_CEILING_INR", 250_000),
    )


def distinct_sorted_localities(corpus: Tuple[RestaurantRecord, ...]) -> list[str]:
    """Unique ``neighborhood`` values (dataset localities), case-insensitive sort."""
    seen = {
        r.neighborhood.strip()
        for r in corpus
        if getattr(r, "neighborhood", None) and str(r.neighborhood).strip()
    }
    return sorted(seen, key=str.lower)


def _cors_origins_from_env() -> list[str]:
    raw = os.environ.get("RECOMMENDER_CORS_ORIGINS", "*")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts if parts else ["*"]


def _add_cors(app: FastAPI) -> None:
    origins = _cors_origins_from_env()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def make_lifespan(
    *,
    corpus_override: Optional[Tuple[RestaurantRecord, ...]],
    dataset_config: DatasetConfig,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if corpus_override is not None:
            app.state.corpus = corpus_override
            logger.info("Using injected corpus (%s rows).", len(corpus_override))
        else:
            rows = materialize_restaurants(dataset_config)
            app.state.corpus = tuple(rows)
            logger.info("Loaded corpus (%s rows) from dataset config.", len(app.state.corpus))
        yield

    return lifespan


def _register_ui_routes(app: FastAPI, *, serve_ui: bool) -> None:
    if not serve_ui:
        return
    if not _UI_INDEX.is_file():
        logger.warning("Phase 4 UI missing at %s; GET / not registered.", _UI_INDEX)
        return

    @app.get("/", include_in_schema=False)
    def ui_home() -> FileResponse:
        return FileResponse(_UI_INDEX, media_type="text/html; charset=utf-8")


def create_app(
    *,
    corpus: Optional[Tuple[RestaurantRecord, ...]] = None,
    dataset_config: Optional[DatasetConfig] = None,
    filter_config: Optional[FilterConfig] = None,
    llm_client: Optional[ChatCompleter] = None,
    load_env_file: bool = True,
    enable_cors: bool = True,
    serve_ui: bool = True,
) -> FastAPI:
    """Build FastAPI app. Pass ``corpus`` in tests to avoid Hugging Face load."""
    ds_cfg = dataset_config or DatasetConfig.from_env()
    filt_cfg = filter_config or _filter_config_from_env()
    lifespan = make_lifespan(corpus_override=corpus, dataset_config=ds_cfg)

    app = FastAPI(
        title="Restaurant Recommender API",
        description="Phase 4 shell: Phase 2 filter + Phase 3 LLM recommendations.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.dataset_config = ds_cfg
    app.state.filter_config = filt_cfg
    app.state.llm_client = llm_client
    app.state.load_env_file = load_env_file

    if enable_cors:
        _add_cors(app)

    _register_ui_routes(app, serve_ui=serve_ui)

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        corpus_rows: Tuple[RestaurantRecord, ...] = app.state.corpus
        return HealthResponse(status="ok", corpus_size=len(corpus_rows))

    @app.get(
        "/api/v1/localities",
        response_model=LocalitiesResponse,
        tags=["meta"],
        summary="List distinct localities (neighborhoods) in the corpus",
    )
    def localities() -> LocalitiesResponse:
        corpus_rows: Tuple[RestaurantRecord, ...] = app.state.corpus
        return LocalitiesResponse(localities=distinct_sorted_localities(corpus_rows))

    @app.post(
        "/api/v1/recommend",
        response_model=RecommendResponse,
        tags=["recommend"],
        summary="Recommend restaurants",
    )
    def recommend_api(body: RecommendRequest) -> RecommendResponse:
        try:
            prefs = parse_preferences_safe(body.model_dump(exclude={"top_k"}))
        except PreferenceValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        try:
            corpus_rows: Tuple[RestaurantRecord, ...] = app.state.corpus
            response, _fr = run_recommendation(
                prefs,
                corpus_rows,
                filter_config=app.state.filter_config,
                llm_client=app.state.llm_client,
                load_env_file=app.state.load_env_file,
                top_k=body.top_k,
            )
            return response
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Unexpected error in recommend")
            raise HTTPException(status_code=500, detail="Internal server error.") from e

    return app
