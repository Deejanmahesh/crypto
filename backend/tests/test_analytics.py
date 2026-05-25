"""Unit tests for the analytics computations."""
import pytest

from app.analytics.compute import (
    compute_asset_metrics,
    momentum,
    pct_change,
    rank_assets,
)


def test_pct_change_basic():
    # last=110, base (1 step back) = 100 -> +10%
    assert pct_change([100, 110], window=1) == pytest.approx(10.0)


def test_pct_change_over_window():
    # window=3 compares index -4 (100) to last (130) -> +30%
    assert pct_change([100, 110, 120, 130], window=3) == pytest.approx(30.0)


def test_pct_change_window_clamped_to_available_data():
    # Only 2 points but window=5 -> clamp to compare 100 -> 120
    assert pct_change([100, 120], window=5) == pytest.approx(20.0)


def test_pct_change_insufficient_data():
    assert pct_change([100], window=1) is None
    assert pct_change([], window=1) is None


def test_pct_change_zero_base():
    assert pct_change([0, 50], window=1) is None


def test_momentum_positive_for_uptrend():
    assert momentum([1, 2, 3, 4, 5], window=5) > 0


def test_momentum_negative_for_downtrend():
    assert momentum([5, 4, 3, 2, 1], window=5) < 0


def test_momentum_flat_is_zero():
    assert momentum([10, 10, 10, 10], window=4) == pytest.approx(0.0)


def test_compute_asset_metrics_bundle():
    prices = [100, 105, 110, 120]
    volumes = [1000, 1100, 900, 1200]
    m = compute_asset_metrics(prices, volumes, window=3)
    assert m["latest_price"] == 120
    assert m["latest_volume"] == 1200
    assert m["price_change_pct"] == pytest.approx(20.0)
    assert m["volume_change_pct"] == pytest.approx(20.0)
    assert m["momentum"] is not None


def test_rank_assets_orders_by_price_change_desc():
    metrics = {
        "AAA": {"price_change_pct": 5.0},
        "BBB": {"price_change_pct": 20.0},
        "CCC": {"price_change_pct": -3.0},
    }
    ranks = rank_assets(metrics)
    assert ranks == {"BBB": 1, "AAA": 2, "CCC": 3}


def test_rank_assets_handles_none_last():
    metrics = {
        "AAA": {"price_change_pct": None},
        "BBB": {"price_change_pct": 1.0},
    }
    ranks = rank_assets(metrics)
    assert ranks["BBB"] == 1
    assert ranks["AAA"] == 2
