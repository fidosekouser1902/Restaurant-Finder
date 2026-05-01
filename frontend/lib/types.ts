export type RecommendationItem = {
  id: string;
  name: string;
  city: string;
  neighborhood: string;
  cuisines: string[];
  rating: number | null;
  cost_for_two: number | null;
  cost_tier: string;
  explanation: string;
  rank: number;
};

export type RecommendResponse = {
  recommendations: RecommendationItem[];
  summary: string | null;
  model_id: string;
  prompt_version: string;
  fallback_used: boolean;
  relaxations_applied: string[];
  truncated: boolean;
  filter_funnel: {
    total_after_location: number;
    total_after_cuisine: number;
    total_after_budget: number;
    total_after_rating: number;
  };
};
