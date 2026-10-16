# Corrected Phase 5 Naive FINRA Ratio Report

> Primary corrected result on the exact-20-date liquidity universe. The frozen
> signal, evaluation, ranking, decile, and HAC rules were unchanged.

## Locked evaluation

This is a gross, illustrative evaluation only. Signal dates are locked to 2025-05-28 through 2026-08-31. The raw ratio is `q = ShortVolume / TotalVolume`, calculated only for present FINRA observations with positive total volume. The naive alpha is `S0 = -q`; higher `S0` is hypothesized to predict higher next-session adjusted open-to-close returns.

Ties are resolved by canonical-symbol alphabetical order, then stable first rank. Deciles use those ranks to create approximately equal daily counts. Inference uses a five-day Newey–West/HAC covariance. Predefined subperiods are 2025-05-28–2026-01-13 and 2026-01-14–2026-08-31.

## Ratio coverage and distribution

There are 126,272 nonmissing ratio observations. All passed the predeclared `[0,1]` numerical-tolerance check; observed minimum/maximum are 0.0118 and 0.9354. Pooled mean is 0.5043, median 0.5057, and 1st/99th percentiles are 0.1908/0.8062.

Of 126,800 locked-window master rows, 126,271 are eligible for IC/decile evaluation. Exclusions are 528 missing FINRA ratios and one missing target. Daily eligible counts range from 397 to 400.

## Gross illustrative performance

| Metric | Result |
| --- | ---: |
| Mean daily S0 Rank IC | 0.01093 |
| Rank-IC standard deviation | 0.09270 |
| Annualized ICIR | 1.87 |
| Ordinary IC t-statistic | 2.10 |
| HAC(5) IC t-statistic | 1.90 |
| Positive IC-day fraction | 57.41% |
| Mean daily D10–D1 return | 2.25 bps |
| Annualized arithmetic D10–D1 return | 5.68% |
| Annualized D10–D1 volatility | 9.08% |
| Gross D10–D1 Sharpe | 0.63 |
| Gross cumulative D10–D1 return | 6.85% |

Both predeclared subperiod mean ICs are positive: 0.01741 and 0.00441. However, the decile-return profile is not reasonably monotonic, and the HAC Rank-IC t-statistic remains below the predeclared threshold of 2. The naive baseline remains **directionally supportive but not statistically convincing** under the locked criteria.

Relative to legacy, mean IC rises by 0.00140, HAC t by 0.24, gross Sharpe by 0.48, and cumulative gross return by 5.72 percentage points. These are corrected-versus-legacy point-estimate comparisons, not a new hypothesis test.

No transaction costs, abnormal normalization, reversal control, conditioning, parameter search, or other extension was applied.

## Outputs

- `data/processed/master_stock_day_naive_signal.parquet`
- `results/tables/phase5_*.csv`
- `results/figures/phase5_raw_ratio_distribution.png`
- `results/figures/phase5_daily_median_ratio.png`
- `results/figures/phase5_decile_forward_returns.png`
- `results/figures/phase5_cumulative_gross_long_short.png`
- `results/figures/phase5_rolling_60d_rank_ic.png`
