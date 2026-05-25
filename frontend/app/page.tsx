"use client";

import { useCallback, useEffect, useState } from "react";
import MarketTable from "@/components/MarketTable";
import PriceChart from "@/components/PriceChart";
import AnalyticsTable from "@/components/AnalyticsTable";
import StrategyPanel from "@/components/StrategyPanel";
import { api } from "@/lib/api";
import type {
  AnalyticsItem,
  Market,
  Snapshot,
  StrategyResult,
} from "@/lib/types";

export default function Home() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsItem[]>([]);
  const [strategyResults, setStrategyResults] = useState<StrategyResult[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMarkets = useCallback(async () => {
    try {
      const data = await api.getMarkets();
      setMarkets(data);
      setSelected((cur) => cur ?? data[0]?.symbol ?? null);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const loadAnalytics = useCallback(async () => {
    try {
      const data = await api.getAnalytics(24);
      setAnalytics(data.items);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const loadStrategyResults = useCallback(async () => {
    try {
      setStrategyResults(await api.getStrategyResults());
    } catch {
      /* results may be empty before first run */
    }
  }, []);

  // Initial load + light polling so the dashboard reflects scheduled ingests.
  useEffect(() => {
    loadMarkets();
    loadAnalytics();
    loadStrategyResults();
    const id = setInterval(() => {
      loadMarkets();
      loadAnalytics();
    }, 30000);
    return () => clearInterval(id);
  }, [loadMarkets, loadAnalytics, loadStrategyResults]);

  // Load history whenever the selected asset changes.
  useEffect(() => {
    if (!selected) return;
    api
      .getHistory(selected, 200)
      .then((h) => setHistory(h.snapshots))
      .catch((e) => setError(String(e)));
  }, [selected]);

  const runStrategy = async (shortW: number, longW: number, mode: string) => {
    setRunning(true);
    setError(null);
    try {
      const res = await api.runStrategy({
        strategy: "ma_crossover",
        params: { short_window: shortW, long_window: longW, mode },
      });
      setStrategyResults(res.results);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold">Crypto Market Data & Analytics</h1>
        <p className="mt-1 text-sm text-slate-400">
          Live data from CoinGecko · analytics &amp; rule-based MA-crossover signals
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
          {error}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-lg font-semibold">Markets</h2>
          <MarketTable markets={markets} selected={selected} onSelect={setSelected} />
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold">
            {selected ? `${selected} charts` : "Charts"}
          </h2>
          <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-4">
            <PriceChart symbol={selected ?? ""} snapshots={history} />
          </div>
        </section>
      </div>

      <section className="mt-10">
        <h2 className="mb-3 text-lg font-semibold">Analytics</h2>
        <p className="mb-3 text-xs text-slate-500">
          Price / volume change, momentum and ranking over the last 24 snapshots.
        </p>
        <AnalyticsTable items={analytics} />
      </section>

      <section className="mt-10">
        <h2 className="mb-3 text-lg font-semibold">Strategy signals</h2>
        <StrategyPanel
          results={strategyResults}
          onRun={runStrategy}
          running={running}
        />
      </section>

      <footer className="mt-12 border-t border-slate-800 pt-4 text-center text-xs text-slate-600">
        API: {api.base}
      </footer>
    </main>
  );
}
