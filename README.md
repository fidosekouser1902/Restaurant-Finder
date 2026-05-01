# Recommender

Phase 1 loads and normalizes the [Zomato restaurant dataset](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) from Hugging Face into canonical `RestaurantRecord` rows.

## Setup

```bash
python3 -m pip install -e ".[dev]"
```

First download can take several minutes (**the on-disk footprint is usually on the order of ~1 GB** under this repo’s cache once built). Optional: set `HF_TOKEN` for higher Hugging Face Hub rate limits.

**Data stays inside this repo:** importing **`recommender.phase1.loader`** (or `import recommender` then using `load_dataset`) configures **`HF_HOME`** with `setdefault` **before** Hugging Face pins cache paths, so Hub blobs and Arrow tables live under **`<repo>/.cache/huggingface/`** (`hub/`, `datasets/`, …). That tree is **gitignored**. If **`HF_HOME`** is already exported in your environment, it is left unchanged. Set **`RECOMMENDER_USE_PROJECT_CACHE=0`** to keep the libraries’ default **`~/.cache/huggingface`** instead. Avoid **`import datasets`** ahead of Phase 1 loader if you rely on project-local caches. Optional normalized parquet path helper: **`recommender.common.paths.default_normalized_parquet_path()`**.

## Phase 1 usage

```python
from recommender import DatasetConfig, load_dataset, validate_corpus, get_schema_version

config = DatasetConfig(max_rows=100)  # omit max_rows for full ~51k rows
for restaurant in load_dataset(config):
    print(restaurant.name, restaurant.city, restaurant.cuisines)
```

## Phase 2 — deterministic filters

```python
from recommender import (
    FilterConfig,
    UserPreferences,
    filter_restaurants,
    load_dataset,
    pack_candidates_for_llm,
    DatasetConfig,
)

prefs = UserPreferences.from_mapping({
    "location": "Bangalore",
    "budget_for_two_inr": 1000,
    "cuisines": ["Chinese"],
    "min_rating": 4.0,
    "extras": "quick service",
})
corpus = list(load_dataset(DatasetConfig(max_rows=8000)))  # omit max_rows for full ~51k
result = filter_restaurants(prefs, corpus, config=FilterConfig(max_candidates=25))
payload = pack_candidates_for_llm(result.candidates)  # Phase 3 prompt input
```

## Phase 3 — Groq LLM (`recommend`)

Copy **`.env.example`** to **`.env`** and set **`GROQ_API_KEY`** (see [Groq console](https://console.groq.com/)). Phase 3 loads `.env` automatically when calling `recommend()` unless `load_env_file=False`.

```python
from recommender import (
    DatasetConfig,
    FilterConfig,
    UserPreferences,
    filter_restaurants,
    load_dataset,
    recommend,
)

corpus = list(load_dataset(DatasetConfig(max_rows=5000)))
prefs = UserPreferences.from_mapping({
    "location": "Bangalore",
    "budget_for_two_inr": 1200,
    "cuisines": ["Italian"],
    "min_rating": 4.0,
})
shortlist = filter_restaurants(prefs, corpus, config=FilterConfig(max_candidates=20))
rec = recommend(prefs, shortlist.candidates, top_k=10)
for item in rec.items:
    print(item.rank, item.restaurant.name, item.explanation)
```

Without an API key (or on LLM/parse errors), **`recommend`** returns a **deterministic fallback** (`fallback_used=True`). Tests use an injected mock client; set **`GROQ_API_KEY`** to run the optional live pytest `test_recommend_live_groq_smoke`.

## Phase 4 — HTTP API and browser UI

Install API extras (included in **`[dev]`**):

```bash
python3 -m pip install -e ".[api]"
```

Start the server (loads the full dataset on first startup unless you cap rows via env):

```bash
python3 -m recommender.phase4.main
# or: recommender-api
```

Open **http://127.0.0.1:8000/** for the form UI (locality dropdown from **`GET /api/v1/localities`**, numeric max budget ₹ for two, optional cuisines). Use **http://127.0.0.1:8000/docs** for OpenAPI. Set **`GROQ_API_KEY`** in `.env` at the repo root for Groq-backed explanations; otherwise the UI still works using the deterministic fallback.

For faster startup while iterating, set e.g. **`RECOMMENDER_MAX_ROWS=3000`** before starting the server.

### Next.js frontend (CraveAI-style)

The **`frontend/`** directory is a **Next.js 14** + **Tailwind** SPA aligned with **`Design/Zomato_ai_frontend_page_reference.png`**. It talks to the same FastAPI (`NEXT_PUBLIC_API_BASE_URL`, default `http://127.0.0.1:8000`).

```bash
# Terminal 1 — API (allow Next dev origin)
export RECOMMENDER_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
python3 -m recommender.phase4.main

# Terminal 2 — UI
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000**. See **`frontend/README.md`** for details.

**Environment-driven config:** `DatasetConfig.from_env()` merges settings from optional env vars below; explicit kwargs override env.

Optional **normalized Parquet cache** (faster restarts; built on first full non-streaming load):

```python
config = DatasetConfig(
    normalized_cache_path=".cache/zomato_normalized.parquet",
    prefer_cache=True,
)
```

**Streaming (`streaming=True`)** avoids materializing the full split in RAM. It **does not** write a Parquet cache; use non-streaming once to produce the cache file, then `prefer_cache=True`.

**Strict schema (`strict_columns=True`):** raises `DatasetSchemaError` if Hugging Face column names omit any field expected by the Phase 1 mapper (default is log + continue).

## Validate Phase 1 (real dataset)

Smoke-check ingestion and optionally enforce minimum valid-row count (`has_required_fields()` requires non-empty normalized `name` and `city`):

```bash
python3 -m recommender.phase1.validate --max-rows 2000 --min-valid 1000
# After editable install:
recommender-validate-phase1 --max-rows 2000 --min-valid 1000
```

Use `--streaming` for a streaming scan without loading the entire split into memory.

## Environment variables

| Variable | Purpose |
|---------|---------|
| `RECOMMENDER_DATASET_NAME` | Hugging Face dataset id (default: Zomato dataset above) |
| `RECOMMENDER_DATASET_REVISION` | Pin a Hub revision/commit |
| `RECOMMENDER_DATASET_SPLIT` | Split name (default `train`) |
| `RECOMMENDER_MAX_ROWS` | Cap rows (useful with `from_env()`) |
| `DATASET_CACHE_DIR` or `RECOMMENDER_DATASET_CACHE_DIR` | Hugging Face datasets Arrow cache dir |
| `RECOMMENDER_NORMALIZED_CACHE_PATH` | Path for normalized `.parquet` cache |
| `RECOMMENDER_PREFER_CACHE` | `1` / `true` / `yes` — read Parquet cache when meta matches |
| `RECOMMENDER_STREAMING` | `1` / `true` — default streaming in `from_env()` |
| `RECOMMENDER_STRICT_COLUMNS` | `1` / `true` — fail closed on incomplete Hub columns |
| `RECOMMENDER_USE_PROJECT_CACHE` | `0` / `false` — do **not** default `HF_HOME` to `./.cache/huggingface`; use Hub default `~/.cache` instead |
| `RECOMMENDER_COST_LOW_MAX_INR` | Upper bound INR for tier `low` (default 400) |
| `RECOMMENDER_COST_MEDIUM_MAX_INR` | Upper bound INR for tier `medium` (default 1000) |
| `GROQ_API_KEY` | Groq API key (Phase 3); also place in `.env` at repo root |
| `GROQ_MODEL` | Groq model id (default `llama-3.3-70b-versatile`) |
| `GROQ_BASE_URL` | OpenAI-compatible base URL (default Groq) |
| `GROQ_TEMPERATURE` / `GROQ_MAX_TOKENS` / `GROQ_MAX_RETRIES` | LLM call tuning |
| `RECOMMENDER_TOP_K` | Default number of ranked picks when `top_k` is omitted (`GroqLLMConfig.top_k`, default **10**; values above **12** are clamped to **12**) |
| `RECOMMENDER_BUDGET_RELAX_STEP_INR` | When relaxing filters, add this many INR to the user's max cost-for-two cap per step (default `400`) |
| `RECOMMENDER_BUDGET_RELAX_CEILING_INR` | Upper cap for budget relaxation (default `250000`) |

## Raw → canonical columns

Source train columns are documented in code as `RAW_COLUMN_MAP` (`recommender.phase1.schema`) — summary:

| HF column | Canonical / use |
|-----------|----------------|
| `name` | `RestaurantRecord.name` |
| `listed_in(city)` | `RestaurantRecord.city` (aliases e.g. Bengaluru → Bangalore) |
| `location` | `RestaurantRecord.neighborhood` |
| `cuisines` | `RestaurantRecord.cuisines` (comma-split, lowercase) |
| `rate` | `RestaurantRecord.rating` (e.g. `4.1/5` → float) |
| `approx_cost(for two people)` | `RestaurantRecord.cost_for_two`, `cost_tier` |
| `votes` | `RestaurantRecord.votes` |
| Other (`url`, `rest_type`, `reviews_list`, …) | `RestaurantRecord.raw_fields` |

Stable `RestaurantRecord.id` is a truncated SHA-256 over name + city + neighborhood + cuisines.

## Canonical schema (JSON)

Machine-readable mapping + [JSON Schema](https://json-schema.org/) for `RestaurantRecord` is stored at **`schemas/canonical_schema.json`**. Regenerate after changing `recommender.schema` or `RestaurantRecord`:

```bash
python3 -m recommender.phase1.export_schema
# or: recommender-export-canonical-schema
```

## Tests

```bash
python3 -m pytest
```
