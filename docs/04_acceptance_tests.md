# Acceptance tests

Each statement below can pass or fail without human judgement, and points to
the test that checks it. Run them all with `pytest`.

## Main test

| # | Statement | Test |
|---|---|---|
| A1 | Suggestion #1 is the scenario capturing the most net value, on every test day and for any reserve price | `test_scenarios.py::test_suggestion_one_captures_the_most_value` |
| A2 | On a tie, the scenario with fewer cycles comes first | `test_scenarios.py::test_on_a_tie_the_scenario_with_fewer_cycles_comes_first` |

## Correctness of the schedule

| # | Statement | Test |
|---|---|---|
| A3 | No schedule ever exceeds power, capacity or cycle limits, or charges and discharges at once | `test_optimizer.py::test_schedule_respects_every_physical_limit` (30 cases) |
| A4 | On a day computable by hand, the value is exact to the cent (15,300 EUR) | `test_optimizer.py::test_hand_computed_day` |
| A5 | The optimiser's value sits between two bounds that do not use its code: exhaustive search (lower) and the pairwise spread argument (upper) | `test_optimizer.py::test_optimiser_sits_between_two_independent_bounds`, `test_full_day_value_never_exceeds_the_upper_bound` |
| A6 | The "worth cycling?" verdict always agrees with the optimiser | `test_economics.py::test_verdict_agrees_with_the_optimiser` |
| A7 | Day-ahead prices are parsed exactly, including omitted repeated values | `test_data.py::test_parser_keeps_15_minute_series_and_forward_fills_a03` |
| A8 | Intervals are reported one by one at 15-minute resolution, with the data source and a non-directive closing line | `test_cli.py::test_report_on_the_sample_day` |

## Edge cases

| # | Situation | Expected behaviour | Test |
|---|---|---|---|
| E1 | No data at all | Explicit error, no schedule | `test_empty_series_is_rejected` |
| E2 | One interval without a price | Explicit error naming the interval | `test_missing_price_is_rejected` |
| E3 | ENTSO-E has no data for the day | Error carrying ENTSO-E's own reason | `test_acknowledgement_document_raises_with_its_reason` |
| E4 | Hourly instead of 15-minute data | Rejected | `test_hourly_prices_are_rejected` |
| E5 | Clock-change days (92 and 100 intervals) | Handled like any day | `test_clock_change_days`, `test_csv_round_trip_on_a_clock_change_day` |
| E6 | Flat prices, or zero all day | Battery idle, value 0 | `test_flat_prices_leave_the_battery_idle`, `test_zero_prices_all_day_leave_the_battery_idle` |
| E7 | Deeply negative prices | No simultaneous charge and discharge | `test_negative_prices_do_not_trigger_simultaneous_charge_and_discharge` |
| E8 | Spread smaller than losses plus wear | "Not worth cycling" | `test_small_spread_is_eaten_by_losses_and_wear` |
| E9 | ENTSO-E unreachable, token rejected, rate limit | A sentence saying what to do next | `test_http_errors_say_what_to_do` |

## Dashboard

| # | Statement | Test (`test_dashboard.py`) |
|---|---|---|
| D1 | The hero shows the scenario capturing the most value, once, before everything else | `test_hero_shows_the_scenario_that_captures_the_most_value`, `test_sections_come_in_order_of_importance` |
| D2 | Every chart has a title and a text description | `test_every_chart_has_a_title_and_a_text_description` |
| D3 | All text meets WCAG AA contrast in light and dark mode; chart marks reach 3:1 | `test_text_meets_wcag_aa_contrast`, `test_chart_marks_meet_graphical_contrast` |
| D4 | No text below 13 px | `test_no_text_smaller_than_13_pixels` |
| D5 | Charge and discharge never rely on colour alone | `test_charge_and_discharge_never_rely_on_colour_alone` |
| D6 | Synthetic data is flagged; a ranking resting on an unconfirmed assumption is flagged | `test_synthetic_data_is_flagged_and_real_data_is_not`, `test_hero_warns_when_the_ranking_rests_on_an_unconfirmed_assumption` |
| D7 | Every failure produces a page saying what happened, what to do and where to get help | `test_error_page_says_what_happened_what_to_do_and_where_to_get_help` |
| D8 | Suggestions are never phrased as orders | `test_suggestions_are_never_phrased_as_orders` |

## Not automated yet

- Readability: an analyst states scenario #1's value and first discharge
  interval in under two minutes without help (checked in a live demo).
- Agent: every number cited comes from a tool call; no suggestion is phrased
  as an order (phase 2 evaluation suite).
