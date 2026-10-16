# Phase 13 — Completion report

> **STALE — governance warning, 2026-09-12.** The prompt this report describes
> (`docs/phase13_claude_design_prompt.md`) is premised on S1 as primary; that premise was
> superseded by `docs/s2_primary_promotion_governance_override.md` the same day. See the warning
> at the top of the prompt file itself before using it.

## Completed

- Read the Trexquant Topic A brief, the Phase 12 final interpretation, the authoritative headline table, and
  the Phase 1–11 reports before drafting.
- Wrote `docs/phase13_claude_design_prompt.md`: a single self-sufficient brief instructing Claude Design to
  build the 20-minute Superday presentation package.
- Transcribed every statistic the deck is permitted to display into a locked-numbers annex (§3 of the
  prompt), each traced to its authoritative source file and row selector, so a mis-read by the downstream
  builder is detectable rather than silent.
- Specified the main deck as exactly 10 slides plus 11 appendix slides, reproducing the sponsor's slide
  requirements verbatim as the binding specification and augmenting each with permitted numbers, the named
  chart and its source series, source-note text, and an explicit "do not say" list.
- Specified the five deliverables (editable `.pptx`, PDF export, 17–18 minute talk track, Q&A preparation
  document covering all 19 required questions, source-to-slide evidence ledger), the design system, an
  eight-step validation protocol, and a prohibition list of honesty guardrails.
- Ran no experiment, changed no methodology, recomputed no statistic, and selected no more favourable result.

## Key findings

- Phase 12's authoritative table carries the headline statistics but not the supporting detail the deck
  needs (Phase 6 confounds, Phase 8 state dependence, Phase 1 raw-file audit, coverage, robustness). The
  prompt therefore names the specific Phase 1–11 table or report for every non-headline number rather than
  leaving the builder to search.
- The two failure modes worth engineering against are (a) inventing or rounding a statistic that already has
  an authoritative value and (b) silently reframing the conclusion — positive Rank IC with negative
  net-of-cost economics — into something more favourable. §1, §7, and §9 of the prompt target these directly.
- Charts must be plotted from the project's own CSVs. The prompt assigns a specific source table to each
  chart (`phase3_coverage_by_month.csv`, `phase6_correlation_summary.csv`, `phase7a_decile_returns.csv`,
  `phase7a_daily_ic_and_rolling60.csv`, `phase8_dependence_summary.csv`, `phase10_performance_summary.csv`)
  so that no chart can be drawn from imagined data.
- Two build decisions were confirmed with the sponsor before drafting: Claude Design will have full read
  access to the project directory, and the deck must be a genuine `python-pptx` build rather than an
  image-only or HTML export.

## Validation

- Every value in the prompt's locked-numbers annex was read from its source file in this session, not
  recalled. Spot-verified directly against `results/tables/phase12_authoritative_headline_statistics.csv`,
  `phase10_performance_summary.csv` (full 0/1/2.5/5 bps grid, both samples),
  `phase8_dependence_summary.csv`, `phase11_placebo_summary.csv`, `phase11_robustness_summary.csv`,
  `phase9_signal_governance.csv`, and `phase1_example_rows.csv`.
- Every artifact path cited in the prompt was confirmed to exist under `results/tables/`,
  `results/figures/`, or `docs/`.
- The prompt contains no pooled estimate and instructs explicitly against producing one; it states the
  frozen roles S1 primary / S0 baseline / S2 robustness comparator; and it labels every performance figure
  gross or net with its cost assumption.
- Coverage check against the sponsor's request: all 10 main slides, all 11 appendix topics, all 5
  deliverables, all 19 Q&A questions, every design requirement, and every validation requirement are
  present in the prompt.
- No file outside `docs/` and `logs/` was created or modified. No file under `data/`, `results/`, `src/`,
  `tests/`, `config/`, `baseline/`, `legacy/`, `presentation/`, or `preservation/` was touched.

## Problems and limitations

- Claude Design natively produces HTML canvas artboards, not `.pptx`. Per the sponsor's decision the prompt
  mandates a `python-pptx` build with native text frames and editable tables so that the "editable
  PowerPoint" and "render every slide to images" requirements are met literally, and instructs the builder
  to stop and say so if `python-pptx`, LibreOffice, or `pdftoppm` is unavailable rather than silently
  substituting an image-only deck.
- The prompt is long because it embeds the locked-numbers annex. That length is deliberate: it is the
  mechanism that makes an invented statistic detectable.
- The prompt cannot itself guarantee the downstream build is accurate. §7's validation protocol and the
  required evidence ledger are the checks; they must actually be executed and reported.
- Phase 13 produces the prompt only. The deck, PDF, talk track, Q&A document, and evidence ledger are not
  built by this phase.

## Decisions required

None for Phase 13. The presentation build is the next step and is governed entirely by
`docs/phase13_claude_design_prompt.md`.

## Files changed

- `docs/phase13_claude_design_prompt.md` (new)
- `docs/phase13_completion_report.md` (new)
- `logs/research_log.md` (one appended entry)
