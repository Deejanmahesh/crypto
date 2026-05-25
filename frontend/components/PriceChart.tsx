"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Snapshot } from "@/lib/types";
import { fmtCompact, fmtUsd } from "@/lib/format";

function formatTick(ts: string): string {
  const d = new Date(ts);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export default function PriceChart({
  symbol,
  snapshots,
}: {
  symbol: string;
  snapshots: Snapshot[];
}) {
  const data = snapshots.map((s) => ({
    t: s.timestamp,
    price: s.price,
    volume: s.volume,
  }));

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-500">
        No history for {symbol} yet.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-sm font-medium text-slate-400">Price (USD)</h3>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="t" tickFormatter={formatTick} stroke="#64748b" fontSize={11} minTickGap={40} />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              width={70}
              domain={["auto", "auto"]}
              tickFormatter={(v) => fmtUsd(v)}
            />
            <Tooltip
              contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }}
              labelFormatter={(l) => new Date(l).toLocaleString()}
              formatter={(v: number) => [fmtUsd(v), "Price"]}
            />
            <Area type="monotone" dataKey="price" stroke="#38bdf8" fill="url(#priceFill)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-medium text-slate-400">Volume</h3>
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="t" tickFormatter={formatTick} stroke="#64748b" fontSize={11} minTickGap={40} />
            <YAxis stroke="#64748b" fontSize={11} width={70} tickFormatter={(v) => fmtCompact(v)} />
            <Tooltip
              contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }}
              labelFormatter={(l) => new Date(l).toLocaleString()}
              formatter={(v: number) => [fmtCompact(v), "Volume"]}
            />
            <Bar dataKey="volume" fill="#6366f1" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
