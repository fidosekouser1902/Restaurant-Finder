"use client";

import type { RecommendResponse } from "@/lib/types";
import { RestaurantCard } from "./RestaurantCard";

type Props = {
  loading: boolean;
  error: string | null;
  data: RecommendResponse | null;
};

export function ResultsPanel({ loading, error, data }: Props) {
  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-neutral-50/80 p-4 md:p-6 lg:p-8">
      {loading && (
        <div className="mb-6 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-neutral-200 bg-white py-12 text-center">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          <p className="mt-4 text-sm font-medium text-neutral-700">
            Finding the best restaurants for you…
          </p>
          <p className="mt-1 max-w-md text-xs text-neutral-500">
            Our AI is analyzing your filters and the shortlist from the dataset.
          </p>
        </div>
      )}

      {error && !loading && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {!loading && data?.summary && (
        <p className="mb-6 text-center text-sm text-neutral-600 md:text-left">{data.summary}</p>
      )}

      {!loading && data && (
        <div className="mb-4 flex flex-wrap gap-2 text-xs text-neutral-500">
          {data.fallback_used && (
            <span className="rounded-full bg-amber-100 px-2 py-1 text-amber-900">Deterministic fallback</span>
          )}
          {!data.fallback_used && (
            <span className="rounded-full bg-emerald-100 px-2 py-1 text-emerald-900">LLM ranking</span>
          )}
          {data.relaxations_applied.length > 0 && (
            <span className="rounded-full bg-neutral-200 px-2 py-1">
              Relaxations: {data.relaxations_applied.join(", ")}
            </span>
          )}
        </div>
      )}

      {!loading && data && data.recommendations.length === 0 && (
        <p className="rounded-xl bg-white p-8 text-center text-sm text-neutral-600 shadow-sm">
          No restaurants matched. Try widening budget, lowering minimum rating, or choosing Any locality.
        </p>
      )}

      {!loading && data && data.recommendations.length > 0 && (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {data.recommendations.map((item) => (
            <RestaurantCard key={item.id + item.rank} item={item} />
          ))}
        </div>
      )}
    </main>
  );
}
