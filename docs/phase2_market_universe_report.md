# Corrected Phase 2 Market Data and Prototype Universe Report

> Primary corrected result, rebuilt 2026-09-11. The former report and artifacts
> are preserved under `legacy/expanding_liquidity_window/`.

## Scope and approved limitation

This phase acquired Yahoo Finance market data only as approved auxiliary OHLCV, liquidity, target-support, and diagnostic data. FINRA Consolidated NMS remains the sole future alpha-data source. No FINRA/market merge, prediction target, feature, signal, portfolio, or backtest was built.

The universe is a retrieval-date-stamped **prototype**. It is survivorship- and selection-biased, excludes delisted securities, has no permanent identifiers or historical constituent membership, and does not have fully licensed corporate-action data. It is not production-ready or conclusive.

## Candidate set and symbol reconciliation

The current constituent table at [Wikipedia’s S&P 500 list](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies) was retrieved at `2026-09-11T01:12:31.668153+00:00`. It supplied 503 rows: slightly above the requested approximate 300–500 range because the current list includes additional share-class rows. It is used as a practical current large-cap candidate set, not a historical constituent universe.

No known ETF or non-common instrument was identified in this source list; this is a best-public-classification screen, not a security-master determination. Source-to-Yahoo symbols were retained for all rows. Two transformations were required: `BRK.B -> BRK-B` and `BF.B -> BF-B`. See `results/tables/phase2_candidate_universe.csv` and `results/tables/phase2_symbol_reconciliation.csv`.

## Dates selected before alpha inspection

- Auxiliary Yahoo download/warm-up: 2025-01-15 through 2026-08-31 (`end=2026-09-01`, exclusive).
- Prospective evaluation window: 2025-05-01 through 2026-08-31 (about 16 months).
- Rationale: the end is the last complete month before the current September 2026 file cycle; warm-up provides more than 60 preceding trading days. Yahoo returned the entire selected range for a test security before the full retrieval, and all 335 Yahoo trading dates in the evaluation range returned HTTP 200 for the corresponding Consolidated NMS FINRA endpoint before alpha inspection.

## Market data results

The final `yfinance` 1.7.0 retrieval returned 503 successful ticker responses, zero vendor download failures, 204,312 OHLCV/action rows, and 408 distinct trading dates. Raw fields retained are open, high, low, close, adjusted close, volume, dividends, and stock splits. The processed panel also calculates an adjustment factor and adjusted open/high/low/close; raw action fields remain present.

Five candidate symbols had incomplete Yahoo date coverage. They are retained in `results/tables/phase2_missing_market_dates.csv`, not silently discarded:

| Symbol | Returned dates | First returned | Missing selected-calendar dates |
| --- | ---: | --- | ---: |
| FDXF | 67 | 2026-05-27 | 341 |
| FISV | 407 | 2025-01-15 | 1 |
| HONA | 54 | 2026-06-15 | 354 |
| Q | 212 | 2025-10-27 | 196 |
| SNDK | 388 | 2025-02-13 | 20 |

The raw and processed panel includes 24 reported split events across 22 symbols. The phase also flagged 39 absolute daily unadjusted-close moves of at least 25%; none occurred on a reported split date. These are inspection flags, not exclusions or return adjustments. See `phase2_split_events.csv` and `phase2_extreme_close_returns.csv`.

## Point-in-time liquidity universe

At each first available trading day of a month, the corrected screen identifies exactly the 20 immediately preceding shared market dates. A candidate must have valid raw Close and Volume on all 20 dates. The screen ranks the median of raw `Close * Volume` using only those dates, breaks ties deterministically by source symbol, selects the top 400, and holds membership fixed until the next monthly refresh.

There was insufficient history to select names on the January 15 and February 3, 2025 refreshes. From March 3 onward, each monthly screen selected 400 names. The daily expanded universe has exactly 400 names on all 335 dates in the prospective evaluation period. The stored `screen_last_observation_date` is strictly earlier than its `rebalance_date` for every selected membership row.

The prior implementation instead used every observation before the rebalance and required only a minimum count of 20. Across the 18 corrected rebalances, corrected-versus-legacy overlap ranges from 381 to 395 names, additions/removals from 5 to 19 names per month, and Jaccard similarity from 0.9093 to 0.9753 (mean 0.9271). There are 546 monthly changed-membership rows covering 144 distinct symbols. Full median and rank differences are preserved in `results/tables/phase2_liquidity_correction_*.csv`.

## Files

- Raw candidate and Yahoo files: `data/raw/` (timestamped).
- Clean Yahoo-only panel: `data/processed/prototype_market_panel.csv`.
- Monthly and daily memberships: `data/processed/prototype_universe_monthly.csv`, `data/processed/prototype_universe_daily.csv`.
- Download, missingness, reconciliation, coverage, actions, return-inspection, and FINRA endpoint-probe outputs: `results/tables/phase2_*.csv`.

## Acquisition incidents

The initial Wikipedia request received a `403` with the default client and was retried using an explicit research User-Agent. Two local builder defects then stopped processing after valid data responses; neither created a market-data output and both were corrected. The final vendor download log records zero Yahoo failures. These incidents are also recorded in the research log.
