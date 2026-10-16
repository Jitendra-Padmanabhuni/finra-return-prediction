# Phase 5 Naive FINRA Ratio Report

## Locked evaluation

This is a gross, illustrative evaluation only. Signal dates are locked to 2025-05-28 through 2026-08-31. The raw ratio is `q = ShortVolume / TotalVolume`, calculated only for present FINRA observations with positive total volume. The naive alpha is `S0 = -q`; higher `S0` is hypothesized to predict higher next-session adjusted open-to-close returns.

Ties are resolved by canonical-symbol alphabetical order, then stable first rank. Deciles use those ranks to create approximately equal daily counts. Inference uses a five-day Newey–West/HAC covariance. Predefined subperiods are 2025-05-28–2026-01-13 and 2026-01-14–2026-08-31.

## Ratio coverage and distribution

There are 126,438 nonmissing ratio observations. All passed the predeclared `[0,1]` numerical-tolerance check; observed minimum/maximum are 0.0118 and 0.9354. Pooled mean is 0.5051, median 0.5067, and 1st/99th percentiles are 0.1913/0.8058.

Of 126,800 locked-window master rows, 126,437 are eligible for IC/decile evaluation. Exclusions are 362 missing FINRA ratios and one missing target (FISV). Daily eligible counts range from 398 to 400.

## Gross illustrative performance

| Metric | Result |
| --- | ---: |
| Mean daily S0 Rank IC | 0.00953 |
| Rank-IC standard deviation | 0.09256 |
| Annualized ICIR | 1.63 |
| Ordinary IC t-statistic | 1.83 |
| HAC(5) IC t-statistic | 1.66 |
| Positive IC-day fraction | 55.52% |
| Mean daily D10–D1 return | 0.52 bps |
| Annualized arithmetic D10–D1 return | 1.32% |
| Annualized D10–D1 volatility | 9.24% |
| Gross D10–D1 Sharpe | 0.14 |
| Gross cumulative D10–D1 return | 1.13% |

Both predeclared subperiod mean ICs are positive: 0.01472 and 0.00431. However, the decile-return profile is not reasonably monotonic, and the HAC Rank-IC t-statistic is below the predeclared two-sided threshold of 2. The naive baseline is therefore **directionally supportive but not statistically convincing** under the locked criteria.

No transaction costs, abnormal normalization, reversal control, conditioning, parameter search, or other extension was applied.

## Outputs

- `data/processed/master_stock_day_naive_signal.parquet`
- `results/tables/phase5_*.csv`
- `results/figures/phase5_raw_ratio_distribution.png`
- `results/figures/phase5_daily_median_ratio.png`
- `results/figures/phase5_decile_forward_returns.png`
- `results/figures/phase5_cumulative_gross_long_short.png`
- `results/figures/phase5_rolling_60d_rank_ic.png`

