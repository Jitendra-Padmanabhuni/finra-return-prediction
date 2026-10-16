# Phase 3 Master Panel Report

## Scope

Phase 3 created a daily-universe master panel only. It did not calculate forward returns, rolling features, ratios, signals, deciles, or portfolio returns.

## Acquisition and provenance

All 408 Consolidated NMS files for the Phase 2 market calendar from 2025-01-15 through 2026-08-31 were downloaded unchanged. Every raw file passed its exact header and numeric trailer check; download failures were zero. `data/raw/finra_consolidated_nms_manifest.jsonl` records URL, trade date, retrieval timestamp, SHA-256, and trailer count per file. Revision status is `undetermined_current_endpoint_no_version_metadata`: FINRA may revise files, but the direct endpoint does not supply an as-first-published vintage.

Raw FINRA volume strings are retained without integer casting. The current data uses decimal-valued volumes.

## Identifier treatment

The panel retains `canonical_research_symbol`, `finra_symbol`, and Yahoo symbols separately. Most mappings use the canonical symbol unchanged. Evidence from raw files establishes `BRK.B -> BRK/B` and `BF.B -> BF/B` for FINRA, while Yahoo uses `BRK-B` and `BF-B`. Both mappings are flagged in `symbol_mapping_status`.

## Spine and join results

The expected spine is the 150,800 `(date, security)` rows in the Phase 2 daily prototype universe (377 dates x 400 members). Market and FINRA records were left-joined onto that spine with one-to-one validation; no inner join or many-to-many join was allowed.

| Join status | Rows |
| --- | ---: |
| Complete match | 150,317 |
| Missing FINRA observation | 482 |
| Missing market observation | 1 |
| Symbol-mapping failure | 0 |
| Other excluded/unresolved | 0 |

The overall complete-match rate is 99.68%. Missing fields remain missing—no FINRA or market value was replaced by zero.

Weakest security coverage was MRSH (41.91% complete), FISV (53.05%), ECHO (75.00%), and BNY (81.17%). The weakest daily complete-match rate was 99.5%; representative unmatched rows and complete per-date/per-month/per-security coverage are saved in `results/tables/phase3_*.csv`.

## Outputs

- `data/processed/master_stock_day_panel.parquet` is the typed master panel suitable for subsequent phases.
- `data/processed/master_stock_day_panel.csv` is a portable copy; use the parquet panel when preserving raw decimal-field representation matters.
- Coverage tables and unmatched examples remain in `results/tables/phase3_*.csv`.

