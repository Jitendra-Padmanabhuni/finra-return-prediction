# Phase 4 Prediction Target Report

## Locked definition

The common primary signal-date window is locked at **2025-05-28 through 2026-08-31**. May 28 is the first master-panel date with 60 strictly prior panel trading dates. All later primary signal comparisons must use this same signal-date window.

For signal date `t`, the target is:

```text
forward_oc_return[t] = adjusted_close[t+1] / adjusted_open[t+1] - 1
```

where `t+1` is the immediately following date in the shared market calendar, not the next date on which a particular security happens to have data.

## Calendar and September extension

Yahoo Finance data for the 400 August 31 universe members was requested with an exclusive end date of 2026-09-02. All 400 returned a September 1 record. Therefore every August 31 signal maps to the designated 2026-09-01 target session.

Every nonmissing target date is strictly later than its signal date and exactly the next date in the shared calendar. The panel stores `signal_date` (the existing `Date` field), `designated_target_date`, next-session adjusted open/close, next-session split/dividend fields, return, availability, and status separately.

## Coverage

| Target status | Rows |
| --- | ---: |
| Available | 150,799 |
| Missing designated next-session market observation | 1 |

The sole unavailable row is FISV: signal date 2025-11-11, designated target date 2025-11-12. Its target remains missing; it was not advanced to any later FISV observation.

MRSH, ECHO, and BNY have 100% target availability despite weaker FINRA coverage; FISV has 99.73% target availability and its Phase 3 missing-FINRA/market coverage remains separately visible in the panel. Target availability must not be confused with FINRA coverage.

## Diagnostics

- No duplicate `(signal date, canonical symbol)` keys.
- No nonpositive next-session adjusted prices or nonfinite available returns.
- Split/dividend data is retained; no corporate-action or extreme-return record was deleted.
- Six absolute forward open-to-close returns of at least 25% were flagged in `results/tables/phase4_extreme_forward_oc_returns.csv`; no winsorization was applied.

## Outputs

- `data/processed/master_stock_day_with_target.parquet`
- `data/processed/master_stock_day_with_target.csv`
- `results/tables/phase4_target_coverage_*.csv`
- `results/tables/phase4_extreme_forward_oc_returns.csv`
- `results/tables/phase4_yahoo_extension_download_log.csv`

