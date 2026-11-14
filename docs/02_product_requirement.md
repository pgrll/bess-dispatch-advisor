# Product requirement

For each delivery day, once French day-ahead prices are published, the tool
shows a BESS analyst the **three dispatch scenarios ranked by net value in
euros** (arbitrage revenue minus wear cost plus reserve revenue), computed in
**under 10 seconds** on a laptop. Each scenario lists **every charge and
discharge interval at 15-minute resolution** with its price, power and state
of charge; intervals are never merged into hour ranges. A **yes/no verdict on
whether cycling is profitable** is shown with the net spread of the best
buy/sell pair. **Every price states its source**, and synthetic data is
labelled as such. "Readable" means an analyst who has never seen the tool can
state scenario #1's value and its first discharge interval **in under two
minutes, without help**. **Suggestion #1 is always the scenario that captures
the most value**; on a tie, the one using fewer cycles. The tool **never
phrases a suggestion as an order**.

## Why each term is defensible

| Term | Decision behind it |
|---|---|
| Net value | Revenue alone would always favour cycling more; wear and reserve revenue make the comparison fair |
| Under 10 seconds | Three MILP solves of 96 intervals take well under a second each; the budget leaves room for data download |
| 15-minute resolution | The market's own time unit since 2025; coarser output would hide value |
| Fewer cycles on a tie | Same money for less wear is the conservative choice |
| Two minutes, no help | Measured in the demo with a person playing the analyst |
