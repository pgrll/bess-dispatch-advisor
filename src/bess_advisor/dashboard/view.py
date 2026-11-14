"""What the dashboard shows, computed once and kept free of HTML.

Separating the content (this module) from its rendering (``page.py``) lets
the tests check the messages and numbers without parsing HTML, and keeps
the rendering code free of business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from bess_advisor.dashboard import text
from bess_advisor.economics import CycleCheck
from bess_advisor.scenarios import ScenarioResult


@dataclass(frozen=True)
class IntervalRow:
    label: str
    action: str  # "charge", "discharge" or "idle"
    action_label: str
    power_mw: float
    price_eur_mwh: float
    soc_mwh: float


@dataclass(frozen=True)
class ScenarioView:
    key: str
    rank: int
    name: str
    explanation: str
    net_value_eur: float
    arbitrage_eur: float
    wear_eur: float
    reserve_eur: float
    cycles: float
    value_per_cycle_eur: float | None
    energy_bought_mwh: float
    energy_sold_mwh: float
    actions: list[str]  # one per interval
    soc_mwh: list[float]  # end of each interval
    rows: list[IntervalRow]  # active intervals only
    reserve_buffer_mwh: float

    @property
    def is_idle(self) -> bool:
        return not self.rows

    @property
    def summary(self) -> str:
        """One sentence describing the scenario's day."""
        if self.is_idle:
            return "La batterie reste au repos toute la journée : aucun échange ne rapporte assez."
        n_charge = sum(1 for r in self.rows if r.action == "charge")
        n_discharge = len(self.rows) - n_charge
        first_sale = next(r.label for r in self.rows if r.action == "discharge")
        return (
            f"La batterie se charge sur {n_charge} créneaux et se décharge sur {n_discharge} créneaux "
            f"de 15 minutes. Première vente : {first_sale}."
        )


@dataclass(frozen=True)
class DashboardView:
    title: str
    day_label: str
    source: str
    is_synthetic: bool
    generated_at: str
    interval_labels: list[str]
    hour_ticks: list[tuple[int, str]]  # (interval index, "06:00")
    prices: list[float]
    energy_mwh: float
    power_mw: float
    worth_cycling: bool
    verdict: str
    verdict_detail: str
    scenarios: list[ScenarioView]  # ranked, best first
    assumptions_note: str

    @property
    def best(self) -> ScenarioView:
        return self.scenarios[0]

    @property
    def headline(self) -> str:
        return f"Suggestion n°1 : {self.best.name}"

    @property
    def ranking_caveat(self) -> str | None:
        """Warn when suggestion n°1 owes its place to an unconfirmed assumption."""
        if self.best.key == "reserve" and self.best.reserve_eur > 0:
            runner_up = self.scenarios[1]
            if self.best.net_value_eur - self.best.reserve_eur <= runner_up.net_value_eur:
                return (
                    "Ce scénario n'arrive en tête que grâce à la rémunération de la réserve, "
                    "une hypothèse encore à confirmer (voir en bas de page)."
                )
        return None

    @property
    def comparison_line(self) -> str:
        """How far ahead suggestion n°1 is, in euros, in plain words."""
        gaps = [
            f"{s.name} rapporterait {text.euros(self.best.net_value_eur - s.net_value_eur)} de moins"
            for s in self.scenarios[1:]
        ]
        return "Par comparaison : " + " ; ".join(gaps) + "."


def _scenario_view(result: ScenarioResult, rank: int) -> ScenarioView:
    schedule = result.schedule
    df = schedule.intervals
    rows = [
        IntervalRow(
            label=text.interval_label(start),
            action=row["action"],
            action_label=text.ACTIONS[row["action"]],
            power_mw=abs(float(row["net_mw"])),
            price_eur_mwh=float(row["price_eur_mwh"]),
            soc_mwh=float(row["soc_mwh"]),
        )
        for start, row in schedule.active_intervals().iterrows()
    ]
    return ScenarioView(
        key=result.name,
        rank=rank,
        name=text.SCENARIO_NAMES.get(result.name, result.name),
        explanation=text.SCENARIO_EXPLANATIONS.get(result.name, result.description),
        net_value_eur=schedule.net_value_eur,
        arbitrage_eur=schedule.arbitrage_revenue_eur,
        wear_eur=schedule.degradation_cost_eur,
        reserve_eur=schedule.reserve_revenue_eur,
        cycles=schedule.cycles,
        value_per_cycle_eur=schedule.value_per_cycle_eur,
        energy_bought_mwh=schedule.energy_charged_mwh,
        energy_sold_mwh=schedule.energy_discharged_mwh,
        actions=df["action"].tolist(),
        soc_mwh=df["soc_mwh"].round(3).tolist(),
        rows=rows,
        reserve_buffer_mwh=schedule.battery.reserve_soc_buffer_mwh,
    )


def _hour_ticks(index: pd.DatetimeIndex) -> list[tuple[int, str]]:
    """A tick every 3 hours of local time, robust to clock-change days."""
    return [(i, f"{ts:%H:%M}") for i, ts in enumerate(index) if ts.minute == 0 and ts.hour % 3 == 0]


def build_view(
    prices: pd.Series,
    ranked: list[ScenarioResult],
    check: CycleCheck,
    source: str,
    is_synthetic: bool,
    generated_at: datetime | None = None,
) -> DashboardView:
    """Assemble everything the page displays."""
    battery = ranked[0].schedule.battery
    reserve = next((r.schedule.battery for r in ranked if r.name == "reserve"), battery)
    generated_at = generated_at or datetime.now().astimezone()

    if check.worth_cycling:
        verdict = "Oui, faire travailler la batterie est rentable"
    else:
        verdict = "Non, aucun échange n'est rentable"
    verdict_detail = (
        f"Meilleur écart net : {text.number(check.net_spread_eur_per_mwh, 2)} € par MWh revendu "
        f"(achat {text.interval_label(check.buy_interval)}, vente {text.interval_label(check.sell_interval)}), "
        "après pertes de conversion et usure."
    )

    return DashboardView(
        title=f"Batterie {battery.power_mw:g} MW / {battery.energy_mwh:g} MWh — marché de la veille, France",
        day_label=text.french_date(prices.index[0].date()),
        source=source,
        is_synthetic=is_synthetic,
        generated_at=f"{text.french_date(generated_at.date())} à {generated_at:%H:%M}",
        interval_labels=[text.interval_label(ts) for ts in prices.index],
        hour_ticks=_hour_ticks(prices.index),
        prices=[float(p) for p in prices],
        energy_mwh=battery.energy_mwh,
        power_mw=battery.power_mw,
        worth_cycling=check.worth_cycling,
        verdict=verdict,
        verdict_detail=verdict_detail,
        scenarios=[_scenario_view(r, rank) for rank, r in enumerate(ranked, start=1)],
        assumptions_note=(
            f"Hypothèses à confirmer : rendement {battery.round_trip_efficiency:.0%}".replace("%", " %")
            + f", usure {text.number(battery.degradation_cost_eur_per_mwh)} €/MWh, "
            f"rémunération de la réserve {text.number(reserve.reserve_price_eur_per_mw_h)} €/MW/h."
        ),
    )
