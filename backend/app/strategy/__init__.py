"""Strategy package.

Importing this package registers all built-in strategies so they're available
via the registry. Add new strategies by subclassing ``Strategy`` and decorating
with ``@register``.
"""
from app.strategy.base import Signal, Strategy, StrategySignal  # noqa: F401
from app.strategy.registry import get_strategy, list_strategies, register  # noqa: F401

# Importing the modules triggers their @register side effects.
from app.strategy import ma_crossover  # noqa: F401,E402
