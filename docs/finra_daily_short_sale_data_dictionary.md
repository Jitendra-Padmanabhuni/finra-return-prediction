# FINRA Daily Short Sale Volume: Phase 1 Data Dictionary

This dictionary describes the raw pipe-delimited daily-file layout. It does not assert that a symbol is a common equity or that it is eligible for the future project universe.

| Raw field | Type observed in 2026-09 sample | FINRA meaning | Phase 1 handling |
| --- | --- | --- | --- |
| `Date` | Eight-character `YYYYMMDD` | Trade date | Parse as a trade-date field in later cleaning; audit requires one date per daily file. |
| `Symbol` | String, up to 14 characters in FINRA’s layout | Security symbol | Preserve raw exactly; do not infer issuer, asset class, listing venue, or permanent identity. |
| `ShortVolume` | Non-negative decimal in the sampled current files | Aggregate reported share volume of executed short-sale activity during regular hours; FINRA’s layout also describes it in relation to short-exempt activity | Preserve as decimal. The specified ratio uses this field as numerator. |
| `ShortExemptVolume` | Non-negative decimal in the sampled current files | Aggregate reported short-exempt volume during regular hours | Preserve separately; it is not added again to the primary numerator. |
| `TotalVolume` | Positive decimal in the sampled current files | Aggregate reported volume of all executed trades during regular hours within the relevant FINRA file | Preserve as decimal. It is the primary ratio denominator, not consolidated U.S. equity volume. A zero denominator must yield missing ratio. |
| `Market` | Single facility code in component files; comma-separated component codes in Consolidated NMS | Reporting-facility identifier | Preserve raw. Historical FINRA layout names `N`, `Q`, `B`, and `D`; current sampled consolidated rows use composite strings such as `B,Q,N`. |

## File framing

The first line is the header. The last line is a numeric trailer equal to the number of data records. The audit validates both. FINRA’s historical formatting guide describes integer numerical fields, but the 2026-09 sample contains decimals; code must not coerce these raw values to integer.

## Source interpretation and limitations

- Files cover short-sale trades executed and reported to FINRA reporting facilities in normal market hours for public dissemination.
- FINRA’s Consolidated NMS file combines exchange-listed security volume reported to its TRFs and ADF. It does not include exchange-executed volume.
- FINRA says the data excludes trades not publicly disseminated, which can make observed short-volume concentration appear high when offsetting activity is not present in the published file.
- Daily short-sale volume is trading flow, not short-interest inventory and not evidence of investor identity or intent.
- FINRA may update a daily file on a subsequent day; its page labels such files “Updated.” The currently downloadable historical file may therefore not equal the version known at the original signal date.

## Official sources

- [FINRA Daily Short Sale Volume Files](https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data/daily-short-sale-volume-files)
- [FINRA Daily Short Sale Volume File Layout](https://www.finra.org/sites/default/files/2021-07/DailyShortSaleVolumeFileLayout.pdf)
- [FINRA Information Notice 5/10/19](https://www.finra.org/rules-guidance/notices/information-notice-051019)

