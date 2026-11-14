# CLAUDE.md

Instructions for AI coding assistants working in this repository.

## Project

Day-ahead dispatch advisor for a 100 MW / 200 MWh battery on the French
market. The source of truth for scope and behaviour is `docs/`, in particular
`02_product_requirement.md`, `03_technical_spec.md` and `04_acceptance_tests.md`.

## Commands

- Install: `pip install -e ".[dev]"`
- Tests: `pytest`
- Lint and format: `ruff check . && ruff format .`
- Demo: `bess-advisor --prices data/sample/synthetic_day.csv`
- Dashboard: `bess-advisor --prices data/sample/synthetic_day.csv --html examples/dashboard_synthetic_day.html`

## Rules

- Schedules and revenues come from the MILP in `optimizer.py`, spreads from
  `economics.py`. Never compute or estimate them any other way.
- 15-minute resolution everywhere; clock-change days have 92 or 100 intervals.
- Never invent market data. Synthetic data is labelled as synthetic.
- Bad input raises an explicit error; never fill gaps silently.
- New assumptions get a default, an `ASSUMPTION` comment and a row in
  `docs/05_decision_log.md`.
- Every requirement change updates `docs/04_acceptance_tests.md` and its test.
- Output phrases suggestions, never orders.
- Dashboard wording lives in `dashboard/text.py`; keep it plain French with units, and keep
  `tests/test_dashboard.py` (contrast, text size, no colour-only meaning) passing.
- Code in English, typed, with docstrings that explain why.
- One pull request per step; the author reviews every line before merging.
