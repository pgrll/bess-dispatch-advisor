"""Optimal day-ahead dispatch of a battery, interval by interval.

The schedule is the solution of a mixed-integer linear programme (MILP)
solved with HiGHS through ``scipy.optimize.milp``. It is deterministic: the
same prices and parameters always give the same schedule, which is what
makes it testable and auditable. The LLM agent explains this schedule; it
never computes one.

Formulation, for each 15-minute interval ``t`` of length ``dt`` hours:

    variables   c_t  charging power (MW, grid side)        0 <= c_t <= P
                d_t  discharging power (MW, grid side)     0 <= d_t <= P
                s_t  state of charge at the end of t (MWh)  b <= s_t <= E - b
                u_t  1 if charging, 0 otherwise (binary)

    maximise    sum_t  price_t * (d_t - c_t) * dt  -  k * d_t * dt

    subject to  s_t = s_{t-1} + eta_c * c_t * dt - d_t * dt / eta_d
                c_t <= P * u_t ;  d_t <= P * (1 - u_t)      (no simultaneous charge and discharge)
                sum_t d_t * dt / eta_d <= N * E              (at most N full cycles)
                s_T >= s_0                                   (no energy sold that was not bought)

where ``P`` is the arbitrage power (rated power minus any reserve), ``b``
the energy buffer kept for the reserve and ``k`` the degradation cost.

The binary ``u_t`` matters on negative-price days: without it, the solver
can charge and discharge at the same time to burn energy in conversion
losses and get paid for it, which a real battery cannot do on demand.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from bess_advisor.config import INTERVAL_HOURS, BatteryConfig

#: Values smaller than this (MW or MWh) are solver noise and set to zero.
_TOLERANCE = 1e-6


class OptimizationError(RuntimeError):
    """Raised when the solver cannot find an optimal schedule."""


@dataclass(frozen=True)
class Schedule:
    """An optimal schedule and its economics.

    Attributes:
        intervals: One row per interval with columns ``price_eur_mwh``,
            ``charge_mw``, ``discharge_mw``, ``net_mw`` (positive when
            selling), ``soc_mwh`` (end of interval) and ``action``.
        battery: The parameters the schedule was computed with.
    """

    intervals: pd.DataFrame
    battery: BatteryConfig

    @property
    def energy_charged_mwh(self) -> float:
        """Energy bought from the grid."""
        return float(self.intervals["charge_mw"].sum() * INTERVAL_HOURS)

    @property
    def energy_discharged_mwh(self) -> float:
        """Energy sold to the grid."""
        return float(self.intervals["discharge_mw"].sum() * INTERVAL_HOURS)

    @property
    def cycles(self) -> float:
        """Full equivalent cycles, measured on the battery side."""
        out_of_battery = self.energy_discharged_mwh / self.battery.discharge_efficiency
        return out_of_battery / self.battery.energy_mwh

    @property
    def arbitrage_revenue_eur(self) -> float:
        """Energy sold minus energy bought, at day-ahead prices."""
        net = self.intervals["net_mw"] * self.intervals["price_eur_mwh"] * INTERVAL_HOURS
        return float(net.sum())

    @property
    def degradation_cost_eur(self) -> float:
        return self.energy_discharged_mwh * self.battery.degradation_cost_eur_per_mwh

    @property
    def reserve_revenue_eur(self) -> float:
        """Capacity revenue of the reserved power over the whole day."""
        hours = len(self.intervals) * INTERVAL_HOURS
        return self.battery.reserve_mw * self.battery.reserve_price_eur_per_mw_h * hours

    @property
    def net_value_eur(self) -> float:
        """Value captured over the day: the quantity used to rank scenarios."""
        return self.arbitrage_revenue_eur - self.degradation_cost_eur + self.reserve_revenue_eur

    def active_intervals(self) -> pd.DataFrame:
        """Only the intervals where the battery charges or discharges."""
        return self.intervals[self.intervals["action"] != "idle"]


def optimise_day(prices: pd.Series, battery: BatteryConfig) -> Schedule:
    """Compute the value-maximising schedule for one delivery day.

    Args:
        prices: Validated 15-minute prices in EUR/MWh (see
            :func:`bess_advisor.data.validation.validate_day_prices`).
        battery: Battery and reserve parameters.

    Returns:
        The optimal :class:`Schedule`.

    Raises:
        OptimizationError: If the solver does not reach an optimal solution.
    """
    p = prices.to_numpy(dtype=float)
    n = len(p)
    dt = INTERVAL_HOURS
    power = battery.arbitrage_power_mw
    buffer = battery.reserve_soc_buffer_mwh
    eta_c, eta_d = battery.charge_efficiency, battery.discharge_efficiency
    s0 = battery.initial_soc_mwh

    # Variable layout: [c_0..c_{n-1}, d_0..d_{n-1}, s_0..s_{n-1}, u_0..u_{n-1}]
    c, d, s, u = (np.arange(n) + k * n for k in range(4))

    # scipy minimises, so the objective is the negative of the value.
    cost = np.zeros(4 * n)
    cost[c] = p * dt
    cost[d] = -(p - battery.degradation_cost_eur_per_mwh) * dt

    lower = np.zeros(4 * n)
    upper = np.empty(4 * n)
    upper[c] = upper[d] = power
    lower[s], upper[s] = buffer, battery.energy_mwh - buffer
    upper[u] = 1
    integrality = np.zeros(4 * n)
    integrality[u] = 1

    rows = 3 * n + 2
    a = lil_matrix((rows, 4 * n))
    lo, hi = np.zeros(rows), np.zeros(rows)

    for t in range(n):
        # State-of-charge balance (equality).
        a[t, s[t]] = 1.0
        a[t, c[t]] = -eta_c * dt
        a[t, d[t]] = dt / eta_d
        if t > 0:
            a[t, s[t - 1]] = -1.0
        lo[t] = hi[t] = s0 if t == 0 else 0.0

        # Charging only when u_t = 1, discharging only when u_t = 0.
        a[n + t, c[t]], a[n + t, u[t]] = 1.0, -power
        lo[n + t], hi[n + t] = -np.inf, 0.0
        a[2 * n + t, d[t]], a[2 * n + t, u[t]] = 1.0, power
        lo[2 * n + t], hi[2 * n + t] = -np.inf, power

    # Daily cycle limit, on energy leaving the battery.
    a[3 * n, d] = dt / eta_d
    lo[3 * n], hi[3 * n] = -np.inf, battery.max_cycles_per_day * battery.energy_mwh

    # End the day with at least the energy we started with.
    a[3 * n + 1, s[n - 1]] = 1.0
    lo[3 * n + 1], hi[3 * n + 1] = s0, np.inf

    result = milp(
        c=cost,
        constraints=LinearConstraint(a.tocsr(), lo, hi),
        bounds=Bounds(lower, upper),
        integrality=integrality,
    )
    if not result.success:
        raise OptimizationError(f"Solver did not find an optimal schedule: {result.message}")

    x = np.where(np.abs(result.x) < _TOLERANCE, 0.0, result.x)
    charge, discharge = x[c], x[d]
    intervals = pd.DataFrame(
        {
            "price_eur_mwh": p,
            "charge_mw": charge,
            "discharge_mw": discharge,
            "net_mw": discharge - charge,
            "soc_mwh": x[s],
        },
        index=prices.index,
    )
    intervals["action"] = np.select([charge > 0, discharge > 0], ["charge", "discharge"], default="idle")
    return Schedule(intervals=intervals, battery=battery)
