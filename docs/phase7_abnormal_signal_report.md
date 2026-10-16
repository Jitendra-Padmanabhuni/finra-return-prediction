# Corrected Phase 7 Stock-Specific Abnormal Short-Volume Signal Report

> Primary corrected result on the exact-20-date liquidity universe. The S1
> construction and all evaluation rules were unchanged.

## Locked construction

For each stock-date, S1 uses the 60 immediately preceding shared market dates only. Every one of those dates must have a valid q observation; any gap, including an interrupted universe membership, makes the primary S1 missing. The window excludes the signal date and never reaches farther backward. The construction is:

```text
z = (q[t] - median(q[t-60:t-1])) / (1.4826 * MAD(q[t-60:t-1]) + 0.000001)
S1 = -z
```

No z value was capped, winsorized, or removed because of a subsequent return. S0 is re-evaluated only on the exact S1-eligible observations.

## Eligibility and data-quality effects

There are 115,007 paired S1-eligible rows across all 317 locked dates, ranging from 359 to 374 daily observations. Ineligible rows are 528 current-q missing observations, 11,084 interrupted-universe-history observations, and 181 missing-FINRA-history observations. No valid-history row had MAD less than or equal to the locked epsilon, so near-zero MAD caused zero eligibility loss. The larger interrupted-history count is a direct consequence of greater turnover in the corrected monthly universe; it does not make the locked start date infeasible.

Baseline ratios are materially heterogeneous: historical-median q has mean 0.5045, standard deviation 0.0985, and ranges from 0.2174 to 0.8122. Historical MAD has median 0.0675.

## Signal distribution and extremes

S1 has median 0.0106, standard deviation 1.1374, and range -6.2259 to 7.4593. The largest absolute z values remain valid unusual q observations with ordinary MAD values—not missing-history artifacts or near-zero denominators. Examples include FAST on 2026-04-06 (z -7.46, MAD 0.0385) and HOOD on 2025-08-20 (z -7.24, MAD 0.0353). They remain in the analysis.

Mechanical rolling examples are A, AAPL, and ABBV: the first three alphabetical symbols with valid S1 history, chosen without reference to alpha performance.

## Paired S0 versus S1 results — gross illustrative

| Metric | Paired S0 | S1 |
| --- | ---: | ---: |
| Mean daily Rank IC | 0.01022 | 0.01399 |
| HAC(5) Rank-IC t | 1.74 | 2.73 |
| Annualized ICIR | 1.74 | 2.90 |
| Positive IC-day fraction | 55.8% | 56.2% |
| Gross annualized L/S return | 2.52% | 10.06% |
| Gross L/S Sharpe | 0.27 | 1.19 |
| Gross cumulative L/S return | 2.64% | 12.97% |
| Decile monotonicity Spearman | 0.41 | 0.68 |

The paired mean IC improvement is 0.00377 with HAC(5) t 1.04. The paired S1-minus-S0 long-short improvement is 2.99 bps/day with HAC(5) t 0.99. Daily S0/S1 cross-sectional rank correlation averages 0.682. Thus S1 improves point estimates, but the incremental improvement over exactly paired S0 remains statistically indistinguishable under the locked inference.

Both subperiod S1 IC means are positive (0.01885 and 0.00910), compared with 0.01788 and 0.00251 for paired S0. S1 appears more stable in point estimates, especially in the second subperiod, but this does not establish robustness by itself.

## Explicit answers

1. **Are stock-level baselines heterogeneous?** Yes, materially.
2. **Does normalization improve mean IC?** Yes, from 0.01022 to 0.01399 on the paired sample.
3. **Is improvement statistically distinguishable?** No; paired HAC t is 1.04.
4. **Does it improve decile monotonicity?** Yes in this sample, though the pattern is not perfectly monotonic.
5. **Does it improve long-short performance?** Yes in gross point estimates; paired HAC evidence is weak.
6. **Is S1 more stable?** It has stronger point estimates in both predefined subperiods, but not decisive paired statistical evidence.
7. **Carry into final realistic backtest?** Yes, only as the locked, pre-specified primary candidate—not as a proven superior signal.

## Outputs

- `data/processed/phase7_abnormal_signal_panel.parquet`
- `results/tables/phase7_s0_s1_summary.csv`
- `results/tables/phase7_paired_differences.csv`
- `results/tables/phase7_eligibility_summary.csv`
- `results/tables/phase7_extreme_z.csv`
- `results/tables/phase7_*.csv`
- `results/figures/phase7_*.png`
