"""Database query helpers shared across routers and services."""
from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, PriceSnapshot


async def get_assets(session: AsyncSession) -> list[Asset]:
    result = await session.execute(
        select(Asset).order_by(Asset.market_cap_rank.asc().nulls_last())
    )
    return list(result.scalars().all())


async def get_asset_by_symbol(session: AsyncSession, symbol: str) -> Asset | None:
    result = await session.execute(
        select(Asset).where(Asset.symbol == symbol.upper())
    )
    return result.scalar_one_or_none()


async def get_latest_snapshot(
    session: AsyncSession, asset_id: int
) -> PriceSnapshot | None:
    result = await session.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.asset_id == asset_id)
        .order_by(desc(PriceSnapshot.timestamp))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_history(
    session: AsyncSession, symbol: str, limit: int = 100
) -> list[PriceSnapshot]:
    """Return up to `limit` most-recent snapshots, ordered oldest -> newest."""
    result = await session.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.symbol == symbol.upper())
        .order_by(desc(PriceSnapshot.timestamp))
        .limit(limit)
    )
    rows = list(result.scalars().all())
    rows.reverse()  # chronological order for charts / indicators
    return rows
