"use client";

import type { Market } from "@/lib/types";
import { fmtCompact, fmtUsd } from "@/lib/format";

export default function MarketTable({
  markets,
  selected,
  onSelect,
}: {
  markets: Market[];
  selected: string | null;
  onSelect: (symbol: string) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-sm">
        <thead className="bg-slate-900 text-slate-400">
          <tr>
            <th className="px-3 py-2 text-left">#</th>
            <th className="px-3 py-2 text-left">Asset</th>
            <th className="px-3 py-2 text-right">Price</th>
            <th className="px-3 py-2 text-right">Volume (24h)</th>
          </tr>
        </thead>
        <tbody>
          {markets.map((m) => {
            const isSel = m.symbol === selected;
            return (
              <tr
                key={m.coingecko_id}
                onClick={() => onSelect(m.symbol)}
                className={`cursor-pointer border-t border-slate-800 transition-colors ${
                  isSel ? "bg-sky-500/10" : "hover:bg-slate-900"
                }`}
              >
                <td className="px-3 py-2 text-slate-500">{m.market_cap_rank ?? "—"}</td>
                <td className="px-3 py-2">
                  <span className="font-semibold">{m.symbol}</span>
                  <span className="ml-2 text-slate-500">{m.name}</span>
                </td>
                <td className="px-3 py-2 text-right tabular-nums">{fmtUsd(m.price)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-slate-300">
                  {fmtCompact(m.volume)}
                </td>
              </tr>
            );
          })}
          {markets.length === 0 && (
            <tr>
              <td colSpan={4} className="px-3 py-6 text-center text-slate-500">
                No market data yet — ingestion may still be running.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
