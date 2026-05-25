"""FastAPI application entry point.

On startup it creates tables, optionally kicks off an initial data ingestion +
history backfill (in the background so the API is immediately responsive), and
starts the APScheduler refresh job.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import AsyncSessionLocal, init_db
from app.ingestion import backfill_history, ingest_markets
from app.routers import analytics, markets, strategy
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _initial_ingest() -> None:
    """Populate current + historical data on first boot."""
    try:
        async with AsyncSessionLocal() as session:
            await ingest_markets(session)
            await backfill_history(session)
    except Exception:  # noqa: BLE001
        logger.exception("Initial ingestion failed (API still available)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.ingest_on_startup:
        # Run in the background so startup doesn't block on network I/O.
        asyncio.create_task(_initial_ingest())
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(
    title="Crypto Market Data & Analytics API",
    version="1.0.0",
    description="Ingests CoinGecko market data, exposes analytics and a "
    "rule-based trading strategy.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(markets.router)
app.include_router(analytics.router)
app.include_router(strategy.router)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}


@app.get("/", tags=["meta"])
async def root():
    return {
        "name": "Crypto Market Data & Analytics API",
        "docs": "/docs",
        "endpoints": [
            "/markets",
            "/prices?symbol=BTC",
            "/history?symbol=BTC&limit=100",
            "/analytics?window=24",
            "/strategy/list",
            "/strategy/run",
            "/strategy/results",
            "/ingest",
        ],
    }
