# Phase 8 — Pre-specified conditional abnormal signal

## Completed

- Locked the five-by-five volume-surprise/prior-volatility conditioning and S2 decision rule before calculation.
- Preserved the additional reconstructed-membership and original fixed-snapshot samples as separate analyses. No pooled estimate was calculated.
- Built S2 only from top-400 signal-date members with valid frozen `z`, volume surprise, and realized volatility; target fields were excluded until signal formation completed.
- Assigned independent five-bucket daily volume-surprise and volatility ranks using the stable alphabetical tie rule, created all 25 cells, and used the contemporaneous inclusive cell median exactly as specified.
- Evaluated S0, S1, and S2 on the exact same valid-S0/S1/S2/target stock-date sample in each period.

## Key findings

All performance is gross and illustrative. One-sided p-values are supplementary; two-sided HAC(5) inference remains primary.

| Sample / signal | Mean IC | HAC(5) t | One-sided p | ICIR | Positive IC days | Gross L/S Sharpe | HAC(5) L/S t | Cumulative | Max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Additional S0 | 0.00744 | 2.24 | 0.0126 | 1.49 | 53.08% | 0.66 | 1.06 | 10.89% | -10.18% |
| Additional S1 | 0.00655 | 2.51 | 0.0061 | 1.58 | 52.91% | 1.22 | 2.08 | 20.42% | -4.78% |
| Additional S2 | 0.00832 | 3.48 | 0.0003 | 2.20 | 56.07% | 1.61 | 2.73 | 22.87% | -5.26% |
| Original S0 | 0.01062 | 1.83 | 0.0336 | 1.81 | 56.47% | 0.57 | 0.58 | 6.20% | -13.02% |
| Original S1 | 0.01295 | 2.59 | 0.0048 | 2.78 | 58.36% | 0.91 | 0.90 | 9.55% | -9.05% |
| Original S2 | 0.01178 | 2.55 | 0.0053 | 2.70 | 58.36% | 1.42 | 1.35 | 15.10% | -8.37% |

S2 improves point estimates versus S1 in the additional sample, with S2-minus-S1 mean IC of +0.00176 (HAC t=1.56; supplementary one-sided p=0.059). In the original sample, it is lower by −0.00117 (HAC t=−0.90; one-sided p=0.815). Neither paired difference is statistically convincing under the locked two-sided standard.

The S2-minus-S1 long-short mean is +0.31 bps/day in the additional sample (HAC t=0.29) and +1.55 bps/day in the original sample (t=0.89). These gross portfolio differences are also not statistically distinguishable from zero.

## State-dependence diagnostics

Conditioning substantially reduces mean daily cross-sectional S1 dependence on volume surprise:

| Sample | Signal | VS correlation | Prior-vol correlation | Same-day-return correlation | Reversal correlation |
| --- | --- | ---: | ---: | ---: | ---: |
| Additional | S1 | 0.0603 | 0.0090 | -0.1203 | 0.1203 |
| Additional | S2 | 0.0054 | 0.0029 | -0.1149 | 0.1149 |
| Original | S1 | 0.0540 | 0.0023 | -0.0909 | 0.0909 |
| Original | S2 | 0.0024 | 0.0009 | -0.0847 | 0.0847 |

Thus S2 removes most state dependence on volume surprise and reduces the already small volatility relation. It does not increase same-day-return/reversal dependence; absolute correlations are modestly lower in both samples.

Daily S1/S2 rank correlations remain high (0.945 additional and 0.943 original), so S2 is a targeted residualization rather than a distinct unrelated alpha.

## State-cell and coverage diagnostics

- All 25 cells are nonempty every evaluation date. Median cell size is 16; the range is 3–36.
- Cells under 10 names make up 3.83% of additional cell-days and 3.95% of original cell-days, but only 1.93% and 2.00% of stock-days respectively.
- Small cells account for 1.90% and 1.95% of S2 extreme-decile stock-days—essentially their overall stock-day share. The primary result is therefore not concentrated in a few small cells.
- S2 retains 100% of S1 target-eligible stock-days: 240,157 additional and 125,980 original. Conditioning causes no coverage reduction.
- Every eligible stock belongs to one VS bucket, one volatility bucket, and one state cell. Every nonempty cell has numerical median residual `a` equal to zero.

## Decision rule

S2 clears standalone positive IC, HAC t≥2, coverage, monotonicity, and small-cell conditions in both samples. It fails the decisive paired requirement: S2-minus-S1 mean IC is not positive in the original sample.

**Decision: retain S1 as the leading candidate. S2 is an informative robustness test, not a replacement.**

## Globe Life diagnostic

The flagged 2024-04-10 Globe Life observation remains in the frozen sample. Its next-session return is −50.07%, but it is in neither extreme alpha decile: S0 decile 5, S1 decile 6, and S2 decile 6. Its mechanical contribution to that 40-stock decile mean is −1.25 percentage points; it does not directly enter either long or short leg. No exclusion or robustness rerun was performed.

## Validation

- The formation panel contains no forward-return or target-availability field; targets are joined only after state-cell formation.
- Sampled volume-surprise histories recompute from exactly the prior 20 shared dates and exclude t. Frozen Phase 7A/7B validation already confirms S1's exact 60-date t−1 history.
- Signal formation and common evaluation panels have unique `(sample, date, security)` keys.
- All rolling, bucket, cell-residual, target-ordering, and common-sample assertions passed.
- Automated test suite: 12/12 passed; Python source compilation passed.

## Problems and limitations

- State-cell sizes can be as low as three. The primary five-by-five structure is retained without merging because that is the locked specification.
- Gross long-short gains cannot be interpreted as implementable returns; costs remain out of scope.
- The public-data, best-effort historical identity and survivorship limitations recorded in Phase 7A remain.
- Calendar-year strength is uneven. In particular, original-period 2026 S2 IC is positive but weaker (HAC t=1.26) and its long-short mean is near zero.

## Decisions required

No decision is required to complete Phase 8. A later realistic backtest should carry S1 as the primary candidate; it may retain S2 as a pre-specified robustness comparator. Do not tune bucket counts or modify S2 based on these results.

## Files changed

- Governance: `config/research_config.yaml`, `README.md`, and `logs/research_log.md`.
- Code/tests: `src/evaluate_conditional_signal_phase8.py` and `tests/test_phase8_conditional_signal.py`.
- Processed panels: `data/processed/phase8_s2_formation_panel.parquet` and `data/processed/phase8_common_evaluation_panel.parquet`.
- Outputs: `results/tables/phase8_*` and `results/figures/phase8_*`.

No Phase 0–7B or Phase 7A output was overwritten.
