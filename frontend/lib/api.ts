import type { RecommendResponse } from "./types";

const base = () =>
  (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export async function fetchLocalities(): Promise<string[]> {
  const res = await fetch(`${base()}/api/v1/localities`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load localities");
  const data = (await res.json()) as { localities: string[] };
  return data.localities ?? [];
}

export async function fetchHealth(): Promise<{ corpus_size: number }> {
  const res = await fetch(`${base()}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load health");
  return res.json();
}

export type RecommendBody = {
  location: string | null;
  budget_for_two_inr: number;
  cuisines: string[];
  min_rating: number;
  extras: string;
  /** Ranked picks to return (API default from server; max 12). */
  top_k?: number;
};

export async function postRecommend(body: RecommendBody): Promise<RecommendResponse> {
  const res = await fetch(`${base()}/api/v1/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* ignore */
  }
  if (!res.ok) {
    const raw =
      typeof data === "object" && data !== null && "detail" in data
        ? (data as { detail: unknown }).detail
        : text || res.statusText;
    let detail: string;
    if (typeof raw === "string") detail = raw;
    else if (Array.isArray(raw))
      detail = raw
        .map((x) =>
          typeof x === "object" && x !== null && "msg" in x
            ? String((x as { msg: string }).msg)
            : JSON.stringify(x)
        )
        .join("; ");
    else detail = JSON.stringify(raw);
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return data as RecommendResponse;
}
