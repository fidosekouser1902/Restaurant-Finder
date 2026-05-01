"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchHealth, fetchLocalities, postRecommend } from "@/lib/api";
import type { RecommendResponse } from "@/lib/types";
import { FilterSidebar } from "@/components/FilterSidebar";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { ResultsPanel } from "@/components/ResultsPanel";

export default function HomePage() {
  const [localities, setLocalities] = useState<string[]>([]);
  const [corpusHint, setCorpusHint] = useState<string>("");
  const [locality, setLocality] = useState("");
  const [budgetInr, setBudgetInr] = useState(1000);
  const [selectedCuisines, setSelectedCuisines] = useState<Set<string>>(new Set());
  const [minRating, setMinRating] = useState(3.5);
  const [extras, setExtras] = useState("");
  const [topK, setTopK] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<RecommendResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [locs, health] = await Promise.all([fetchLocalities(), fetchHealth()]);
        if (!cancelled) {
          setLocalities(locs);
          setCorpusHint(`${health.corpus_size.toLocaleString("en-IN")} restaurants in API corpus`);
        }
      } catch {
        if (!cancelled) setCorpusHint("Could not reach API — start FastAPI on port 8000");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleCuisine = useCallback((value: string) => {
    setSelectedCuisines((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  }, []);

  const handleSubmit = useCallback(async () => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await postRecommend({
        location: locality.trim() || null,
        budget_for_two_inr: budgetInr,
        cuisines: Array.from(selectedCuisines),
        min_rating: minRating,
        extras: extras.trim(),
        top_k: topK,
      });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [locality, budgetInr, selectedCuisines, minRating, extras, topK]);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <Hero />
      <p className="border-b border-neutral-100 bg-white px-4 py-2 text-center text-xs text-neutral-500 md:px-6">
        {corpusHint}
      </p>
      <div className="flex flex-1 flex-col md:flex-row">
        <FilterSidebar
          localities={localities}
          locality={locality}
          onLocality={setLocality}
          budgetInr={budgetInr}
          onBudget={setBudgetInr}
          selectedCuisines={selectedCuisines}
          onToggleCuisine={toggleCuisine}
          minRating={minRating}
          onMinRating={setMinRating}
          extras={extras}
          onExtras={setExtras}
          topK={topK}
          onTopK={setTopK}
          loading={loading}
          onSubmit={handleSubmit}
        />
        <ResultsPanel loading={loading} error={error} data={data} />
      </div>
      <Footer />
    </div>
  );
}
