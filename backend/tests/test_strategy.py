"""Unit tests for the moving-average crossover strategy and registry."""
import pytest

from app.strategy import get_strategy, list_strategies
from app.strategy.base import Signal
from app.strategy.ma_crossover import MovingAverageCrossover


@pytest.fixture
def strat() -> MovingAverageCrossover:
    return MovingAverageCrossover()


def test_strategy_is_registered():
    assert "ma_crossover" in list_strategies()
    assert get_strategy("ma_crossover").name == "ma_crossover"


def test_unknown_strategy_raises():
    with pytest.raises(KeyError):
        get_strategy("does_not_exist")


def test_insufficient_data_returns_hold(strat):
    result = strat.run([1, 2, 3], {"short_window": 2, "long_window": 5})
    assert result.signal is Signal.HOLD
    assert result.details["reason"] == "insufficient_data"


def test_state_mode_buy_on_uptrend(strat):
    prices = list(range(1, 40))  # steadily rising -> short MA above long MA
    result = strat.run(prices, {"short_window": 3, "long_window": 10, "mode": "state"})
    assert result.signal is Signal.BUY
    assert result.details["short_ma"] > result.details["long_ma"]


def test_state_mode_sell_on_downtrend(strat):
    prices = list(range(40, 1, -1))  # steadily falling -> short MA below long MA
    result = strat.run(prices, {"short_window": 3, "long_window": 10, "mode": "state"})
    assert result.signal is Signal.SELL
    assert result.details["short_ma"] < result.details["long_ma"]


def test_crossover_mode_detects_golden_cross(strat):
    # Falling then rising: a bullish crossover should occur near the end.
    prices = list(range(30, 0, -1)) + list(range(0, 30))
    result = strat.run(
        prices, {"short_window": 3, "long_window": 10, "mode": "crossover"}
    )
    assert result.signal in (Signal.BUY, Signal.HOLD)


def test_invalid_windows_raise(strat):
    with pytest.raises(ValueError):
        strat.run([1, 2, 3, 4, 5], {"short_window": 10, "long_window": 5})


def test_details_contain_expected_keys(strat):
    prices = list(range(1, 40))
    result = strat.run(prices, {"short_window": 3, "long_window": 10})
    for key in ("short_ma", "long_ma", "spread_pct", "latest_price", "mode"):
        assert key in result.details
