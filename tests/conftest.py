"""Shared helpers to build price days for the tests."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
import pytest


def make_day(prices: Sequence[float] | np.ndarray, day: str = "2026-11-14") -> pd.Series:
    """A delivery day of 15-minute prices in market local time."""
    index = pd.date_range(day, periods=len(prices), freq="15min", tz="Europe/Paris")
    return pd.Series(np.asarray(prices, dtype=float), index=index, name="price_eur_mwh")


def random_day(seed: int, negative_share: float = 0.15) -> pd.Series:
    """A noisy day with two peaks and, sometimes, negative prices."""
    rng = np.random.default_rng(seed)
    hour = np.arange(96) / 4
    shape = 60 + 40 * np.sin((hour - 7) / 24 * 4 * np.pi) + rng.normal(0, 15, 96)
    shape[rng.random(96) < negative_share] *= -0.5
    return make_day(np.round(shape, 2))


@pytest.fixture
def two_block_day() -> pd.Series:
    """Hand-computable day: 8 intervals at 0, 8 at 100, the rest at 80 EUR/MWh."""
    prices = np.full(96, 80.0)
    prices[4:12] = 0.0
    prices[72:80] = 100.0
    return make_day(prices)
