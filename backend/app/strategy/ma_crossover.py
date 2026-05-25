"""Moving-average crossover strategy.

Compares a short-window simple moving average (SMA) against a long-window SMA.

Two modes:
- "state" (default): BUY while short SMA is above long SMA, SELL while below,
  HOLD when they're within `tolerance` of each other. Produces an actionable
  signal on every run -- useful for a dashboard demo.
- "crossover": only emits BUY/SELL on the bar where the lines actually cross
  (golden / death cross); HOLD otherwise. More conservative / lower-frequency.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from app.strategy.base import Signal, Strategy, StrategySignal
from app.strategy.registry import register


@register
class MovingAverageCrossover(Strategy):
    name = "ma_crossover"
    default_params = {
        "short_window": 7,
        "long_window": 21,
        "mode": "state",
        "tolerance": 0.0,  # relative gap (fraction of price) treated as "flat"
    }

    def run(self, prices: Sequence[float], params: dict | None = None) -> StrategySignal:
        p = self.resolve_params(params)
        short_w = int(p["short_window"])
        long_w = int(p["long_window"])
        mode = p.get("mode", "state")
        tolerance = float(p.get("tolerance", 0.0))

        if short_w >= long_w:
            raise ValueError("short_window must be smaller than long_window")

        series = pd.Series(list(prices), dtype="float64").dropna()
        if len(series) < long_w + 1:
            return StrategySignal(
                Signal.HOLD,
                {
                    "reason": "insufficient_data",
                    "points": int(len(series)),
                    "required": long_w + 1,
                },
            )

        short_ma = series.rolling(short_w).mean()
        long_ma = series.rolling(long_w).mean()

        short_now = float(short_ma.iloc[-1])
        long_now = float(long_ma.iloc[-1])
        short_prev = float(short_ma.iloc[-2])
        long_prev = float(long_ma.iloc[-2])

        diff_now = short_now - long_now
        diff_prev = short_prev - long_prev
        flat_band = tolerance * long_now

        if mode == "crossover":
            if diff_prev <= 0 < diff_now:
                signal = Signal.BUY
            elif diff_prev >= 0 > diff_now:
                signal = Signal.SELL
            else:
                signal = Signal.HOLD
        else:  # "state"
            if diff_now > flat_band:
                signal = Signal.BUY
            elif diff_now < -flat_band:
                signal = Signal.SELL
            else:
                signal = Signal.HOLD

        return StrategySignal(
            signal,
            {
                "mode": mode,
                "short_window": short_w,
                "long_window": long_w,
                "short_ma": round(short_now, 6),
                "long_ma": round(long_now, 6),
                "spread_pct": round(diff_now / long_now * 100, 4) if long_now else None,
                "latest_price": float(series.iloc[-1]),
                "crossed": bool(np.sign(diff_now) != np.sign(diff_prev)),
            },
        )
