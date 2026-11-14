"""Battery and market parameters.

Every number here is either a fixed design choice of the project or an
explicit assumption. Assumptions are marked ``ASSUMPTION`` and listed in
``docs/05_decision_log.md`` so they can be challenged and recalibrated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

#: Length of one day-ahead market time unit, in hours. The European
#: day-ahead market (SDAC) moved to a 15-minute resolution in 2025.
INTERVAL_HOURS: float = 0.25


@dataclass(frozen=True)
class BatteryConfig:
    """Physical and economic parameters of the reference battery.

    Attributes:
        power_mw: Maximum charge and discharge power, measured at the grid.
        energy_mwh: Usable energy capacity of the battery.
        round_trip_efficiency: Fraction of the energy bought back out of
            the battery, split evenly between charging and discharging.
        degradation_cost_eur_per_mwh: Cost of wear charged on every MWh
            discharged to the grid.
        max_cycles_per_day: Upper bound on full equivalent cycles per day.
        initial_soc_mwh: State of charge at the start of the day. The
            optimiser must end the day at least at this level, so the
            schedule never "sells" energy it did not buy that day.
        reserve_mw: Power withheld from arbitrage for balancing services.
        reserve_energy_hours: Energy kept in both directions for each
            reserved MW (a reserve must be deliverable up and down).
        reserve_price_eur_per_mw_h: Capacity price earned per reserved MW
            and per hour.
    """

    power_mw: float = 100.0
    energy_mwh: float = 200.0
    round_trip_efficiency: float = 0.85  # ASSUMPTION: typical Li-ion BESS, AC-to-AC
    degradation_cost_eur_per_mwh: float = 10.0  # ASSUMPTION: to calibrate
    max_cycles_per_day: float = 2.0  # ASSUMPTION: typical warranty-compatible upper bound
    initial_soc_mwh: float = 0.0
    reserve_mw: float = 0.0
    reserve_energy_hours: float = 0.5  # ASSUMPTION: simplified FCR/aFRR energy requirement
    reserve_price_eur_per_mw_h: float = 0.0

    def __post_init__(self) -> None:
        if self.power_mw <= 0 or self.energy_mwh <= 0:
            raise ValueError("power_mw and energy_mwh must be positive")
        if not 0 < self.round_trip_efficiency <= 1:
            raise ValueError("round_trip_efficiency must be in (0, 1]")
        if self.degradation_cost_eur_per_mwh < 0:
            raise ValueError("degradation_cost_eur_per_mwh must be >= 0")
        if self.max_cycles_per_day <= 0:
            raise ValueError("max_cycles_per_day must be positive")
        if not 0 <= self.reserve_mw < self.power_mw:
            raise ValueError("reserve_mw must be in [0, power_mw)")
        if not 0 <= self.initial_soc_mwh <= self.energy_mwh:
            raise ValueError("initial_soc_mwh must be within the battery capacity")
        if 2 * self.reserve_soc_buffer_mwh > self.energy_mwh:
            raise ValueError("the reserve energy buffer does not fit in the battery")

    @property
    def charge_efficiency(self) -> float:
        """One-way efficiency, grid to battery."""
        return math.sqrt(self.round_trip_efficiency)

    @property
    def discharge_efficiency(self) -> float:
        """One-way efficiency, battery to grid."""
        return math.sqrt(self.round_trip_efficiency)

    @property
    def arbitrage_power_mw(self) -> float:
        """Power left for energy arbitrage once the reserve is withheld."""
        return self.power_mw - self.reserve_mw

    @property
    def reserve_soc_buffer_mwh(self) -> float:
        """Energy kept free at both ends of the state of charge for the reserve."""
        return self.reserve_mw * self.reserve_energy_hours

    @property
    def duration_hours(self) -> float:
        return self.energy_mwh / self.power_mw

    def with_changes(self, **changes: float) -> BatteryConfig:
        """Return a copy with some parameters changed (used to build scenarios)."""
        return replace(self, **changes)


#: The reference asset of the project: 100 MW / 200 MWh (2 hours).
REFERENCE_BATTERY = BatteryConfig()
