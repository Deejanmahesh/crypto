export function fmtUsd(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (v >= 1)
    return v.toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    });
  return `$${v.toPrecision(4)}`;
}

export function fmtCompact(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  });
}

export function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export function pctColor(v: number | null | undefined): string {
  if (v === null || v === undefined) return "text-slate-400";
  return v >= 0 ? "text-emerald-400" : "text-rose-400";
}

export function signalColor(signal: string): string {
  switch (signal) {
    case "BUY":
      return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
    case "SELL":
      return "bg-rose-500/20 text-rose-300 border-rose-500/40";
    default:
      return "bg-slate-500/20 text-slate-300 border-slate-500/40";
  }
}
