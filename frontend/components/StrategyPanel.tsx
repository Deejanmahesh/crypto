"use client";

import { useState } from "react";
import type { StrategyResult } from "@/lib/types";
import { signalColor } from "@/lib/format";

export default function StrategyPanel({
  results,
  onRun,
  running,
}: {
  results: StrategyResult[];
  onRun: (shortW: number, longW: number, mode: string) => void;
  running: boolean;
}) {
  const [shortW, setShortW] = useState(7);
  const [longW, setLongW] = useState(21);
  const [mode, setMode] = useState("state");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-800 bg-slate-900/50 p-4">
        <label className="flex flex-col text-xs text-slate-400">
          Short MA
          <input
            type="number"
            min={1}
            value={shortW}
            onChange={(e) => setShortW(Number(e.target.value))}
            className="mt-1 w-20 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
          />
        </label>
        <label className="flex flex-col text-xs text-slate-400">
          Long MA
          <input
            type="number"
            min={2}
            value={longW}
            onChange={(e) => setLongW(Number(e.target.value))}
            className="mt-1 w-20 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
          />
        </label>
        <label className="flex flex-col text-xs text-slate-400">
          Mode
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="mt-1 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
          >
            <option value="state">state</option>
            <option value="crossover">crossover</option>
          </select>
        </label>
        <button
          onClick={() => onRun(shortW, longW, mode)}
          disabled={running}
          className="ml-auto rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-500 disabled:opacity-50"
        >
          {running ? "Running…" : "Run strategy"}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {results.map((r, i) => (
          <div
            key={`${r.symbol}-${i}`}
            className="rounded-lg border border-slate-800 bg-slate-900/50 p-3"
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold">{r.symbol}</span>
              <span
                className={`rounded border px-2 py-0.5 text-xs font-medium ${signalColor(
                  r.signal
                )}`}
              >
                {r.signal}
              </span>
            </div>
            {typeof r.details?.spread_pct === "number" && (
              <p className="mt-2 text-xs text-slate-500">
                spread {(r.details.spread_pct as number).toFixed(2)}%
              </p>
            )}
            {r.details?.reason === "insufficient_data" && (
              <p className="mt-2 text-xs text-slate-500">insufficient data</p>
            )}
          </div>
        ))}
        {results.length === 0 && (
          <p className="col-span-full py-4 text-center text-sm text-slate-500">
            No strategy results yet. Click “Run strategy”.
          </p>
        )}
      </div>
    </div>
  );
}
