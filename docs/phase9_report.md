# Phase 9 — Final signal choice and bounded rank score

## Completed

- Read the authoritative configuration, append-only log, and Phase 7A/Phase 8 reports before implementation.
- Locked S1 as the primary signal, S0 as the baseline, and S2 as the frozen robustness comparator before score construction.
- Created the target-independent daily bounded score

  `final_rank_score = 2 × (rank − 1) / (n − 1) − 1`

  from S1 ordered low-to-high with stable alphabetical tie-breaking. The score maps the lowest S1 to −1, the highest to +1, and has daily mean zero.
- Created equivalent S0 and S2 bounded benchmark-score fields without changing their raw signals.
- Preserved missing signals and scores as missing. Targets were joined only after score formation and retained as separate evaluation metadata.
- Kept the additional reconstructed-membership and original fixed-snapshot analyses separate. No pooled estimate, portfolio backtest, or transaction-cost analysis was run.

## Key findings

| Sample | Top-400 stock-days | S1 score eligible | S0 score eligible | S2 score eligible | Target available |
| --- | ---: | ---: | ---: | ---: | ---: |
| Additional, 2023-01-03 to 2025-05-27 | 240,400 | 240,157 | 240,399 | 240,157 | 240,400 |
| Original, 2025-05-28 to 2026-08-31 | 126,800 | 125,980 | 126,272 | 125,980 | 126,799 |

The primary score's pooled-within-sample distribution has mean effectively zero, standard deviation about 0.579, minimum −1, median zero, and maximum +1 in each sample. These are mechanical properties of the chosen bounded rank representation, not new evidence about alpha performance.

The score preserves predictive rank content exactly: all 918 daily S1 raw-versus-score Rank IC comparisons have zero numerical difference at the configured tolerance. This is expected because the score is a strictly increasing re-expression of S1 after deterministic tie resolution.

The governance table freezes the intended roles:

| Signal | Role | Bounded score field |
| --- | --- | --- |
| S1 | Primary predictive signal | `final_rank_score` |
| S0 | Baseline | `S0_bounded_rank_score` |
| S2 | Robustness comparator | `S2_bounded_rank_score` |

## Validation

- Bounds: every nonmissing score is in `[−1, +1]`.
- Centering: each daily score cross-section has mean zero within `1e-12` tolerance.
- Endpoints: every cross-section with at least two eligible names has exact minimum −1 and maximum +1.
- Ordering: score ranks exactly reproduce ascending raw-signal order; exact ties use canonical alphabetical order.
- Target isolation: the formation panel omits target and target-availability fields. Synthetic tests changing target fields leave all scores unchanged.
- Missingness: unavailable signals remain unavailable scores; no price, volume, signal, score, or target field is replaced with zero.
- Samples: 601 historical and 317 original dates retain exactly 400 signal-date members per date, matching authoritative prior phases.
- Preservation: a pre-score source manifest covers 84 Phase 7A/7B/8 source artifacts; all hashes match after construction.
- Automated validation: 15 tests pass, including focused formula, bounds, centering, ties, missing-signal, target-independence, Rank-IC-equivalence, source-preservation, and sample-membership checks.

## Problems and limitations

- This score is a rank-scale transformation, not a new alpha model. It does not resolve S1's earlier paired-comparison ambiguity against S0.
- The original and additional samples retain their different universe methodologies and cannot be pooled.
- Public-data survivorship, identifier, corporate-action, and FINRA revision-vintage limitations remain unchanged.
- Realistic portfolio construction, turnover, borrowing, capacity, and transaction costs remain deliberately unexamined in this phase.

## Decisions required

No decision is required to complete Phase 9. The project is ready for review before any separately authorized realistic portfolio backtest. S1 is frozen as the primary score; S0 and S2 remain benchmarks.

## Files changed

- Governance: `config/research_config.yaml`, `README.md`, and `logs/research_log.md`.
- Implementation/test: `src/build_final_rank_score_phase9.py` and `tests/test_phase9_final_rank_score.py`.
- Preservation: `preservation/phase9_pre_score_source_artifacts/SHA256SUMS.txt`.
- Score panel: `data/processed/phase9_final_rank_score_panel.parquet`.
- Tables: `results/tables/phase9_score_coverage.csv`, `phase9_score_distributions.csv`, `phase9_daily_score_validation.csv`, `phase9_s1_rank_ic_equivalence.csv`, and `phase9_signal_governance.csv`.

No realistic portfolio backtest or transaction-cost artifact was created, and no Phase 7A/7B/8 source artifact was changed.
