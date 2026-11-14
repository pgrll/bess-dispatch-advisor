# Data

| Folder | Content | In git? |
|---|---|---|
| `sample/` | `synthetic_day.csv`: **invented prices** shaped like a sunny spring day, for the offline demo and tests. Regenerate with `python scripts/make_synthetic_day.py`. | Yes |
| `cache/` | Real day-ahead prices downloaded from ENTSO-E, one CSV per day. | No (re-downloadable) |

CSV format: `interval_start` (ISO 8601 with UTC offset, start of the 15-minute
interval) and `price_eur_mwh`. Keeping the offset makes clock-change days
unambiguous.

Source of real prices: ENTSO-E Transparency Platform, document type A44
(day-ahead prices), bidding zone France `10YFR-RTE------C`.
