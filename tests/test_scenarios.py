"""Main acceptance test of the project: suggestion number 1 is always the
scenario that captures the most value over the next day."""

from __future__ import annotations

import numpy as np
import pytest

from bess_advisor.config import BatteryConfig
from bess_advisor.scenarios import run_scenarios
from tests.conftest import make_day, random_day

DAYS = {
    "random_0": random_day(0),
    "random_1": random_day(1),
    "random_2": random_day(2),
    "deep_negative": random_day(3, negative_share=0.4),
    "flat": make_day(np.full(96, 70.0)),
}


@pytest.mark.parametrize("reserve_price", [0.0, 10.0, 60.0])
@pytest.mark.parametrize("day", DAYS.values(), ids=DAYS.keys())
def test_suggestion_one_captures_the_most_value(day, reserve_price):
    ranked = run_scenarios(day, reserve_price_eur_per_mw_h=reserve_price)
    best_value = max(result.net_value_eur for result in ranked)
    assert ranked[0].net_value_eur == pytest.approx(best_value, abs=0.01)
    values = [result.net_value_eur for result in ranked]
    assert values == sorted(values, reverse=True)


def test_every_scenario_is_returned_once():
    ranked = run_scenarios(DAYS["random_0"])
    assert sorted(result.name for result in ranked) == ["max_arbitrage", "preserve", "reserve"]


@pytest.mark.parametrize("day", DAYS.values(), ids=DAYS.keys())
def test_max_arbitrage_is_never_worth_less_than_preserve(day):
    """preserve is max_arbitrage with a tighter cycle limit (see scenarios.py)."""
    values = {r.name: r.net_value_eur for r in run_scenarios(day)}
    assert values["max_arbitrage"] >= values["preserve"] - 0.01


def test_on_a_tie_the_scenario_with_fewer_cycles_comes_first(two_block_day):
    """One profitable cycle only: max_arbitrage and preserve capture the same value."""
    ranked = [r for r in run_scenarios(two_block_day, reserve_price_eur_per_mw_h=0.0) if r.name != "reserve"]
    assert ranked[0].net_value_eur == pytest.approx(ranked[1].net_value_eur, abs=0.01)
    assert ranked[0].schedule.cycles <= ranked[1].schedule.cycles


def test_reserve_ranks_first_only_when_capacity_pays_enough():
    day = DAYS["random_0"]
    assert run_scenarios(day, reserve_price_eur_per_mw_h=0.0)[0].name != "reserve"
    assert run_scenarios(day, reserve_price_eur_per_mw_h=200.0)[0].name == "reserve"


def test_scenarios_derive_from_the_base_battery():
    base = BatteryConfig(round_trip_efficiency=0.9)
    for result in run_scenarios(DAYS["random_1"], base=base):
        assert result.schedule.battery.round_trip_efficiency == 0.9
