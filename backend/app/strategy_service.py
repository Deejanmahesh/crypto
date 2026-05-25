"""Service layer that connects stored data to the strategy modules.

Loads historical prices from the DB, runs the requested strategy per symbol,
and persists the resulting BUY/SELL/HOLD signals.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.models import StrategyResult
from app.strategy import get_strategy

# History depth pulled per symbol when running a strategy.
STRATEGY_HISTORY_LIMIT = 500


async def run_strategy(
    session: AsyncSession,
    strategy_name: str,
    symbols: list[str] | None = None,
    params: dict | None = None,
) -> list[StrategyResult]:
    strategy = get_strategy(strategy_name)  # raises KeyError if unknown

    if symbols:
        symbols = [s.upper() for s in symbols]
    else:
        assets = await crud.get_assets(session)
        symbols = [a.symbol for a in assets]

    results: list[StrategyResult] = []
    for symbol in symbols:
        history = await crud.get_history(session, symbol, limit=STRATEGY_HISTORY_LIMIT)
        prices = [s.price for s in history]
        outcome = strategy.run(prices, params)
        record = StrategyResult(
            symbol=symbol,
            strategy_name=strategy_name,
            signal=outcome.signal.value,
            params=params or {},
            details=outcome.details,
        )
        session.add(record)
        results.append(record)

    await session.commit()
    for record in results:
        await session.refresh(record)
    return results
