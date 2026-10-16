# Phase 12 — Completion report

## Completed

- Read the authoritative configuration, append-only research log, and Phase 1–11 reports.
- Reconciled every Phase 12 headline number to the Phase 7A, Phase 8, Phase 10, or Phase 11 authoritative result table.
- Wrote the final interpretation without adding data, experiments, signals, portfolios, samples, costs, or methodological changes.
- Created a machine-readable headline-statistics table with exact values, source artifacts, and row selectors.
- Kept the additional and original samples separate and produced no pooled estimate.

## Key findings

- Frozen S1 has positive standalone mean Rank IC in both samples: 0.00655 (HAC(5) t = 2.51) additional and 0.01295 (t = 2.59) original.
- S1 is not definitively better than S0 on paired inference, and S2 does not improve consistently across both samples.
- The continuous S1 portfolio's gross mean is positive but modest: 0.75 and 1.68 bp/day, with gross HAC(5) t-statistics of 1.71 and 1.64.
- At 2.5 bp per side, net means are -4.25 and -3.32 bp/day. Break-even one-way costs are only 0.37 and 0.84 bp.
- The deterministic permutation result is strong for the specific random-assignment null, but it neither proves causality nor overcomes the negative net economics.

## Validation

- Verified all 726 entries in the Phase 7A pre-acquisition preservation manifest, all 84 entries in the Phase 9 manifest, all 91 entries in the Phase 10 manifest, and all 139 entries in the Phase 11 manifest: zero failures.
- Before Phase 12 edits, directly hashed 232 current Phase 1–11 documentation/result artifacts; aggregate inventory digest: `0b0ffe13f7f0788a9f355129c9a3ad4dcd290f84c766959e9931c0745917ce1b`.
- Repeated the direct Phase 1–11 inventory hash after writing Phase 12 and confirmed the same file count and digest.
- Validated the headline CSV against its source rows and confirmed that the interpretation is no more than approximately 900 words.

## Problems and limitations

- Historical and original samples use different universe methodologies and cannot support a pooled estimate.
- Public-data survivorship, identifier, corporate-action, delisting, FINRA-vintage, and publication-timing risks remain.
- The research cannot identify trader intent or causal mechanisms, and the backtest omits several implementation costs.
- Existing historical sector and market-cap classifications are inadequate.

## Decisions required

None for Phase 12. Any further work should be separately pre-registered; no slides were started.

## Files changed

- `config/research_config.yaml`
- `docs/phase12_final_interpretation.md`
- `docs/phase12_completion_report.md`
- `results/tables/phase12_authoritative_headline_statistics.csv`
- `logs/research_log.md`
