"""Checks run on every price series before it reaches the optimiser.

The optimiser trusts its input completely, so any data problem must be
caught here and reported in words an analyst understands. A wrong price
silently turned into a schedule is the worst failure this tool can have.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

MARKET_TIMEZONE = "Europe/Paris"
INTERVAL = pd.Timedelta(minutes=15)


class PriceDataError(ValueError):
    """Raised when a price series cannot be used to build a schedule."""


def expected_intervals(delivery_day: date, tz: str = MARKET_TIMEZONE) -> int:
    """Number of 15-minute intervals in a delivery day.

    96 on a normal day, 92 on the spring clock change, 100 in autumn.
    """
    start = pd.Timestamp(delivery_day, tz=tz)
    end = pd.Timestamp(delivery_day + pd.Timedelta(days=1), tz=tz)
    return int((end - start) / INTERVAL)


def validate_day_prices(prices: pd.Series, delivery_day: date | None = None) -> pd.Series:
    """Validate one delivery day of 15-minute day-ahead prices.

    Args:
        prices: Prices in EUR/MWh, indexed by the timezone-aware start of
            each interval.
        delivery_day: The day the prices are for, in market local time.
            Inferred from the first timestamp when omitted.

    Returns:
        The same prices, sorted, converted to market local time and named
        ``price_eur_mwh``.

    Raises:
        PriceDataError: If the series is empty, has missing or duplicated
            intervals, is not at 15-minute resolution, or does not cover
            exactly one delivery day.
    """
    if prices is None or len(prices) == 0:
        raise PriceDataError("No price data: the series is empty.")
    if not isinstance(prices.index, pd.DatetimeIndex) or prices.index.tz is None:
        raise PriceDataError("Prices must be indexed by timezone-aware timestamps.")
    if prices.isna().any():
        missing = prices.index[prices.isna()]
        raise PriceDataError(
            f"{len(missing)} interval(s) have no price, first at {missing[0]}. "
            "Refusing to build a schedule on incomplete data."
        )
    if prices.index.has_duplicates:
        raise PriceDataError("Some intervals appear twice in the price series.")

    local = prices.sort_index().tz_convert(MARKET_TIMEZONE)
    day = delivery_day or local.index[0].date()
    n_expected = expected_intervals(day)

    steps = local.index.to_series().diff().dropna()
    if not (steps == INTERVAL).all():
        bad = steps[steps != INTERVAL]
        raise PriceDataError(f"Prices are not at a regular 15-minute step: gap of {bad.iloc[0]} before {bad.index[0]}.")
    if local.index[0] != pd.Timestamp(day, tz=MARKET_TIMEZONE) or len(local) != n_expected:
        raise PriceDataError(
            f"Expected {n_expected} intervals covering {day} (local time), "
            f"got {len(local)} starting at {local.index[0]}."
        )
    return local.rename("price_eur_mwh").astype(float)
