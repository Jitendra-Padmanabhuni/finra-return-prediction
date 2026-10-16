# Phase 6 Confound Analysis Report

## Scope

This phase leaves the naive signal unchanged and asks what the raw FINRA ratio is associated with. It uses the locked 2025-05-28–2026-08-31 window, exactly 20 strictly prior valid observations for volume surprise, exactly 20 strictly prior close-to-close returns for realized volatility, and HAC/Newey–West lag 5. No abnormal signal, state conditioning, transaction costs, alternative horizon, or optimization was introduced.

Daily regression predictors use average-tie percentile ranks scaled to approximately `[-1,1]`. All three models use the same 126,062 observations across 317 dates. These are associational regressions, not causal identification.

## Main daily correlations

| Pair | Mean daily Spearman | HAC(5) t | Same-sign day fraction |
| --- | ---: | ---: | ---: |
| q, same-day O-C return | 0.0759 | 12.81 | 80.1% |
| q, reversal | -0.0759 | -12.81 | 80.1% |
| q, volume surprise | -0.0489 | -10.38 | 80.4% |
| q, prior realized volatility | 0.0003 | 0.04 | 51.1% |
| S0, next-session O-C return | 0.0095 | 1.66 | 55.5% |

The same-day-return relation is stable but smaller in the second subperiod: 0.0870 then 0.0647. The volume-surprise relation is negative in both periods: -0.0398 then -0.0582. Prior-volatility correlation changes from 0.0299 to -0.0295, leaving essentially zero full-sample association.

The complete 21-pair correlation matrix, HAC inference, sign consistency, and both subperiods are in `results/tables/phase6_correlation_*.csv`.

## Quintile diagnostics

Mean q rises across same-day-return quintiles from 0.4937 in the lowest-return quintile to 0.5224 in the highest. Thus higher observed FINRA short-volume ratios occur with stronger same-day price performance, not simply same-day declines. Within-quintile S0 Rank IC is positive in four of five quintiles but statistically clear only in the lowest same-day-return quintile; the middle quintile is slightly negative.

| Same-day-return quintile | Mean q | Mean S0 | Mean next-session return | Mean within-quintile S0 IC |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.4937 | -0.4937 | 0.0410% | 0.0226 |
| 2 | 0.4966 | -0.4966 | 0.0170% | 0.0117 |
| 3 | 0.5006 | -0.5006 | 0.0170% | -0.0014 |
| 4 | 0.5123 | -0.5123 | 0.0079% | 0.0113 |
| 5 | 0.5224 | -0.5224 | 0.0136% | 0.0041 |

Mean q declines across volume-surprise quintiles from 0.5153 to 0.4937, consistent with the negative daily rank correlation. The prior-volatility quintile pattern is nonmonotonic (0.4978, 0.5033, 0.5150, 0.5144, 0.4951), consistent with negligible full-sample rank association.

## Common-sample daily regressions

| Specification | Mean coefficient on rank S0 | HAC(5) t |
| --- | ---: | ---: |
| Model 1: S0 | 0.000105 | 0.57 |
| Model 2: S0 + reversal | 0.000145 | 0.82 |
| Model 3: S0 + reversal + volume surprise + realized volatility | 0.000141 | 0.82 |

The S0 coefficient retains the expected positive sign and increases modestly after reversal is added. Observable controls therefore do not explain away the weak relationship, but none of the S0 coefficients is statistically persuasive.

## Explicit answers

- **Is q strongly related to same-day price movement?** Yes. The association is positive, stable, and statistically strong, although economically modest in rank-correlation magnitude.
- **Is q strongly related to unusual volume or prior volatility?** It has a stable, statistically strong negative association with volume surprise. Its full-sample association with prior volatility is effectively zero and unstable across subperiods.
- **Does S0 retain the expected positive next-day relationship after reversal?** Yes in sign, but weakly: its HAC t-statistic is only 0.82 with reversal.
- **Incremental or market-state proxy?** The raw ratio clearly contains observable same-day price/volume-state variation. Its S0 coefficient is not attenuated by these controls, so a small incremental component is plausible, but the data do not establish it convincingly.

## Outputs

- `data/processed/phase6_confound_panel.parquet`
- `results/tables/phase6_daily_correlations.csv`
- `results/tables/phase6_correlation_summary.csv`
- `results/tables/phase6_correlation_subperiods.csv`
- `results/tables/phase6_quintile_summary.csv`
- `results/tables/phase6_daily_regression_coefficients.csv`
- `results/tables/phase6_regression_summary.csv`
- `results/figures/phase6_*.png`
