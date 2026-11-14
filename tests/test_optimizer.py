"""The optimiser must be feasible, exact on hand-computed cases, and no worse
than an independent brute-force search."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from bess_advisor.config import INTERVAL_HOURS, BatteryConfig
from bess_advisor.optimizer import optimise_day
from tests.conftest import make_day, random_day

TOL = 1e-6


def assert_physically_feasible(schedule, battery: BatteryConfig) -> None:
    df = schedule.intervals
    power = battery.arbitrage_power_mw
    buffer = battery.reserve_soc_buffer_mwh
    assert (df["charge_mw"] >= -TOL).all() and (df["charge_mw"] <= power + TOL).all()
    assert (df["discharge_mw"] >= -TOL).all() and (df["discharge_mw"] <= power + TOL).all()
    assert not ((df["charge_mw"] > TOL) & (df["discharge_mw"] > TOL)).any(), "simultaneous charge and discharge"
    assert (df["soc_mwh"] >= buffer - TOL).all() and (df["soc_mwh"] <= battery.energy_mwh - buffer + TOL).all()

    # Recompute the state of charge from the powers: it must match exactly.
    soc = battery.initial_soc_mwh
    for _, row in df.iterrows():
        soc += row["charge_mw"] * battery.charge_efficiency * INTERVAL_HOURS
        soc -= row["discharge_mw"] / battery.discharge_efficiency * INTERVAL_HOURS
        assert row["soc_mwh"] == pytest.approx(soc, abs=1e-4)

    assert schedule.cycles <= battery.max_cycles_per_day + 1e-6
    assert df["soc_mwh"].iloc[-1] >= battery.initial_soc_mwh - TOL


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize(
    "battery",
    [
        BatteryConfig(),
        BatteryConfig(max_cycles_per_day=1.0),
        BatteryConfig(reserve_mw=20.0, initial_soc_mwh=10.0, reserve_price_eur_per_mw_h=10.0),
    ],
    ids=["two_cycles", "one_cycle", "reserve"],
)
def test_schedule_respects_every_physical_limit(seed, battery):
    assert_physically_feasible(optimise_day(random_day(seed), battery), battery)


def test_hand_computed_day(two_block_day):
    """Buy 8 intervals at 0, sell at 100: computable on paper.

    Charging 8 x 25 MWh stores 200 x sqrt(0.85) MWh; discharging it returns
    200 x 0.85 = 170 MWh to the grid. Revenue 170 x 100 = 17,000 EUR,
    wear 170 x 10 = 1,700 EUR, net 15,300 EUR. Buying at 80 to sell at 100
    loses money (100 - 80 / 0.85 - 10 < 0), so nothing else is traded.
    """
    battery = BatteryConfig(max_cycles_per_day=1.0)
    schedule = optimise_day(two_block_day, battery)

    assert schedule.energy_charged_mwh == pytest.approx(200.0, abs=1e-4)
    assert schedule.energy_discharged_mwh == pytest.approx(170.0, abs=1e-4)
    assert schedule.arbitrage_revenue_eur == pytest.approx(17_000.0, abs=0.01)
    assert schedule.net_value_eur == pytest.approx(15_300.0, abs=0.01)
    charging = schedule.intervals.index[schedule.intervals["action"] == "charge"]
    assert list(charging) == list(two_block_day.index[4:12])


def brute_force_best_value(prices: np.ndarray, battery: BatteryConfig) -> float:
    """Best value over all full-power charge/idle/discharge sequences."""
    step = battery.power_mw * INTERVAL_HOURS
    best = 0.0
    for actions in itertools.product((-1, 0, 1), repeat=len(prices)):  # -1 charge, +1 discharge
        soc, value, out_of_battery, feasible = battery.initial_soc_mwh, 0.0, 0.0, True
        for price, action in zip(prices, actions, strict=True):
            if action == -1:
                soc += step * battery.charge_efficiency
                value -= price * step
            elif action == 1:
                soc -= step / battery.discharge_efficiency
                out_of_battery += step / battery.discharge_efficiency
                value += (price - battery.degradation_cost_eur_per_mwh) * step
            if not -TOL <= soc <= battery.energy_mwh + TOL:
                feasible = False
                break
        feasible = feasible and soc >= battery.initial_soc_mwh - TOL
        feasible = feasible and out_of_battery <= battery.max_cycles_per_day * battery.energy_mwh + TOL
        if feasible:
            best = max(best, value)
    return best


def pairwise_upper_bound(prices: np.ndarray, battery: BatteryConfig) -> float:
    """Value no schedule can exceed, computed without any solver.

    Every MWh sold was bought earlier at a cost of ``buy / efficiency`` plus
    wear, so it earns at most the best pairwise net spread. At most
    ``cycles x capacity x discharge efficiency`` MWh can be sold in a day
    (battery starting empty). Written independently of ``economics.py`` on
    purpose: a shared mistake would hide in both.
    """
    best_spread = max(
        prices[j] - prices[i] / battery.round_trip_efficiency - battery.degradation_cost_eur_per_mwh
        for i in range(len(prices))
        for j in range(i + 1, len(prices))
    )
    max_sold = battery.max_cycles_per_day * battery.energy_mwh * battery.discharge_efficiency
    return max(0.0, best_spread) * max_sold


@pytest.mark.parametrize("seed", range(5))
def test_optimiser_sits_between_two_independent_bounds(seed):
    """Lower bound: exhaustive search over 3^8 full-power schedules (the optimiser
    must do at least as well). Upper bound: the pairwise spread argument (it
    cannot do better). Neither bound uses the optimiser's code."""
    battery = BatteryConfig(energy_mwh=50.0, max_cycles_per_day=1.0)
    prices = np.round(np.random.default_rng(seed).normal(60, 40, 8), 2)
    index = pd.date_range("2026-11-14", periods=8, freq="15min", tz="Europe/Paris")
    value = optimise_day(pd.Series(prices, index=index), battery).net_value_eur
    assert brute_force_best_value(prices, battery) - 1e-4 <= value <= pairwise_upper_bound(prices, battery) + 1e-4


@pytest.mark.parametrize("seed", range(10))
def test_full_day_value_never_exceeds_the_upper_bound(seed):
    battery = BatteryConfig()
    day = random_day(seed)
    value = optimise_day(day, battery).net_value_eur
    assert 0.0 <= value <= pairwise_upper_bound(day.to_numpy(), battery) + 1e-4


def test_negative_prices_do_not_trigger_simultaneous_charge_and_discharge():
    """Without the binary variable the solver would burn energy in losses."""
    battery = BatteryConfig()
    schedule = optimise_day(make_day(np.full(96, -200.0)), battery)
    df = schedule.intervals
    assert not ((df["charge_mw"] > TOL) & (df["discharge_mw"] > TOL)).any()


def test_flat_prices_leave_the_battery_idle():
    schedule = optimise_day(make_day(np.full(96, 75.0)), BatteryConfig())
    assert schedule.active_intervals().empty
    assert schedule.net_value_eur == pytest.approx(0.0, abs=1e-6)


def test_zero_prices_all_day_leave_the_battery_idle():
    schedule = optimise_day(make_day(np.zeros(96)), BatteryConfig())
    assert schedule.active_intervals().empty


@pytest.mark.parametrize(("day", "n_intervals"), [("2026-03-29", 92), ("2026-10-25", 100)])
def test_clock_change_days(day, n_intervals):
    hour = np.arange(n_intervals) / 4
    prices = make_day(60 + 40 * np.sin(hour / 24 * 4 * np.pi), day=day)
    battery = BatteryConfig()
    schedule = optimise_day(prices, battery)
    assert len(schedule.intervals) == n_intervals
    assert_physically_feasible(schedule, battery)
