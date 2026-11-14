"""HTML dashboard: one self-contained page per delivery day.

Usage from code::

    html = build_dashboard(prices, source="ENTSO-E", is_synthetic=False)
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from bess_advisor.config import REFERENCE_BATTERY, BatteryConfig
from bess_advisor.dashboard.errors import explain
from bess_advisor.dashboard.page import render_dashboard, render_error_page
from bess_advisor.dashboard.view import build_view
from bess_advisor.economics import check_cycle_value
from bess_advisor.scenarios import run_scenarios


def build_dashboard(
    prices: pd.Series,
    source: str,
    is_synthetic: bool,
    battery: BatteryConfig = REFERENCE_BATTERY,
    generated_at: datetime | None = None,
) -> str:
    """HTML of the dashboard for validated prices."""
    ranked = run_scenarios(prices, base=battery)
    view = build_view(prices, ranked, check_cycle_value(prices, battery), source, is_synthetic, generated_at)
    return render_dashboard(view)


def build_error_page(error: Exception) -> str:
    """HTML page explaining why the dashboard could not be built."""
    explanation = explain(error)
    return render_error_page(explanation.what_happened, explanation.what_to_do, explanation.technical_detail)


__all__ = ["build_dashboard", "build_error_page"]
