# Phase 12 — Final research interpretation

## Research question and measure

This project asked whether unusually high FINRA-reported short-sale volume for a stock predicts weaker relative returns during the next shared market session. The economic hypothesis was that unusually heavy short-marked selling may contain adverse information; therefore, stocks with lower raw or abnormal short-volume measures should rank higher for next-session returns.

FINRA daily short-sale volume is the file's aggregate volume of trades marked short in exchange-listed securities reported through FINRA facilities, including trade reporting facilities and the ADF; short-exempt volume is reported separately and is not added again. It measures reported short-marked transaction flow, not all U.S. trading. It does **not** measure outstanding short positions, trader identity, investor type, intent, conviction, position formation, or whether a position was later covered. A short-marked sale need not create a lasting directional exposure, and the public files do not connect sales to subsequent purchases.

The target was each stock's next shared-session adjusted open-to-close return, `adjusted_close[t+1] / adjusted_open[t+1] - 1`, evaluated cross-sectionally. The mapping always used the next common market session, never the next stock-specific available observation.

## Signal progression and frozen choice

S0 was the negative raw FINRA ratio, `-(ShortVolume / TotalVolume)`. S1 was the negative stock-specific abnormality: current ratio minus its median over exactly 60 prior shared dates, divided by `1.4826 × MAD + 0.000001`. S2 further removed the contemporaneous median abnormality within 25 daily cells formed from volume surprise and prior volatility. Phase 9 converted frozen S1 into a bounded daily rank score from -1 to +1. That monotonic transformation improved interpretability and portfolio use but did not change rank-based predictive content. S0 remained the baseline and S2 the robustness comparator.

S1 remained primary because its standalone Rank IC was positive in both separately analyzed samples. Confound analysis found that the raw ratio was strongly related to same-day price movement and unusual volume; reversal controls left S0's expected positive coefficient intact but statistically weak. Normalization improved some point estimates and portfolio diagnostics, but its paired advantage over S0 was not established: the S1-minus-S0 mean IC difference was -0.00089 in the additional sample and +0.00234 in the original sample, with HAC(5) t-statistics of -0.33 and 0.63. S2 substantially reduced dependence on volume surprise, but its paired IC improvement over S1 was positive only in the additional sample (+0.00176) and negative in the original sample (-0.00117). It therefore failed the predeclared replacement rule.

## Authoritative headline evidence

The samples are not pooled because they use different universe methodologies: best-effort reconstructed historical membership versus a fixed September 2026 candidate snapshot.

| Statistic | Additional: 2023-01-03–2025-05-27 | Original: 2025-05-28–2026-08-31 | Source |
| --- | ---: | ---: | --- |
| S1 mean daily Rank IC | 0.00655 | 0.01295 | [Phase 7A performance](../results/tables/phase7a_performance_summary.csv) |
| S1 Rank IC HAC(5) t-statistic | 2.51 | 2.59 | [Phase 7A performance](../results/tables/phase7a_performance_summary.csv) |
| Continuous gross mean return | 0.75 bp/day | 1.68 bp/day | [Phase 10 performance](../results/tables/phase10_performance_summary.csv) |
| Continuous gross HAC(5) t-statistic | 1.71 | 1.64 | [Phase 10 performance](../results/tables/phase10_performance_summary.csv) |
| Net mean at 2.5 bp per side | -4.25 bp/day | -3.32 bp/day | [Phase 10 performance](../results/tables/phase10_performance_summary.csv) |
| Break-even one-way cost | 0.37 bp | 0.84 bp | [Phase 10 performance](../results/tables/phase10_performance_summary.csv) |
| 1,000-permutation empirical one-sided p | 0.000999 | 0.000999 | [Phase 11 placebo](../results/tables/phase11_placebo_summary.csv) |

No randomized assignment matched or exceeded the actual mean in either sample. With the recorded plus-one convention and 1,000 permutations, `1 / 1,001 = 0.000999` is the minimum attainable empirical p-value. This rejects the specific within-date random-assignment placebo; it does not establish causality.

Positive Rank IC, a strong permutation result, modest portfolio t-statistics, and negative net returns are compatible. Rank IC detects a recurring ordinal cross-sectional relationship and aggregates many stock comparisons. The permutation test asks whether the actual stock-score matching beats shuffled matching conditional on each date. Portfolio inference instead concerns the magnitude and time-series variability of one economically scaled daily return over 601 and 317 sessions; those gross HAC t-statistics remained below conventional two-sided significance. Finally, the fully rebalanced intraday portfolio paid a modeled 5 bp round trip at 2.5 bp per side, far above its 0.75 and 1.68 bp gross daily means.

## Conclusion, limitations, and next work

The public measure contains repeatable cross-sectional information in both samples, but the evidence does not prove informed directional short selling. The effect was too small for the tested fully rebalanced intraday standalone strategy after reasonable illustrative costs. It may still be useful within a broader model, execution process, or lower-turnover strategy, but those uses were not tested.

Material limitations remain: current-snapshot survivorship and selection bias; Yahoo price, corporate-action, and identifier limitations; no licensed security master or complete delisted-security coverage; unverified FINRA revision vintages and precise historical pre-open availability; and aggregate short volume's inability to identify trader type, intent, position formation, or short covering. Borrow fees, market impact, locates, financing, taxes, and commissions were not modeled. Adequate historical sector and market-cap classifications were unavailable.

Another month should prioritize licensed survivorship-safe equity data with permanent identifiers; verification of FINRA publication timing and historical vintages; better execution and transaction-cost data; pre-registered lower-turnover and alternative-horizon tests; and mechanism tests using separate short-interest or borrow data if available.

AI tools assisted coding, validation, and research organization. The methodology, assumptions, decisions, limitations, and conclusions remain explicitly documented and auditable.
