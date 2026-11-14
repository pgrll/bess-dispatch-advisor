# Problem brief

## The user

**Primary: a BESS analyst** running a grid-scale battery on the French
market, for example the 100 MW / 200 MWh (2-hour) reference asset of this
project. They know the market well: the tool must not explain basics, it
must make the day readable in seconds.

Secondary users:

- **Intraday trader**: adjusts the position once day-ahead results are known.
- **Asset manager**: watches revenue against battery wear and the yearly cycle budget.
- **Risk manager**: needs to know which numbers rest on assumptions.

## What they actually need

Not "a dashboard". They need to **decide quickly and with confidence which
15-minute intervals to use, to know when doing nothing is the right call,
and to justify the choice to the desk in one sentence**.

## A timing fact that shapes the scope

The day-ahead auction (SDAC) closes at 12:00 CET the day before delivery;
preliminary results come out at 12:45 and final results at 12:57
([BSP SouthPool, day-ahead market](https://bsp-southpool.com/day-ahead-market)).
**The bid is placed before prices are known.** A tool built on published prices therefore supports:

1. the physical dispatch plan and intraday adjustments once results are out;
2. after-the-fact analysis: how much value a strategy left on the table.

Helping *before* gate closure requires a price forecast. That is a natural
extension (forecasting was the author's work at Akaysha Energy) and is
explicitly **out of scope for version 1**.

## What a great experience looks like

At 13:05 the results are out. The analyst opens the tool. Within two
minutes they see the three strategies ranked by value, the exact intervals
of each, and whether cycling is worth it today. They pick one and can say why.

## Constraints

| Constraint | Consequence |
|---|---|
| Public data only | ENTSO-E Transparency Platform for prices, RTE eCO2mix for market context |
| No portfolio data | Curtailment suggestions stay qualitative, flagged as low confidence |
| One person, three days for version 1 | Optimiser and report first; dashboard next; agent in phase 2 |
| Free tools | Open-source solver (HiGHS through SciPy), no paid API in the core |
| Decisions stay human | The tool ranks and explains; it never issues an order |
