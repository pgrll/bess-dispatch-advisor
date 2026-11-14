"""Read and write price series as CSV, so each day is downloaded only once.

File format: two columns, ``interval_start`` (ISO 8601 with UTC offset)
and ``price_eur_mwh``. Keeping the offset in the file makes clock-change
days unambiguous.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_prices_csv(prices: pd.Series, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = prices.rename("price_eur_mwh").to_frame()
    frame.index = frame.index.map(lambda ts: ts.isoformat())
    frame.index.name = "interval_start"
    frame.to_csv(path)
    return path


def load_prices_csv(path: str | Path) -> pd.Series:
    frame = pd.read_csv(path)
    missing = {"interval_start", "price_eur_mwh"} - set(frame.columns)
    if missing:
        raise ValueError(f"{path}: missing column(s) {sorted(missing)}")
    index = pd.DatetimeIndex(pd.to_datetime(frame["interval_start"], utc=True), name="interval_start")
    return pd.Series(frame["price_eur_mwh"].to_numpy(dtype=float), index=index, name="price_eur_mwh")
