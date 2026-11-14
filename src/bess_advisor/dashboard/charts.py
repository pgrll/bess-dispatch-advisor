"""Charts drawn as inline SVG, with no plotting library.

Inline SVG keeps the dashboard a single file that opens offline in any
browser, prints cleanly, and can be read by screen readers (each chart has
a title and a text description).

Encoding rules, so meaning never depends on colour alone:

* charge = upward triangle, drawn in the lower half of timeline rows;
* discharge = downward triangle, drawn in the upper half;
* every chart is backed by a table elsewhere on the page.

Day-ahead prices are constant over each 15-minute interval, so prices and
state of charge are drawn as steps, not as lines between points.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from html import escape

# Geometry shared by every chart so their time axes line up.
WIDTH = 720
LEFT, RIGHT = 64, 16
PLOT_WIDTH = WIDTH - LEFT - RIGHT
PRICE_HEIGHT, PRICE_TOP, PRICE_BOTTOM = 330.0, 14.0, 44.0
MARK_OFFSET = 9.0


def nice_ticks(low: float, high: float, target: int = 5) -> list[float]:
    """Round axis values covering [low, high], about ``target`` of them."""
    if math.isclose(low, high):
        low, high = low - 1, high + 1
    raw_step = (high - low) / target
    magnitude = 10 ** math.floor(math.log10(raw_step))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw_step)
    first = math.floor(low / step) * step
    ticks, value = [], first
    while value < high + step * 0.999:
        ticks.append(round(value, 10))
        value += step
    return ticks


def _x(i: float, n: int) -> float:
    return LEFT + PLOT_WIDTH * i / n


def _fmt(value: float) -> str:
    return f"{value:.1f}"


def _step_path(values: Sequence[float], y_of, n: int) -> str:
    points = []
    for i, value in enumerate(values):
        y = _fmt(y_of(value))
        points.append(f"{'M' if i == 0 else 'L'}{_fmt(_x(i, n))},{y} L{_fmt(_x(i + 1, n))},{y}")
    return " ".join(points)


def _triangle(cx: float, cy: float, up: bool, size: float = 6.0) -> str:
    h = size * 0.95
    if up:
        pts = [(cx, cy - h), (cx - size, cy + h * 0.6), (cx + size, cy + h * 0.6)]
    else:
        pts = [(cx, cy + h), (cx - size, cy - h * 0.6), (cx + size, cy - h * 0.6)]
    return " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in pts)


def _x_axis(hour_ticks: list[tuple[int, str]], n: int, y: float) -> str:
    parts = [f'<line class="axis" x1="{LEFT}" x2="{WIDTH - RIGHT}" y1="{_fmt(y)}" y2="{_fmt(y)}"/>']
    for i, label in hour_ticks:
        x = _fmt(_x(i, n))
        parts.append(f'<line class="tick" x1="{x}" x2="{x}" y1="{_fmt(y)}" y2="{_fmt(y + 5)}"/>')
        parts.append(f'<text class="tick-label" x="{x}" y="{_fmt(y + 20)}" text-anchor="middle">{label}</text>')
    return "".join(parts)


def _svg(height: float, title: str, description: str, body: str, chart_id: str) -> str:
    return (
        f'<svg class="chart" viewBox="0 0 {WIDTH} {_fmt(height)}" role="img" '
        f'aria-labelledby="{chart_id}-title {chart_id}-desc" data-chart="{chart_id}">'
        f'<title id="{chart_id}-title">{escape(title)}</title>'
        f'<desc id="{chart_id}-desc">{escape(description)}</desc>{body}</svg>'
    )


def price_chart(
    prices: Sequence[float],
    hour_ticks: list[tuple[int, str]],
    scenario_actions: dict[str, list[str]],
    selected: str,
    description: str,
) -> str:
    """Price over the day, with the charge and discharge intervals of each scenario.

    Every scenario's marks are drawn; only the selected one is visible. The
    page script switches visibility, so the chart works without a server.
    """
    n = len(prices)
    height, top, bottom = PRICE_HEIGHT, PRICE_TOP, PRICE_BOTTOM
    ticks = nice_ticks(min(min(prices), 0.0), max(prices))
    # Leave room for the marks drawn beside extreme prices, without adding a tick.
    margin = 0.06 * (max(prices) - min(min(prices), 0.0) or 1.0)
    lo, hi = min(ticks[0], min(prices) - margin), max(ticks[-1], max(prices) + margin)

    def y_of(value: float) -> float:
        return top + (height - top - bottom) * (hi - value) / (hi - lo)

    parts = []
    # Negative-price zone first, so everything else draws on top of it.
    if lo < 0:
        parts.append(
            f'<rect class="negative-zone" x="{LEFT}" y="{_fmt(y_of(0))}" width="{PLOT_WIDTH}" '
            f'height="{_fmt(y_of(lo) - y_of(0))}"/>'
            f'<text class="zone-label" x="{LEFT + 8}" y="{_fmt(y_of(lo) - 8)}">Prix négatifs</text>'
        )
    for tick in ticks:
        y = _fmt(y_of(tick))
        css = "grid zero" if tick == 0 else "grid"
        parts.append(f'<line class="{css}" x1="{LEFT}" x2="{WIDTH - RIGHT}" y1="{y}" y2="{y}"/>')
        parts.append(f'<text class="tick-label" x="{LEFT - 8}" y="{y}" dy="0.32em" text-anchor="end">{tick:g}</text>')
    parts.append(
        f'<text class="axis-title" transform="translate(14 {_fmt((height - bottom) / 2)}) rotate(-90)" '
        'text-anchor="middle">€/MWh</text>'
    )

    width = PLOT_WIDTH / n
    bands, marks = [], []
    for key, actions in scenario_actions.items():
        hidden = "" if key == selected else " hidden"
        band_group = [f'<g class="scenario-layer" data-scenario="{key}"{hidden}>']
        mark_group = [f'<g class="scenario-layer" data-scenario="{key}"{hidden}>']
        for i, action in enumerate(actions):
            if action == "idle":
                continue
            band_group.append(
                f'<rect class="band {action}" x="{_fmt(_x(i, n))}" y="{top}" '
                f'width="{_fmt(width)}" height="{_fmt(height - top - bottom)}"/>'
            )
            # Charge marks sit just below the price, discharge marks just above,
            # pointing at the price so the line never hides them.
            up = action == "charge"
            cy = y_of(prices[i]) + (MARK_OFFSET if up else -MARK_OFFSET)
            mark_group.append(f'<polygon class="mark {action}" points="{_triangle(_x(i + 0.5, n), cy, up)}"/>')
        bands.append("".join(band_group) + "</g>")
        marks.append("".join(mark_group) + "</g>")

    parts.extend(bands)
    parts.append(f'<path class="price-line" d="{_step_path(prices, y_of, n)}"/>')
    parts.extend(marks)
    parts.append(_x_axis(hour_ticks, n, height - bottom))
    parts.append(
        f'<rect class="hover-zone" x="{LEFT}" y="{top}" width="{PLOT_WIDTH}" height="{_fmt(height - top - bottom)}"/>'
    )
    return _svg(height, "Prix de l'électricité par créneau de 15 minutes", description, "".join(parts), "price")


def soc_chart(
    scenario_soc: dict[str, list[float]],
    buffers: dict[str, float],
    energy_mwh: float,
    hour_ticks: list[tuple[int, str]],
    selected: str,
    description: str,
) -> str:
    """Energy stored in the battery at the end of each interval."""
    n = len(next(iter(scenario_soc.values())))
    height, top, bottom = 190.0, 12.0, 44.0
    ticks = nice_ticks(0, energy_mwh, 4)

    def y_of(value: float) -> float:
        return top + (height - top - bottom) * (energy_mwh - value) / energy_mwh

    parts = []
    for tick in ticks:
        if tick > energy_mwh:
            continue
        y = _fmt(y_of(tick))
        parts.append(f'<line class="grid" x1="{LEFT}" x2="{WIDTH - RIGHT}" y1="{y}" y2="{y}"/>')
        parts.append(f'<text class="tick-label" x="{LEFT - 8}" y="{y}" dy="0.32em" text-anchor="end">{tick:g}</text>')
    parts.append(
        f'<text class="axis-title" transform="translate(14 {_fmt((height - bottom) / 2)}) rotate(-90)" '
        'text-anchor="middle">MWh</text>'
    )
    for key, soc in scenario_soc.items():
        hidden = "" if key == selected else " hidden"
        line = _step_path(soc, y_of, n)
        area = f"{line} L{_fmt(_x(n, n))},{_fmt(y_of(0))} L{_fmt(_x(0, n))},{_fmt(y_of(0))} Z"
        group = [f'<g class="scenario-layer" data-scenario="{key}"{hidden}>']
        group.append(f'<path class="soc-area" d="{area}"/><path class="soc-line" d="{line}"/>')
        buffer = buffers.get(key, 0.0)
        if buffer > 0:
            for level in (buffer, energy_mwh - buffer):
                y = _fmt(y_of(level))
                group.append(f'<line class="reserve-limit" x1="{LEFT}" x2="{WIDTH - RIGHT}" y1="{y}" y2="{y}"/>')
            group.append(
                f'<text class="zone-label" x="{WIDTH - RIGHT - 6}" y="{_fmt(y_of(energy_mwh - buffer) - 6)}" '
                'text-anchor="end">Limites gardées pour la réserve</text>'
            )
        group.append("</g>")
        parts.append("".join(group))
    parts.append(_x_axis(hour_ticks, n, height - bottom))
    return _svg(height, "Énergie stockée dans la batterie", description, "".join(parts), "soc")


def timeline_chart(
    rows: list[tuple[str, list[str]]],
    hour_ticks: list[tuple[int, str]],
    description: str,
) -> str:
    """One row per scenario: when it charges (lower half) and discharges (upper half)."""
    n = len(rows[0][1])
    row_height, gap, top, bottom = 34.0, 14.0, 8.0, 40.0
    height = top + len(rows) * (row_height + gap) - gap + bottom
    width = PLOT_WIDTH / n
    parts = []
    for r, (label, actions) in enumerate(rows):
        y0 = top + r * (row_height + gap)
        mid = y0 + row_height / 2
        parts.append(
            f'<rect class="row-bg" x="{LEFT}" y="{_fmt(y0)}" width="{PLOT_WIDTH}" height="{row_height}"/>'
            f'<text class="row-label" x="{LEFT - 8}" y="{_fmt(mid)}" dy="0.32em" text-anchor="end">'
            f"{escape(label)}</text>"
        )
        for i, action in enumerate(actions):
            if action == "idle":
                continue
            y = mid if action == "charge" else y0
            parts.append(
                f'<rect class="block {action}" x="{_fmt(_x(i, n))}" y="{_fmt(y)}" '
                f'width="{_fmt(width)}" height="{_fmt(row_height / 2)}"/>'
            )
    parts.append(_x_axis(hour_ticks, n, height - bottom))
    return _svg(height, "Créneaux utilisés par chaque scénario", description, "".join(parts), "timeline")
