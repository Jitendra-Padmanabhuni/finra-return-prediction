# Phase 7A pre-performance data-quality gate

Recorded before any Phase 7A performance calculation on 2026-09-11.

## Coverage decision

The historical evaluation spine contains 240,400 signal-date top-400 stock-days from 2023-01-03 through 2025-05-27. Of these, 240,399 (99.9996%) have both market and FINRA observations. Market coverage is 100%; one eligible Biogen stock-day lacks a FINRA observation. All 240,400 designated next-session targets are available. The predeclared 95% gate passes, so frozen-signal performance evaluation is permitted.

This gate does **not** make the reconstruction survivorship-safe. It measures data joins conditional on the reconstructed universe. The universe is a best-effort public reconstruction, not a licensed point-in-time security master.

## Membership and identity audit

- The preserved September 2026 snapshot has 503 securities.
- The raw public additions/removals table contributes 84 dated rows in scope.
- Eleven separately preserved, source-linked identity events reconcile ticker-only changes omitted by that table. Paramount Global (`PARA`) is treated as a distinct predecessor security to Paramount Skydance (`PSKY`), not as a ticker alias.
- Backward reconstruction produces 576 distinct security instances and 587 observed symbol aliases. Daily reconstructed security counts range from 503 to 505 because share classes, one-sided events, and merger timing can temporarily change the number of listed security lines.
- Three ticker/name ambiguities remain flagged for review. No reverse addition match is unresolved.
- Yahoo acquisition issued 586 requests: 544 succeeded and 42 failures were retained in the download log. Failures are concentrated in unavailable historical/delisted aliases and securities not yet trading in the requested interval.
- All 686 required FINRA shared-date files from 2022-09-01 through 2025-05-28 were acquired or checksum-verified, with source URLs, retrieval timestamps, trailers, and checksums in the Phase 7A manifest.

The monthly liquidity audit uses exactly the 20 shared dates immediately before each rebalance. September 2022 is warm-up-only and lacks 20 prior dates; every later monthly refresh has at least 477 eligible securities and selects exactly 400. Membership is held fixed until the next refresh.

## Pooling decision locked before performance

The additional period uses reconstructed point-in-time S&P membership, while exact reproduction of the original Phase 7B period requires its preserved September 2026 fixed candidate snapshot. These are different universe-construction regimes. Therefore the two periods will be reported independently and will **not** be pooled into a combined performance estimate. Pooling would hide a methodological break at 2025-05-28 and fail the specification's comparability condition.

## Preserved limitations

Public Yahoo data lacks licensed historical-security-master guarantees and does not reliably serve every retired ticker. CIKs are missing for many removed constituents. Merger, share-class, spinoff, and ticker-reuse treatment is best effort. FINRA files expose the currently retrievable immutable-looking daily files but not a complete publication-vintage history, so revision-vintage limitations remain.
