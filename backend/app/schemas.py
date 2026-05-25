"""Pydantic schemas for API request/response bodies."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---- Market data ----------------------------------------------------------
class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    coingecko_id: str
    symbol: str
    name: str
    market_cap_rank: int | None = None


class MarketOut(AssetOut):
    """An asset plus its latest price/volume snapshot."""

    price: float | None = None
    volume: float | None = None
    timestamp: datetime | None = None


class PriceOut(BaseModel):
    symbol: str
    price: float
    volume: float
    timestamp: datetime


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: float
    volume: float
    timestamp: datetime


class HistoryOut(BaseModel):
    symbol: str
    count: int
    snapshots: list[SnapshotOut]


# ---- Analytics ------------------------------------------------------------
class AnalyticsItem(BaseModel):
    symbol: str
    name: str
    latest_price: float | None = None
    latest_volume: float | None = None
    price_change_pct: float | None = None
    volume_change_pct: float | None = None
    momentum: float | None = None  # signed trend indicator
    rank: int | None = None  # 1 = strongest price change in the window


class AnalyticsOut(BaseModel):
    window: int = Field(..., description="Number of snapshots used per asset")
    generated_at: datetime
    items: list[AnalyticsItem]


# ---- Strategy -------------------------------------------------------------
class StrategyRunRequest(BaseModel):
    strategy: str = Field(default="ma_crossover", description="Registered strategy name")
    symbols: list[str] | None = Field(
        default=None, description="Symbols to run on; defaults to all tracked assets"
    )
    params: dict = Field(default_factory=dict, description="Strategy-specific params")


class StrategyResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    strategy_name: str
    signal: str
    params: dict
    details: dict
    created_at: datetime


class StrategyRunResponse(BaseModel):
    strategy: str
    results: list[StrategyResultOut]


class IngestResponse(BaseModel):
    status: str
    assets_ingested: int
    snapshots_written: int
