# S2 Primary-Promotion Governance Override

> Approved 2026-09-12. **This is an explicit governance override, not a data-driven result.**
> S2 is promoted to primary, replacing S1. S1 becomes former primary, now robustness comparator,
> reported prominently alongside S2 going forward. S0 is unchanged as baseline. No signal, panel,
> backtest, or statistic was recomputed to produce this decision; every referenced figure below is
> read from the already-frozen Phase 8, 9, 10, 14, and 15 artifacts, unchanged.

## Why this document exists, and what it does not do

`docs/phase8_report.md` and `docs/phase9_report.md` — the two reports whose original language
most directly states "S1 is primary" — are checksum-pinned as frozen source artifacts in the
Phase 9, 10, 11, and 15 preservation manifests (verified before this document was written; see
Validation below). They cannot be edited in place without breaking those phases' frozen-input
guarantee, following the same constraint this project encountered during the 2026-09-12 one-sided
IC amendment (`docs/one_sided_ic_inference_amendment_report.md`). Rather than mutate them, this
document serves as the clearly labeled, dated amendment those two reports would otherwise carry
inline, exactly as the sponsor requested; it is written for anyone auditing "why does Phase 8 say
S1 is primary but the project now treats S2 as primary."

`docs/phase14_market_neutrality_report.md` and `docs/phase15_robustness_S2_report.md` are **not**
pinned; each carries its own inline superseding note pointing back to this document, in addition
to the record kept here.

**Nothing in Phase 8's, Phase 9's, Phase 11's, or Phase 15's original text is rewritten, deleted,
or reworded anywhere in this project as a result of this override.** Every quoted figure below is
transcribed, not paraphrased, from the cited report.

## The decision

| | Before 2026-09-12 | After 2026-09-12 |
| --- | --- | --- |
| **S1** | Primary predictive signal | Former primary, now robustness comparator — reported prominently, not diminished |
| **S2** | Robustness comparator | **Primary** |
| **S0** | Baseline | Baseline (unchanged) |

S1 does not lose visibility for having lost the primary label. Its unresolved paired comparison
against S2 (below) and S2's weaker placebo result relative to S1 (below) are both permanent parts
of this record and must remain visible in any future summary of either signal's standing.

## The pre-registered Phase 8 promotion rule was not met — under either standard

Phase 8 locked a decision rule before calculating S2 (`config/research_config.yaml`,
`evaluation.conditional_abnormal_signal_phase_8.leading_candidate_rule`): S2 could replace S1 only
if, among other conditions, **the paired S2-minus-S1 mean Rank IC difference was positive and
HAC-significant in both samples.** From `docs/phase8_report.md`, verbatim, in the order it
appears in that report:

> "S2 improves point estimates versus S1 in the additional sample, with S2-minus-S1 mean IC of
> +0.00176 (HAC t=1.56; supplementary one-sided p=0.059). In the original sample, it is lower by
> −0.00117 (HAC t=−0.90; one-sided p=0.815). Neither paired difference is statistically convincing
> under the locked two-sided standard." — `docs/phase8_report.md`, "Key findings"

> "S2 clears standalone positive IC, HAC t≥2, coverage, monotonicity, and small-cell conditions in
> both samples. It fails the decisive paired requirement: S2-minus-S1 mean IC is not positive in
> the original sample." — `docs/phase8_report.md`, "Decision rule"

> "**Decision: retain S1 as the leading candidate. S2 is an informative robustness test, not a
> replacement.**" — `docs/phase8_report.md`, "Decision rule"

**This condition was not met under Phase 8's original two-sided standard.**

It is also not met under the 2026-09-12 one-sided IC amendment
(`docs/one_sided_ic_inference_amendment_report.md`), which switched the primary rule for paired
IC-difference tests to `t >= 1.645`: the additional-sample difference (t = 1.5627) still falls
short of 1.645, and the original-sample difference remains negative (t = −0.8979). That amendment
report states, verbatim, under "Phase 8 leading-candidate decision (confirmed unchanged)":

> "S2's standalone HAC(5) IC t-statistics (3.48 additional, 2.55 original) already cleared the old
> bar and continue to clear the new one, so the primary-criterion switch does not by itself change
> anything here. The decision remains blocked by the independent, non-threshold requirement that
> the paired S2-minus-S1 mean IC be positive in **both** samples... **Result:
> `retain_S1_S2_is_informative_robustness_test`, unchanged.**" — `docs/one_sided_ic_inference_amendment_report.md`

**This override does not claim the Phase 8 criterion was met. It was not met then, and it is not
met now, under either the original or the amended standard. The promotion rests on the three
reasons below, applied as an explicit sponsor decision, not on satisfying the pre-registered rule.**

## The three reasons cited for the override

### 1. S2's standalone metrics, established in Phase 8

From `docs/phase8_report.md`'s performance table:

| Sample / signal | Mean IC | HAC(5) t | Gross L/S Sharpe |
| --- | ---: | ---: | ---: |
| Additional S1 | 0.00655 | 2.51 | 1.22 |
| Additional S2 | 0.00832 | 3.48 | 1.61 |
| Original S1 | 0.01295 | 2.59 | 0.91 |
| Original S2 | 0.01178 | 2.55 | 1.42 |

S2's HAC(5) t-statistic and gross long-short Sharpe exceed S1's in **both** samples. Mean Rank IC
exceeds S1's in the additional sample only — **in the original sample, S1's mean IC (0.01295) is
higher than S2's (0.01178)**. This document states that plainly rather than selectively citing
only the metrics that favor S2.

### 2. Phase 14's market-neutrality regression

From `docs/phase14_market_neutrality_report.md`:

| Strategy | Gross alpha (bp/day) | HAC(5) t | Clears the one-sided bar (t≥1.645) | Beta | Beta flagged |
| --- | ---: | ---: | :---: | ---: | :---: |
| S1_continuous | 1.661 | 1.619 | No (misses narrowly) | 0.0110 | No |
| S2_continuous | 1.560 | 1.711 | **Yes** | −0.0036 | No |

S2's gross standalone alpha clears the primary one-sided bar; S1's narrowly misses it. Both
signals show a clean, statistically insignificant beta (the significantly-flagged beta in that
phase belonged to S0, not S1).

### 3. Phase 15's robustness/falsification battery — including the placebo gap, disclosed plainly

From `docs/phase15_robustness_S2_report.md`'s side-by-side table, S2 matches or beats S1 on:
gross HAC-lag sensitivity, calendar-year and half-split means, the fixed-universe diagnostic, the
liquidity-neutral control, leave-one-calendar-year-out sign stability, and single-day tail risk
(worst day −38.39 bps vs S1's −137.95 bps, additional sample; −49.71 vs −61.61 bps, original).

**S2 is materially weaker than S1 on the deterministic placebo/permutation test, and this is
recorded here as a known, accepted weakness in the promoted signal — not glossed over:**

> "S1's actual gross mean exceeded essentially every one of 1,000 within-date score permutations
> in both samples (`p = 0.000999`, the minimum attainable value with 1,000 permutations under the
> plus-one convention — no permutation matched or beat it). **S2's result is qualitatively the
> same direction but far less extreme**: `p = 0.0200` additional and `p = 0.0180` original — still
> below the conventional 5% threshold... but by a much narrower margin. Roughly 1 in 50 random
> permutations of S2's scores matched or beat its actual mean, versus roughly 1 in 1,000 for S1."
> — `docs/phase15_robustness_S2_report.md`, "The one place S2 does not hold up as well: the
> placebo test"

S2's placebo-permutation distribution is centered near zero (and slightly positive) in both
samples, rather than clearly negative as S1's was — a structural difference in how the two
signals' score distributions interact with random reassignment, not a computational discrepancy.

## What this override does and does not establish

- It **does** change which signal this project reports as primary, effective 2026-09-12.
- It **does not** claim the Phase 8 pre-registered promotion rule was satisfied. It was not.
- It **does not** alter Phase 10's net-of-cost conclusion: S2's net return at the primary 2.5
  bps-per-side cost remains negative in both samples (−3.89 and −3.45 bps/day), just as S1's was
  (−4.25 and −3.32 bps/day). Neither signal is economically viable as a standalone fully-rebalanced
  intraday strategy at that cost.
- It **does not** retroactively make S2's placebo result as strong as S1's. That gap is real,
  disclosed here, and must stay disclosed in any future reporting on S2 as primary.
- It **does not** require, and this override performs no, recomputation. Phase 9's
  `S2_bounded_rank_score`, Phase 10's `S2_continuous` backtest, Phase 14's S2 alpha/beta, and
  Phase 15's S2 robustness suite already exist, frozen, and are consumed here exactly as they
  stand.

## Files changed

| File | Change |
| --- | --- |
| `config/research_config.yaml` | New top-level `approved_S2_primary_promotion_override_2026_09_12` block; superseded-by comments added above the four now-historical role fields (Phase 9 `roles`/`primary_score_field`, Phase 10 `frozen_signal_roles`, Phase 11 `frozen_primary`) and above Phase 15's `governance_clarification`/`headline_conclusion` — every original value preserved unchanged. |
| `results/tables/phase9_signal_governance_amended_2026-09-12.csv` (new) | Machine-readable current role table. The original `results/tables/phase9_signal_governance.csv` is unchanged — it is pinned in the Phase 9/10/11/15 preservation manifests and was not touched. |
| `docs/s2_primary_promotion_governance_override.md` (this file, new) | Full record; the amendment note for `docs/phase8_report.md` and `docs/phase9_report.md`, which are pinned and could not be edited in place. |
| `docs/phase14_market_neutrality_report.md` | Inline superseding note added (not pinned). Original text unchanged. |
| `docs/phase15_robustness_S2_report.md` | Inline superseding note added (not pinned). Original text unchanged. |
| `docs/phase13_claude_design_prompt.md`, `docs/phase13_completion_report.md` | Inline stale-governance warning added (not pinned; these were never built into an actual deck). Original text unchanged. |
| `README.md` | New section; existing phase-summary paragraphs annotated with pointers, not rewritten. |
| `logs/research_log.md` | One appended, dated entry. |
| `tests/test_s2_primary_governance_override.py` (new) | Covers the new governance CSV, the config override block, and byte-identical preservation of every file this override could not edit. |

**Not changed, and not recomputed:** `docs/phase8_report.md`, `docs/phase9_report.md`,
`docs/phase10_report.md`, `docs/phase11_report.md`, `results/tables/phase9_signal_governance.csv`,
every Phase 9/10/14/15 data panel and result table, and every preservation manifest's pinned
checksums.

## Validation

- Every file listed as "pinned, not edited" above was confirmed pinned in at least one
  preservation manifest before this document was written, and confirmed byte-identical to its
  pinned checksum after.
- `config/research_config.yaml` confirmed to parse under `yaml.safe_load` after all edits.
- Every figure quoted in this document was re-read from its source table/report at the time of
  writing, not transcribed from memory: `results/tables/phase8_common_sample_performance.csv`,
  `results/tables/phase8_paired_differences.csv`, `results/tables/phase14_market_model_results.csv`,
  `results/tables/phase15_placebo_summary.csv`, `results/tables/phase11_placebo_summary.csv`,
  `results/tables/phase15_day_influence.csv`, `results/tables/phase11_day_influence.csv`.
- Full project test suite passed after this override; see the final validation log entry for the
  exact count.

## Problems and limitations

- This is a governance decision, not an empirical finding. It cannot be validated the way a
  statistical result can; it can only be checked for internal consistency (does it accurately
  represent what Phase 8/14/15 found) and for whether it discloses the parts of the record that
  cut against it. Both were the explicit goals of this document.
- S2's weaker placebo result is disclosed but not explained. Phase 15's report notes the
  difference is "a structural difference in how the two signals' score distributions interact
  with the random-reassignment mechanism," without a deeper mechanistic account. That remains an
  open question.
- `docs/phase13_claude_design_prompt.md`, the Superday presentation-prep prompt, is now stale on
  its central premise (S1 as primary) in addition to its earlier staleness on the one-sided IC
  framing. It has not been rewritten; it carries a warning instead. If a presentation is built from
  it, the prompt needs reconciling with both amendments first.
- This override does not revisit whether S0 should be re-examined given the new S1/S2 ordering;
  S0 remains baseline, unchanged, by explicit statement in the decision above.

## Decisions required

None to complete this override. Whether to formally re-run Phase 8's promotion rule against any
future signal candidate, or to pre-register a different criterion given this project's experience
with S2, is a decision for a future phase, not implied by this one.
