# FINRA Short-Sale Volume Alpha Research

## Research question

Can publicly available FINRA daily short-sale volume data be transformed into a robust daily cross-sectional alpha signal for next-session open-to-close relative returns among liquid U.S. equities?

This repository implements the authoritative research specification. FINRA data is an **off-exchange FINRA short-volume** measure, not total U.S. market volume, short interest, investor identity, or trader intent.

## Status

**Current phase: Phase 11 robustness and falsification analysis complete; stopped for review.** The historical additional and original fixed-snapshot samples remain separate. S1's frozen continuous rank-score portfolio is positive gross in both samples but negative under the primary illustrative 2.5-bps-per-side cost assumption; deterministic score permutations reject random assignment, but no result justifies changing the frozen primary specification.

**Signal roles as of 2026-09-12: S2 is primary; S1 is former primary, now comparator; S0 is unchanged baseline.** This is an explicit governance override, not a data-driven result — see "S2 primary-promotion governance override" below. Everything above and below this note that describes S1 as primary is preserved unchanged as an accurate record of what was true when written.

## Repository layout

```text
config/                  Explicit research choices and data paths
data/raw/                Immutable source downloads (not committed)
data/intermediate/       Cleaned source-level data (not committed)
data/processed/          Research panels and derived datasets (not committed)
src/                     Reusable research modules, added by later phases
notebooks/               Phase-specific notebooks, added by later phases
results/tables/          Generated research tables (not committed)
results/figures/         Generated figures (not committed)
presentation/            Presentation materials, only after research completion
scripts/                 Reproducible project utilities
tests/                   Assertions and tests, added with implementation
logs/                    Append-only research experiment log
```

## Primary design (locked by specification)

- Signal date: end of trading day `t`.
- Primary target: `(Close[t+1] - Open[t+1]) / Open[t+1]`.
- Primary raw FINRA feature: `short_volume / total_reported_volume`.
- Primary anomaly baseline: strictly prior 60 observations, median/MAD normalized.
- Primary normalized signal: negative 60-date stock-relative median/MAD abnormality (`S1`).
- Cross-sectional ranks are the portfolio representation of `S0` and `S1`, not a separate empirical signal.
- Primary portfolio: equal-dollar long top decile / short bottom decile, 100% gross and dollar neutral.

> This section records Phase 0's original, unmodified locked design. **As of 2026-09-12, S2 is
> primary** (see "S2 primary-promotion governance override" below); the bullets above are
> preserved verbatim as the original specification, not current governance.

The Phase 2 date window was selected before alpha inspection: warm-up begins 2025-01-15 and the evaluation window is 2025-05-01 through 2026-08-31. The candidate source returned 503 current constituent rows (including three additional share-class rows). The corrected monthly screen selects the top 400 using raw `Close × Volume` over exactly the 20 immediately preceding shared market dates, requiring valid Close and Volume on all 20 dates. Volatility lookback and all optional extensions remain deferred.

## Approved liquidity implementation correction

The original Phase 2 implementation mistakenly calculated each security's liquidity median over every prior observation while merely requiring at least 20 observations. Consequently, the original Phase 2–7 outputs did **not** use the documented exact-20-date rule. Those artifacts are preserved and labeled legacy under `legacy/expanding_liquidity_window/`.

On 2026-09-11, the sponsor approved rebuilding Phases 2–7 consistently. The corrected rebuild and validation are complete, and corrected outputs are now the primary research results.

## Phase 7B candidate-history amendment

On 2026-09-11, the sponsor approved a candidate-history layer: all existing Yahoo and FINRA observations for the 503 timestamped candidates are used to form strictly prior 20- and 60-shared-date histories. Corrected top-400 membership remains unchanged and controls only signal-date eligibility. The prior corrected, universe-member-only-history results are preserved under `baseline/corrected_universe_member_history_phase7b/`; Phase 7B output files use the `phase7b_` prefix and are the current primary outputs. As approved on 2026-09-11, the locked two-sided HAC(5) rules were primary for all HAC-based tests, with one-sided expected-direction p-values supplementary only. **This was amended on 2026-09-12 for rank-IC and paired rank-IC-difference tests only** — see "Approved one-sided IC inference amendment" below; long-short and portfolio-return HAC tests remain two-sided primary as originally approved here.

## Phase 7A historical validation

Phase 7A acquired 686 FINRA shared-date files beginning 2022-09-01 and public Yahoo history, reconstructed historical S&P membership backward from the preserved September 2026 snapshot, and formed a monthly exact-prior-20-date top 400. The reconstruction has 576 distinct security instances and explicitly separates the Paramount Global predecessor from Paramount Skydance. Complete market+FINRA coverage among historical signal-date top-400 rows is 99.9996%, above the locked 95% gate.

In the additional period, S1 mean Rank IC is 0.00655 (two-sided HAC(5) t=2.51) and its gross D10-minus-D1 Sharpe is 1.22. S0's paired mean IC is higher at 0.00744 (t=2.24); the S1-minus-S0 IC difference is -0.00089 (t=-0.33). S1 therefore validates as independently positive but does not validate as superior to S0. The two periods are not pooled because their universe-construction regimes are not sufficiently comparable. See `docs/phase7a_report.md`.

## Phase 8 conditional abnormal-signal robustness test

Phase 8 formed the pre-specified five-by-five daily volume-surprise/prior-volatility conditioned residual, `S2`, from frozen S1 abnormality. It retained every S1-eligible stock-day in both separate samples. S2 independently has positive IC with HAC(5) t-statistics of 3.48 in the additional sample and 2.55 in the original sample, and reduces dependence on volume surprise and prior volatility.

It does **not** replace S1: S2-minus-S1 mean IC is positive in the additional sample (+0.00176) but negative in the original sample (−0.00117). This fails the predeclared requirement for a positive paired IC difference in both samples. S1 remains the leading candidate; S2 is an informative robustness test. See `docs/phase8_report.md`.

## Phase 9 final signal score

Phase 9 freezes S1 as the primary predictive signal and transforms it into `final_rank_score`, a daily target-independent bounded rank from −1 to +1. The score preserves S1 ordering, maps daily low/high signals exactly to −1/+1, and is centered at zero. S0 and S2 have equivalent bounded benchmark-score fields. The transformation changes scale and portfolio usability only: all 918 daily S1 score Rank IC values exactly match raw-S1 Rank IC. See `docs/phase9_report.md`.

## Phase 10 realistic portfolio backtest

Phase 10 holds score-weighted, dollar-neutral positions from the designated next shared-session open through close only. It uses target-independent continuous weights, applies entry and exit costs, and treats any nonzero position with a missing designated target as an unavailable strategy-day with no reweighting. S1 is positive gross in both samples (0.75 and 1.68 bps/day) but its break-even one-way costs are only 0.37 and 0.84 bps; the 2.5-bps-per-side primary illustrative net results are negative. S0, S1, and S2 differences are not statistically distinguishable in paired daily portfolio comparisons. See `docs/phase10_report.md`.

## Phase 11 robustness and falsification

Phase 11 keeps S1 and the Phase 10 continuous portfolio frozen, and reports separate time-stability, breadth, fixed-first-date-universe, liquidity-neutral, outlier, concentration, HAC-lag, and deterministic placebo checks. The actual gross mean exceeds every one of 1,000 within-date score permutations in both samples (empirical one-sided p=0.000999), while the primary cost conclusion remains negative. Existing sector classifications were unavailable, so sector-neutralization was not calculated. See `docs/phase11_report.md`.

> The four paragraphs above (Phase 8–11) are preserved verbatim as written; each states S1's role
> as it stood at the time. **As of 2026-09-12, S2 is primary and S1 is former primary, now
> comparator** — see the next section. Phase 11's placebo result quoted above was itself part of
> the basis for that decision, alongside a materially weaker placebo result for S2 found in
> Phase 15 (`docs/phase15_robustness_S2_report.md`) — both are disclosed together in the override.

## Approved one-sided IC inference amendment

On 2026-09-12, the sponsor approved switching the primary decision rule for standalone S0/S1/S2 mean
Rank-IC tests and paired mean-IC-difference tests (Phases 5, 6 regression coefficients, 7, 7A, 7B, and
8 only) from two-sided (`H0: mean IC = 0`, pass if `|t| >= 2`) to one-sided (`H0: mean IC <= 0` vs
`HA: mean IC > 0`, pass if `t >= 1.645`, the standard one-sided 5% normal-approximation cutoff this
project already uses for its `stats.norm.sf` p-values), reflecting a directional prior held before
results were examined. Phase 10 portfolio-return HAC tests, the Phase 11 placebo/permutation test,
decile-monotonicity diagnostics, and every long-short/portfolio-return HAC test in any phase are
unaffected and remain two-sided as originally defined. No raw signal, panel, mean, standard error, or
t-statistic was recomputed; only the hypothesis framing and the resulting pass/fail labels changed.

This flips exactly one class of result from fail to pass: the original-period standalone S0 mean IC
(HAC(5) t = 1.83–1.90 depending on architecture), reported in Phases 5, 6, 7, 7A, 7B, and 8. No paired
IC-difference result flips — the closest, additional-sample S2-minus-S1 at t = 1.56, still fails the
new bar — and Phase 8's leading-candidate decision for S2 is unchanged, since it remains blocked by
the paired `S2-minus-S1` sign requirement failing in the original sample, independent of either
threshold. Full accounting, every affected file, and every t-statistic checked are in
`docs/one_sided_ic_inference_amendment_report.md`.

## S2 primary-promotion governance override

On 2026-09-12, following Phase 14's market-neutrality regression and Phase 15's robustness suite
extended to S2, the sponsor promoted **S2 to primary, replacing S1**. S1 becomes former primary,
now robustness comparator, reported prominently alongside S2 going forward; S0 is unchanged as
baseline. **This is an explicit governance override, not a data-driven result.**

Phase 8's pre-registered promotion rule — a positive, HAC-significant paired S2-minus-S1 mean Rank
IC difference in both samples — was not met then (additional t=1.56, original t=−0.90) and remains
unmet under the 2026-09-12 one-sided reframing above (additional t=1.5627, still below 1.645;
original still negative). The override does not claim otherwise. It rests instead on three reasons
held together: S2's standalone HAC-t and Sharpe exceed S1's in both samples (Phase 8; mean IC
exceeds S1's in the additional sample only — S1's original-sample mean IC is higher); S2's gross
alpha clears Phase 14's market-neutrality bar with a clean beta while S1's narrowly misses it; and
S2 matches or beats S1 on Phase 15's full robustness battery except the placebo test, where S2's
result (p=0.0200/0.0180) is materially weaker than S1's (p=0.000999, the floor) — disclosed here as
a known, accepted weakness in the promoted signal, not resolved or hidden by this decision.

No signal, panel, or backtest was recomputed; Phase 9's `S2_bounded_rank_score`, Phase 10's
`S2_continuous` backtest, Phase 14's S2 alpha/beta, and Phase 15's S2 robustness suite already
existed and are used exactly as frozen. Every phase-summary paragraph above that names S1 as
primary is preserved unchanged as an accurate record of what was true when written. Full record,
every quoted finding, and the complete accounting are in
`docs/s2_primary_promotion_governance_override.md`.

## Approved proof-of-concept amendment

On 2026-09-10, the project sponsor approved a bounded interview proof of concept. FINRA Consolidated NMS remains the sole alpha-data source. Yahoo Finance via `yfinance` may be used only for auxiliary daily OHLCV, adjusted-price/corporate-action fields, targets, liquidity filters, and diagnostic controls.

The prototype candidate set is a retrieval-date-stamped set of roughly 300–500 current, large, liquid U.S. exchange-listed common stocks. It is explicitly **survivorship- and selection-biased**, lacks permanent identifiers and historical constituent membership, and is not production-ready or conclusive. Delisted securities, fully licensed corporate-action data, and complete historical ticker mappings are absent. Every failed download, missing date, symbol transformation, and FINRA/Yahoo mismatch is retained in audit output.

The amended primary empirical comparison is raw FINRA ratio versus 60-day stock-relative median/MAD abnormality. Same-day return/short-term reversal is the primary confound. Cross-sectional ranking is a portfolio representation of the abnormality signal, not a separate signal experiment. Volume/volatility conditioning, sector and market-cap tests, alternative horizons, placebos, flow-versus-inventory, and extensive cost work are optional extensions only.

## Setup

Create an isolated environment using Python 3.11–3.13, then install the research dependencies:

```bash
python -m pip install -r requirements.txt
python scripts/check_environment.py
```

The environment check is read-only and reports interpreter and package availability. It does not download data or run research.

## Phase protocol

Work proceeds one phase at a time. Each phase must report completed work, findings, validation, problems, decisions required, and files changed before stopping. See `logs/research_log.md` for the initial record.

## Data policy

- Raw data remains immutable after acquisition.
- Missing data is never silently converted to zero.
- Raw FINRA files are retained with source URL, retrieval date, and checksum metadata when acquired.
- No feature may use information after its signal date.
- No historical universe may be constructed from present-day membership or liquidity.
