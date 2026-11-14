"""The dashboard must say the right thing, to everyone, and explain its failures.

Checks follow the four criteria set for the reader: clarity, hierarchy,
accessibility and feedback.
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

import numpy as np
import pytest

from bess_advisor.cli import main
from bess_advisor.config import REFERENCE_BATTERY
from bess_advisor.dashboard import build_dashboard, build_error_page
from bess_advisor.dashboard.page import _CSS
from bess_advisor.dashboard.view import build_view
from bess_advisor.data.entsoe import EntsoeError
from bess_advisor.data.validation import PriceDataError
from bess_advisor.economics import check_cycle_value
from bess_advisor.scenarios import run_scenarios
from tests.conftest import make_day, random_day

SAMPLE = Path(__file__).parents[1] / "data" / "sample" / "synthetic_day.csv"


def view_for(prices, **scenario_options):
    ranked = run_scenarios(prices, **scenario_options)
    return build_view(prices, ranked, check_cycle_value(prices, REFERENCE_BATTERY), "test", is_synthetic=False)


# --- Hierarchy: the most important thing comes first and looks it ---------------


def test_hero_shows_the_scenario_that_captures_the_most_value():
    view = view_for(random_day(0))
    assert view.best.net_value_eur == max(s.net_value_eur for s in view.scenarios)
    html = build_dashboard(random_day(0), source="test", is_synthetic=False)
    hero = html[html.index('class="card hero"') :]
    assert view.best.name in hero[: hero.index("</section>")]


def test_sections_come_in_order_of_importance():
    html = build_dashboard(random_day(0), source="test", is_synthetic=False)
    order = ["hero-title", "day-title", "compare-title", "detail-title", "help-title"]
    positions = [html.index(f'id="{anchor}"') for anchor in order]
    assert positions == sorted(positions)
    assert html.count('class="figure"') == 1, "exactly one hero figure"


# --- Clarity: every element says what it is -------------------------------------


def test_every_chart_has_a_title_and_a_text_description():
    html = build_dashboard(random_day(1), source="test", is_synthetic=False)
    charts = re.findall(r"<svg[^>]*>", html)
    assert len(charts) == 3
    for chart in charts:
        assert 'role="img"' in chart and "aria-labelledby" in chart
    assert html.count("<title id=") == 3 and html.count("<desc id=") == 3


def test_hero_warns_when_the_ranking_rests_on_an_unconfirmed_assumption():
    view = view_for(random_day(0))  # reserve wins only thanks to its assumed capacity price
    assert view.best.key == "reserve"
    assert view.ranking_caveat is not None
    assert view_for(make_day(np.full(96, 70.0))).ranking_caveat is not None
    assert view_for(random_day(0), reserve_price_eur_per_mw_h=0.0).ranking_caveat is None


def test_comparison_is_written_in_plain_euros():
    line = view_for(random_day(0)).comparison_line
    assert "de moins" in line and "€" in line


def test_flat_day_says_nothing_is_worth_doing():
    html = build_dashboard(make_day(np.full(96, 70.0)), source="test", is_synthetic=False)
    assert escape("Non, aucun échange n'est rentable") in html
    assert "reste au repos" in html


def test_suggestions_are_never_phrased_as_orders():
    html = build_dashboard(random_day(2), source="test", is_synthetic=False)
    assert "La décision de charge et de décharge reste la vôtre" in html
    for order in ("Vous devez", "Chargez", "Déchargez", "Il faut"):
        assert order not in html


def test_synthetic_data_is_flagged_and_real_data_is_not():
    assert "Données de démonstration" in build_dashboard(random_day(0), source="x", is_synthetic=True)
    assert "Données de démonstration" not in build_dashboard(random_day(0), source="x", is_synthetic=False)


@pytest.mark.parametrize(("day", "n"), [("2026-03-29", 92), ("2026-10-25", 100)])
def test_clock_change_days_show_their_true_number_of_intervals(day, n):
    hour = np.arange(n) / 4
    html = build_dashboard(make_day(60 + 40 * np.sin(hour / 24 * 4 * np.pi), day=day), source="t", is_synthetic=False)
    assert f"{n} créneaux de 15 minutes" in html


# --- Accessibility: readable by everyone ------------------------------------------


def _tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block))


def _luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


THEMES = {
    "light": _tokens(_CSS[: _CSS.index("@media (prefers-color-scheme: dark)")]),
    "dark": _tokens(_CSS[_CSS.index(':root[data-theme="dark"]') : _CSS.index("* {")]),
}


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize(
    ("ink", "background"),
    [("ink", "card"), ("ink-2", "card"), ("ink-2", "surface"), ("muted", "surface"),
     ("good", "good-bg"), ("bad", "bad-bg"), ("warn-ink", "warn-bg")],
)  # fmt: skip
def test_text_meets_wcag_aa_contrast(theme, ink, background):
    tokens = THEMES[theme]
    assert contrast(tokens[ink], tokens[background]) >= 4.5


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("mark", ["charge", "discharge", "price"])
def test_chart_marks_meet_graphical_contrast(theme, mark):
    tokens = THEMES[theme]
    assert contrast(tokens[mark], tokens["surface"]) >= 3.0


def test_no_text_smaller_than_13_pixels():
    sizes = [float(size) for size in re.findall(r"font-size:\s*([\d.]+)px", _CSS)]
    rem_sizes = [float(size) * 16 for size in re.findall(r"font-size:\s*([\d.]+)rem", _CSS)]
    assert min(sizes + rem_sizes) >= 13


def test_charge_and_discharge_never_rely_on_colour_alone():
    html = build_dashboard(random_day(0), source="test", is_synthetic=False)
    assert "▲" in html and "▼" in html  # shape in legends and table
    assert "Charge (moitié basse de la ligne)" in html  # position in the timeline
    assert re.search(r"<td><span class=\"action\">.*?Charge</span></td>", html)  # words in the table


def test_page_declares_its_language_and_scales_on_phones():
    html = build_dashboard(random_day(0), source="test", is_synthetic=False)
    assert '<html lang="fr">' in html and 'name="viewport"' in html


# --- Feedback: failures are explained, never shown raw ---------------------------------


@pytest.mark.parametrize(
    "error",
    [
        PriceDataError("1 interval(s) have no price"),
        EntsoeError("ENTSO-E rejected the API token (HTTP 401)."),
        EntsoeError("ENTSO-E returned no data: No matching data found"),
        EntsoeError("Could not reach the ENTSO-E platform."),
        FileNotFoundError("prices.csv"),
        RuntimeError("something unexpected"),
    ],
)
def test_error_page_says_what_happened_what_to_do_and_where_to_get_help(error):
    html = build_error_page(error)
    for heading in ("Ce qui s'est passé", "Que faire maintenant", "Obtenir de l'aide"):
        assert heading in html
    # The raw error is only inside the folded technical detail.
    visible = html[: html.index("<details>")]
    assert type(error).__name__ not in visible


def test_cli_writes_the_dashboard(tmp_path, capsys):
    output = tmp_path / "dashboard.html"
    with pytest.raises(SystemExit) as exit_info:
        main(["--prices", str(SAMPLE), "--html", str(output)])
    assert exit_info.value.code == 0
    assert "Suggestion n°1" in output.read_text(encoding="utf-8")


def test_cli_writes_an_explained_error_page_when_data_is_missing(tmp_path):
    output = tmp_path / "dashboard.html"
    with pytest.raises(SystemExit) as exit_info:
        main(["--prices", str(tmp_path / "missing.csv"), "--html", str(output)])
    assert exit_info.value.code == 1
    assert "Le fichier de prix indiqué est introuvable" in output.read_text(encoding="utf-8")
