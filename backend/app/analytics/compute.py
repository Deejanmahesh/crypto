"""Analytics computations built on pandas / numpy.

These functions are intentionally pure (they take plain sequences, not ORM
objects) so they're trivial to unit-test and reuse. The router is responsible
for loading snapshots from the DB and feeding ordered price/volume series here.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def pct_change(values: Sequence[float], window: int) -> float | None:
    """Percentage change between the value `window` points ago and the latest.

    Returns None if there is not enough data or the base value is zero.
    """
    s = pd.Series(values, dtype="float64").dropna()
    if len(s) < 2:
        return None
    window = min(window, len(s) - 1)
    base = s.iloc[-(window + 1)]
    latest = s.iloc[-1]
    if base == 0:
        return None
    return float((latest - base) / base * 100.0)


def momentum(values: Sequence[float], window: int) -> float | None:
    """Trend indicator: slope of a linear fit over the last `window` points,
    normalised by the mean price so it's comparable across assets.

    Positive => upward trend, negative => downward trend.
    """
    s = pd.Series(values, dtype="float64").dropna()
    if len(s) < 2:
        return None
    window = min(window, len(s))
    recent = s.iloc[-window:].to_numpy()
    x = np.arange(len(recent))
    slope = float(np.polyfit(x, recent, 1)[0])
    mean = float(recent.mean())
    if mean == 0:
        return None
    # Slope per step as a fraction of mean price, expressed in percent.
    return slope / mean * 100.0


def compute_asset_metrics(
    prices: Sequence[float], volumes: Sequence[float], window: int
) -> dict:
    """Compute the per-asset analytics bundle."""
    price_list = [p for p in prices if p is not None]
    volume_list = [v for v in volumes if v is not None]
    return {
        "latest_price": float(price_list[-1]) if price_list else None,
        "latest_volume": float(volume_list[-1]) if volume_list else None,
        "price_change_pct": pct_change(price_list, window),
        "volume_change_pct": pct_change(volume_list, window),
        "momentum": momentum(price_list, window),
    }


def rank_assets(metrics_by_symbol: dict[str, dict]) -> dict[str, int]:
    """Rank assets by price change (descending). Rank 1 = best performer.

    Symbols with no price_change_pct are ranked last.
    """
    def sort_key(item: tuple[str, dict]) -> float:
        val = item[1].get("price_change_pct")
        return val if val is not None else float("-inf")

    ordered = sorted(metrics_by_symbol.items(), key=sort_key, reverse=True)
    return {symbol: i + 1 for i, (symbol, _) in enumerate(ordered)}
