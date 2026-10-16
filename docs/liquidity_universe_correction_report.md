# Phase 2–7 Liquidity-Universe Correction Report

## Completed

The approved correction was completed without acquiring the Phase 7A historical extension or changing any signal, target, inference, ranking, decile, or evaluation-date parameter.

The existing Phase 2–7 artifacts were copied to `legacy/expanding_liquidity_window/` before primary files were regenerated. Its manifest contains SHA-256 checksums for 92 preserved files, including the archive label. Corrected outputs are now primary; legacy results remain available only for audit and comparison.

## Exact cause and affected outputs

The former `build_monthly_membership` implementation filtered all rows with `Date < rebalance_date`, calculated a grouped median across that expanding history, and retained securities with at least 20 observations. The `liquidity_days=20` argument controlled only the minimum count. It never sliced the shared calendar to the 20 immediately preceding dates.

The error directly affected monthly and daily universe membership and therefore every downstream stock-day panel and Phase 5–7 statistic. The affected primary artifact groups were:

- `data/processed/prototype_universe_monthly.csv`, `prototype_universe_daily.csv`, and `phase2_market_universe_metadata.json`;
- `data/processed/master_stock_day_panel.{csv,parquet}` and all `results/tables/phase3_*` coverage outputs;
- `data/processed/master_stock_day_with_target.{csv,parquet}`, `phase4_target_metadata.json`, and all `results/tables/phase4_*` outputs;
- `data/processed/master_stock_day_naive_signal.parquet`, all `results/tables/phase5_*`, and all `results/figures/phase5_*`;
- `data/processed/phase6_confound_panel.parquet`, all `results/tables/phase6_*`, and all `results/figures/phase6_*`;
- `data/processed/phase7_abnormal_signal_panel.parquet`, all `results/tables/phase7_*`, and all `results/figures/phase7_*`;
- the Phase 2–7 Markdown reports and the corresponding claims in README/configuration.

The exact preserved legacy file list and checksums are in `legacy/expanding_liquidity_window/SHA256SUMS.txt`. The candidate snapshot, full pre-existing Yahoo market panel, immutable FINRA files, and research parameters were not changed. The corrected August universe required 16 additional September 1 Yahoo target rows; these were saved separately as `data/raw/yahoo_target_extension_20260901_corrected.csv`, while the legacy raw extension was retained unchanged.

## Corrected universe versus legacy

All 18 eligible monthly rebalances from 2025-03-03 through 2026-08-03 selected exactly 400 of at least 499 eligible securities. Every corrected input window contains exactly 20 shared dates, ends strictly before the rebalance, starts on the twentieth preceding shared date, excludes older rows, and requires 20 valid raw Close/Volume observations.

| Monthly comparison | Minimum | Mean | Maximum |
| --- | ---: | ---: | ---: |
| Overlap out of 400 | 381 | 384.8 | 395 |
| Names added | 5 | 15.2 | 19 |
| Names removed | 5 | 15.2 | 19 |
| Jaccard similarity | 0.9093 | 0.9271 | 0.9753 |

There are 546 monthly added/removed records across 144 distinct securities. Exact security-level medians, ranks, membership changes, and monthly summaries are in `results/tables/phase2_liquidity_correction_full_rank_comparison.csv`, `phase2_liquidity_correction_affected_securities.csv`, and `phase2_liquidity_correction_monthly_comparison.csv`.

## Corrected versus legacy S0

All performance remains gross and illustrative.

| Metric | Legacy | Corrected |
| --- | ---: | ---: |
| Eligible stock-days | 126,437 | 126,271 |
| Mean daily Rank IC | 0.00953 | 0.01093 |
| HAC(5) IC t-statistic | 1.66 | 1.90 |
| Annualized ICIR | 1.63 | 1.87 |
| Positive-IC-day fraction | 55.52% | 57.41% |
| Mean daily D10–D1 | 0.52 bps | 2.25 bps |
| Gross Sharpe | 0.14 | 0.63 |
| Gross cumulative return | 1.13% | 6.85% |

Both corrected predefined subperiod ICs remain positive (0.01741 and 0.00441). The corrected HAC IC t-statistic remains below the locked threshold of 2 and the decile profile remains insufficiently monotonic. The S0 conclusion therefore remains directionally supportive but not statistically convincing.

## Corrected versus legacy confound results

| Daily Spearman pair | Legacy mean (HAC t) | Corrected mean (HAC t) |
| --- | ---: | ---: |
| q vs same-day return | 0.07589 (12.81) | 0.07515 (12.73) |
| q vs volume surprise | -0.04894 (-10.38) | -0.04855 (-10.32) |
| q vs prior volatility | 0.00027 (0.04) | 0.02157 (3.11) |
| S0 vs next-session return | 0.00953 (1.66) | 0.01093 (1.90) |

The corrected S0 regression coefficient remains positive after reversal: model 1 is 0.000143 (t 0.78), model 2 is 0.000178 (t 1.00), and model 3 is 0.000173 (t 1.00). The main same-day-price and unusual-volume conclusions are unchanged. The prior-volatility conclusion changes: the corrected full sample is positive and statistically nonzero, but it is concentrated in subperiod 1 (0.0463 versus -0.0033 in subperiod 2), so it is not temporally stable. S0 remains plausibly incremental but statistically weak after controls; the regressions remain associational.

## Corrected versus legacy S1

| Metric | Legacy paired S0 | Corrected paired S0 | Legacy S1 | Corrected S1 |
| --- | ---: | ---: | ---: | ---: |
| Eligible S1 stock-days | 124,198 | 115,007 | 124,198 | 115,007 |
| Mean daily Rank IC | 0.00911 | 0.01022 | 0.01313 | 0.01399 |
| HAC(5) IC t-statistic | 1.56 | 1.74 | 2.66 | 2.73 |
| Annualized ICIR | 1.55 | 1.74 | 2.77 | 2.90 |
| Gross L/S Sharpe | 0.04 | 0.27 | 1.27 | 1.19 |
| Gross cumulative L/S | -0.04% | 2.64% | 13.67% | 12.97% |
| Decile monotonicity Spearman | 0.31 | 0.41 | 0.67 | 0.68 |

Corrected S1 exceeds paired S0 by 0.00377 mean IC, but the paired HAC t-statistic is 1.04. Its daily long-short advantage is 2.99 bps with HAC t 0.99. Both corrected S1 subperiod ICs are positive (0.01885 and 0.00910). Thus normalization continues to improve point estimates and monotonicity, but superiority over paired S0 remains statistically indistinguishable.

Eligibility falls because the corrected monthly screen turns over more: interrupted-universe-history exclusions rise from 2,056 to 11,084. Nevertheless, all 317 locked evaluation dates have valid S1 observations (359–374 per day), so no evaluation-period change was required. Near-zero MAD caused no exclusion.

## Substantive conclusion

The primary conclusions mostly survive the correction:

- S0 remains positive and stronger in point estimates, but still fails the locked HAC threshold and monotonicity standard.
- The strong q relationships with same-day return and volume surprise persist.
- S0 remains positive but weak after the reversal and diagnostic controls.
- S1 retains positive IC, HAC significance, improved decile monotonicity, and substantially better gross long-short results than paired S0, but the paired improvements remain statistically indistinguishable.

The substantive change is that q now has a positive full-sample association with prior realized volatility; its sign is not stable across the two predefined subperiods.

## Validation

- Two focused synthetic regression tests pass, including a construction where expanding and exact-20 medians choose different securities.
- Three corrected-pipeline artifact tests pass, covering monthly/daily membership, exact date bounds, complete Close/Volume histories, 400-name counts, fixed monthly membership, panel key uniqueness, missing-as-missing FINRA fields, target sequencing, q bounds, and S1 history counts.
- All 92 legacy archive checksums verify.
- Corrected and legacy candidate tables and full Yahoo market panels are exactly equal.
- Phase 3 has one row per expected key: 150,800 rows, 150,151 complete matches, 648 missing FINRA rows, and one missing market row.
- Phase 4 retains 150,799 targets and one missing designated-session target, with no stock-specific date shifting.
- Phase 5 and Phase 7 retain all 317 locked dates; no research parameter was changed.

Four non-research execution incidents were recorded: the first reuse-mode Phase 2 run reached a metadata-only undefined variable after writing outputs and was rerun after correction; the first checksum manifest included itself and was regenerated excluding itself; an auxiliary FINRA verifier initially looked for a nonexistent path field before being rerun against the manifest's filename field; and a strengthened CSV-recalculation test initially used an absolute tolerance below ordinary CSV float round-trip noise (maximum discrepancy about 0.0000019 on dollar-volume values as large as tens of billions). The latter was rerun with a still-negligible absolute tolerance of 0.00001. None changed data, universe logic, ranks, memberships, or results.

## Problems and remaining limitations

- The candidate set remains a September 2026 current S&P 500 snapshot and is survivorship- and selection-biased.
- The prototype lacks delisted securities, permanent identifiers, historical membership, and fully licensed corporate-action data.
- Yahoo is an unlicensed public auxiliary source, and FINRA files do not establish as-first-published revision vintage.
- Corrected FINRA completeness is 99.57%; ECHO, MRSH, FISV, and BNY remain the weakest-coverage securities.
- Higher corrected universe turnover materially reduces exact-60-date S1 eligibility.
- Performance is gross and illustrative; no costs or Phase 8 backtest were run.

## Decisions required

None within the approved correction. Phase 7A historical acquisition has not begun and remains stopped for review.

## Files changed

- Implementation: `src/build_universe.py`, `src/build_prediction_target.py`, `src/audit_liquidity_correction.py`, `src/compare_corrected_legacy_results.py`.
- Tests: `tests/test_build_universe.py`, `tests/test_corrected_pipeline.py`.
- Governance: `config/research_config.yaml`, `README.md`, `logs/research_log.md`.
- Reports: `docs/phase2_market_universe_report.md` through `docs/phase7_abnormal_signal_report.md`, plus this report.
- Corrected data/results: Phase 2–7 files under `data/processed/`, `results/tables/`, and `results/figures/`; new corrected target extension under `data/raw/`.
- Preserved legacy archive: `legacy/expanding_liquidity_window/`.
