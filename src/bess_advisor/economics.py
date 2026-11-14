"""Is it worth cycling the battery today?

A quick, transparent check an analyst can redo by hand. It looks for the
best pair of intervals (buy in one, sell in a later one) and measures the
margin per MWh sold once conversion losses and wear are paid for:

    net spread = sell price - buy price / round-trip efficiency - degradation cost

Buying ``1 / efficiency`` MWh is needed to sell 1 MWh, hence the division.

If no pair has a positive net spread, no schedule can make money: any
schedule can be split into such buy/sell pairs, and its value is the sum of
their margins. The test suite checks that this verdict always agrees with
the optimiser.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bess_advisor.config import BatteryConfig


@dataclass(frozen=True)
class CycleCheck:
    """Verdict of the cycle-value check.

    Attributes:
        worth_cycling: True if at least one buy/sell pair is profitable.
        net_spread_eur_per_mwh: Margin of the best pair, per MWh sold.
            Negative when cycling would lose money.
        buy_interval: Start of the interval where the best pair buys.
        sell_interval: Start of the interval where the best pair sells.
    """

    worth_cycling: bool
    net_spread_eur_per_mwh: float
    buy_interval: pd.Timestamp
    sell_interval: pd.Timestamp


def check_cycle_value(prices: pd.Series, battery: BatteryConfig) -> CycleCheck:
    """Find the most profitable buy/sell pair of the day.

    Buying must happen before selling, unless the battery starts the day
    with energy, in which case it may sell first and buy back later.
    """
    if len(prices) < 2:
        raise ValueError("At least two intervals are needed to cycle.")
    eta = battery.round_trip_efficiency
    wear = battery.degradation_cost_eur_per_mwh
    can_sell_first = battery.initial_soc_mwh > 0

    best_spread, best_buy, best_sell = float("-inf"), prices.index[0], prices.index[1]
    cheapest_so_far = (float(prices.iloc[0]), prices.index[0])
    dearest_so_far = (float(prices.iloc[0]), prices.index[0])

    for when, price in list(prices.items())[1:]:
        # Buy at the cheapest earlier interval, sell now.
        spread = float(price) - cheapest_so_far[0] / eta - wear
        if spread > best_spread:
            best_spread, best_buy, best_sell = spread, cheapest_so_far[1], when
        # Sell at the dearest earlier interval, buy back now.
        if can_sell_first:
            spread = dearest_so_far[0] - float(price) / eta - wear
            if spread > best_spread:
                best_spread, best_buy, best_sell = spread, when, dearest_so_far[1]
        if price < cheapest_so_far[0]:
            cheapest_so_far = (float(price), when)
        if price > dearest_so_far[0]:
            dearest_so_far = (float(price), when)

    return CycleCheck(
        worth_cycling=best_spread > 0,
        net_spread_eur_per_mwh=best_spread,
        buy_interval=best_buy,
        sell_interval=best_sell,
    )
