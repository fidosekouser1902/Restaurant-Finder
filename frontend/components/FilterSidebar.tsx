"use client";

const CUISINE_OPTIONS = [
  { label: "North Indian", value: "north indian" },
  { label: "Chinese", value: "chinese" },
  { label: "Italian", value: "italian" },
  { label: "Continental", value: "continental" },
];

type Props = {
  localities: string[];
  locality: string;
  onLocality: (v: string) => void;
  budgetInr: number;
  onBudget: (v: number) => void;
  selectedCuisines: Set<string>;
  onToggleCuisine: (value: string) => void;
  minRating: number;
  onMinRating: (v: number) => void;
  extras: string;
  onExtras: (v: string) => void;
  topK: number;
  onTopK: (v: number) => void;
  loading: boolean;
  onSubmit: () => void;
};

export function FilterSidebar({
  localities,
  locality,
  onLocality,
  budgetInr,
  onBudget,
  selectedCuisines,
  onToggleCuisine,
  minRating,
  onMinRating,
  extras,
  onExtras,
  topK,
  onTopK,
  loading,
  onSubmit,
}: Props) {
  return (
    <aside className="w-full shrink-0 border-b border-neutral-200 bg-white p-5 shadow-sm md:w-80 md:border-b-0 md:border-r md:shadow-none lg:w-96">
      <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-neutral-500">
        Search filters
      </h2>

      <label className="mb-1 block text-sm font-medium text-neutral-800">Locality</label>
      <select
        value={locality}
        onChange={(e) => onLocality(e.target.value)}
        className="mb-5 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm outline-none ring-brand focus:ring-2"
      >
        <option value="">Any locality</option>
        {localities.map((loc) => (
          <option key={loc} value={loc}>
            {loc}
          </option>
        ))}
      </select>

      <label className="mb-1 block text-sm font-medium text-neutral-800">
        Budget for two (max ₹{budgetInr.toLocaleString("en-IN")})
      </label>
      <input
        type="range"
        min={200}
        max={5000}
        step={50}
        value={budgetInr}
        onChange={(e) => onBudget(Number(e.target.value))}
        className="mb-1 h-2 w-full cursor-pointer accent-brand"
      />
      <p className="mb-5 text-xs text-neutral-500">Slide to set your maximum approximate cost for two.</p>

      <label className="mb-2 block text-sm font-medium text-neutral-800">Cuisine</label>
      <div className="mb-5 flex flex-wrap gap-2">
        {CUISINE_OPTIONS.map(({ label, value }) => {
          const on = selectedCuisines.has(value);
          return (
            <button
              key={value}
              type="button"
              onClick={() => onToggleCuisine(value)}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                on
                  ? "border-brand bg-brand text-white"
                  : "border-neutral-200 bg-neutral-100 text-neutral-600 hover:border-neutral-300"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      <label className="mb-1 block text-sm font-medium text-neutral-800">
        Minimum rating ({minRating.toFixed(1)}+)
      </label>
      <input
        type="range"
        min={0}
        max={5}
        step={0.1}
        value={minRating}
        onChange={(e) => onMinRating(Number(e.target.value))}
        className="mb-5 h-2 w-full cursor-pointer accent-brand"
      />

      <label className="mb-1 block text-sm font-medium text-neutral-800">
        Number of recommendations (up to {topK})
      </label>
      <select
        value={topK}
        onChange={(e) => onTopK(Number(e.target.value))}
        className="mb-5 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm outline-none ring-brand focus:ring-2"
      >
        {[3, 5, 8, 10, 12].map((n) => (
          <option key={n} value={n}>
            {n} picks
          </option>
        ))}
      </select>

      <label className="mb-1 block text-sm font-medium text-neutral-800">Additional preferences</label>
      <textarea
        value={extras}
        onChange={(e) => onExtras(e.target.value)}
        rows={3}
        placeholder="e.g. romantic, family-friendly, live music"
        className="mb-5 w-full resize-none rounded-lg border border-neutral-200 px-3 py-2 text-sm outline-none ring-brand focus:ring-2"
      />

      <button
        type="button"
        disabled={loading}
        onClick={onSubmit}
        className="w-full rounded-lg bg-brand py-3 text-sm font-semibold text-white shadow transition hover:bg-brand-dark disabled:opacity-50"
      >
        {loading ? "Finding restaurants…" : "Get Recommendations"}
      </button>
    </aside>
  );
}
