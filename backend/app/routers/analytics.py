"""Analytics endpoint: /analytics."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.analytics.compute import compute_asset_metrics, rank_assets
from app.db import get_session
from app.schemas import AnalyticsItem, AnalyticsOut

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsOut)
async def get_analytics(
    window: int = Query(
        24, ge=1, le=1000, description="Number of recent snapshots used per asset"
    ),
    session: AsyncSession = Depends(get_session),
):
    """Per-asset price/volume change, momentum and ranking over a window."""
    assets = await crud.get_assets(session)

    metrics_by_symbol: dict[str, dict] = {}
    meta: dict[str, str] = {}
    for asset in assets:
        # Pull a bit more than the window so pct_change has its baseline point.
        history = await crud.get_history(session, asset.symbol, limit=window + 1)
        prices = [s.price for s in history]
        volumes = [s.volume for s in history]
        metrics_by_symbol[asset.symbol] = compute_asset_metrics(prices, volumes, window)
        meta[asset.symbol] = asset.name

    ranks = rank_assets(metrics_by_symbol)

    items = [
        AnalyticsItem(
            symbol=symbol,
            name=meta[symbol],
            rank=ranks.get(symbol),
            **metrics,
        )
        for symbol, metrics in metrics_by_symbol.items()
    ]
    items.sort(key=lambda i: i.rank or 10**9)

    return AnalyticsOut(
        window=window,
        generated_at=datetime.now(timezone.utc),
        items=items,
    )
