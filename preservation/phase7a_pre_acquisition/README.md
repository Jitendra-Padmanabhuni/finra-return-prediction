# FINRA Short-Sale Volume Alpha Research

## Research question

Can publicly available FINRA daily short-sale volume data be transformed into a robust daily cross-sectional alpha signal for next-session open-to-close relative returns among liquid U.S. equities?

This repository implements the authoritative research specification. FINRA data is an **off-exchange FINRA short-volume** measure, not total U.S. market volume, short interest, investor identity, or trader intent.

## Status

**Current phase: Phase 7B candidate-history layer complete; stopped for review.** Features are now built from all 503 candidate histories, while corrected top-400 membership gates only signal-date evaluation. Phase 7A historical acquisition has not begun.

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
- Conditioning: daily 5 x 5 cross-sectional volume-surprise and realized-volatility cells.
- Final score: cross-sectional rank of negative conditioned anomaly, scaled approximately to `[-1, 1]`.
- Primary portfolio: equal-dollar long top decile / short bottom decile, 100% gross and dollar neutral.

The Phase 2 date window was selected before alpha inspection: warm-up begins 2025-01-15 and the evaluation window is 2025-05-01 through 2026-08-31. The candidate source returned 503 current constituent rows (including three additional share-class rows). The corrected monthly screen selects the top 400 using raw `Close × Volume` over exactly the 20 immediately preceding shared market dates, requiring valid Close and Volume on all 20 dates. Volatility lookback and all optional extensions remain deferred.

## Approved liquidity implementation correction

The original Phase 2 implementation mistakenly calculated each security's liquidity median over every prior observation while merely requiring at least 20 observations. Consequently, the original Phase 2–7 outputs did **not** use the documented exact-20-date rule. Those artifacts are preserved and labeled legacy under `legacy/expanding_liquidity_window/`.

On 2026-09-11, the sponsor approved rebuilding Phases 2–7 consistently. The corrected rebuild and validation are complete, and corrected outputs are now the primary research results. Phase 7A acquisition has not begun and remains stopped for sponsor review.

## Phase 7B candidate-history amendment

On 2026-09-11, the sponsor approved a candidate-history layer: all existing Yahoo and FINRA observations for the 503 timestamped candidates are used to form strictly prior 20- and 60-shared-date histories. Corrected top-400 membership remains unchanged and controls only signal-date eligibility. The prior corrected, universe-member-only-history results are preserved under `baseline/corrected_universe_member_history_phase7b/`; Phase 7B output files use the `phase7b_` prefix and are the current primary outputs. The locked two-sided HAC(5) rules remain primary, and reported one-sided expected-direction p-values are supplementary only.

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
