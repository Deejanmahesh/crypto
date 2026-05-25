import type {
  AnalyticsResponse,
  History,
  Market,
  StrategyResult,
  StrategyRunResponse,
} from "./types";

// The browser always talks to the host-exposed backend port, so this default
// works for both `npm run dev` and the docker-compose setup. Override with
// NEXT_PUBLIC_API_URL at build time if the backend lives elsewhere.
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  base: API_URL,

  getMarkets: () => getJSON<Market[]>("/markets"),

  getHistory: (symbol: string, limit = 200) =>
    getJSON<History>(`/history?symbol=${encodeURIComponent(symbol)}&limit=${limit}`),

  getAnalytics: (window = 24) =>
    getJSON<AnalyticsResponse>(`/analytics?window=${window}`),

  getStrategyResults: () => getJSON<StrategyResult[]>("/strategy/results?limit=100"),

  runStrategy: async (body: {
    strategy: string;
    symbols?: string[];
    params?: Record<string, unknown>;
  }): Promise<StrategyRunResponse> => {
    const res = await fetch(`${API_URL}/strategy/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Strategy run failed: ${res.status}`);
    return res.json();
  },
};
