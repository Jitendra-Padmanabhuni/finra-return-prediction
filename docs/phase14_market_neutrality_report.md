# Phase 14 — Market-Neutrality Regression

## Completed

- Read the governing configuration and append-only log, then locked the full specification —
  market proxy (SPY), regression form, HAC lag, hypotheses, critical values, and the
  original-sample-only scope — in `config/research_config.yaml` and `logs/research_log.md`
  before acquiring any market data or running any regression.
- Pinned the exact Phase 10 artifacts this phase consumes (the daily portfolio exposure and
  returns-by-cost panels, the Phase 10 report, implementation, and tests, plus every
  `results/tables/phase10_*` file) as unchanged, immutable source artifacts in
  `preservation/phase14_pre_market_neutrality_source_artifacts/SHA256SUMS.txt`.
- Pulled the exact frozen Phase 10 daily gross return series for S0_continuous, S1_continuous,
  and S2_continuous on the original sample (2025-05-28 to 2026-08-31) only — not rebuilt or
  re-derived — with the primary-2.5-bps-per-side net series as a labeled secondary check. The
  additional sample was not touched.
- Acquired SPY via `yfinance` (not the raw index), built the same-session
  `adjusted_close[t] / adjusted_open[t] - 1` market factor using this project's standard
  adjustment-factor convention (`adjustment_factor = Adj Close / Close`), and aligned it to
  each strategy's own available trade dates.
- Ran `strategy_return[t] = alpha + beta * market_return[t] + epsilon[t]` for each of S0, S1,
  S2, via `statsmodels.OLS` on `[constant, market_return]` with `cov_type="HAC"`,
  `cov_kwds={"maxlags": 5}`, exactly matching the HAC(5) machinery used throughout this project.
- Evaluated alpha as the primary, decisive one-sided test (`H0: alpha <= 0` vs `HA: alpha > 0`,
  pass if `t >= 1.645`) and beta as a two-sided diagnostic only (`H0: beta = 0`, not a pass/fail
  gate, flagged if `|beta| >= 0.10` or its two-sided p-value is below 0.05).
- Modified no Phase 1–13 frozen artifact. This is a new, additive analysis.

## Key findings

All figures below are for the **original sample only** (317 signal dates, S1/S2; 316 for S0,
excluding the one known Phase 10 unavailable strategy-day — original S0, 2025-11-11, FISV
missing designated target — exactly matching how Phase 10's own HAC(5) tests are constructed).

### Gross (primary)

| Strategy | n | Alpha (bp/day) | HAC(5) t | One-sided p (`H0: alpha<=0`) | Clears primary bar (`t>=1.645`) | Beta | HAC(5) t | Two-sided p | Beta flagged |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: |
| S0_continuous | 316 | 0.893 | 0.731 | 0.232 | **No** | 0.0595 | 2.603 | 0.0092 | **Yes** |
| S1_continuous | 317 | 1.661 | 1.619 | 0.053 | **No** (falls just short) | 0.0110 | 0.599 | 0.549 | No |
| S2_continuous | 317 | 1.560 | 1.711 | 0.044 | **Yes** | −0.0036 | −0.227 | 0.820 | No |

### Net at 2.5 bps per side (labeled secondary check only)

| Strategy | Alpha (bp/day) | HAC(5) t | Clears primary bar |
| --- | ---: | ---: | :---: |
| S0_continuous | −4.107 | −3.364 | No |
| S1_continuous | −3.339 | −3.256 | No |
| S2_continuous | −3.440 | −3.770 | No |

**Only S2's gross standalone alpha clears the primary one-sided bar.** S1's gross alpha misses
narrowly (t = 1.619 against a 1.645 bar). S0's gross alpha does not clear the bar and, unlike S1
and S2, carries a modest but two-sided-statistically-significant positive market beta (0.0595,
p = 0.0092) — flagged per the pre-registered diagnostic rule. Since the continuous dollar-neutral
construction (unit gross exposure, zero net exposure, 0.5/0.5 long/short legs) should mechanically
produce a beta close to zero, S0's flagged beta means part of its gross mean return may reflect
residual market exposure rather than pure cross-sectional skill; S1 and S2 show no such pattern
(betas 0.011 and −0.004, neither economically nor statistically distinguishable from zero). Net of
the primary 2.5-bps-per-side cost, alpha is negative and fails the primary bar for all three
strategies, consistent with Phase 10's and Phase 12's existing net-of-cost conclusion.

R-squared is low throughout (0.036 for S0, 0.002 for S1, 0.0003 for S2), meaning same-session SPY
moves explain very little of any strategy's daily return variance — consistent with a genuinely
dollar-neutral construction whose returns are dominated by idiosyncratic, cross-sectional
dispersion rather than market direction.

### Market data coverage

SPY was retrieved via `yfinance` 1.7.0 on 2026-09-12T19:57:19Z, `auto_adjust=False`, for the
window 2025-05-22 through 2026-09-01 (padded seven calendar days before the earliest strategy
trade date to guarantee full coverage), returning 323 trading-day rows. **Zero trade dates were
missing from the SPY series for any of the three strategies** — every trade date present in each
original-sample strategy's available-day series has a matching SPY same-session return. The raw
retrieval is preserved unchanged at `data/raw/spy_market_factor_2025-05-22_2026-09-01_20260912T195719.csv`.

## Validation

- The pre-registered specification in `config/research_config.yaml` and `logs/research_log.md`
  was locked and committed before any SPY data was acquired or any regression result was viewed.
- `preservation/phase14_pre_market_neutrality_source_artifacts/SHA256SUMS.txt` pins 14 Phase 10
  source artifacts (the two consumed parquet panels, the Phase 10 report, its implementation and
  test file, and every `results/tables/phase10_*` output); all verified unchanged both before
  acquisition and after this phase's outputs were written.
- 11 new automated tests (`tests/test_phase14_market_neutrality.py`) cover: the regression helper
  reproducing a hand-built `statsmodels` HAC(5) fit exactly; alpha's decision rule being one-sided
  (a large-magnitude *negative* alpha t must still fail the primary bar, not merely `|t|>=1.645`);
  beta's diagnostic flag being symmetric (a large negative beta is flagged the same as a large
  positive one); correct date alignment and per-strategy exclusion of Phase-10-unavailable
  strategy-days (S0 = 316, S1 = S2 = 317, no duplicate keys); the market-factor formula matching
  this project's existing `adjustment_factor = Adj Close / Close` convention; missing-date
  reporting; strict scope to the original sample only (no `sample` column survives the loader,
  and every trade date falls within the locked original-sample window); and a full re-hash of the
  pinned Phase 10 source manifest confirming no Phase 10 artifact was modified; and an explicit
  cross-check asserting each strategy's regression alpha sits within 5 bps/day of its own raw
  Phase 10 original-sample gross mean, computed independently from the frozen exposure panel.
- Full project test suite: 36 of 36 passed (25 pre-existing, 11 new).
- Cross-check detail: raw Phase 10 original-sample gross means, computed directly and
  independently from the frozen exposure panel over the same 316/317 available days, are S0
  0.989, S1 1.678, S2 1.555 bp/day. S1 and S2's regression alpha point estimates (1.661 and 1.560
  bp/day) sit close to their raw means, as expected given their near-zero betas. S0's alpha
  (0.893 bp/day) sits further from its raw mean (0.989 bp/day) specifically because its
  non-trivial beta (0.0595) absorbs part of the raw mean return via the
  `beta * mean(market_return)` term — the expected behavior of a market-model decomposition, not
  a discrepancy.
- `config/research_config.yaml` confirmed to parse under `yaml.safe_load` after all edits.

## Problems and limitations

- This is a single-factor market model against one proxy (SPY). It does not control for size,
  value, momentum, or any other common risk factor; a positive alpha here means "not explained by
  contemporaneous same-session SPY exposure," not "not explained by any risk factor."
- The regression window is short (316–317 trading days, roughly 15 months); HAC(5) inference on a
  sample this size, especially for the beta diagnostic, should be read as indicative rather than
  asymptotically well-calibrated.
- SPY's same-session open-to-close return is a same-day contemporaneous factor, not a lagged or
  forward-looking one; it measures whether the strategy's return is compensation for holding
  market risk during the exact window it is held, not whether the *signal* itself is correlated
  with any subsequent market move.
- As with every other phase in this project, SPY's Yahoo-sourced adjusted prices are unlicensed,
  public data with the same corporate-action and revision caveats already documented for every
  other Yahoo-sourced series in this project (see `docs/phase2_market_universe_report.md`,
  `docs/phase4_prediction_target_report.md`).
- The additional sample (2023-01-03 to 2025-05-27) was deliberately excluded from this phase per
  its pre-registered scope; this diagnostic has therefore not been replicated out-of-sample. A
  natural extension, not performed here, would be to run the identical locked specification on
  the additional sample as an out-of-sample check on the alpha/beta pattern found here.
- The beta diagnostic flag thresholds (`|beta| >= 0.10` or two-sided p < 0.05) were fixed in the
  pre-registration as a reasonable but somewhat arbitrary screening rule; they were not tuned
  against these results, but a different reasonable threshold could label S0's beta differently
  in magnitude (though not in two-sided statistical significance, which is threshold-independent).

> **Superseding note, 2026-09-12.** The sentence below ("does not change the frozen S1-primary /
> S0-baseline / S2-robustness-comparator governance") was accurate when this report was written.
> Later the same day, an explicit governance override promoted S2 to primary, with S1 becoming
> former primary, now comparator; S0 is unchanged. This diagnostic's own finding — that S2's gross
> alpha clears the primary bar while S1's narrowly misses it — was cited as one of three reasons
> for that override. See `docs/s2_primary_promotion_governance_override.md` and
> `logs/research_log.md` (2026-09-12 entry). The original text below is preserved unchanged.

## Decisions required

None to complete Phase 14. This diagnostic does not change the frozen S1-primary /
S0-baseline / S2-robustness-comparator governance established in Phase 9, nor the Phase 10/12
net-of-cost conclusion that all three strategies are unprofitable at the primary 2.5-bps-per-side
cost. Whether to run the identical specification on the additional sample as an out-of-sample
check, or to extend this to a multi-factor model, is a decision for a future phase, not implied by
this one.

## Files changed

- Governance: `config/research_config.yaml` (new `evaluation.market_neutrality_regression_phase_14`
  block, locked before results and completed after), `logs/research_log.md` (three appended
  entries: pre-registration, results, final validation), this report.
- Implementation and tests: `src/run_market_neutrality_phase14.py`,
  `tests/test_phase14_market_neutrality.py`.
- Preservation: `preservation/phase14_pre_market_neutrality_source_artifacts/SHA256SUMS.txt`.
- Raw data: `data/raw/spy_market_factor_2025-05-22_2026-09-01_20260912T195719.csv` (and one
  earlier same-day developmental retrieval, `..._20260912T195703.csv`, retained unchanged per
  this project's raw-data-immutability policy; the two differ only at the ~1e-6 relative level in
  vendor-side adjusted-close recomputation and do not affect any reported figure, which is drawn
  from the later, canonical retrieval).
- Results: `results/tables/phase14_market_model_results.csv`,
  `results/tables/phase14_strategy_returns_used.csv`, `results/tables/phase14_spy_market_factor.csv`,
  `results/tables/phase14_spy_coverage_check.csv`, `results/tables/phase14_spy_download_log.csv`,
  `results/figures/phase14_S0_continuous_market_model_scatter.png`,
  `results/figures/phase14_S1_continuous_market_model_scatter.png`,
  `results/figures/phase14_S2_continuous_market_model_scatter.png`.

No Phase 1–13 artifact was modified. All 14 pinned Phase 10 source artifacts and every prior
preservation manifest remain unchanged and were verified before and after this phase.
