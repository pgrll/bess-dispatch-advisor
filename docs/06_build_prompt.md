# Build prompt

The instructions given to the AI assistant to turn the specification into
code. They are kept here because the quality of the result depends on them,
and because they are reusable for the next components.

---

You are helping me build version 1 of a day-ahead dispatch advisor for a
100 MW / 200 MWh battery on the French electricity market. This repository
will be reviewed by recruiters, so code must be clean, typed, documented,
and readable by a professional who has never seen it.

**Read first**: `docs/02_product_requirement.md`, `docs/03_technical_spec.md`
and `docs/04_acceptance_tests.md`. They are the source of truth.

**Stack**: Python 3.11+, pandas, NumPy, SciPy (`scipy.optimize.milp`). No
other runtime dependency. pytest for tests, ruff for lint and format.

**Constraints**:

- The schedule is computed by a deterministic MILP, never by an LLM.
- 15-minute resolution everywhere. Handle clock-change days (92/100 intervals).
- Public data only. Never invent prices; synthetic data must be labelled.
- Reject bad data with an explicit error rather than guessing.
- Every assumption is named, has a default, and is listed in the decision log.
- Output suggestions, never orders.

**Tests come with the code**: every acceptance test in
`docs/04_acceptance_tests.md` must exist and pass, including an independent
check of the optimiser (hand-computed day and brute-force search).

**Way of working**: small modules with one responsibility each, docstrings
that explain *why*, not *what*. Tell me when the specification is wrong or
ambiguous instead of guessing.
