"""Simple in-memory registry of strategies, keyed by name."""
from __future__ import annotations

from app.strategy.base import Strategy

_REGISTRY: dict[str, Strategy] = {}


def register(cls: type[Strategy]) -> type[Strategy]:
    """Class decorator that instantiates and registers a strategy."""
    instance = cls()
    if not instance.name or instance.name == "base":
        raise ValueError(f"Strategy {cls.__name__} must define a unique `name`")
    _REGISTRY[instance.name] = instance
    return cls


def get_strategy(name: str) -> Strategy:
    if name not in _REGISTRY:
        raise KeyError(name)
    return _REGISTRY[name]


def list_strategies() -> list[str]:
    return sorted(_REGISTRY.keys())
