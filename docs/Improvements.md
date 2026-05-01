# Improvements tracking

The following UX and contract changes were requested and are **implemented** in code, UI, and [phase-wise-architecture.md](./phase-wise-architecture.md):

1. **Locality dropdown** — The UI loads distinct **neighborhoods / localities** from **`GET /api/v1/localities`** and uses a `<select>` (with “Any locality”). The same string is sent as **`location`** in `POST /api/v1/recommend` and matched by Phase 2 substring rules (neighborhood, city, address).
2. **Numeric budget** — Users specify **`budget_for_two_inr`** (maximum approximate cost for two in INR). Phase 2 filters with `cost_for_two <= budget_for_two_inr` (rows without cost are excluded under that constraint). Relaxation raises this cap in steps (`increased_budget_cap_inr`) up to **`RECOMMENDER_BUDGET_RELAX_CEILING_INR`**. Legacy enum `budget: low|medium|high` on the API was removed in favour of this field.
3. **Prompt + optional cuisines** — Prompt template is **`v2`**: it sends `max_budget_inr_for_two`, describes optional/empty cuisines as “any cuisine”, and instructs the model to respect the INR ceiling in explanations. Empty **`cuisines`** continues to mean no cuisine filter in Phase 2.
4. **Recommendation list length** — Phase 3 previously defaulted to **`top_k = 5`** (via `GroqLLMConfig` / `RECOMMENDER_TOP_K`), so users often saw at most five picks. **Resolved:** default **`top_k` is 10**; **`POST /api/v1/recommend`** accepts **`top_k`** (1–**12**) on the JSON body so clients can choose how many ranked results to ask for; **`RECOMMENDER_TOP_K`** still sets the server default when the field is omitted (also capped at 12). UIs (embedded form + Next.js sidebar) expose the same control.

For API shapes and env vars, see **§2.2**, **§2.4**, **§3.2**, and **§4** in the architecture doc.

**Next.js:** An enhanced UI lives in **`frontend/`** (see **`Design/Zomato_ai_frontend_page_reference.png`** and **`frontend/README.md`**).
