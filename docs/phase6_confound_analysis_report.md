# Corrected Phase 6 Confound Analysis Report

> Primary corrected result on the exact-20-date liquidity universe. All Phase 6
> definitions and HAC settings were held fixed.

## Scope

This phase leaves the naive signal unchanged and asks what the raw FINRA ratio is associated with. It uses the locked 2025-05-28–2026-08-31 window, exactly 20 strictly prior valid observations for volume surprise, exactly 20 strictly prior close-to-close returns for realized volatility, and HAC/Newey–West lag 5. No abnormal signal, state conditioning, transaction costs, alternative horizon, or optimization was introduced.

Daily regression predictors use average-tie percentile ranks scaled to approximately `[-1,1]`. All three models use the same 125,279 observations across 317 dates. These are associational regressions, not causal identification.

## Main daily correlations

| Pair | Mean daily Spearman | HAC(5) t | Same-sign day fraction |
| --- | ---: | ---: | ---: |
| q, same-day O-C return | 0.0752 | 12.73 | 79.8% |
| q, reversal | -0.0752 | -12.73 | 79.8% |
| q, volume surprise | -0.0485 | -10.32 | 78.5% |
| q, prior realized volatility | 0.0216 | 3.11 | 62.1% |
| S0, next-session O-C return | 0.0109 | 1.90 | 57.4% |

The same-day-return relation is stable but smaller in the second subperiod: 0.0855 then 0.0648. The volume-surprise relation is negative in both periods: -0.0412 then -0.0560. Prior-volatility correlation is positive in the first period (0.0463) and near zero/slightly negative in the second (-0.0033), so its positive full-sample mean is not stable across subperiods.

The complete 21-pair correlation matrix, HAC inference, sign consistency, and both subperiods are in `results/tables/phase6_correlation_*.csv`.

## Quintile diagnostics

Mean q rises across same-day-return quintiles from 0.4937 in the lowest-return quintile to 0.5224 in the highest. Thus higher observed FINRA short-volume ratios occur with stronger same-day price performance, not simply same-day declines. Within-quintile S0 Rank IC is positive in four of five quintiles but statistically clear only in the lowest same-day-return quintile; the middle quintile is slightly negative.

| Same-day-return quintile | Mean q | Mean S0 | Mean next-session return | Mean within-quintile S0 IC |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.4936 | -0.4936 | 0.0409% | 0.0208 |
| 2 | 0.4956 | -0.4956 | 0.0121% | 0.0175 |
| 3 | 0.4991 | -0.4991 | 0.0166% | 0.0004 |
| 4 | 0.5112 | -0.5112 | 0.0076% | 0.0102 |
| 5 | 0.5221 | -0.5221 | 0.0088% | 0.0042 |

Mean q declines across volume-surprise quintiles from 0.5145 to 0.4934. The prior-volatility quintile pattern remains nonmonotonic (0.4937, 0.5006, 0.5131, 0.5129, 0.5006), despite the corrected positive full-sample rank association.

## Common-sample daily regressions

| Specification | Mean coefficient on rank S0 | HAC(5) t |
| --- | ---: | ---: |
| Model 1: S0 | 0.000143 | 0.78 |
| Model 2: S0 + reversal | 0.000178 | 1.00 |
| Model 3: S0 + reversal + volume surprise + realized volatility | 0.000173 | 1.00 |

The S0 coefficient retains the expected positive sign and increases modestly after reversal is added. Observable controls therefore do not explain away the weak relationship, but none of the S0 coefficients is statistically persuasive.

## Explicit answers

- **Is q strongly related to same-day price movement?** Yes. The association is positive, stable, and statistically strong, although economically modest in rank-correlation magnitude.
- **Is q strongly related to unusual volume or prior volatility?** It has a stable, statistically strong negative association with volume surprise. The corrected sample also has a statistically positive full-period association with prior volatility, but that relation is concentrated in the first subperiod and is not temporally stable.
- **Does S0 retain the expected positive next-day relationship after reversal?** Yes in sign, but weakly: its HAC t-statistic is 1.00 with reversal.
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
