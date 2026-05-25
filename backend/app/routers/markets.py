"""Market-data endpoints: /markets, /prices, /history, /ingest."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.db import get_session
from app.ingestion import backfill_history, ingest_markets
from app.schemas import (
    HistoryOut,
    IngestResponse,
    MarketOut,
    PriceOut,
    SnapshotOut,
)

router = APIRouter(tags=["market-data"])


@router.get("/markets", response_model=list[MarketOut])
async def list_markets(session: AsyncSession = Depends(get_session)):
    """List tracked assets with their latest price/volume snapshot."""
    assets = await crud.get_assets(session)
    out: list[MarketOut] = []
    for asset in assets:
        snap = await crud.get_latest_snapshot(session, asset.id)
        out.append(
            MarketOut(
                coingecko_id=asset.coingecko_id,
                symbol=asset.symbol,
                name=asset.name,
                market_cap_rank=asset.market_cap_rank,
                price=snap.price if snap else None,
                volume=snap.volume if snap else None,
                timestamp=snap.timestamp if snap else None,
            )
        )
    return out


@router.get("/prices", response_model=PriceOut)
async def get_price(
    symbol: str = Query(..., description="Asset symbol, e.g. BTC"),
    session: AsyncSession = Depends(get_session),
):
    """Latest price/volume for a single symbol."""
    asset = await crud.get_asset_by_symbol(session, symbol)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    snap = await crud.get_latest_snapshot(session, asset.id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"No price data for {symbol}")
    return PriceOut(
        symbol=asset.symbol,
        price=snap.price,
        volume=snap.volume,
        timestamp=snap.timestamp,
    )


@router.get("/history", response_model=HistoryOut)
async def get_history(
    symbol: str = Query(..., description="Asset symbol, e.g. BTC"),
    limit: int = Query(100, ge=1, le=2000),
    session: AsyncSession = Depends(get_session),
):
    """Historical snapshots for a symbol, oldest -> newest."""
    asset = await crud.get_asset_by_symbol(session, symbol)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    rows = await crud.get_history(session, symbol, limit=limit)
    return HistoryOut(
        symbol=asset.symbol,
        count=len(rows),
        snapshots=[SnapshotOut.model_validate(r) for r in rows],
    )


@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingest(
    with_history: bool = Query(
        False, description="Also backfill historical snapshots (slower)"
    ),
    session: AsyncSession = Depends(get_session),
):
    """Manually trigger a market-data refresh."""
    assets, snapshots = await ingest_markets(session)
    if with_history:
        snapshots += await backfill_history(session)
    return IngestResponse(
        status="ok", assets_ingested=assets, snapshots_written=snapshots
    )
