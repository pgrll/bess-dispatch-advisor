"""Three dispatch strategies, compared and ranked by value captured.

The optimiser runs once per scenario with different parameters, so the
analyst compares genuinely different strategies rather than three near
copies of the same schedule.

* ``max_arbitrage``: up to 2 cycles a day, all power on the day-ahead market.
* ``preserve``: at most 1 cycle a day, to spare the battery.
* ``reserve``: 20 MW withheld for balancing services, earning a capacity price.

Ranking rule (the project's main acceptance test): scenarios are sorted
by net value captured over the day; on a tie, the one using fewer cycles
comes first. The agent's suggestion number 1 must always be the first
scenario of this ranking.

Note for the analyst: ``max_arbitrage`` can never be worth less than
``preserve`` on the same day, because ``preserve`` is the same problem
with a tighter limit. They tie when a second cycle is not profitable.
What ``preserve`` buys is a smaller share of the yearly cycle budget,
which a single day's value does not capture.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bess_advisor.config import REFERENCE_BATTERY, BatteryConfig
from bess_advisor.optimizer import Schedule, optimise_day

#: ASSUMPTION: capacity price for the reserve scenario, in EUR per MW per
#: hour. Replace with recent FCR/aFRR auction results before relying on it.
DEFAULT_RESERVE_PRICE_EUR_PER_MW_H = 10.0
DEFAULT_RESERVE_MW = 20.0


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    description: str
    schedule: Schedule

    @property
    def net_value_eur(self) -> float:
        return self.schedule.net_value_eur


def build_scenarios(
    base: BatteryConfig = REFERENCE_BATTERY,
    reserve_mw: float = DEFAULT_RESERVE_MW,
    reserve_price_eur_per_mw_h: float = DEFAULT_RESERVE_PRICE_EUR_PER_MW_H,
) -> dict[str, tuple[str, BatteryConfig]]:
    """Parameters of the three scenarios, derived from one base battery."""
    reserve = base.with_changes(
        max_cycles_per_day=2.0,
        reserve_mw=reserve_mw,
        reserve_price_eur_per_mw_h=reserve_price_eur_per_mw_h,
    )
    # The reserve needs an energy buffer at both ends of the state of charge,
    # so the day cannot start below it.
    reserve = reserve.with_changes(initial_soc_mwh=max(base.initial_soc_mwh, reserve.reserve_soc_buffer_mwh))
    return {
        "max_arbitrage": ("Up to 2 cycles, all power on day-ahead", base.with_changes(max_cycles_per_day=2.0)),
        "preserve": ("At most 1 cycle, to spare the battery", base.with_changes(max_cycles_per_day=1.0)),
        "reserve": (f"{reserve_mw:g} MW held for balancing services, up to 2 cycles", reserve),
    }


def rank_scenarios(results: list[ScenarioResult]) -> list[ScenarioResult]:
    """Sort by net value (highest first), then by fewest cycles."""
    return sorted(results, key=lambda r: (-round(r.net_value_eur, 2), r.schedule.cycles))


def run_scenarios(prices: pd.Series, base: BatteryConfig = REFERENCE_BATTERY, **kwargs: float) -> list[ScenarioResult]:
    """Optimise every scenario on the same prices and return them ranked.

    Keyword arguments are passed to :func:`build_scenarios`.
    """
    results = [
        ScenarioResult(name=name, description=description, schedule=optimise_day(prices, config))
        for name, (description, config) in build_scenarios(base, **kwargs).items()
    ]
    return rank_scenarios(results)
