"""Assemble the dashboard as one self-contained HTML file.

No framework and no network access: the file opens offline in any browser,
can be e-mailed, and can be published as a static page. The page reads top
to bottom in order of importance:

1. the suggestion and its value (what to look at first);
2. the chosen scenario on the day's prices (when the battery works);
3. the comparison of the three scenarios (what the alternatives cost);
4. every interval in a table (the detail an analyst checks);
5. how to read the page, sources and assumptions.
"""

from __future__ import annotations

import json
from html import escape

from bess_advisor.dashboard import charts, text
from bess_advisor.dashboard.view import DashboardView, ScenarioView

_CSS = """
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --card: #ffffff;
  --ink: #0b0b0b; --ink-2: #52514e; --muted: #6e6c66;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --charge: #2a78d6; --discharge: #eb6834; --price: #3d3c39;
  --charge-wash: rgba(42,120,214,0.12); --discharge-wash: rgba(235,104,52,0.12);
  --negative-wash: rgba(42,120,214,0.06);
  --good: #006300; --good-bg: #e7f3e7; --bad: #9f2b2b; --bad-bg: #fbeaea;
  --warn-bg: #fff4d6; --warn-ink: #5c4300; --focus: #1c5cab;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --card: #1f1f1e;
    --ink: #f0efec; --ink-2: #c3c2b7; --muted: #a3a29b;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --charge: #3987e5; --discharge: #d95926; --price: #e4e3de;
    --charge-wash: rgba(57,135,229,0.18); --discharge-wash: rgba(217,89,38,0.18);
    --negative-wash: rgba(57,135,229,0.08);
    --good: #4cc24c; --good-bg: #13301a; --bad: #f08080; --bad-bg: #3a1717;
    --warn-bg: #3a2e05; --warn-ink: #f6d77a; --focus: #86b6ef;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --card: #1f1f1e;
  --ink: #f0efec; --ink-2: #c3c2b7; --muted: #a3a29b;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
  --charge: #3987e5; --discharge: #d95926; --price: #e4e3de;
  --charge-wash: rgba(57,135,229,0.18); --discharge-wash: rgba(217,89,38,0.18);
  --negative-wash: rgba(57,135,229,0.08);
  --good: #4cc24c; --good-bg: #13301a; --bad: #f08080; --bad-bg: #3a1717;
  --warn-bg: #3a2e05; --warn-ink: #f6d77a; --focus: #86b6ef;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--page); color: var(--ink);
  font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
}
main { max-width: 1040px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 1.5rem; line-height: 1.25; margin: 4px 0 6px; }
h2 { font-size: 1.25rem; margin: 0 0 4px; }
h3 { font-size: 1rem; margin: 0 0 8px; }
p { margin: 0 0 8px; }
a { color: var(--focus); }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.eyebrow { color: var(--ink-2); font-size: 0.875rem; font-weight: 600; letter-spacing: 0.02em; margin: 0; }
.meta { color: var(--ink-2); font-size: 0.9375rem; }
.lead { color: var(--ink-2); max-width: 70ch; }
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 20px; margin-top: 16px;
}
.banner {
  display: flex; gap: 10px; align-items: flex-start; border-radius: 10px;
  padding: 12px 14px; margin-top: 16px; background: var(--warn-bg); color: var(--warn-ink); font-weight: 500;
}
.banner .icon { font-size: 1.25rem; line-height: 1.2; }
.hero { display: grid; gap: 4px; }
.hero .figure { font-size: clamp(2.5rem, 7vw, 3.5rem); font-weight: 650; line-height: 1.1; margin: 6px 0 2px; }
.hero .figure-unit { color: var(--ink-2); font-size: 1rem; }
.verdict {
  display: inline-flex; gap: 8px; align-items: center; border-radius: 999px;
  padding: 6px 14px; font-weight: 600; margin-top: 12px; width: fit-content;
}
.verdict.good { background: var(--good-bg); color: var(--good); }
.verdict.bad { background: var(--bad-bg); color: var(--bad); }
.note { color: var(--ink-2); font-size: 0.9375rem; }
.decision { border-left: 3px solid var(--axis); padding-left: 10px; margin-top: 12px; color: var(--ink-2); }
.selector { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 4px; }
.selector button {
  font: inherit; text-align: left; cursor: pointer; border-radius: 10px; padding: 10px 14px;
  border: 1px solid var(--border); background: var(--surface); color: var(--ink); min-width: 200px;
}
.selector button[aria-pressed="true"] { border: 2px solid var(--ink); padding: 9px 13px; background: var(--card); }
.selector .rank { display: block; font-size: 0.8125rem; color: var(--ink-2); font-weight: 600; }
.selector .name { display: block; font-weight: 600; }
.selector .value { display: block; font-size: 0.9375rem; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 12px; }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; }
.tile .label { font-size: 0.875rem; color: var(--ink-2); }
.tile .value { font-size: 1.25rem; font-weight: 650; }
.legend { display: flex; flex-wrap: wrap; gap: 16px; margin: 8px 0; font-size: 0.9375rem; color: var(--ink-2); }
.key { display: inline-flex; align-items: center; gap: 6px; }
.chart-wrap { position: relative; overflow-x: auto; }
.chart { display: block; width: 100%; min-width: 720px; height: auto; background: var(--surface); border-radius: 8px; }
.chart text { fill: var(--ink-2); font-size: 14px; }
.chart .axis-title { fill: var(--muted); font-size: 13px; }
.chart .zone-label { fill: var(--muted); font-size: 13px; }
.chart .row-label { fill: var(--ink); font-size: 14px; font-weight: 600; }
.grid { stroke: var(--grid); stroke-width: 1; }
.grid.zero, .axis { stroke: var(--axis); stroke-width: 1.5; }
.tick { stroke: var(--axis); }
.negative-zone { fill: var(--negative-wash); }
.band.charge { fill: var(--charge-wash); }
.band.discharge { fill: var(--discharge-wash); }
.mark { stroke: var(--surface); stroke-width: 2; }
.mark.charge, .block.charge, .swatch.charge { fill: var(--charge); background: var(--charge); }
.mark.discharge, .block.discharge, .swatch.discharge { fill: var(--discharge); background: var(--discharge); }
.price-line { fill: none; stroke: var(--price); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.soc-area { fill: var(--charge-wash); }
.soc-line { fill: none; stroke: var(--charge); stroke-width: 2; }
.reserve-limit { stroke: var(--muted); stroke-width: 1; }
.row-bg { fill: var(--page); }
.block { stroke: var(--surface); stroke-width: 0.5; }
.hover-zone { fill: transparent; cursor: crosshair; }
.crosshair { stroke: var(--ink-2); stroke-width: 1; pointer-events: none; }
.tooltip {
  position: absolute; pointer-events: none; background: var(--card); color: var(--ink);
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; font-size: 0.875rem;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12); white-space: nowrap; z-index: 2;
}
.tooltip strong { display: block; }
.bars { display: grid; gap: 10px; margin: 12px 0 16px; }
.bar-row { display: grid; grid-template-columns: minmax(150px, 220px) 1fr; gap: 12px; align-items: center; }
.bar-label { font-weight: 600; }
.bar-label small { display: block; font-weight: 400; color: var(--ink-2); }
.bar-track { display: flex; align-items: center; gap: 8px; }
.bar { height: 20px; background: var(--price); border-radius: 0 4px 4px 0; min-width: 2px; }
.bar-value { font-variant-numeric: tabular-nums; white-space: nowrap; }
table { border-collapse: collapse; width: 100%; font-size: 0.9375rem; }
caption { text-align: left; color: var(--ink-2); padding-bottom: 8px; }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--grid); text-align: left; }
th { font-weight: 600; color: var(--ink-2); font-size: 0.875rem; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.table-wrap { overflow-x: auto; }
.action { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; }
.swatch { display: inline-block; width: 12px; height: 12px; border-radius: 2px; }
.glyph { font-size: 0.8125rem; }
.glyph.charge { color: var(--charge); }
.glyph.discharge { color: var(--discharge); }
.line-key { display: inline-block; width: 18px; height: 2px; background: var(--price); }
dl { display: grid; grid-template-columns: minmax(140px, 220px) 1fr; gap: 8px 16px; margin: 8px 0 0; }
dt { font-weight: 600; }
dd { margin: 0; color: var(--ink-2); }
footer { margin-top: 24px; color: var(--ink-2); font-size: 0.9375rem; }
footer p { margin-bottom: 6px; }
.error-steps li { margin-bottom: 6px; }
details summary { cursor: pointer; color: var(--ink-2); }
pre { white-space: pre-wrap; background: var(--surface); padding: 10px; border-radius: 8px; font-size: 0.875rem; }
[hidden] { display: none !important; }
@media (max-width: 640px) {
  dl { grid-template-columns: 1fr; }
  dd { margin-bottom: 8px; }
  .bar-row { grid-template-columns: 1fr; gap: 4px; }
  .selector button { min-width: 100%; }
}
@media print {
  .selector, .tooltip { display: none; }
  .card { break-inside: avoid; }
}
"""

_SCRIPT = """
(() => {
  const data = JSON.parse(document.getElementById('dashboard-data').textContent);
  let current = data.selected;

  function select(key) {
    current = key;
    // toggleAttribute, not the .hidden property: SVG elements have no .hidden property.
    document.querySelectorAll('[data-scenario]')
      .forEach(el => el.toggleAttribute('hidden', el.dataset.scenario !== key));
    document.querySelectorAll('.selector button').forEach(b => {
      b.setAttribute('aria-pressed', String(b.dataset.select === key));
    });
    const status = document.getElementById('selection-status');
    if (status) status.textContent = 'Scénario affiché : ' + data.names[key];
  }
  document.querySelectorAll('.selector button')
    .forEach(b => b.addEventListener('click', () => select(b.dataset.select)));

  const svg = document.querySelector('svg[data-chart="price"]');
  const wrap = svg && svg.closest('.chart-wrap');
  if (!svg || !wrap) return;
  const ns = 'http://www.w3.org/2000/svg';
  const tip = document.createElement('div');
  tip.className = 'tooltip'; tip.hidden = true; tip.setAttribute('role', 'status');
  wrap.appendChild(tip);
  const cross = document.createElementNS(ns, 'line');
  cross.setAttribute('class', 'crosshair'); cross.setAttribute('y1', data.plot.top);
  cross.setAttribute('y2', data.plot.bottom); cross.style.display = 'none';
  svg.appendChild(cross);

  svg.addEventListener('mousemove', event => {
    const box = svg.getBoundingClientRect();
    const x = (event.clientX - box.left) * (data.plot.width / box.width);
    const i = Math.floor((x - data.plot.left) / (data.plot.plotWidth / data.labels.length));
    if (i < 0 || i >= data.labels.length) { hide(); return; }
    const cx = data.plot.left + (i + 0.5) * data.plot.plotWidth / data.labels.length;
    cross.setAttribute('x1', cx); cross.setAttribute('x2', cx); cross.style.display = '';
    const action = data.actions[current][i];
    const power = data.power[current][i];
    const doing = action === 'charge' ? '▲ Charge ' + power + ' MW'
      : action === 'discharge' ? '▼ Décharge ' + power + ' MW' : 'Repos';
    tip.innerHTML = '<strong>' + data.labels[i] + '</strong>' + data.priceText[i] + '<br>' + doing;
    tip.hidden = false;
    const wrapBox = wrap.getBoundingClientRect();
    let left = event.clientX - wrapBox.left + wrap.scrollLeft + 14;
    if (left + tip.offsetWidth > wrap.scrollWidth) left -= tip.offsetWidth + 28;
    tip.style.left = left + 'px';
    tip.style.top = (event.clientY - wrapBox.top + 14) + 'px';
  });
  function hide() { tip.hidden = true; cross.style.display = 'none'; }
  svg.addEventListener('mouseleave', hide);
})();
"""


def _page(title: str, body: str, script: str = "") -> str:
    return (
        '<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n<style>{_CSS}</style>\n</head>\n"
        f"<body>\n<main>\n{body}\n</main>\n{script}</body>\n</html>\n"
    )


def _key(kind: str) -> str:
    glyph = "▲" if kind == "charge" else "▼"
    return f'<span class="glyph {kind}" aria-hidden="true">{glyph}</span>'


def _cycles(value: float) -> str:
    return text.number(value, 2)


def _per_cycle(scenario: ScenarioView) -> str:
    return "—" if scenario.value_per_cycle_eur is None else text.euros(scenario.value_per_cycle_eur)


def _tiles(s: ScenarioView, hidden: bool) -> str:
    first_sale = next((r.label for r in s.rows if r.action == "discharge"), "aucune")
    tiles = [
        ("Énergie achetée", f"{text.number(s.energy_bought_mwh, 1)} MWh"),
        ("Énergie revendue", f"{text.number(s.energy_sold_mwh, 1)} MWh"),
        ("Cycles complets", _cycles(s.cycles)),
        ("Valeur par cycle", _per_cycle(s)),
        ("Première vente", first_sale),
    ]
    cells = "".join(
        f'<div class="tile"><div class="label">{label}</div><div class="value">{value}</div></div>'
        for label, value in tiles
    )
    return (
        f'<div data-scenario="{s.key}"{" hidden" if hidden else ""}>'
        f'<p class="lead"><strong>{escape(s.name)}.</strong> {escape(s.explanation)}</p>'
        f'<p class="lead">{escape(s.summary)}</p><div class="tiles">{cells}</div></div>'
    )


def _interval_table(s: ScenarioView, hidden: bool) -> str:
    attrs = f'data-scenario="{s.key}"{" hidden" if hidden else ""}'
    if s.is_idle:
        return f'<p {attrs} class="lead">Aucun créneau utilisé dans ce scénario : la batterie reste au repos.</p>'
    rows = "".join(
        f'<tr><td>{r.label}</td><td><span class="action">{_key(r.action)} {r.action_label}</span></td>'
        f'<td class="num">{text.number(r.power_mw, 1)}</td><td class="num">{text.number(r.price_eur_mwh, 2)}</td>'
        f'<td class="num">{text.number(r.soc_mwh, 1)}</td></tr>'
        for r in s.rows
    )
    return (
        f'<div class="table-wrap" {attrs}><table><caption>{len(s.rows)} créneaux utilisés dans le scénario '
        f"« {escape(s.name)} ». Les autres créneaux de la journée sont au repos.</caption>"
        '<thead><tr><th scope="col">Créneau</th><th scope="col">Action</th><th scope="col" class="num">'
        'Puissance (MW)</th><th scope="col" class="num">Prix (€/MWh)</th><th scope="col" class="num">'
        f"Énergie stockée après (MWh)</th></tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _comparison(view: DashboardView) -> str:
    best = max(s.net_value_eur for s in view.scenarios)
    scale = best if best > 0 else 1.0
    bars = "".join(
        f'<div class="bar-row"><div class="bar-label">n°{s.rank} · {escape(s.name)}</div>'
        f'<div class="bar-track"><div class="bar" style="width:{max(s.net_value_eur, 0) / scale * 85:.1f}%"></div>'
        f'<span class="bar-value">{text.euros(s.net_value_eur)}</span></div></div>'
        for s in view.scenarios
    )
    rows = "".join(
        f'<tr><th scope="row">n°{s.rank} · {escape(s.name)}</th><td class="num">{text.euros(s.net_value_eur)}</td>'
        f'<td class="num">{text.euros(s.arbitrage_eur)}</td><td class="num">{text.euros(-s.wear_eur)}</td>'
        f'<td class="num">{text.euros(s.reserve_eur)}</td><td class="num">{_cycles(s.cycles)}</td>'
        f'<td class="num">{_per_cycle(s)}</td></tr>'
        for s in view.scenarios
    )
    timeline = charts.timeline_chart(
        [(f"n°{s.rank}", s.actions) for s in view.scenarios],
        view.hour_ticks,
        "Pour chaque scénario, une ligne sur la journée : les blocs du bas sont les créneaux de charge, "
        "ceux du haut les créneaux de décharge.",
    )
    return f"""
<section class="card" aria-labelledby="compare-title">
  <h2 id="compare-title">Comparer les trois scénarios</h2>
  <p class="lead">Valeur nette de la journée : revenus de l'achat-revente, moins l'usure de la batterie,
  plus la rémunération de la réserve. Le classement suit cette valeur.</p>
  <div class="bars" role="list">{bars.replace('class="bar-row"', 'class="bar-row" role="listitem"')}</div>
  <h3>Quand chaque scénario fait-il travailler la batterie ?</h3>
  <div class="legend">
    <span class="key"><span class="swatch charge"></span>Charge (moitié basse de la ligne)</span>
    <span class="key"><span class="swatch discharge"></span>Décharge (moitié haute)</span>
  </div>
  <div class="chart-wrap">{timeline}</div>
  <div class="table-wrap" style="margin-top:16px"><table>
    <caption>Détail des valeurs, en euros sur la journée. La valeur par cycle montre ce que rapporte
    chaque cycle d'usure : un scénario prudent peut y être meilleur.</caption>
    <thead><tr><th scope="col">Scénario</th><th scope="col" class="num">Valeur nette</th>
    <th scope="col" class="num">Achat-revente</th><th scope="col" class="num">Usure</th>
    <th scope="col" class="num">Réserve</th><th scope="col" class="num">Cycles</th>
    <th scope="col" class="num">Valeur par cycle</th></tr></thead>
    <tbody>{rows}</tbody></table></div>
</section>"""


def render_dashboard(view: DashboardView) -> str:
    """The full dashboard page."""
    best = view.best
    selected = best.key

    banner = (
        f'<div class="banner" role="note"><span class="icon" aria-hidden="true">⚠</span>'
        f"<span><strong>Attention :</strong> {text.SYNTHETIC_WARNING}</span></div>"
        if view.is_synthetic
        else ""
    )
    caveat = (
        f'<p class="note"><strong>À noter :</strong> {escape(view.ranking_caveat)}</p>' if view.ranking_caveat else ""
    )
    verdict_class = "good" if view.worth_cycling else "bad"
    verdict_icon = "✓" if view.worth_cycling else "✕"

    buttons = "".join(
        f'<button type="button" data-select="{s.key}" aria-pressed="{str(s.key == selected).lower()}">'
        f'<span class="rank">Suggestion n°{s.rank}</span><span class="name">{escape(s.name)}</span>'
        f'<span class="value">{text.euros(s.net_value_eur)}</span></button>'
        for s in view.scenarios
    )
    tiles = "".join(_tiles(s, s.key != selected) for s in view.scenarios)
    tables = "".join(_interval_table(s, s.key != selected) for s in view.scenarios)

    price_svg = charts.price_chart(
        view.prices,
        view.hour_ticks,
        {s.key: s.actions for s in view.scenarios},
        selected,
        f"Prix du {view.day_label}, de {text.number(min(view.prices), 2)} à {text.number(max(view.prices), 2)} €/MWh. "
        "Les zones bleues et les triangles vers le haut marquent les créneaux de charge, les zones orange et "
        "les triangles vers le bas les créneaux de décharge. Le détail est dans le tableau plus bas.",
    )
    soc_svg = charts.soc_chart(
        {s.key: s.soc_mwh for s in view.scenarios},
        {s.key: s.reserve_buffer_mwh for s in view.scenarios},
        view.energy_mwh,
        view.hour_ticks,
        selected,
        f"Énergie stockée à la fin de chaque créneau, entre 0 et {view.energy_mwh:g} MWh.",
    )

    glossary = "".join(f"<dt>{escape(term)}</dt><dd>{escape(definition)}</dd>" for term, definition in text.GLOSSARY)

    body = f"""
<header>
  <p class="eyebrow">Tableau de bord · aide à la décision</p>
  <h1>{escape(view.title)}</h1>
  <p class="meta">Journée du <strong>{view.day_label}</strong> · {len(view.prices)} créneaux de 15 minutes
  · Source : {escape(view.source)}</p>
</header>
{banner}

<section class="card hero" aria-labelledby="hero-title">
  <p class="eyebrow">Suggestion n°1</p>
  <h2 id="hero-title">{escape(best.name)}</h2>
  <p class="figure">{text.euros(best.net_value_eur)}</p>
  <p class="figure-unit">de valeur nette estimée sur la journée</p>
  <p class="note">{escape(view.comparison_line)}</p>
  {caveat}
  <p class="verdict {verdict_class}"><span aria-hidden="true">{verdict_icon}</span> {escape(view.verdict)}</p>
  <p class="note">{escape(view.verdict_detail)}</p>
  <p class="decision">{escape(text.DECISION_NOTE)}</p>
</section>

<section class="card" aria-labelledby="day-title">
  <h2 id="day-title">Quand la batterie charge-t-elle et décharge-t-elle ?</h2>
  <p class="lead">Choisissez un scénario : le graphique, les chiffres et le tableau détaillé s'adaptent.
  Survolez la courbe pour lire le prix d'un créneau.</p>
  <div class="selector" role="group" aria-label="Scénario affiché">{buttons}</div>
  <p id="selection-status" class="note" aria-live="polite">Scénario affiché : {escape(best.name)}</p>
  {tiles}
  <h3 style="margin-top:20px">Prix de l'électricité, créneau par créneau</h3>
  <div class="legend">
    <span class="key"><span class="line-key"></span>Prix (€/MWh)</span>
    <span class="key">{_key("charge")} Charge : la batterie achète</span>
    <span class="key">{_key("discharge")} Décharge : la batterie revend</span>
  </div>
  <div class="chart-wrap">{price_svg}</div>
  <h3 style="margin-top:20px">Énergie stockée dans la batterie</h3>
  <div class="chart-wrap">{soc_svg}</div>
</section>

{_comparison(view)}

<section class="card" aria-labelledby="detail-title">
  <h2 id="detail-title">Détail créneau par créneau</h2>
  <p class="lead">Chaque ligne est un créneau de 15 minutes du scénario affiché. Ce tableau contient
  toutes les valeurs des graphiques.</p>
  {tables}
</section>

<section class="card" aria-labelledby="help-title">
  <h2 id="help-title">Comment lire ce tableau de bord</h2>
  <p class="lead">Le prix de chaque créneau est connu la veille. Un calcul d'optimisation cherche,
  pour chaque scénario, les créneaux où acheter puis revendre rapporte le plus, en respectant les
  limites de la batterie ({view.power_mw:g} MW, {view.energy_mwh:g} MWh).</p>
  <dl>{glossary}</dl>
</section>

<footer>
  <p><strong>Source des prix :</strong> {escape(view.source)}.</p>
  <p>{escape(view.assumptions_note)}</p>
  <p>Généré le {view.generated_at}. Une question, une erreur ?
  <a href="{text.HELP_URL}">Signalez-la sur le dépôt du projet</a>.</p>
</footer>
"""
    data = {
        "selected": selected,
        "names": {s.key: s.name for s in view.scenarios},
        "labels": view.interval_labels,
        "priceText": [text.price(p) for p in view.prices],
        "actions": {s.key: s.actions for s in view.scenarios},
        "power": {s.key: _power_series(s) for s in view.scenarios},
        "plot": {
            "left": charts.LEFT,
            "plotWidth": charts.PLOT_WIDTH,
            "width": charts.WIDTH,
            "top": charts.PRICE_TOP,
            "bottom": charts.PRICE_HEIGHT - charts.PRICE_BOTTOM,
        },
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    script = f'<script type="application/json" id="dashboard-data">{payload}</script>\n<script>{_SCRIPT}</script>\n'
    return _page(f"{view.title} — {view.day_label}", body, script)


def _power_series(s: ScenarioView) -> list[str]:
    """Power per interval as French text, aligned with ``actions``."""
    active_rows = iter(s.rows)
    return ["0" if action == "idle" else text.number(next(active_rows).power_mw, 1) for action in s.actions]


def render_error_page(what_happened: str, what_to_do: list[str], technical_detail: str) -> str:
    """A page that explains a failure instead of showing a raw error."""
    steps = "".join(f"<li>{escape(step)}</li>" for step in what_to_do)
    body = f"""
<header>
  <p class="eyebrow">Tableau de bord · aide à la décision</p>
  <h1>Le tableau de bord n'a pas pu être préparé</h1>
</header>
<section class="card" aria-labelledby="what-title">
  <h2 id="what-title">Ce qui s'est passé</h2>
  <p class="lead">{escape(what_happened)}</p>
  <p class="lead">Aucune suggestion n'est affichée : mieux vaut aucun chiffre qu'un chiffre faux.</p>
</section>
<section class="card" aria-labelledby="todo-title">
  <h2 id="todo-title">Que faire maintenant</h2>
  <ol class="error-steps">{steps}</ol>
</section>
<section class="card" aria-labelledby="help-title">
  <h2 id="help-title">Obtenir de l'aide</h2>
  <p class="lead">Si le problème persiste, <a href="{text.HELP_URL}">signalez-le sur le dépôt du projet</a>
  en copiant le détail technique ci-dessous.</p>
  <details><summary>Détail technique (pour le support)</summary><pre>{escape(technical_detail)}</pre></details>
</section>
"""
    return _page("Tableau de bord indisponible", body)
