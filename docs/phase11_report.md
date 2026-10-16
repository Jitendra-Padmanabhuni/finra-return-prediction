# Phase 11 — Robustness and Falsification Analysis

## Completed

- Read the governing configuration, log, and Phase 7A–10 reports before implementation.
- Locked the robustness definitions before examining results. S1 and `final_rank_score` remain frozen; the Phase 10 continuous dollar-neutral portfolio remains primary.
- Kept the additional reconstructed-membership and original fixed-snapshot samples separate. No pooled estimate was calculated.
- Ran time-stability, HAC-lag, exploratory breadth, fixed-first-date-universe, liquidity-neutral, outlier/concentration, leave-one-year-out, and deterministic 1,000-permutation placebo analyses.
- No new data were acquired and no signal or primary portfolio rule was changed.

## Key findings

The unchanged Phase 10 primary gross results remain positive but modest: S1 averages **+0.75 bps/day** in the additional sample and **+1.68 bps/day** in the original sample. The primary 2.5-bps-per-side net results remain **-4.25** and **-3.32 bps/day**, respectively. The central economic conclusion is unchanged.

Time stability is mixed rather than uniformly broad. Gross calendar-year means are +1.07, +0.24, and +1.23 bps in additional 2023, 2024, and partial 2025; original 2025 and 2026 are +2.46 and +0.97 bps. Both sample halves are positive, but the original first half (+2.42 bps) is materially stronger than its second half (+0.94 bps). HAC sensitivity does not create a robust conventional result: additional gross t-statistics range from 1.49 to 1.81 across lags 0–20; original ranges from 1.95 at lag 0 to 1.41 at lag 20.

Exploratory breadth variants are gross-positive in both samples, but none is a permitted replacement. At 1 bp per side, the primary continuous portfolio is negative in both samples; some original-sample exploratory tails remain slightly positive (5%: +0.79 bps/day; 20%: +0.02 bps/day), but this is post-result exploratory evidence and does not rescue the primary result. Every breadth variant is negative at 2.5 bps per side.

The fixed-first-date universe diagnostic is close to the primary result: gross +0.70 bps/day additional and +1.68 bps/day original. It does not remove survivorship bias and is not a superior universe construction. Liquidity-neutralization is also similar gross (+0.67 and +1.80 bps/day) and negative at primary cost. No usable existing sector classification was present, so sector-neutralization was not calculated.

The deterministic within-date placebo test is sharply separated from the actual gross result. With 1,000 permutations and seed `20260911`, the empirical one-sided probability that placebo mean return is at least the actual mean is **0.000999 in each sample** (plus-one correction). This addresses score-to-security assignment chance, not data-mining, universe, vendor, or implementation risk.

Outlier checks do not overturn the result. Removing all previously flagged extreme-target strategy-days changes additional gross cumulative return from 4.54% to 6.04% and original from 5.42% to 5.38%; the primary-cost conclusion remains negative. Removing Globe Life alone changes additional gross cumulative return only to 4.54%. The best additional day contributed +101.1 bps and the worst -137.9 bps; corresponding original values were +69.1 and -61.6 bps. Leave-one-calendar-year-out gross means stay positive in every case. The ten most influential securities account for about -0.316% signed cumulative contribution in additional and -0.054% in original, with absolute contribution sums of 3.45% and 2.90%; no single year or security reverses the full-sample gross sign.

## Validation

- A Phase 11 manifest hash-checks 139 Phase 7A–10 source artifacts before and after execution.
- Phase 10 S1 primary daily returns reproduce exactly before variants are evaluated.
- Every formed variant is checked for unit gross exposure, zero net exposure, and 0.5/0.5 long-short legs.
- Signal and portfolio formation use scores, membership, and prior liquidity only; target data are consulted only for availability and return evaluation. Missing observations remain missing.
- The first-date fixed universe is formed separately for each sample and excludes later entrants without replacing missing observations.
- Prior dollar-volume quintiles use the exactly prior-20-session raw `Close × Volume` median; all 240,157 additional and 125,980 original S1 positions have valid prior liquidity diagnostics.
- Sector status is explicitly reported as unavailable: no adequate existing sector field is present in the Phase 9/10 panels.
- Placebo permutations are deterministic under the recorded seed and samples remain separate.
- The complete test suite passes: 22 tests.

## Problems and limitations

- These checks cannot remove survivorship and selection bias, identifier uncertainty, Yahoo corporate-action issues, or unknown as-first-published FINRA vintages.
- Sector-neutralization would require a new classification source and was intentionally not acquired.
- Breadth, fixed-universe, liquidity-neutral, and outlier exclusions are robustness or exploratory diagnostics, not alternative optimized strategies.
- The placebo test is conditional on the existing universe, score distribution, target sample, and data history; it is not a full research-process permutation.
- Transaction-cost, borrow, impact, locate, financing, tax, and commission limitations from Phase 10 remain.

## Decisions required

None. The frozen Phase 10 primary specification remains primary. No robustness result justifies modifying S1, changing costs, or selecting a replacement portfolio.

## Files changed

- Governance: `config/research_config.yaml` and `logs/research_log.md`.
- Implementation/tests: `src/run_robustness_phase11.py` and `tests/test_phase11_robustness.py`.
- Preservation: `preservation/phase11_pre_robustness_source_artifacts/SHA256SUMS.txt`.
- Panels: `data/processed/phase11_daily_robustness_portfolio_panel.parquet` and `phase11_robustness_positions.parquet`.
- Tables: `results/tables/phase11_*`.
- Figures: `results/figures/phase11_*`, including the two deterministic placebo distributions.
