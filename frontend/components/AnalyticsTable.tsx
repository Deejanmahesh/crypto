"use client";

import type { AnalyticsItem } from "@/lib/types";
import { fmtPct, fmtUsd, pctColor } from "@/lib/format";

export default function AnalyticsTable({ items }: { items: AnalyticsItem[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-sm">
        <thead className="bg-slate-900 text-slate-400">
          <tr>
            <th className="px-3 py-2 text-left">Rank</th>
            <th className="px-3 py-2 text-left">Asset</th>
            <th className="px-3 py-2 text-right">Price</th>
            <th className="px-3 py-2 text-right">Price Δ%</th>
            <th className="px-3 py-2 text-right">Volume Δ%</th>
            <th className="px-3 py-2 text-right">Momentum</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.symbol} className="border-t border-slate-800">
              <td className="px-3 py-2 text-slate-500">{it.rank ?? "—"}</td>
              <td className="px-3 py-2 font-semibold">{it.symbol}</td>
              <td className="px-3 py-2 text-right tabular-nums">{fmtUsd(it.latest_price)}</td>
              <td className={`px-3 py-2 text-right tabular-nums ${pctColor(it.price_change_pct)}`}>
                {fmtPct(it.price_change_pct)}
              </td>
              <td className={`px-3 py-2 text-right tabular-nums ${pctColor(it.volume_change_pct)}`}>
                {fmtPct(it.volume_change_pct)}
              </td>
              <td className={`px-3 py-2 text-right tabular-nums ${pctColor(it.momentum)}`}>
                {it.momentum === null ? "—" : it.momentum.toFixed(3)}
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                No analytics available yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
