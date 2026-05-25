"""APScheduler background job that periodically refreshes market data."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.db import AsyncSessionLocal
from app.ingestion import ingest_markets

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


async def _scheduled_ingest() -> None:
    try:
        async with AsyncSessionLocal() as session:
            await ingest_markets(session)
    except Exception:  # noqa: BLE001
        logger.exception("Scheduled ingest failed")


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _scheduled_ingest,
        trigger="interval",
        minutes=settings.ingest_interval_minutes,
        id="ingest_markets",
        replace_existing=True,
        next_run_time=None,  # first run happens after one interval
    )
    scheduler.start()
    logger.info(
        "Scheduler started: refreshing markets every %d min",
        settings.ingest_interval_minutes,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
