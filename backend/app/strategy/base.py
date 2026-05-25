"""Strategy abstraction.

A strategy takes an ordered price series + params and returns a single
``StrategySignal`` (BUY / SELL / HOLD plus context). Strategies are pure and
DB-agnostic, which keeps them isolated and easy to unit-test. New strategies
plug in by subclassing ``Strategy`` and registering themselves.
"""
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field


class Signal(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategySignal:
    signal: Signal
    details: dict = field(default_factory=dict)


class Strategy(ABC):
    #: unique registry key
    name: str = "base"
    #: default parameters, overridable per run
    default_params: dict = {}

    def resolve_params(self, params: dict | None) -> dict:
        merged = dict(self.default_params)
        if params:
            merged.update(params)
        return merged

    @abstractmethod
    def run(self, prices: Sequence[float], params: dict | None = None) -> StrategySignal:
        """Evaluate the strategy on an ordered (oldest -> newest) price series."""
        raise NotImplementedError
