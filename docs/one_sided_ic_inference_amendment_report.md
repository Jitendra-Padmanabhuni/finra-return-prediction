# One-Sided Rank-IC Inference Amendment Report

> Approved 2026-09-12. This is a decision-rule amendment only: no raw signal, panel, mean, standard
> error, or t-statistic was recomputed. Only the hypothesis framing, which p-value counts as primary,
> and the resulting pass/fail labels change, and only for the specific test class described below.

## Scope of the change

Before this amendment, every mean-Rank-IC and paired mean-Rank-IC-difference test in this project used
a two-sided primary standard (`H0: mean IC = 0` vs `HA: mean IC != 0`, pass if `|t| >= 2`), with a
one-sided p-value (`stats.norm.sf(t)`) reported alongside as supplementary and non-decisive.

This amendment switches the primary standard for **standalone S0/S1/S2 mean Rank-IC tests and paired
mean-IC-difference tests only** (S1-minus-S0, S2-minus-S1, S2-minus-S0) across Phases 5, 6 (regression
coefficients), 7, 7A, 7B, and 8, to a one-sided rule:

```text
Standalone:  H0: mean IC <= 0            HA: mean IC > 0
Paired:      H0: mean IC difference <= 0  HA: mean IC difference > 0
Critical value: t >= 1.645 (standard one-sided 5% cutoff under the normal
                approximation this project already uses for its stats.norm.sf
                p-values), replacing the prior t >= 2 (two-sided |t|) bar.
```

This reflects a directional prior held before results were examined — the signal, and any incremental
difference between signals, is expected to be positive if real — not a reaction to already-observed
results.

**Explicitly out of scope, unchanged, and still two-sided as originally defined:**
- Phase 10 portfolio-return HAC tests (gross/net daily strategy returns).
- The Phase 11 placebo/permutation test.
- Decile-monotonicity diagnostics.
- Any long-short/portfolio-return HAC test in any phase (Phase 5 D10-D1, Phase 7/7A/7B/8 long-short,
  Phase 8 state-dependence correlations to confound variables).

## Where the rule is implemented

A search of the codebase found exactly **one** place where a t-statistic was mechanically converted to
a hardcoded pass/fail boolean for a Rank-IC-type test: `src/evaluate_conditional_signal_phase8.py`, the
`leading_candidate_rule` decision block (`s2_hac5_t_at_least_2`, testing `s2.hac5_ic_t >= 2`). Every
other phase script (`evaluate_naive_signal.py`, `analyze_confounds.py`, `evaluate_abnormal_signal.py`,
`evaluate_historical_validation_phase7a.py`, `evaluate_candidate_history_phase7b.py`) computes and
reports the HAC mean/SE/t (and, where present, the one-sided `stats.norm.sf` p-value) as plain numeric
columns without a code-level threshold; the pass/fail judgment for those tests has always lived in the
prose of the phase reports, compared manually against the two-sided bar of 2.

Because `config/research_config.yaml` is a governance/documentation record — no script in this project
parses it at runtime — its `statistically_convincing_if` and `leading_candidate_rule` fields describe
the rule rather than implement it; both code and config are updated below.

### Files changed

| File | Change |
| --- | --- |
| `src/one_sided_ic_inference.py` (new) | Reusable `ic_clears_one_sided_bar` / `ic_clears_two_sided_bar_superseded` helpers and the `1.645` / `2.0` constants. |
| `src/apply_one_sided_ic_amendment_phase8.py` (new) | Re-derives the Phase 8 leading-candidate decision from the already-persisted, unchanged result tables under the new rule, without recomputing any panel or signal. Writes to a **new** file, never to the original. |
| `results/tables/phase8_decision_rule_evaluation_one_sided_amendment_2026-09-12.json` (new) | The re-derived decision, both samples, with the superseded two-sided value retained alongside for audit. |
| `results/tables/phase8_decision_rule_evaluation.json` | **Unchanged.** Its checksum is pinned in the Phase 9, 10, and 11 preservation manifests (see the section below); it was not touched. |
| `src/evaluate_conditional_signal_phase8.py` | Unchanged in behavior. A comment was added at the decision block pointing to the amendment and explaining why this script continues to reproduce the original two-sided result exactly. |
| `tests/test_phase8_conditional_signal.py` | Three new tests: the threshold helper against known historical t-values (including every flip and near-miss identified below); the new amendment JSON's internal consistency and agreement with the unchanged persisted tables; and an explicit checksum check that the original decision file still matches all three preservation manifests. |
| `config/research_config.yaml` | New top-level `approved_one_sided_ic_inference_amendment` block; `evaluation.naive_signal_phase_5.statistically_convincing_if` renamed; `evaluation.conditional_abnormal_signal_phase_8.inference` and `.leading_candidate_rule` restructured to separate rank-IC (amended) from long-short/portfolio (unchanged); `approved_candidate_history_layer_phase_7b.primary_inference`/`supplementary_inference` restructured the same way. Not pinned in any preservation manifest at its live path (only archived copies under `legacy/`/`baseline/` are pinned), confirmed before editing. |
| `README.md` | Governance sentence in the Phase 7B section qualified; new "Approved one-sided IC inference amendment" section added. Not pinned at its live path, confirmed before editing. |
| `logs/research_log.md` | One appended, dated entry. Append-only by design; not pinned. |

**No existing phase report (`docs/phase5_naive_signal_report.md` through `docs/phase8_report.md`,
`docs/liquidity_universe_correction_report.md`, or any other pre-existing `docs/*.md` file) was
edited.** See the section below for why.

### Why the original Phase 8 decision file was not overwritten, and why the phase reports were not edited in place

An initial implementation regenerated `results/tables/phase8_decision_rule_evaluation.json` in place,
and separately added a short superseding note directly into each affected phase report
(`docs/phase5_naive_signal_report.md`, `docs/phase6_confound_analysis_report.md`,
`docs/phase7_abnormal_signal_report.md`, `docs/phase7a_report.md`,
`docs/phase7b_candidate_history_report.md`, `docs/phase8_report.md`, and
`docs/liquidity_universe_correction_report.md`). Running the full test suite caught both: the decision
JSON's checksum is pinned as a frozen source artifact in three downstream preservation manifests
(`preservation/phase9_pre_score_source_artifacts/SHA256SUMS.txt`,
`preservation/phase10_pre_backtest_source_artifacts/SHA256SUMS.txt`,
`preservation/phase11_pre_robustness_source_artifacts/SHA256SUMS.txt`), and — once that was fixed and
the suite rerun — every one of those seven phase reports is *also* pinned, each in at least one of
`preservation/phase7a_pre_acquisition/SHA256SUMS.txt` or
`preservation/phase9_pre_score_source_artifacts/SHA256SUMS.txt`. A systematic check found that in this
project, essentially every `docs/*.md` phase report from Phase 1 through Phase 10, plus
`docs/liquidity_universe_correction_report.md` and the FINRA data dictionary, is pinned somewhere as a
frozen source artifact for a later phase; only `config/research_config.yaml` and `README.md` are not
pinned at their live paths (their archived copies under `legacy/`/`baseline/` are pinned instead, which
this amendment does not touch).

This project's own established pattern for "an earlier result needs to change" is not to mutate a
downstream-pinned file, but to produce a new, clearly labeled artifact (as Phase 7B did for Phase 7,
and as the liquidity correction did by archiving the legacy outputs separately). Both the decision JSON
and every phase report were therefore restored to their exact pinned checksums, and all superseding
content was consolidated into this single new report instead — itself pinned nowhere, since it did not
exist before this amendment. Dedicated tests now assert the original decision file's checksum continues
to match all three manifests; the seven phase reports' checksums were verified by direct comparison
against their pinned values in the relevant manifests before this report was finalized.

## Complete accounting of results checked

Every standalone mean-Rank-IC and paired mean-IC-difference t-statistic across Phases 5, 6
(regression coefficients), 7, 7A, 7B, and 8 was read directly from its authoritative result table (not
recomputed) and evaluated against both the superseded two-sided bar (`|t| >= 2`) and the new one-sided
bar (`t >= 1.645`).

### Verdicts that flip from fail to pass

| Result | HAC(5) t | Old verdict (`\|t\|>=2`) | New verdict (`t>=1.645`) | Appears in |
| --- | ---: | :---: | :---: | --- |
| Original-period S0, full-sample mean IC (all eligible, pre-Phase-7-pairing) | 1.8997 | fail | **pass** | `docs/phase5_naive_signal_report.md`, `docs/phase6_confound_analysis_report.md`, `docs/liquidity_universe_correction_report.md`, `config/research_config.yaml` (`frozen_phase_7b_benchmarks.s0_full_hac5_ic_t`) |
| Original-period S0, paired (candidate-history architecture, primary) | 1.8307 | fail | **pass** | `docs/phase7b_candidate_history_report.md`, `docs/phase7a_report.md`, `docs/phase8_report.md`, `config/research_config.yaml` (`frozen_phase_7b_benchmarks.s0_paired_hac5_ic_t`) — **this is the result the sponsor specifically flagged** |
| Original-period S0, paired (member-history architecture, superseded, non-primary) | 1.7373 | fail | **pass** | `docs/phase7_abnormal_signal_report.md` — this architecture is no longer primary (Phase 7B's candidate-history reconstruction is), but the result is a documented historical artifact and its verdict flips under the same rule |

No other standalone S0/S1/S2 mean-IC result flips: every additional-sample S0/S1 result and every
original-sample S1/S2 result already cleared `t >= 2` and therefore also clears `t >= 1.645`
(additional S0 full 2.31, S0 paired 2.24, S1 2.51; original S1 2.59, S2 2.55; additional S2 3.48).

### Paired IC-difference results confirmed unchanged (still fail)

| Comparison | Sample | HAC(5) t | Verdict under both rules |
| --- | --- | ---: | --- |
| S2 − S1 | additional | 1.5627 | fail — closest of any paired result to the new bar, still short |
| S2 − S1 | original | −0.8979 | fail |
| S2 − S0 | additional | 0.3156 | fail |
| S2 − S0 | original | 0.2913 | fail |
| S1 − S0 | additional (7A) | −0.3322 | fail |
| S1 − S0 | original (7B/7A reproduction) | 0.6279 | fail |
| S1 − S0 | original (member-history, superseded) | 1.0359 | fail |

No paired IC-difference result flips, confirming the sponsor's expectation.

### Phase 6 regression coefficients (in scope, none flip)

| Model | Coefficient on rank S0 | HAC(5) t | Verdict under both rules |
| --- | --- | ---: | --- |
| Model 1: S0 alone | 0.000143 | 0.782 | fail |
| Model 2: + reversal | 0.000178 | 1.003 | fail |
| Model 3: + reversal, volume surprise, volatility | 0.000173 | 1.001 | fail |

### Phase 8 leading-candidate decision (confirmed unchanged)

S2's standalone HAC(5) IC t-statistics (3.48 additional, 2.55 original) already cleared the old bar and
continue to clear the new one, so the primary-criterion switch does not by itself change anything here.
The decision remains blocked by the independent, non-threshold requirement that the paired
S2-minus-S1 mean IC be positive in **both** samples: it is positive in the additional sample
(+0.00176) but negative in the original sample (−0.00117). This sign failure is unrelated to either
critical value.

**Result: `retain_S1_S2_is_informative_robustness_test`, unchanged.** See
`results/tables/phase8_decision_rule_evaluation_one_sided_amendment_2026-09-12.json` for the
machine-readable re-derived decision, alongside the unchanged original
`results/tables/phase8_decision_rule_evaluation.json`.

## What this does and does not establish

The three flips above mean the **original-period standalone S0 mean Rank IC** — under whichever
architecture it is reported — is now independently significant by this project's primary criterion,
where it previously was not. It does **not** mean:

- S0 is now shown to be superior to S1: every paired S1-minus-S0 IC-difference test still fails the new
  bar, in every architecture and sample.
- Any conclusion about net-of-cost economics changes: Phase 10's portfolio-return tests, which drive the
  central negative net-return conclusion in `docs/phase12_final_interpretation.md`, are explicitly out
  of scope for this amendment and are unaffected.
- The Phase 8 leading-candidate decision changes: it was never determined by the IC threshold in the
  original sample; it is blocked by a sign condition that this amendment does not touch.
- Any decile-monotonicity, placebo, or long-short conclusion changes.

## Validation

- Full test suite (`pytest tests/`): 25 passed (22 pre-existing, 3 new), after two rounds of an
  initial in-place edit being caught by the existing preservation-manifest tests (first the decision
  JSON, then the seven phase-report superseding notes), reverted, and replaced with the non-destructive
  approach described above.
- `results/tables/phase8_decision_rule_evaluation.json` SHA-256 confirmed to still match all three
  entries in the Phase 9/10/11 preservation manifests.
- All seven affected phase reports' SHA-256 confirmed to still match their pinned values in
  `preservation/phase7a_pre_acquisition/SHA256SUMS.txt` and/or
  `preservation/phase9_pre_score_source_artifacts/SHA256SUMS.txt`, as applicable.
- `config/research_config.yaml` confirmed to parse under `yaml.safe_load` after all edits.
- Every t-statistic in the accounting tables above was read directly from its source CSV
  (`phase5_naive_summary.csv`, `phase6_regression_summary.csv`, `phase6_correlation_summary.csv`,
  `phase7_s0_s1_summary.csv`, `phase7_paired_differences.csv`, `phase7b_phase7_s0_s1_summary.csv`,
  `phase7b_phase7_paired_differences.csv`, `phase7a_performance_summary.csv`,
  `phase7a_paired_differences.csv`, `phase8_common_sample_performance.csv`,
  `phase8_paired_differences.csv`) rather than transcribed from prose, to avoid propagating a rounding
  or transcription error into the amendment.
- No file under `data/`, `results/tables/` (other than the new Phase 8 amendment JSON),
  `results/figures/`, `docs/` (other than this new report), `preservation/`, `legacy/`, or `baseline/`
  was modified.

## Problems and limitations

- This amendment changes which of two pre-specifiable hypothesis-testing conventions is primary; it
  does not and cannot resolve the underlying question of whether a one-sided or two-sided test was the
  more appropriate choice to have pre-registered originally. Both are documented, and neither the
  original two-sided results nor the superseded-key audit trail were deleted.
- The three flipped results are all variants of the same underlying quantity (the original-period
  standalone S0 ratio-vs-forward-return relationship) computed under three different architectures
  (full-sample, candidate-history-paired, member-history-paired). They are not three independent
  confirmations of a new finding — they are the same finding, reported three times as this project's
  architecture evolved, all crossing the same numeric neighborhood (1.74–1.90) that happens to sit
  between the two critical values.
- This report does not revisit `docs/phase13_claude_design_prompt.md` (the Superday presentation brief),
  which was written under the prior two-sided-primary framing and cites several of the t-statistics
  above. That document is downstream presentation preparation, not a research-methodology report, and
  updating it was out of scope for this amendment; it should be reconciled with this amendment before
  any deck is built from it.

## Decisions required

None to complete this amendment. If the presentation-prep prompt (`docs/phase13_claude_design_prompt.md`)
is used to build a deck, its IC-significance framing should be reconciled with this amendment first.
