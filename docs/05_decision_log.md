# Decision log

Newest decisions at the bottom. Each entry: the decision, the reason, and
what would make us revisit it.

| # | Decision | Reason | Revisit if |
|---|---|---|---|
| D1 | Work at 15-minute resolution | The European day-ahead market moved to 15-minute products for delivery day 1 October 2025 ([EPEX SPOT](https://www.epexspot.com/en/news/market-coupling-steering-committee-confirms-go-live-15-minute-mtu-sdac-trading-day-30)) | Never for France; other zones may differ |
| D2 | Deterministic optimiser computes schedules; the LLM only explains | Exact, reproducible, testable, free | — |
| D3 | `scipy.optimize.milp` (HiGHS) instead of PuLP | Same solver, one fewer dependency | The model needs features SciPy lacks |
| D4 | Binary variable forbidding simultaneous charge and discharge | Prevents a fake profit from burning energy on negative-price days | — |
| D5 | End the day with at least the starting energy | Otherwise the optimiser sells energy it never bought | Multi-day optimisation is added |
| D6 | Rank scenarios on net value; fewer cycles wins a tie | Fair comparison including wear and reserve income | The analyst's real criterion turns out different |
| D7 | Version 1 works on published prices only | Bids close at 12:00, results come at 12:45-12:57 ([BSP SouthPool](https://bsp-southpool.com/day-ahead-market)); a forecast is a separate project | Phase 3: price forecasting |
| D8 | Repository written in English | Readable by any reviewer | — |
| D9 | Show value per cycle next to total value | Total value can never favour `preserve` (see below); value per cycle shows what it buys | The cycle budget gets an explicit price |

## Known limitation, stated plainly

Within a single day, `max_arbitrage` can never be worth less than
`preserve`: `preserve` is the same problem with a tighter cycle limit. They
tie when a second cycle is not profitable. The real benefit of `preserve`,
a smaller share of the yearly cycle budget, is invisible in a one-day value.
The report and dashboard therefore also show **value per cycle**, where
`preserve` usually wins. Pricing the cycle budget properly (an opportunity
cost per cycle) remains the way to make one ranking capture both. Whether to
keep `preserve` as a scenario is an open decision for the author.

## Assumptions to recalibrate

All values below are generic orders of magnitude set by the AI assistant,
not French market data. Each must be confirmed or replaced by the author.

| Parameter | Value | Where | How to calibrate | Status |
|---|---|---|---|---|
| Round-trip efficiency | 85 % | `config.py` | Manufacturer data, AC-to-AC including auxiliaries | To confirm |
| Degradation cost | 10 EUR/MWh discharged | `config.py` | Replacement cost / warranted throughput | To confirm |
| Max cycles per day | 2 | `config.py` | Warranty terms | To confirm |
| Reserve energy per MW | 0.5 h | `config.py` | FCR/aFRR prequalification rules | To confirm |
| Reserve capacity price | 10 EUR/MW/h | `scenarios.py` | Recent FCR and aFRR capacity auction results | To confirm |
| Starting state of charge | 0 MWh | `config.py` | Actual state at the start of the day | Simplification |
