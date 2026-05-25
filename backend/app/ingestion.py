"""Fetch market data from CoinGecko and persist it.

Two operations:
- ``ingest_markets``  : refresh the tracked asset list + write a current snapshot.
- ``backfill_history``: load historical snapshots so analytics/strategy have
  enough data to work with immediately (rather than waiting for the scheduler
  to accumulate points over time).

Writes are idempotent: we only insert (asset, timestamp) pairs that don't
already exist, so re-running on startup never duplicates rows. This keeps the
logic portable across Postgres and SQLite (no dialect-specific upsert).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.coingecko import CoinGeckoClient
from app.config import settings
from app.models import Asset, PriceSnapshot

logger = logging.getLogger(__name__)


def _ms_to_dt(ms: int | float) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


async def _upsert_asset(session: AsyncSession, market: dict) -> Asset:
    result = await session.execute(
        select(Asset).where(Asset.coingecko_id == market["id"])
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        asset = Asset(
            coingecko_id=market["id"],
            symbol=market["symbol"].upper(),
            name=market["name"],
            market_cap_rank=market.get("market_cap_rank"),
        )
        session.add(asset)
        await session.flush()  # assign asset.id
    else:
        asset.symbol = market["symbol"].upper()
        asset.name = market["name"]
        asset.market_cap_rank = market.get("market_cap_rank")
    return asset


async def _existing_timestamps(session: AsyncSession, asset_id: int) -> set[datetime]:
    result = await session.execute(
        select(PriceSnapshot.timestamp).where(PriceSnapshot.asset_id == asset_id)
    )
    return set(result.scalars().all())


async def ingest_markets(
    session: AsyncSession, client: CoinGeckoClient | None = None
) -> tuple[int, int]:
    """Refresh the top-N asset list and store a current price/volume snapshot.

    Returns (assets_ingested, snapshots_written).
    """
    client = client or CoinGeckoClient()
    markets = await client.get_top_markets(per_page=settings.top_n_assets)

    snapshots_written = 0
    now = datetime.now(timezone.utc).replace(microsecond=0)

    for market in markets:
        asset = await _upsert_asset(session, market)
        existing = await _existing_timestamps(session, asset.id)
        price = market.get("current_price")
        volume = market.get("total_volume")
        if price is None or volume is None:
            continue
        if now not in existing:
            session.add(
                PriceSnapshot(
                    asset_id=asset.id,
                    symbol=asset.symbol,
                    price=float(price),
                    volume=float(volume),
                    timestamp=now,
                )
            )
            snapshots_written += 1

    await session.commit()
    logger.info("Ingested %d assets, wrote %d snapshots", len(markets), snapshots_written)
    return len(markets), snapshots_written


async def backfill_history(
    session: AsyncSession,
    client: CoinGeckoClient | None = None,
    days: int | None = None,
) -> int:
    """Load historical snapshots for every tracked asset. Returns rows written."""
    client = client or CoinGeckoClient()
    days = days or settings.history_days

    assets = (await session.execute(select(Asset))).scalars().all()
    total_written = 0

    for asset in assets:
        try:
            chart = await client.get_market_chart(asset.coingecko_id, days=days)
        except Exception as exc:  # noqa: BLE001 - keep ingesting other assets
            logger.warning("History fetch failed for %s: %s", asset.coingecko_id, exc)
            continue

        prices = chart.get("prices", [])
        volumes = {int(ts): vol for ts, vol in chart.get("total_volumes", [])}
        existing = await _existing_timestamps(session, asset.id)

        for ts_ms, price in prices:
            dt = _ms_to_dt(ts_ms)
            if dt in existing:
                continue
            session.add(
                PriceSnapshot(
                    asset_id=asset.id,
                    symbol=asset.symbol,
                    price=float(price),
                    volume=float(volumes.get(int(ts_ms), 0.0)),
                    timestamp=dt,
                )
            )
            existing.add(dt)
            total_written += 1

        await session.commit()
        # Be gentle with the public rate limit between coin calls (the client
        # also retries 429s with backoff on top of this).
        await asyncio.sleep(2.5)

    logger.info("Backfilled %d historical snapshots", total_written)
    return total_written
