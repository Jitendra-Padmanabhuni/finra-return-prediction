# Phase 7A — Historical data extension and frozen-signal validation

## Completed

- Locked the 2022-09-01 warm-up, 2023-01-03 to 2025-05-27 additional evaluation, and 2025-05-28 to 2026-08-31 original evaluation before acquisition.
- Preserved the September 2026 S&P snapshot, public additions/removals tables, raw Yahoo downloads, 686 FINRA files and their manifest metadata, and a pre-acquisition checksum inventory of all existing project artifacts.
- Reconstructed daily membership backward, preserving 576 distinct security instances and 587 ticker aliases. Eleven source-linked ticker/identity events supplement—but do not overwrite—the raw S&P table. Paramount Global is a distinct predecessor, not an alias or silent successor substitution.
- Built features across the entire reconstructed security union before applying signal-date S&P membership and the exact-prior-20-date top-400 liquidity gate.
- Passed the predeclared coverage gate, reproduced Phase 7B exactly, and then evaluated the untouched additional period with frozen S0/S1, tie, decile, target, and HAC(5) rules.
- Did not construct S2, tune any parameter, add costs, or run a fixed-universe/alternative-horizon model.

## Key findings

All performance is gross and illustrative.

| Period / signal | Mean IC | HAC(5) t | One-sided p | ICIR | Positive IC days | Gross ann. D10-D1 | Sharpe | HAC(5) L/S t | Cumulative | Max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Additional S0, paired | 0.00744 | 2.24 | 0.0126 | 1.49 | 53.08% | 4.58% | 0.66 | 1.06 | 10.89% | -10.18% |
| Additional S1 | 0.00655 | 2.51 | 0.0061 | 1.58 | 52.91% | 8.01% | 1.22 | 2.08 | 20.42% | -4.78% |
| Original S0, paired | 0.01062 | 1.83 | 0.0336 | 1.81 | 56.47% | 5.20% | 0.57 | 0.58 | 6.20% | -13.02% |
| Original S1 | 0.01295 | 2.59 | 0.0048 | 2.78 | 58.36% | 7.60% | 0.91 | 0.90 | 9.55% | -9.05% |

The added period supports a positive S1 relationship, but not S1's superiority. On the exact paired sample, S1-minus-S0 mean IC is **-0.00089** (HAC t=-0.33; supplementary one-sided p=0.630). Its long-short improvement is +1.36 bps/day annualized arithmetically to about 3.43 percentage points, but the paired HAC t is only 0.78 (one-sided p=0.217).

S1's additional-period decile profile is modestly more monotonic than paired S0 (Spearman 0.527 versus 0.442; both have six nonnegative adjacent steps). S1 has positive mean IC and positive gross D10-D1 mean in every reported calendar-year segment, but strength is uneven: annual IC HAC t-statistics are 1.65 in 2023, 1.08 in 2024, 1.70 in early 2025, 2.32 in original-period 2025, and 1.33 in 2026. The 2026 long-short mean is essentially zero.

### Explicit answers

1. **Does S1 retain the expected positive IC in the additional period?** Yes: 0.00655, HAC(5) t=2.51.
2. **Does S1 outperform S0 there?** No on mean IC; S1 is lower by 0.00089 and the paired difference is not significant. It has a better gross long-short Sharpe and drawdown, but that paired return improvement is also not significant.
3. **Is the decile profile more monotonic?** Slightly: decile-return Spearman is 0.527 for S1 versus 0.442 for paired S0; both have six upward adjacent steps.
4. **Is performance present across calendar years?** Directionally yes, but not uniformly convincing. Mean S1 IC and long-short return are positive in every year segment, while annual t-statistics vary materially and 2026 long-short performance is near zero.
5. **Does S0 outperform S1 in any period?** Yes. S0 has the higher mean IC in the additional period. S1 has the higher mean IC in the original period, but neither paired difference is statistically distinguishable from zero.
6. **Does the combined validation materially strengthen S1?** It strengthens evidence that S1 is independently positive in a separate historical regime. It does not strengthen the claim that normalization improves on S0.
7. **Does pooling increase confidence or conceal regime differences?** Pooling was not performed. It would conceal a preidentified universe-method break: reconstructed membership in the added period versus the fixed September 2026 candidate snapshot required for exact Phase 7B reproduction.
8. **How much survivorship and identifier risk remains?** Material risk remains. Historical membership risk is reduced by the reconstruction and inclusion of removed securities, but public Yahoo coverage, missing CIKs for removed names, corporate-successor decisions, ticker reuse, and unavailable retired symbols prevent a survivorship-safe claim. The original period remains selection- and survivorship-biased by design.
9. **Does evidence justify carrying S1 into a realistic final backtest?** Qualified yes—as the frozen normalized candidate alongside S0, not as a proven superior signal. Positive IC replicated, but paired incremental evidence remains absent and regime stability is imperfect.

## Validation

- Coverage: 240,399 of 240,400 historical top-400 stock-days have complete market+FINRA data (99.9996%); market and target coverage are 100%, and one Biogen row lacks FINRA.
- Eligibility: 240,157 S1 stock-days are eligible; 242 are lost to incomplete exact-60 q history and one to missing current q. Missing values remain missing, never zero.
- Liquidity: every selected monthly window contains exactly the 20 shared dates immediately before rebalance; every post-warm-up refresh selects exactly 400 from at least 477 eligible names.
- Lookback/target: sampled S1 rows recompute exactly from t-60 through t-1; targets equal the next shared session with no stock-specific shift.
- Original reproduction: Phase 7B S0/S1 daily IC and long-short series match within 1e-15 on all 317 dates before the additional period is evaluated.
- Raw FINRA: all 686 manifest rows have positive trailers and every file checksum matches.
- Preservation: all 102 pre-acquisition Phase 7B artifacts identified by the preservation manifest retain their original checksums.
- Automated suite: 10 tests passed.

## Problems

- The public S&P changes table moved during 2026; both the current page and dated pre-move revisions are preserved.
- Yahoo logged 42 failed ticker requests, mostly retired/delisted or not-yet-trading aliases. The retired `PARA` request resolved to an unrelated/malformed price series; it is preserved but quarantined. Yahoo's `PSKY` backfilled predecessor history supplies market fields while canonical/source/FINRA identity remains distinct `PARA`.
- Removed/delisted security coverage is heterogeneous; some retired Yahoo symbols are unavailable even where FINRA rows exist. Top-400 eligibility's valid-market-history rule prevents those rows from silently entering portfolios, but this creates vendor-selection risk.
- Eleven top-400 target observations exceed 20% in absolute value. Globe Life's -50.1% observation coincides with a split-related Yahoo adjusted-open discontinuity; it is flagged and retained under the frozen Phase 4 method, not silently winsorized or deleted.
- FINRA revision-vintage history cannot be fully determined from the public endpoint.

## Decisions required

No decision is required to complete Phase 7A. Before a later phase, the sponsor may decide whether to carry both S0 and S1 into the realistic backtest. Phase 7A itself is complete and stops here. No combined-period estimate was produced because the locked methodology-comparability gate failed.

## Files changed

- Governance: `config/research_config.yaml`, `README.md`, `logs/research_log.md`, `docs/phase7a_data_quality_gate.md`, this report, and `preservation/phase7a_pre_acquisition/`.
- Code/tests: `src/reconstruct_sp500_history_phase7a.py`, `src/acquire_historical_yahoo_phase7a.py`, `src/build_phase7a_calendar.py`, `src/build_historical_panel_phase7a.py`, `src/evaluate_historical_validation_phase7a.py`, `src/candidate_history_features.py`, and `tests/test_phase7a_historical.py`.
- Raw/audit: `data/raw/phase7a_*`, the 686 `CNMSshvolYYYYMMDD.txt` files referenced by the Phase 7A manifest, and Phase 7A download/source tables under `results/tables/`.
- Processed/results: `data/processed/phase7a_*`, `results/tables/phase7a_*`, and `results/figures/phase7a_*`.

All Phase 0–7B artifacts remain preserved; Phase 7A used prefixed outputs and did not overwrite prior performance tables.
