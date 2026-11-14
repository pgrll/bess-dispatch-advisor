"""The quick 'is it worth cycling?' check must agree with the optimiser."""

from __future__ import annotations

import numpy as np
import pytest

from bess_advisor.config import BatteryConfig
from bess_advisor.economics import check_cycle_value
from bess_advisor.optimizer import optimise_day
from tests.conftest import make_day, random_day


def test_net_spread_formula(two_block_day):
    """Best pair: buy at 0, sell at 100 -> 100 - 0 / 0.85 - 10 = 90 EUR/MWh."""
    check = check_cycle_value(two_block_day, BatteryConfig())
    assert check.worth_cycling
    assert check.net_spread_eur_per_mwh == pytest.approx(90.0)
    assert check.buy_interval < check.sell_interval


def test_flat_day_is_not_worth_cycling():
    check = check_cycle_value(make_day(np.full(96, 70.0)), BatteryConfig())
    assert not check.worth_cycling
    # 70 - 70 / 0.85 - 10 = -22.35 EUR/MWh
    assert check.net_spread_eur_per_mwh == pytest.approx(70 - 70 / 0.85 - 10)


def test_small_spread_is_eaten_by_losses_and_wear():
    prices = np.full(96, 60.0)
    prices[80:] = 75.0  # +15 EUR/MWh spread, but 60 / 0.85 + 10 = 80.6 > 75
    assert not check_cycle_value(make_day(prices), BatteryConfig()).worth_cycling


@pytest.mark.parametrize("seed", range(12))
def test_verdict_agrees_with_the_optimiser(seed):
    day = random_day(seed, negative_share=0.0)
    # Compress some days so that cycling is sometimes unprofitable.
    day = 70 + (day - 70) * (0.05 if seed % 2 else 1.0)
    battery = BatteryConfig()
    worth = check_cycle_value(day, battery).worth_cycling
    makes_money = optimise_day(day, battery).net_value_eur > 1e-6
    assert worth == makes_money


def test_battery_with_initial_energy_may_sell_first():
    prices = np.full(96, 50.0)
    prices[:4] = 150.0  # expensive at the start of the day only
    battery = BatteryConfig(initial_soc_mwh=100.0)
    check = check_cycle_value(make_day(prices), battery)
    assert check.worth_cycling
    assert check.sell_interval < check.buy_interval
