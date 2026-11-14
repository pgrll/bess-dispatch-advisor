# Decision log

Newest decisions at the bottom. Each entry: the decision, the reason, and
what would make us revisit it.

| # | Decision | Reason | Revisit if |
|---|---|---|---|
| D1 | Work at 15-minute resolution | The European day-ahead market moved to 15-minute products in 2025 | Never for France; other zones may differ |
| D2 | Deterministic optimiser computes schedules; the LLM only explains | Exact, reproducible, testable, free | — |
| D3 | `scipy.optimize.milp` (HiGHS) instead of PuLP | Same solver, one fewer dependency | The model needs features SciPy lacks |
| D4 | Binary variable forbidding simultaneous charge and discharge | Prevents a fake profit from burning energy on negative-price days | — |
| D5 | End the day with at least the starting energy | Otherwise the optimiser sells energy it never bought | Multi-day optimisation is added |
| D6 | Rank scenarios on net value; fewer cycles wins a tie | Fair comparison including wear and reserve income | The analyst's real criterion turns out different |
| D7 | Version 1 works on published prices only | The bid is placed before prices are known; a forecast is a separate project | Phase 3: price forecasting |
| D8 | Repository written in English | Readable by any reviewer | — |

## Known limitation, stated plainly

Within a single day, `max_arbitrage` can never be worth less than
`preserve`: `preserve` is the same problem with a tighter cycle limit. They
tie when a second cycle is not profitable. The real benefit of `preserve`,
a smaller share of the yearly cycle budget, is invisible in a one-day value.
Pricing that budget properly (an opportunity cost per cycle) is the way to
make the comparison meaningful.

## Assumptions to recalibrate

| Parameter | Value | Where | How to calibrate |
|---|---|---|---|
| Round-trip efficiency | 85 % | `config.py` | Manufacturer data, AC-to-AC including auxiliaries |
| Degradation cost | 10 EUR/MWh discharged | `config.py` | Replacement cost / warranted throughput |
| Max cycles per day | 2 | `config.py` | Warranty terms |
| Reserve energy per MW | 0.5 h | `config.py` | FCR/aFRR prequalification rules |
| Reserve capacity price | 10 EUR/MW/h | `scenarios.py` | Recent FCR and aFRR capacity auction results |
| Starting state of charge | 0 MWh | `config.py` | Actual state at the start of the day |
