"""
Streamlit entrypoint for Streamlit Community Cloud.

Main file path to enter in the Cloud UI: ``streamlit_app.py`` (repo root).
"""

from __future__ import annotations

import os
from typing import Tuple

import streamlit as st

from recommender.common.errors import PreferenceValidationError
from recommender.common.models import RestaurantRecord
from recommender.phase2.filter_engine import FilterConfig
from recommender.phase4.service import parse_preferences_safe, run_recommendation


def _filter_config_from_env() -> FilterConfig:
    """Mirror ``recommender.phase4.app`` without importing FastAPI (lighter Streamlit deploy)."""

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
    seen = {
        r.neighborhood.strip()
        for r in corpus
        if getattr(r, "neighborhood", None) and str(r.neighborhood).strip()
    }
    return sorted(seen, key=str.lower)


@st.cache_resource(show_spinner="Loading restaurant dataset…")
def _load_corpus():
    from recommender.phase1.config import DatasetConfig
    from recommender.phase1.loader import materialize_restaurants

    cfg = DatasetConfig.from_env()
    rows = materialize_restaurants(cfg)
    return tuple(rows), cfg


def _parse_cuisines(raw: str) -> list[str]:
    return [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]


def main() -> None:
    st.set_page_config(page_title="Restaurant Finder", layout="wide")
    st.title("Restaurant Finder")
    st.caption("Filter + AI recommendations (same pipeline as Phase 4 API).")

    corpus, _ds_cfg = _load_corpus()
    localities = distinct_sorted_localities(corpus)
    filt = _filter_config_from_env()

    with st.sidebar:
        st.header("Preferences")
        loc_options = ["(Any locality)"] + localities
        loc_label = st.selectbox("Locality", options=loc_options, index=0)
        location = None if loc_label == "(Any locality)" else loc_label

        budget_for_two_inr = st.number_input(
            "Max budget (₹ for two)",
            min_value=1,
            max_value=1_000_000,
            value=1500,
            step=100,
        )
        cuisines_raw = st.text_input(
            "Cuisines (comma-separated; empty = any)",
            value="",
        )
        min_rating = st.slider("Minimum rating", 0.0, 5.0, 3.5, 0.1)
        extras = st.text_area("Extras (optional)", value="", height=68)
        top_k = st.number_input(
            "Number of recommendations",
            min_value=1,
            max_value=12,
            value=10,
            step=1,
            help="Omit uses RECOMMENDER_TOP_K from env when you leave as default; here we always send this value.",
        )

        go = st.button("Recommend", type="primary")

    if not go:
        st.info(f"Corpus loaded: **{len(corpus):,}** restaurants. Set preferences and click **Recommend**.")
        return

    body = {
        "location": location,
        "budget_for_two_inr": int(budget_for_two_inr),
        "cuisines": _parse_cuisines(cuisines_raw),
        "min_rating": float(min_rating),
        "extras": extras or "",
    }

    try:
        prefs = parse_preferences_safe(body)
    except PreferenceValidationError as e:
        st.error(str(e))
        return

    with st.spinner("Filtering and ranking…"):
        response, _fr = run_recommendation(
            prefs,
            corpus,
            filter_config=filt,
            load_env_file=True,
            top_k=int(top_k),
        )

    if response.fallback_used:
        st.warning("LLM fallback was used (missing key, error, or parse issue). Results are still grounded in the dataset.")

    if response.summary:
        st.subheader("Summary")
        st.write(response.summary)

    st.subheader("Recommendations")
    for r in response.recommendations:
        with st.expander(f"#{r.rank} — {r.name}", expanded=r.rank <= 3):
            st.markdown(
                f"**Area:** {r.neighborhood or '—'} · **City:** {r.city}  \n"
                f"**Rating:** {r.rating if r.rating is not None else '—'} · "
                f"**Cost for two:** ₹{r.cost_for_two} ({r.cost_tier})  \n"
                f"**Cuisines:** {', '.join(r.cuisines) or '—'}"
            )
            st.markdown(r.explanation)

    with st.expander("Metadata"):
        st.json(
            {
                "model_id": response.model_id,
                "prompt_version": response.prompt_version,
                "relaxations_applied": response.relaxations_applied,
                "truncated": response.truncated,
                "filter_funnel": response.filter_funnel.model_dump(),
            }
        )


if __name__ == "__main__":
    main()
