# Phase 7B Candidate-History-Layer Report

## Completed

Phase 7B is complete using existing data only. No Phase 7A historical files were acquired.

The candidate-history panel contains 205,224 rows: 503 timestamped candidates on each of 408 shared market dates from 2025-01-15 through 2026-08-31. It has one row per `(date, canonical security)`, separately retains canonical/Yahoo/FINRA identifiers and market/FINRA availability status, and attaches the unchanged corrected top-400 membership Boolean.

All rolling Phase 6 and 7 features were calculated before filtering on membership. Top-400 membership is imposed only on the signal date for the locked 2025-05-28–2026-08-31 evaluation. The prior corrected member-history outputs were preserved in `baseline/corrected_universe_member_history_phase7b/` and verified against its 62-file SHA-256 manifest.

## Candidate-history coverage

| Signal-date membership | Market/FINRA status | Rows |
| --- | --- | ---: |
| Member | Present / present | 150,151 |
| Member | Present / missing FINRA | 648 |
| Member | Missing market / present FINRA | 1 |
| Nonmember | Present / present | 52,709 |
| Nonmember | Present / missing FINRA | 804 |
| Nonmember | Missing market / missing FINRA | 911 |

The candidate panel has exactly the same 150,800 corrected top-400 member rows as Phase 2. Full-sample S0 daily Rank IC reproduces Phase 5 exactly: 126,271 eligible rows, mean IC 0.01093, HAC(5) t 1.90, and gross Sharpe 0.63.

## Eligibility

| S1 status | Member-history | Candidate-history | Change |
| --- | ---: | ---: | ---: |
| Eligible | 115,007 | 125,980 | +10,973 |
| Interrupted universe history | 11,084 | 0 | -11,084 |
| Missing FINRA history | 181 | 292 | +111 |
| Current q missing | 528 | 528 | 0 |

Candidate history recovers 10,973 S1-eligible stock-days, a 9.5% increase over the member-history baseline. All 317 locked signal dates remain represented.

## Phase 6 confound analysis

| Relationship | Member history | Candidate history |
| --- | ---: | ---: |
| q vs same-day return, mean Spearman (HAC t) | 0.07515 (12.73) | 0.07515 (12.73) |
| q vs volume surprise | -0.04855 (-10.32) | -0.05629 (-11.44) |
| q vs prior volatility | 0.02157 (3.11) | 0.00926 (1.38) |
| S0 rank coefficient, model 1 | 0.000143 (0.78) | 0.000151 (0.83) |
| S0 rank coefficient, model 2 (+ reversal) | 0.000178 (1.00) | 0.000186 (1.05) |
| S0 rank coefficient, model 3 (+ controls) | 0.000173 (1.00) | 0.000168 (0.98) |

Same-day price movement and unusual volume remain strong confounds. The apparent member-history full-sample q/volatility relationship does not survive as two-sided statistically convincing after candidate-history construction. S0 remains positive but statistically weak after reversal and controls. These regressions remain associational.

## Phase 7 frozen S1 evaluation

All performance is gross and illustrative. The one-sided p-values below are asymptotic HAC p-values for the supplementary directional hypothesis `H0: effect <= 0` against `HA: effect > 0`; the locked two-sided HAC rule remains the primary decision standard.

| Metric | Paired S0 | S1 |
| --- | ---: | ---: |
| Mean Rank IC | 0.01062 | 0.01295 |
| Two-sided HAC(5) t | 1.83 | 2.59 |
| Supplementary one-sided IC p | 0.0336 | 0.0048 |
| Annualized ICIR | 1.81 | 2.78 |
| Positive-IC fraction | 56.5% | 58.4% |
| Gross L/S mean daily return | 2.06 bps | 3.01 bps |
| Gross L/S Sharpe | 0.57 | 0.91 |
| Gross cumulative L/S return | 6.20% | 9.55% |
| Decile monotonicity Spearman | 0.37 | 0.61 |

S1-minus-S0 paired mean IC is 0.00234 with two-sided HAC t 0.63 and supplementary one-sided p 0.265. The paired long-short difference is 0.95 bps/day with HAC t 0.33 and one-sided p 0.370. Thus S1 remains independently significant by the locked two-sided IC criterion, but its incremental advantage over S0 is not statistically distinguishable.

Both S1 subperiod IC means remain positive: 0.01680 (HAC t 2.39) and 0.00908 (t 1.30). S0 is 0.01742 (t 2.43) and 0.00377 (t 0.42), respectively.

## Comparison with universe-member-only history

| Metric | Member history S1 | Candidate history S1 |
| --- | ---: | ---: |
| Mean IC | 0.01399 | 0.01295 |
| HAC t | 2.73 | 2.59 |
| Supplementary one-sided IC p | 0.0032 | 0.0048 |
| ICIR | 2.90 | 2.78 |
| L/S Sharpe | 1.19 | 0.91 |
| Cumulative gross L/S | 12.97% | 9.55% |
| Decile monotonicity | 0.68 | 0.61 |

The candidate-history architecture is more faithful to the stated information set and increases eligibility, but S1 point estimates are modestly lower. S1 does not depend on uninterrupted top-400 membership to remain positive and two-sided HAC-significant; however, the stronger member-history point estimates are not replicated after the restriction is removed.

## Explicit answers

1. **How much eligibility is recovered?** 10,973 stock-days, or 9.5% relative to the member-history baseline.
2. **Do Phase 6 conclusions change?** Same-day return and volume conclusions do not. The prior-volatility association weakens from HAC t 3.11 to 1.38 and is no longer two-sided statistically convincing. S0 remains weakly positive after controls.
3. **Does S1 remain independently significant?** Yes. Its mean IC is 0.01295 with two-sided HAC(5) t 2.59.
4. **Does performance depend on uninterrupted top-400 membership?** No for the existence of positive, significant S1 IC; yes in the limited sense that performance point estimates are lower when all valid candidate history is retained.
5. **Does the substantive research conclusion change?** No. S1 remains a promising normalized candidate with positive standalone IC, but neither architecture establishes statistically distinguishable superiority over paired S0. S0 remains directionally positive but not convincing under the locked primary rules.

## Validation

- A synthetic security with continuous raw data, a membership interruption, and reentry retains valid Phase 6/7 histories and is signal-eligible immediately on reentry.
- The same synthetic test changes only future raw data and verifies that features at the reentry date do not change.
- Candidate panel cardinality, one-row keys, availability statuses, and exact corrected membership attachment are asserted.
- Full-sample S0 daily Rank IC matches Phase 5 exactly.
- All seven project tests pass.
- No target, signal, ranking, decile, epsilon, lookback, or HAC parameter changed.

## Problems and limitations

The project retains all existing prototype limitations: current-snapshot survivorship/selection bias, public Yahoo market data, missing permanent identifiers and delisted securities, FINRA revision-vintage uncertainty, and gross illustrative performance. Candidate-history construction cures the artificial membership-history interruption, not those broader data limitations.

## Decisions required

None. Phase 7A historical acquisition remains unstarted, and this phase stops for review.

## Files changed

- Candidate panel and frozen feature panel: `data/processed/candidate_history_panel.{parquet,csv}` and `candidate_history_feature_panel.parquet`.
- Phase 7B evaluation panels: `data/processed/phase7b_phase6_evaluation_panel.parquet` and `phase7b_phase7_evaluation_panel.parquet`.
- Reusable implementation: `src/candidate_history_features.py`, `src/build_candidate_history_panel.py`, `src/evaluate_candidate_history_phase7b.py`, `src/compare_phase7b_candidate_history.py`.
- Validation: `tests/test_candidate_history_features.py` and expanded `tests/test_corrected_pipeline.py`.
- Results and figures: `results/tables/phase7b_*` and `results/figures/phase7b_*`.
- Preserved baseline: `baseline/corrected_universe_member_history_phase7b/`.
