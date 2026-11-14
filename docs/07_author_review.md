# Author review

The code was written with an AI assistant. These are the checks the author
does personally before presenting the work as his own. Tick each box only
when it is done.

## Does it run outside the build environment?

- [ ] Continuous integration is green on GitHub (Actions tab).
- [ ] `pytest` passes on the author's machine.
- [ ] One real day downloaded with an ENTSO-E token: `bess-advisor --date <day>`.
- [ ] Five prices of that day, picked at random, match the ENTSO-E website.

## Are the facts right?

- [x] 15-minute day-ahead go-live: delivery day 1 October 2025 (source in `05_decision_log.md`).
- [x] Gate closure 12:00, results 12:45-12:57 (source in `05_decision_log.md`).
- [ ] Every assumption marked "To confirm" in `05_decision_log.md` is replaced by the author's own value.

## Can the author explain it without notes?

- [ ] Why the optimiser has one binary variable per interval.
- [ ] Why the hand-computed test day is worth exactly 15,300 EUR.
- [ ] Why `preserve` can never win on total value, and what value per cycle adds.
- [ ] What version 1 cannot do (bidding before 12:00), and what would fix it.
- [ ] Every module read once, questions written down and answered.
