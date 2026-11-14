# BESS Dispatch Advisor

**Which 15-minute intervals should a grid-scale battery charge and discharge
tomorrow on the French day-ahead market, and is it worth cycling at all?**

This tool answers for a 100 MW / 200 MWh battery. It downloads French
day-ahead prices from ENTSO-E, computes the optimal schedule of three
strategies with a mixed-integer linear programme, and ranks them by the
value they capture. It suggests; the analyst decides.

```text
Day-ahead France - 2026-04-18 - 96 intervals of 15 min
Source: file data/sample/synthetic_day.csv  (SYNTHETIC prices for demonstration, not market data)

Is it worth cycling?
  Yes: best net spread +187.19 EUR/MWh (buy 13:30-13:45, sell 19:45-20:00)

Scenarios, ranked by net value captured (EUR)
  #  scenario          net value  arbitrage     wear  reserve  cycles
  1  reserve              33,960     32,479   -3,319    4,800    1.80
  2  max_arbitrage        33,553     37,241   -3,688        0    2.00
  3  preserve             29,776     31,620   -1,844        0    1.00

Intervals of scenario #1 (reserve: 20 MW held for balancing services, up to 2 cycles)
  ...
  12:30-12:45  charge      80.0 MW  at   -12.62 EUR/MWh   SoC after   28.4 MWh
  12:45-13:00  charge      80.0 MW  at   -30.37 EUR/MWh   SoC after   46.9 MWh
  ...
```

## Why it is built this way

The project follows the steps of a Forward Deployed Engineer engagement:
understand the user, separate what needs an LLM from what does not, define
"done" in testable terms, then build. Every step is documented in
[`docs/`](docs/README.md).

Three design choices matter most:

1. **The schedule is computed by an optimiser, not by an LLM.** It is exact,
   reproducible and free. A language model will come in phase 2 to *explain*
   schedules and answer questions, using these functions as tools.
2. **15-minute resolution end to end**, the market's time unit since 2025,
   including clock-change days (92 and 100 intervals).
3. **Bad data is rejected, never guessed.** A missing interval stops the run
   with an explicit message rather than producing a wrong schedule.

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

bess-advisor --prices data/sample/synthetic_day.csv   # offline demo
pytest                                                 # 97 tests, a few seconds
```

With real data, get a free API token from the
[ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) (account
settings, "Web API Security Token"), then:

```bash
cp .env.example .env               # put your token in it, then:
export ENTSOE_API_TOKEN=...        # or load .env with your tool of choice
bess-advisor --date 2026-11-14
```

## How the optimiser is tested

A schedule that looks plausible but is wrong is the main risk, so the tests
check the optimiser against independent references, not against itself:

- **A day computed by hand**: buy 8 intervals at 0, sell at 100; the expected
  value (15,300 EUR) is derived on paper in the test's docstring.
- **Exhaustive search**: on short horizons, no schedule found by brute force
  beats the optimiser.
- **Physics on every schedule**: power, capacity and cycle limits, no
  simultaneous charge and discharge, state of charge recomputed from powers.
- **Agreement with a one-line formula**: the "worth cycling?" verdict and the
  optimiser always agree.
- **Main acceptance test**: suggestion #1 is always the scenario capturing the
  most value.

The full mapping from requirements to tests is in
[`docs/04_acceptance_tests.md`](docs/04_acceptance_tests.md).

## Project structure

```text
src/bess_advisor/
  config.py          battery parameters; every assumption marked in code
  optimizer.py       MILP schedule (formulation in the module docstring)
  economics.py       "is it worth cycling?" check
  scenarios.py       three strategies and the ranking rule
  cli.py             text report
  data/
    entsoe.py        ENTSO-E download and XML parsing
    validation.py    rejects incomplete or malformed price days
    storage.py       local CSV cache
tests/               97 tests, with ENTSO-E XML fixtures
docs/                problem brief, delegation plan, spec, decisions
scripts/             synthetic sample generator
```

## Assumptions and limits

Efficiency (85 %), wear cost (10 EUR/MWh), reserve capacity price
(10 EUR/MW/h) and the other assumptions are listed with how to calibrate
them in [`docs/05_decision_log.md`](docs/05_decision_log.md). Version 1 works
on **published** day-ahead prices: it supports dispatch planning and
after-the-fact analysis, not bidding before the auction, which would need a
price forecast.

## Roadmap

- [x] Data pipeline, optimiser, scenarios, CLI report, test suite
- [ ] Dashboard: price curve with each scenario's charge and discharge points
- [ ] Market context from RTE eCO2mix (consumption, generation mix)
- [ ] LLM agent explaining schedules, with an evaluation suite and a cost/latency table
- [ ] Same agent on an open-weight model (Mistral), compared on the same evaluations
- [ ] Day-ahead price forecast, to support bidding before gate closure

## Author

Paul Grall, data scientist in energy markets.
[LinkedIn](https://www.linkedin.com/in/paulgrall)
