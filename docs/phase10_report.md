# Phase 10 — Realistic Portfolio Backtest

## Completed

- Read the configuration, append-only log, and Phase 7A, Phase 7B, Phase 8, and Phase 9 reports before implementation.
- Locked all execution, exposure, cost, missing-data, and HAC(5) inference rules before backtest results were calculated.
- Backtested target-independent continuous dollar-neutral S0, S1, and S2 bounded scores from the designated next shared-session open to close, with no overnight holding. S1 equal-weight top-minus-bottom deciles are a secondary specification.
- Kept the additional reconstructed-membership and original fixed-snapshot samples separate; no pooled performance estimate was calculated.
- Applied the full 0/1/2.5/5 bps one-way cost grid on both entry and exit. The 2.5-bps-per-side case is primary and illustrative.

## Key findings

All results are illustrative. The primary signal is frozen S1, not the stronger-looking S2 robustness comparator.

| Sample | S1 gross days | Gross mean/day | Gross HAC(5) t (two-sided p) | Gross Sharpe | Gross cumulative | Break-even one-way cost | Primary net mean/day, 2.5 bps/side | Primary net cumulative |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Additional, 2023-01-03 to 2025-05-27 | 601 | +0.75 bps | 1.71 (0.088) | 0.96 | +4.54% | 0.37 bps | -4.25 bps | -22.60% |
| Original, 2025-05-28 to 2026-08-31 | 317 | +1.68 bps | 1.64 (0.102) | 1.74 | +5.42% | 0.84 bps | -3.32 bps | -10.03% |

S1 is gross-positive in both samples, but its break-even one-way cost is below 1 bp in both. Thus the primary 2.5-bps-per-side result is negative in every calendar year and in both original predefined subperiods. At 1 bp/side, S1 is already negative in both samples. The secondary S1 D10-minus-D1 portfolio is gross-positive (+1.59 bps/day additional; +1.51 bps/day original), but it is also negative at the primary cost.

On exact common available dates, S1-minus-S0 is -0.13 bps/day in the additional sample (HAC t=-0.32) and +0.67 bps/day in the original sample (t=0.87). S1-minus-S2 is -0.37 bps/day (t=-1.52) and +0.12 bps/day (t=0.39), respectively. Neither paired comparison is statistically distinguishable. Costs cancel algebraically in these paired full-gross-exposure differences, but every pre-specified cost case is recorded.

The Globe Life discontinuity remains in primary results. On 2024-04-10 it was a nonzero S1 position of +0.081% and contributed -4.07 bps to that day's portfolio. Removing only that affected S1 strategy-day as a nonprimary sensitivity changes additional-sample gross cumulative return from +4.536% to +4.541%, and primary-net cumulative return from -22.601% to -22.558%; it does not change the conclusion.

## Validation

- The Phase 9 panel reproduces the authoritative two samples and 400 signal-date universe members per date. A new preservation manifest verifies 91 Phase 7A–9 inputs both before and after the run.
- Each formed continuous portfolio exactly equals score divided by the sum of absolute scores. Daily gross exposure equals 1, net exposure is zero within `4.5e-16`, and both long and short gross exposure equal 0.5.
- Signals and weights are formed without target fields. The designated trade date is one shared, strictly later session for every signal date.
- One strategy-day is unavailable: original S0 on 2025-11-11 because FISV has no designated 2025-11-12 return and has a nonzero weight. It was retained in the exposure panel, reported explicitly, and not reweighted. S1, S2, and the S1 decile strategy have all their formed days available.
- Entry and exit costs are both applied: a 2.5-bps one-way assumption deducts 5 bps/day at unit gross exposure.
- Capacity uses only the exact twenty prior shared dates' raw `Close × Volume`. For S1 continuous, all nonzero positions have valid prior ADV; at hypothetical $10m and $50m gross, no position exceeds 1%, 5%, or 10% of that median ADV. These are mechanical diagnostics, not sizing rules.
- All 19 automated tests pass, including focused score-weight, exposure, entry-and-exit cost, missing-target, paired-sample, and arithmetic tests. The backtest reruns deterministically.

## Problems and limitations

- The assumed availability of FINRA's date-*t* file before the date-*t+1* open is an implementation assumption, not an as-first-published vintage verification.
- The additional sample uses best-effort reconstructed membership and the original sample uses a current-snapshot candidate set. Neither result is survivorship-safe, and they must not be pooled.
- The cost grid is an illustrative aggregate spread/slippage/fee assumption. Borrow fees, market impact, locate failures, financing, taxes, commissions, and capacity-induced price effects are omitted.
- Gross S1 evidence is suggestive but does not meet conventional two-sided HAC significance here; primary net performance is negative. No optimization was attempted in response.

## Decisions required

None for Phase 10 completion. Review is required before any new robustness work, alternative implementation assumption, or strategy change.

## Files changed

- Governance: `config/research_config.yaml`, `README.md`, and `logs/research_log.md`.
- Implementation and validation: `src/run_realistic_backtest_phase10.py` and `tests/test_phase10_backtest.py`.
- Preservation: `preservation/phase10_pre_backtest_source_artifacts/SHA256SUMS.txt`.
- Panels: `data/processed/phase10_daily_portfolio_exposure_panel.parquet`, `phase10_portfolio_position_panel.parquet`, and `phase10_daily_portfolio_returns_by_cost.parquet`.
- Tables: `results/tables/phase10_*`.
- Figures: `results/figures/phase10_*`.
