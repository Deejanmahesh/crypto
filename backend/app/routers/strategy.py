"""Strategy endpoints: /strategy/run, /strategy/results, /strategy/list."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import StrategyResult
from app.schemas import (
    StrategyResultOut,
    StrategyRunRequest,
    StrategyRunResponse,
)
from app.strategy import list_strategies
from app.strategy_service import run_strategy

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.get("/list")
async def available_strategies():
    """List registered strategy names."""
    return {"strategies": list_strategies()}


@router.post("/run", response_model=StrategyRunResponse)
async def run(
    request: StrategyRunRequest,
    session: AsyncSession = Depends(get_session),
):
    """Run a strategy over stored history and persist BUY/SELL/HOLD signals."""
    try:
        results = await run_strategy(
            session,
            strategy_name=request.strategy,
            symbols=request.symbols,
            params=request.params,
        )
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Unknown strategy: {request.strategy}"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return StrategyRunResponse(
        strategy=request.strategy,
        results=[StrategyResultOut.model_validate(r) for r in results],
    )


@router.get("/results", response_model=list[StrategyResultOut])
async def results(
    symbol: str | None = Query(None, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    """Return the most recent persisted strategy results."""
    stmt = select(StrategyResult).order_by(desc(StrategyResult.created_at))
    if symbol:
        stmt = stmt.where(StrategyResult.symbol == symbol.upper())
    stmt = stmt.limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [StrategyResultOut.model_validate(r) for r in rows]
