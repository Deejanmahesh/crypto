export interface Market {
  coingecko_id: string;
  symbol: string;
  name: string;
  market_cap_rank: number | null;
  price: number | null;
  volume: number | null;
  timestamp: string | null;
}

export interface Snapshot {
  price: number;
  volume: number;
  timestamp: string;
}

export interface History {
  symbol: string;
  count: number;
  snapshots: Snapshot[];
}

export interface AnalyticsItem {
  symbol: string;
  name: string;
  latest_price: number | null;
  latest_volume: number | null;
  price_change_pct: number | null;
  volume_change_pct: number | null;
  momentum: number | null;
  rank: number | null;
}

export interface AnalyticsResponse {
  window: number;
  generated_at: string;
  items: AnalyticsItem[];
}

export interface StrategyResult {
  symbol: string;
  strategy_name: string;
  signal: "BUY" | "SELL" | "HOLD";
  params: Record<string, unknown>;
  details: Record<string, unknown>;
  created_at: string;
}

export interface StrategyRunResponse {
  strategy: string;
  results: StrategyResult[];
}
