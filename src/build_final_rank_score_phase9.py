"""Phase 9: freeze S1 and form target-independent bounded daily rank scores."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


SAMPLES = {
    "additional_2023-01-03_2025-05-27": ("2023-01-03", "2025-05-27"),
    "original_2025-05-28_2026-08-31": ("2025-05-28", "2026-08-31"),
}
SCORE_FIELDS = {
    "S0": "S0_bounded_rank_score",
    "S1": "S1_final_rank_score",
    "S2": "S2_bounded_rank_score",
}
TARGET_COLUMNS = ["designated_target_date", "next_session_adjusted_open", "next_session_adjusted_close", "forward_oc_return", "target_available", "target_status"]


def assign_bounded_rank_score(panel: pd.DataFrame, signal: str, score_column: str) -> pd.DataFrame:
    """Score a signal without reading target fields; ties follow canonical order."""
    output = panel.copy()
    rank_column, n_column = f"{signal}_rank", f"{signal}_rank_n"
    output[rank_column] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    output[n_column] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    output[score_column] = np.nan
    eligible = output.loc[output["universe_member"] & output[signal].notna()].copy()
    for _, day in eligible.groupby("Date", sort=False):
        ordered = day.sort_values([signal, "canonical_research_symbol"], kind="stable")
        n = len(ordered)
        ranks = np.arange(1, n + 1, dtype=int)
        scores = np.zeros(n, dtype=float) if n == 1 else 2 * (ranks - 1) / (n - 1) - 1
        output.loc[ordered.index, rank_column] = ranks
        output.loc[ordered.index, n_column] = n
        output.loc[ordered.index, score_column] = scores
    return output


def source_artifact_paths(root: Path) -> list[Path]:
    explicit = [
        root / "data/processed/phase7a_candidate_history_panel.parquet",
        root / "data/processed/phase7b_phase7_evaluation_panel.parquet",
        root / "data/processed/phase8_s2_formation_panel.parquet",
        root / "docs/phase7a_report.md",
        root / "docs/phase8_report.md",
    ]
    tables = sorted((root / "results/tables").glob("phase7a_*")) + sorted((root / "results/tables").glob("phase7b_*")) + sorted((root / "results/tables").glob("phase8_*"))
    return sorted(set(explicit + tables))


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_or_validate_source_manifest(root: Path) -> tuple[Path, int]:
    manifest_path = root / "preservation/phase9_pre_score_source_artifacts/SHA256SUMS.txt"
    paths = source_artifact_paths(root)
    if not all(path.exists() for path in paths):
        missing = [str(path) for path in paths if not path.exists()]
        raise FileNotFoundError(f"Missing Phase 9 source artifacts: {missing}")
    if not manifest_path.exists():
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"{hash_file(path)}  {path.relative_to(root)}" for path in paths]
        manifest_path.write_text("\n".join(lines) + "\n")
    expected = {}
    for line in manifest_path.read_text().splitlines():
        digest, relative = line.split("  ", 1)
        expected[relative] = digest
    failures = [relative for relative, digest in expected.items() if not (root / relative).exists() or hash_file(root / relative) != digest]
    if failures:
        raise AssertionError(f"Prior source artifact hash mismatch: {failures}")
    return manifest_path, len(expected)


def distribution(frame: pd.DataFrame, sample: str) -> list[dict[str, object]]:
    rows = []
    for signal, score in SCORE_FIELDS.items():
        values = frame[score].dropna()
        rows.append({"sample": sample, "signal": signal, "score_field": score, "n": len(values), "mean": values.mean(), "std": values.std(ddof=1), "min": values.min(), "p01": values.quantile(.01), "p50": values.median(), "p99": values.quantile(.99), "max": values.max()})
    return rows


def validate_scores(frame: pd.DataFrame, sample: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily_rows, ic_rows = [], []
    for signal, score in SCORE_FIELDS.items():
        eligible = frame.loc[frame[score].notna()].copy()
        if not eligible[score].between(-1, 1).all():
            raise AssertionError(f"{sample} {signal} score violates bounds")
        for date, day in eligible.groupby("Date"):
            n = len(day)
            minimum, maximum, mean = day[score].min(), day[score].max(), day[score].mean()
            if not np.isclose(mean, 0, atol=1e-12, rtol=0):
                raise AssertionError(f"{sample} {signal} daily score is not centered")
            if n >= 2 and (not np.isclose(minimum, -1, atol=1e-12) or not np.isclose(maximum, 1, atol=1e-12)):
                raise AssertionError(f"{sample} {signal} daily endpoints are incorrect")
            ordered = day.sort_values([signal, "canonical_research_symbol"], kind="stable")
            if not np.array_equal(ordered[f"{signal}_rank"].astype(int).to_numpy(), np.arange(1, n + 1)):
                raise AssertionError(f"{sample} {signal} rank ordering/ties differ from canonical deterministic order")
            daily_rows.append({"sample": sample, "Date": date, "signal": signal, "eligible_n": n, "score_min": minimum, "score_max": maximum, "score_mean": mean, "score_std": day[score].std(ddof=1)})
        if signal == "S1":
            for date, day in frame.loc[frame["S1"].notna() & frame[score].notna() & frame["target_available"] & frame["forward_oc_return"].notna()].groupby("Date"):
                raw_ic = stats.spearmanr(day["S1"], day["forward_oc_return"]).statistic
                score_ic = stats.spearmanr(day[score], day["forward_oc_return"]).statistic
                difference = score_ic - raw_ic
                if not np.isclose(difference, 0, atol=1e-12, rtol=0):
                    raise AssertionError(f"{sample} {date:%Y-%m-%d} S1 Rank IC differs after rank score: {difference}")
                ic_rows.append({"sample": sample, "Date": date, "raw_s1_rank_ic": raw_ic, "final_score_rank_ic": score_ic, "difference": difference, "observations": len(day)})
    return pd.DataFrame(daily_rows), pd.DataFrame(ic_rows)


def prepare_sample(parent: pd.DataFrame, s2: pd.DataFrame, sample: str) -> pd.DataFrame:
    start, end = SAMPLES[sample]
    panel = parent.loc[parent["Date"].between(start, end) & parent["universe_member"]].copy()
    if panel.duplicated(["Date", "canonical_research_symbol"]).any():
        raise AssertionError(f"Duplicate parent key in {sample}")
    expected_dates = 601 if sample.startswith("additional") else 317
    if panel["Date"].nunique() != expected_dates or not panel.groupby("Date").size().eq(400).all():
        raise AssertionError(f"{sample} date or top-400 membership no longer matches authoritative prior phase")
    s2_values = s2.loc[s2["sample"].eq(sample), ["Date", "canonical_research_symbol", "S2"]]
    if s2_values.duplicated(["Date", "canonical_research_symbol"]).any():
        raise AssertionError(f"Duplicate S2 key in {sample}")
    panel = panel.merge(s2_values, on=["Date", "canonical_research_symbol"], how="left", validate="one_to_one", suffixes=("", "_phase8"))
    if "S2_phase8" in panel.columns:
        panel["S2"] = panel["S2_phase8"]
        panel = panel.drop(columns=["S2_phase8"])
    formation = panel.drop(columns=[column for column in TARGET_COLUMNS if column in panel.columns])
    if set(TARGET_COLUMNS).intersection(formation.columns):
        raise AssertionError("Target column leaked into score formation")
    for signal, score in SCORE_FIELDS.items():
        formation = assign_bounded_rank_score(formation, signal, score)
    formation["final_rank_score"] = formation["S1_final_rank_score"]
    # Targets remain optional, separate evaluation metadata and are joined after score formation.
    targets = panel[[column for column in ["Date", "canonical_research_symbol", *TARGET_COLUMNS] if column in panel.columns]]
    output = formation.merge(targets, on=["Date", "canonical_research_symbol"], how="left", validate="one_to_one")
    output["sample"] = sample
    if not output["universe_member"].all():
        raise AssertionError(f"Non-member leaked into {sample} score panel")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(); root = args.root.resolve()
    manifest, artifact_count = create_or_validate_source_manifest(root)
    historical = pd.read_parquet(root / "data/processed/phase7a_candidate_history_panel.parquet")
    original = pd.read_parquet(root / "data/processed/phase7b_phase7_evaluation_panel.parquet")
    s2 = pd.read_parquet(root / "data/processed/phase8_s2_formation_panel.parquet")
    sources = {"additional_2023-01-03_2025-05-27": historical, "original_2025-05-28_2026-08-31": original}
    panels, distributions, coverage, daily_validation, rank_ics = [], [], [], [], []
    for sample, parent in sources.items():
        output = prepare_sample(parent, s2, sample)
        daily, ic = validate_scores(output, sample)
        panels.append(output); distributions.extend(distribution(output, sample)); daily_validation.append(daily); rank_ics.append(ic)
        coverage.append({
            "sample": sample,
            "top400_stock_days": len(output),
            "dates": output["Date"].nunique(),
            "s0_signal_eligible": int(output["S0"].notna().sum()),
            "s1_signal_eligible": int(output["S1"].notna().sum()),
            "s2_signal_eligible": int(output["S2"].notna().sum()),
            "s0_score_eligible": int(output["S0_bounded_rank_score"].notna().sum()),
            "s1_score_eligible": int(output["final_rank_score"].notna().sum()),
            "s2_score_eligible": int(output["S2_bounded_rank_score"].notna().sum()),
            "target_available": int(output.get("target_available", pd.Series(False, index=output.index)).fillna(False).sum()),
        })
    score_panel = pd.concat(panels, ignore_index=True)
    if score_panel.duplicated(["sample", "Date", "canonical_research_symbol"]).any():
        raise AssertionError("Score-enhanced panel has duplicate keys")
    score_panel.to_parquet(root / "data/processed/phase9_final_rank_score_panel.parquet", index=False)
    pd.DataFrame(coverage).to_csv(root / "results/tables/phase9_score_coverage.csv", index=False)
    pd.DataFrame(distributions).to_csv(root / "results/tables/phase9_score_distributions.csv", index=False)
    pd.concat(daily_validation, ignore_index=True).to_csv(root / "results/tables/phase9_daily_score_validation.csv", index=False)
    pd.concat(rank_ics, ignore_index=True).to_csv(root / "results/tables/phase9_s1_rank_ic_equivalence.csv", index=False)
    pd.DataFrame([
        {"signal": "S1", "role": "primary_signal", "raw_field": "S1", "bounded_score_field": "final_rank_score", "status": "frozen_primary"},
        {"signal": "S0", "role": "baseline", "raw_field": "S0", "bounded_score_field": "S0_bounded_rank_score", "status": "frozen_benchmark"},
        {"signal": "S2", "role": "robustness_comparator", "raw_field": "S2", "bounded_score_field": "S2_bounded_rank_score", "status": "frozen_benchmark"},
    ]).to_csv(root / "results/tables/phase9_signal_governance.csv", index=False)
    # Validate source artifact preservation again after all output writes.
    _, verified_artifact_count = create_or_validate_source_manifest(root)
    print(json.dumps({"score_panel_rows": len(score_panel), "coverage": coverage, "source_artifacts_verified": verified_artifact_count, "source_manifest": str(manifest.relative_to(root))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
