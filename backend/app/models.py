"""SQLAlchemy ORM models.

Three tables:
- assets:          the tracked crypto assets (top-N by market cap).
- price_snapshots: time-series of (price, volume) per asset.
- strategy_results: persisted output of strategy runs (BUY/SELL/HOLD).
"""
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # CoinGecko coin id, e.g. "bitcoin"
    coingecko_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    market_cap_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    snapshots: Mapped[list["PriceSnapshot"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (
        # A given asset has at most one snapshot per timestamp; lets us
        # backfill history idempotently and de-duplicate scheduled writes.
        UniqueConstraint("asset_id", "timestamp", name="uq_asset_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    asset: Mapped["Asset"] = relationship(back_populates="snapshots")


class StrategyResult(Base):
    __tablename__ = "strategy_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    strategy_name: Mapped[str] = mapped_column(String(64), index=True)
    signal: Mapped[str] = mapped_column(String(8))  # BUY / SELL / HOLD
    # Strategy parameters and any extra context (indicator values, reason).
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
