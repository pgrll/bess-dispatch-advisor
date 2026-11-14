"""Command-line report: the three scenarios and the exact intervals to use.

Examples:
    bess-advisor --prices data/sample/synthetic_day.csv
    bess-advisor --date 2026-11-14            # needs ENTSOE_API_TOKEN
    bess-advisor --prices data/sample/synthetic_day.csv --html dashboard.html

The report states where the prices come from and never recommends an
action: it ranks scenarios, the analyst decides.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from bess_advisor.config import REFERENCE_BATTERY
from bess_advisor.dashboard import build_dashboard, build_error_page
from bess_advisor.data.entsoe import fetch_day_ahead_prices
from bess_advisor.data.storage import load_prices_csv
from bess_advisor.data.validation import validate_day_prices
from bess_advisor.economics import check_cycle_value
from bess_advisor.scenarios import ScenarioResult, run_scenarios


def _format_interval(start: pd.Timestamp) -> str:
    return f"{start:%H:%M}-{start + pd.Timedelta(minutes=15):%H:%M}"


def format_report(prices: pd.Series, ranked: list[ScenarioResult], source: str) -> str:
    battery = REFERENCE_BATTERY
    check = check_cycle_value(prices, battery)
    day = prices.index[0].date()
    lines = [
        f"Day-ahead France - {day} - {len(prices)} intervals of 15 min",
        f"Source: {source}",
        f"Battery: {battery.power_mw:g} MW / {battery.energy_mwh:g} MWh, "
        f"round-trip efficiency {battery.round_trip_efficiency:.0%}, "
        f"wear cost {battery.degradation_cost_eur_per_mwh:g} EUR/MWh",
        "",
        "Is it worth cycling?",
        f"  {'Yes' if check.worth_cycling else 'No'}: best net spread "
        f"{check.net_spread_eur_per_mwh:+.2f} EUR/MWh "
        f"(buy {_format_interval(check.buy_interval)}, sell {_format_interval(check.sell_interval)})",
        "",
        "Scenarios, ranked by net value captured (EUR)",
        f"  {'#':<3}{'scenario':<16}{'net value':>11}{'arbitrage':>11}{'wear':>9}{'reserve':>9}"
        f"{'cycles':>8}{'per cycle':>11}",
    ]
    for rank, result in enumerate(ranked, start=1):
        s = result.schedule
        per_cycle = "-" if s.value_per_cycle_eur is None else f"{s.value_per_cycle_eur:,.0f}"
        lines.append(
            f"  {rank:<3}{result.name:<16}{s.net_value_eur:>11,.0f}{s.arbitrage_revenue_eur:>11,.0f}"
            f"{-s.degradation_cost_eur:>9,.0f}{s.reserve_revenue_eur:>9,.0f}{s.cycles:>8.2f}{per_cycle:>11}"
        )
    lines.append("  'per cycle' = arbitrage value net of wear, per full cycle (reserve income excluded).")

    top = ranked[0]
    lines += ["", f"Intervals of scenario #1 ({top.name}: {top.description})"]
    active = top.schedule.active_intervals()
    if active.empty:
        lines.append("  No interval used: the battery stays idle.")
    for start, row in active.iterrows():
        lines.append(
            f"  {_format_interval(start)}  {row['action']:<9} {abs(row['net_mw']):>6.1f} MW"
            f"  at {row['price_eur_mwh']:>8.2f} EUR/MWh   SoC after {row['soc_mwh']:>6.1f} MWh"
        )
    lines += ["", "These are suggestions. The dispatch decision stays with the analyst."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prices", help="CSV file of 15-minute prices (see data/README.md)")
    source.add_argument("--date", type=date.fromisoformat, help="delivery day to download from ENTSO-E")
    parser.add_argument("--html", metavar="PATH", help="write the HTML dashboard to PATH instead of printing a report")
    args = parser.parse_args(argv)
    synthetic = bool(args.prices) and "synthetic" in args.prices

    if args.html:
        sys.exit(_write_dashboard(args, synthetic))

    if args.prices:
        prices = validate_day_prices(load_prices_csv(args.prices))
        origin = f"file {args.prices}"
        if synthetic:
            origin += "  (SYNTHETIC prices for demonstration, not market data)"
    else:
        prices = fetch_day_ahead_prices(args.date)
        origin = "ENTSO-E Transparency Platform, document A44, bidding zone 10YFR-RTE------C"
    print(format_report(prices, run_scenarios(prices), origin))


def _write_dashboard(args: argparse.Namespace, synthetic: bool) -> int:
    """Write the dashboard, or a page explaining why it could not be built.

    Returns the process exit code: 0 on success, 1 when an error page was written.
    """
    output = Path(args.html)
    try:
        if args.prices:
            prices = validate_day_prices(load_prices_csv(args.prices))
            source = f"fichier {Path(args.prices).name}"
        else:
            prices = fetch_day_ahead_prices(args.date)
            source = "ENTSO-E Transparency Platform, prix de la veille, zone France"
        html = build_dashboard(prices, source=source, is_synthetic=synthetic)
        code = 0
    except Exception as error:  # noqa: BLE001 - every failure becomes an explained page
        html = build_error_page(error)
        print(f"Dashboard not built: {error}", file=sys.stderr)
        code = 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(f"Wrote {output}")
    return code


if __name__ == "__main__":
    main()
