# Phase 15 — Robustness and Falsification Analysis, Extended to S2

> This phase is a direct mirror of Phase 11's methodology (`docs/phase11_report.md`,
> `src/run_robustness_phase11.py`), substituting S2 for S1 as the subject signal, with every
> locked parameter reused unchanged. **Governance note (accurate when written):** S2 has not been
> promoted to primary anywhere in this project. Frozen Phase 9 roles are unchanged — S1 primary,
> S0 baseline, S2 robustness comparator. This phase extends the robustness battery to the
> comparator signal for parity and completeness; it is additive and does not alter that governance.
>
> **Superseding note, 2026-09-12 (later the same day).** S2 was subsequently promoted to primary
> by an explicit governance override, with S1 becoming former primary, now comparator; S0 is
> unchanged. This report's own findings below — including the placebo gap — were cited as one of
> three reasons for that override. See `docs/s2_primary_promotion_governance_override.md`. The
> governance note above is preserved unchanged as an accurate record of what was true when this
> report was written.

## Completed

- Read the governing configuration and append-only log, then locked the full specification —
  identical to Phase 11's, with S2 substituted throughout — in `config/research_config.yaml`
  and `logs/research_log.md` before running anything.
- Pinned Phase 9's S2-bearing score panel and Phase 10's S2 backtest artifacts (the same
  physical files Phase 11 pinned for S1, since S0/S1/S2 share the same frozen panels) as
  immutable source inputs in `preservation/phase15_pre_robustness_s2_source_artifacts/SHA256SUMS.txt`
  (140 artifacts), verified unchanged both before and after execution.
- Reproduced Phase 10's frozen `S2_continuous` daily gross returns exactly (`atol=1e-15`)
  before evaluating any robustness variant, mirroring Phase 11's own S1 reproduction check.
- Ran the identical battery on S2 in **both** the additional (2023-01-03 to 2025-05-27) and
  original (2025-05-28 to 2026-08-31) samples, matching Phase 11's own scope: time-stability
  (calendar years, half-splits, HAC-lag sensitivity at 0/5/10/20), breadth variants at 5%/10%/20%
  (post-result exploratory, not decisive), a fixed-first-date-universe diagnostic, a
  liquidity-neutral control (S2's own bounded score demeaned within daily prior-20-session
  dollar-volume quintiles; sector-neutralization remains unavailable for the same documented
  reason as Phase 11), outlier/concentration diagnostics (Globe Life, all previously-flagged
  extreme targets, leave-one-calendar-year-out, top-10 most-influential-security contribution),
  and the deterministic within-date placebo/permutation test (1,000 permutations, seed `20260911`
  reused unchanged from Phase 11 for direct comparability).
- Modified no Phase 1–14 frozen artifact. This is a new, additive analysis.

## Key findings

**Headline: S2 clears every Phase 11 check qualitatively except the placebo/permutation test,
where it is materially weaker than S1 — though still below the conventional 0.05 threshold in
both samples.** Every other check shows the same qualitative pattern S1 showed: gross-positive,
net-negative at the primary 2.5-bps-per-side cost, sign-stable across years, and no single
security or day dominating the result. S2's single-day tail risk is notably smaller than S1's.

### Side-by-side: Phase 11 (S1) vs Phase 15 (S2)

All figures gross unless labeled net. Primary cost is 2.5 bps per side.

| Check | Sample | S1 (Phase 11) | S2 (Phase 15) |
| --- | --- | ---: | ---: |
| **Primary continuous gross mean (bps/day, HAC(5) t)** | Additional | 0.746, t=1.71 | 1.112, t=2.97 |
| | Original | 1.678, t=1.64 | 1.555, t=1.70 |
| **Primary continuous net mean at 2.5 bps/side (bps/day)** | Additional | −4.254 | −3.888 |
| | Original | −3.322 | −3.445 |
| **HAC-lag sensitivity, gross t (lags 0/5/10/20)** | Additional | 1.49 / 1.71 / 1.78 / 1.81 | 2.87 / 2.97 / 2.97 / 2.97 |
| | Original | 1.95 / 1.64 / 1.56 / 1.41 | 2.02 / 1.70 / 1.62 / 1.55 |
| **Calendar-year gross means (bps/day)** | Additional 2023 / 2024 / 2025-part | 1.07 / 0.24 / 1.23 | 1.37 / 0.41 / 2.25 |
| | Original 2025 / 2026 | 2.46 / 0.97 | 2.49 / 0.71 |
| **Breadth variants at 2.5 bps/side** | Both | All negative | All negative |
| **Fixed-universe gross mean (bps/day, t)** | Additional | 0.696, t=1.58 | 1.018, t=2.68 |
| | Original | 1.682, t=1.62 | 1.601, t=1.73 |
| **Liquidity-neutral gross mean (bps/day, t)** | Additional | 0.675, t=1.63 | 1.041, t=2.89 |
| | Original | 1.796, t=1.90 | 1.628, t=1.91 |
| **Sector-neutral** | Both | Unavailable (no field) | Unavailable (no field) |
| **Leave-one-year-out sign** | Both | Always positive | Always positive |
| **Worst single day (bps)** | Additional | −137.95 | −38.39 |
| | Original | −61.61 | −49.71 |
| **Top-10 security abs. contribution (cumulative %)** | Additional | 3.45% | 3.56% |
| | Original | 2.90% | 2.71% |
| **Placebo empirical one-sided p (1,000 perms, seed 20260911)** | Additional | **0.000999** | **0.019980** |
| | Original | **0.000999** | **0.017982** |
| **Placebo distribution mean (actual mean shown for reference)** | Additional | placebo −0.0172%, actual 0.0075% | placebo +0.0033%, actual 0.0111% |
| | Original | placebo −0.0108%, actual 0.0168% | placebo +0.0014%, actual 0.0155% |

### The one place S2 does not hold up as well: the placebo test

S1's actual gross mean exceeded essentially every one of 1,000 within-date score permutations in
both samples (`p = 0.000999`, the minimum attainable value with 1,000 permutations under the
plus-one convention — no permutation matched or beat it). **S2's result is qualitatively the
same direction but far less extreme**: `p = 0.0200` additional and `p = 0.0180` original — still
below the conventional 5% threshold, so the specific within-date random-assignment null is still
rejected in both samples, but by a much narrower margin. Roughly 1 in 50 random permutations of
S2's scores matched or beat its actual mean, versus roughly 1 in 1,000 for S1.

The underlying placebo distributions also differ in a way that is worth flagging on its own: S1's
placebo-permutation mean sits clearly negative in both samples (−0.0172%, −0.0108%), so the
actual result is a genuine positive outlier against a distribution centered below zero. S2's
placebo-permutation mean sits close to zero and **slightly positive** in both samples (+0.0033%,
+0.0014%), so S2's actual result is a smaller positive deviation from a distribution that is
itself not clearly negative. This is a structural difference in how the two signals' score
distributions interact with the random-reassignment mechanism (S2 is a state-conditioned residual
of S1, not the same score shape), not a computational discrepancy — both placebo runs used the
identical method, seed, and permutation count, verified in tests.

### Where S2 matches or slightly outperforms S1

- **Gross HAC(5) t-statistics are higher for S2 in the additional sample at every lag** (2.87–2.97
  vs S1's 1.49–1.81), and comparable in the original sample (1.55–2.02 vs 1.41–1.95).
- **Fixed-universe and liquidity-neutral gross means are stronger for S2 in the additional sample**
  (1.02/1.04 vs S1's 0.70/0.68 bps/day) and close to S1's in the original sample.
- **Tail risk is smaller for S2 in both samples**: its worst single day is −38.4 bps (additional)
  and −49.7 bps (original), versus S1's −137.9 bps and −61.6 bps.
- **Leave-one-year-out sign stability and top-10 security concentration are essentially
  identical** between the two signals — no single year or security drives either result.

### Where the conclusion is unchanged for both signals

- Every breadth variant (5%, 10%, 20%) is negative at the primary 2.5-bps-per-side cost, in both
  samples, for S2 exactly as it was for S1.
- Net returns at the primary cost remain solidly negative for S2 (−3.89 and −3.45 bps/day),
  comparable in magnitude to S1's (−4.25 and −3.32 bps/day).
- Sector-neutralization remains unavailable for the identical documented reason as Phase 11: no
  adequate existing sector classification is present in the Phase 9/10 panels.

## Validation

- The pre-registered specification in `config/research_config.yaml` and `logs/research_log.md`
  was locked before any result was viewed.
- `preservation/phase15_pre_robustness_s2_source_artifacts/SHA256SUMS.txt` pins 140 Phase 9/10
  source artifacts (one more than Phase 11's original 139, because the frozen artifact set now
  also includes the 2026-09-12 one-sided-IC-amendment output that did not exist when Phase 11
  ran); all verified unchanged both before this phase's execution and after its outputs were
  written.
- Phase 10's frozen `S2_continuous` daily gross returns were reproduced exactly
  (`np.allclose(..., atol=1e-15)`) before any robustness variant was formed, identical to Phase
  11's own S1 reproduction check.
- Every dollar-neutral variant (continuous, breadth, fixed-universe, liquidity-neutral) passes
  the same unit-gross-exposure, zero-net-exposure, 0.5/0.5-long-short-leg validation Phase 11
  used.
- The placebo permutation is deterministic under the reused seed `20260911` — rerunning produces
  identical results, verified in tests.
- 10 new automated tests (`tests/test_phase15_robustness_s2.py`) cover: the S1→S2 unit-test
  mirrors (rank/breadth weight determinism and neutrality, missing-signal handling,
  date-local scoring); that every locked parameter (seed, permutation count, HAC lags, cost grid,
  both samples) is reused unchanged from Phase 11; that no output contains a pooled or combined
  estimate; that the S2 placebo result is a genuinely distinct computation from S1's (not copied)
  while using the identical method and seed; the exact reproduction of Phase 10's frozen S2 daily
  returns; that every breadth variant is negative at the primary cost, matching S1's pattern; the
  full re-hash of the Phase 15 source manifest; and — critically — a direct re-hash of the entire
  **Phase 11** preservation manifest, confirming Phase 15 modified none of Phase 10's or Phase
  11's own frozen output files.
- Full project test suite: 46 of 46 passed (36 pre-existing, 10 new).
- `config/research_config.yaml` confirmed to parse under `yaml.safe_load` after all edits.

## Problems and limitations

- This phase inherits every data limitation already documented for Phase 11 and the underlying
  research: current-snapshot survivorship and selection bias, public Yahoo market data, FINRA
  revision-vintage uncertainty, and the omission of borrow, impact, locate, financing, tax, and
  commission costs from the illustrative cost grid.
- The placebo test addresses only the specific within-date random-assignment null; it does not
  address data-mining, universe-construction, vendor, or implementation risk, for either signal.
- S2's markedly weaker placebo result, while still statistically below 0.05 in both samples, is a
  genuine difference from S1's near-maximal separation from its own null distribution. This
  report does not attempt to explain the mechanism beyond noting that S2 is a state-conditioned
  residual of S1 with a different cross-sectional score shape; a deeper investigation of *why*
  the placebo distributions differ in centering was not performed and would be a reasonable
  follow-up.
- As in Phase 11, breadth, fixed-universe, and liquidity-neutral results are robustness or
  exploratory diagnostics, not alternative optimized strategies, and none was used to select or
  tune S2 after the fact.
- This phase does not revisit the Phase 8 leading-candidate decision (S2 vs. S1) or the Phase 14
  market-neutrality diagnostic; it is a parallel robustness extension, not a re-adjudication of
  either.

## Decisions required

None to complete Phase 15. This is an additive parity check. It does not change S1's frozen
primary status, S2's frozen robustness-comparator role, or any Phase 1–14 conclusion. Whether the
placebo-strength gap between S1 and S2 warrants further investigation is a decision for a future
phase, not implied by this one.

> **Superseding note, 2026-09-12.** "S1's frozen primary status" above was accurate when this
> phase completed. It was superseded later the same day by an explicit governance override
> promoting S2 to primary; this report's placebo-strength gap finding was cited explicitly as a
> disclosed, accepted weakness in that decision, not resolved by it. See
> `docs/s2_primary_promotion_governance_override.md`. The original text above is preserved
> unchanged.

## Files changed

- Governance: `config/research_config.yaml` (new `evaluation.robustness_falsification_phase_15_s2`
  block, locked before results and completed after), `logs/research_log.md` (three appended
  entries: pre-registration, results, final validation), this report.
- Implementation and tests: `src/run_robustness_phase15_s2.py`,
  `tests/test_phase15_robustness_s2.py`.
- Preservation: `preservation/phase15_pre_robustness_s2_source_artifacts/SHA256SUMS.txt`.
- Processed panels: `data/processed/phase15_daily_robustness_s2_portfolio_panel.parquet`,
  `data/processed/phase15_robustness_s2_positions.parquet`.
- Results: `results/tables/phase15_time_stability.csv`, `phase15_hac_lag_sensitivity.csv`,
  `phase15_rolling_63_session.csv`, `phase15_breadth_comparison.csv`,
  `phase15_fixed_universe_results.csv`, `phase15_sector_liquidity_neutral.csv`,
  `phase15_liquidity_coverage.csv`, `phase15_outlier_sensitivity.csv`,
  `phase15_day_influence.csv`, `phase15_security_influence_top10.csv`,
  `phase15_leave_one_year_out.csv`, `phase15_placebo_permutations.csv`,
  `phase15_placebo_summary.csv`, `phase15_rank_ic_diagnostics.csv`,
  `phase15_robustness_summary.csv`.
- Figures: `results/figures/phase15_additional_placebo_distribution.png`,
  `phase15_original_placebo_distribution.png`, `phase15_additional_rolling_stability.png`,
  `phase15_original_rolling_stability.png`, `phase15_breadth_comparison.png`.

No Phase 1–14 artifact was modified. All 140 pinned Phase 9/10 source artifacts and the entire
Phase 11 preservation manifest (checked directly, not merely assumed) remain unchanged and were
verified before and after this phase.
