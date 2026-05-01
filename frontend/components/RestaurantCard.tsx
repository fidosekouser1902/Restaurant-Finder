import type { RecommendationItem } from "@/lib/types";

function hashHue(name: string): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h << 5) - h + name.charCodeAt(i);
  return Math.abs(h) % 360;
}

type Props = { item: RecommendationItem };

export function RestaurantCard({ item }: Props) {
  const hue = hashHue(item.name);
  const area = [item.neighborhood, item.city].filter(Boolean).join(", ");
  const cost =
    item.cost_for_two != null
      ? `₹${item.cost_for_two.toLocaleString("en-IN")} for two`
      : "—";

  return (
    <article className="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm transition hover:shadow-md">
      <div
        className="relative h-44 w-full"
        style={{
          background: `linear-gradient(135deg, hsl(${hue}, 45%, 42%) 0%, hsl(${(hue + 40) % 360}, 50%, 28%) 100%)`,
        }}
      >
        <span className="absolute right-3 top-3 rounded-md bg-white/95 px-2 py-1 text-xs font-semibold text-neutral-800 shadow">
          ★ {item.rating != null ? item.rating.toFixed(1) : "—"}
        </span>
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-lg font-bold text-neutral-900">{item.name}</h3>
          <span className="shrink-0 text-sm font-semibold text-brand">{cost}</span>
        </div>
        <p className="mt-1 text-sm text-neutral-500">{area}</p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {item.cuisines.slice(0, 6).map((c) => (
            <span
              key={c}
              className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600"
            >
              {c}
            </span>
          ))}
        </div>
        <div className="mt-4 rounded-xl bg-brand-muted/80 px-3 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand">✨ AI insight</p>
          <p className="mt-1 text-sm leading-relaxed text-neutral-800">{item.explanation}</p>
        </div>
      </div>
    </article>
  );
}
