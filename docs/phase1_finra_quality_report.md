# Phase 1 FINRA Raw-Data Quality Report

## Scope

This is a raw-file audit only. It does not apply a stock universe, map symbols to permanent identifiers, clean records, construct a ratio, or run a signal.

The sampled files are three consecutive **FINRA Consolidated NMS** files (2026-09-08 through 2026-09-10) and the four facility files available on 2026-09-10. Checksums and URLs are in `data/raw/finra_source_manifest.json`; machine-readable audit output is `results/phase1_finra_quality_report.json`.

## Exact files/endpoints

The primary future FINRA candidate is the `CNMSshvolYYYYMMDD.txt` endpoint, e.g. `https://cdn.finra.org/equity/regsho/daily/CNMSshvol20260910.txt`. FINRA describes Consolidated NMS as the combination of exchange-listed security activity reported to FINRA’s TRFs and ADF. Component endpoint prefixes observed on 2026-09-10 were `FNQCshvol` (Chicago), `FNSQshvol` (Carteret), `FNYXshvol` (NYSE TRF), and `FORFshvol` (ORF).

FINRA says files contain aggregate volume by security for short-sale trades executed and reported to the named reporting facilities during normal market hours and for public dissemination. The firm normally posts them by 6 p.m. ET on the trade date. [FINRA file page](https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data/daily-short-sale-volume-files)

## Schema and file framing

All seven files had the exact header:

```text
Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market
```

Every file had a numeric final-line trailer matching its data-row count. No file-level schema exception occurred. The official layout defines `Date` as the trade date, `Symbol` as security symbol, volume fields as reported aggregate volume, and `Market` as reporting-facility information. [FINRA formatting guide](https://www.finra.org/sites/default/files/2021-07/DailyShortSaleVolumeFileLayout.pdf)

Important observed schema difference: the official historical layout calls the volume fields integer values, while the current sample has fractional values. For example, `CNMSshvol20260910.txt` starts with `A|377880.263894|126|627107.276031|B,Q,N`. Therefore all volume fields must be stored as decimals, not integer-cast.

## Coverage summary

| File | Scope | Trade date | Data rows | Unique symbols | Zero total-volume rows | Duplicate `(date,symbol,market)` rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| CNMSshvol20260908.txt | Consolidated NMS | 2026-09-08 | 12,325 | 12,325 | 0 | 0 |
| CNMSshvol20260909.txt | Consolidated NMS | 2026-09-09 | 12,275 | 12,275 | 0 | 0 |
| CNMSshvol20260910.txt | Consolidated NMS | 2026-09-10 | 12,327 | 12,327 | 0 | 0 |
| FNQCshvol20260910.txt | Nasdaq Chicago TRF | 2026-09-10 | 5,596 | 5,596 | 0 | 0 |
| FNSQshvol20260910.txt | Nasdaq Carteret TRF | 2026-09-10 | 12,277 | 12,277 | 0 | 0 |
| FNYXshvol20260910.txt | NYSE TRF | 2026-09-10 | 7,572 | 7,572 | 0 | 0 |
| FORFshvol20260910.txt | ORF | 2026-09-10 | 3,034 | 3,034 | 0 | 0 |

There were no blank values in any raw field, no negative or zero `TotalVolume` values, and no row where `ShortVolume > TotalVolume`. Market values in the component files were `B`, `Q`, `N`, and `O`; Consolidated NMS used the expected composite facility strings (`B`, `Q`, `N`, `B,Q`, `Q,N`, and `B,Q,N`).

## Ratio diagnostics (raw descriptive only)

For Consolidated NMS, `ShortVolume / TotalVolume` had median values of 0.4969, 0.5020, and 0.4975 on 2026-09-08, 09, and 10, respectively. The 1st–99th percentile ranges were approximately 0.0032–0.9994 across those three dates, with maxima of 1. This confirms substantial raw cross-sectional heterogeneity but is not an alpha result.

## Component reconciliation

For 2026-09-10, aggregating Chicago, Carteret, and NYSE TRF raw files by symbol reconciled exactly to Consolidated NMS for all 12,327 common symbols and all three volume fields. There were zero missing symbols in either direction and zero volume mismatches. ORF was not included in this reconciliation because FINRA defines Consolidated NMS as TRF/ADF exchange-listed coverage, not ORF coverage.

## Interpretation limitations

- `TotalVolume` is total reported volume in the relevant FINRA file, **not** all U.S. equity volume. FINRA data is not consolidated with exchange data.
- The files only include publicly disseminated trades. FINRA explicitly warns this can make the reported short-volume concentration appear high when related offsetting activity is not publicly reflected.
- Daily short-sale volume is flow, not bi-monthly short-interest inventory, and does not identify institutional activity, directional exposure, or trader intent.
- FINRA notes that it may update a file later and label it “Updated.” This sample is a current retrieval; Phase 1 did not establish an archival, as-first-published version for every historical date. A future backtest therefore cannot claim exact publication-vintage timing unless such versioned data is obtained.
- The sample contains all securities the files report, including instruments outside the project’s future common-equity universe. Asset-class filtering and permanent identifier mapping are deferred to Phase 2.

The source caveats above are described in [FINRA Information Notice 5/10/19](https://www.finra.org/rules-guidance/notices/information-notice-051019).

