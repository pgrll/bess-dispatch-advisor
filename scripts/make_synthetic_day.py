"""Generate a SYNTHETIC day of 15-minute prices for demos and tests.

These prices are invented. They mimic the shape of a sunny spring day in
France (morning and evening peaks, a midday dip below zero when solar
output is high) so the tool can be tried without an ENTSO-E token.
Never present them as market data.

Usage:
    python scripts/make_synthetic_day.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from bess_advisor.data.storage import save_prices_csv

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "sample" / "synthetic_day.csv"


def synthetic_prices(day: str = "2026-04-18", seed: int = 7) -> pd.Series:
    index = pd.date_range(day, periods=96, freq="15min", tz="Europe/Paris")
    hour = np.arange(96) / 4
    base = 70.0
    morning_peak = 45 * np.exp(-((hour - 8.0) ** 2) / 2.0)
    evening_peak = 75 * np.exp(-((hour - 20.0) ** 2) / 2.5)
    solar_dip = -110 * np.exp(-((hour - 13.5) ** 2) / 4.0)
    noise = np.random.default_rng(seed).normal(0, 4, size=96)
    return pd.Series(np.round(base + morning_peak + evening_peak + solar_dip + noise, 2), index=index)


if __name__ == "__main__":
    path = save_prices_csv(synthetic_prices(), OUTPUT)
    print(f"Wrote {path} (synthetic data, not market prices)")
