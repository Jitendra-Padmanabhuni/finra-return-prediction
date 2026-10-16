"""Build Phase 7A historical membership, top-400 universe, features, and coverage gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from candidate_history_features import add_candidate_history_features
from inspect_finra import read_finra_file
from reconstruct_sp500_history_phase7a import locate_active


ADDITIONAL_START, ADDITIONAL_END = pd.Timestamp("2023-01-03"), pd.Timestamp("2025-05-27")


def current_active(current: pd.DataFrame) -> dict[str, dict[str, object]]:
    active = {}
    for row in current.itertuples(index=False):
        cik = str(row.CIK).zfill(10) if pd.notna(row.CIK) else "missing"
        identity = f"current_cik_{cik}_symbol_{row.source_symbol}"
        active[identity] = {"canonical_research_symbol": identity, "source_symbol": row.source_symbol, "company_name": row.security_name, "cik": cik, "identity_origin": "september_2026_snapshot"}
    return active


def reverse_change(active: dict[str, dict[str, object]], row: object) -> None:
    view = {key: {"active_symbol": value["source_symbol"], "active_name": value["company_name"]} for key, value in active.items()}
    if row.is_ticker_or_name_change and pd.notna(row.added_ticker) and pd.notna(row.removed_ticker):
        identity, _ = locate_active(view, str(row.added_ticker), str(row.added_security))
        if identity is None:
            raise ValueError(f"Unresolved explicit ticker change {row.change_row_id}")
        active[identity]["source_symbol"] = str(row.removed_ticker)
        active[identity]["company_name"] = str(row.removed_security)
        return
    if pd.notna(row.added_ticker):
        identity, _ = locate_active(view, str(row.added_ticker), str(row.added_security))
        if identity is None:
            raise ValueError(f"Unresolved addition reversal {row.change_row_id}")
        active.pop(identity)
    if pd.notna(row.removed_ticker):
        identity = f"historical_{row.effective_date:%Y%m%d}_{row.change_row_id}_{row.removed_ticker}"
        active[identity] = {"canonical_research_symbol": identity, "source_symbol": str(row.removed_ticker), "company_name": str(row.removed_security), "cik": pd.NA, "identity_origin": f"removed_table_{row.change_row_id}"}


def reconstruct_daily_membership(dates: pd.Series, current: pd.DataFrame, changes: pd.DataFrame) -> pd.DataFrame:
    active = current_active(current)
    event_groups = [(date, group) for date, group in changes.sort_values(["effective_date", "change_row_id"], ascending=[False, False]).groupby("effective_date", sort=False)]
    event_index = 0; records = []
    for date in sorted(pd.to_datetime(dates.unique()), reverse=True):
        while event_index < len(event_groups) and event_groups[event_index][0] > date:
            _, group = event_groups[event_index]
            for row in group.itertuples(index=False):
                reverse_change(active, row)
            event_index += 1
        for value in active.values():
            records.append({"Date": date, **value, "sp500_member": True})
    output = pd.DataFrame(records)
    if output.duplicated(["Date", "canonical_research_symbol"]).any() or output.duplicated(["Date", "source_symbol"]).any():
        raise ValueError("Reconstructed daily membership is not unique")
    return output.sort_values(["Date", "source_symbol"]).reset_index(drop=True)


def time_dependent_aliases(spine: pd.DataFrame, union: pd.DataFrame, event_audit: pd.DataFrame) -> pd.DataFrame:
    base = spine.merge(union, on="canonical_research_symbol", how="left", validate="many_to_one")
    base = base.rename(columns={"registry_symbol": "source_symbol", "registry_company_name": "company_name"})
    # Yahoo generally backfills the surviving/current symbol across earlier
    # ticker-only changes, while FINRA files retain the symbol actually traded
    # on each date. Preserve those vendor identifiers separately.
    base["yahoo_symbol"] = base["source_symbol"].str.replace(".", "-", regex=False)
    base["yahoo_mapping_status"] = "registry_symbol_backfilled_by_yahoo"
    paramount_predecessor = base["identity_origin"].eq("removed_table_supplemental_0005")
    base.loc[paramount_predecessor, "yahoo_symbol"] = "PSKY"
    base.loc[paramount_predecessor, "yahoo_mapping_status"] = "distinct_predecessor_history_served_under_yahoo_successor_symbol"
    explicit = event_audit.loc[event_audit["operation"].eq("reverse_explicit_ticker_or_name_change") & event_audit["security_instance_id"].notna()].copy()
    explicit["effective_date"] = pd.to_datetime(explicit["effective_date"])
    for row in explicit.sort_values("effective_date", ascending=False).itertuples(index=False):
        mask = base["canonical_research_symbol"].eq(row.security_instance_id) & base["Date"].lt(row.effective_date)
        base.loc[mask, "source_symbol"] = row.removed_ticker
    base["finra_symbol"] = base["source_symbol"].str.replace(".", "/", regex=False)
    return base


def parse_finra(raw_dir: Path, dates: pd.Series, wanted: set[str]) -> pd.DataFrame:
    rows = []
    for date in dates.sort_values():
        path = raw_dir / f"CNMSshvol{date:%Y%m%d}.txt"
        records, _ = read_finra_file(path)
        for record in records:
            if record["Symbol"] in wanted:
                rows.append({"Date": pd.Timestamp(record["Date"]), "finra_symbol": record["Symbol"], "ShortVolume": record["ShortVolume"], "ShortExemptVolume": record["ShortExemptVolume"], "TotalVolume": record["TotalVolume"], "finra_market": record["Market"], "finra_source_file": path.name})
    output = pd.DataFrame(rows)
    if output.duplicated(["Date", "finra_symbol"]).any():
        raise ValueError("FINRA historical aliases are not unique")
    return output


def build_top400(panel: pd.DataFrame, membership: pd.DataFrame, dates: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    month_starts = dates.groupby(dates.dt.to_period("M")).min()
    selected_rows, audit_rows = [], []
    ordered_dates = dates.sort_values().reset_index(drop=True)
    member_lookup = membership[["Date", "canonical_research_symbol", "source_symbol"]]
    for rebalance in month_starts:
        location = int(ordered_dates.searchsorted(rebalance))
        if location < 20:
            audit_rows.append({"rebalance_date": rebalance, "status": "insufficient_20_date_history", "selected": 0})
            continue
        window_dates = ordered_dates.iloc[location - 20 : location]
        candidates = member_lookup.loc[member_lookup["Date"].eq(rebalance)]
        history = panel.loc[panel["Date"].isin(window_dates), ["Date", "canonical_research_symbol", "Close", "Volume"]].merge(candidates[["canonical_research_symbol", "source_symbol"]], on="canonical_research_symbol", how="inner", validate="many_to_one")
        history["valid"] = history[["Close", "Volume"]].notna().all(axis=1)
        history["raw_dollar_volume"] = history["Close"] * history["Volume"]
        trailing = history.groupby(["canonical_research_symbol", "source_symbol"], as_index=False).agg(valid_observations=("valid", "sum"), distinct_dates=("Date", "nunique"), trailing_median_dollar_volume=("raw_dollar_volume", "median"))
        eligible = trailing.loc[trailing["valid_observations"].eq(20) & trailing["distinct_dates"].eq(20)].sort_values(["trailing_median_dollar_volume", "source_symbol", "canonical_research_symbol"], ascending=[False, True, True]).head(400).copy()
        if len(trailing.loc[trailing["valid_observations"].eq(20) & trailing["distinct_dates"].eq(20)]) >= 400 and len(eligible) != 400:
            raise AssertionError("Historical top-400 count failure")
        eligible["universe_refresh_date"] = rebalance; eligible["screen_first_date"] = window_dates.min(); eligible["screen_last_date"] = window_dates.max()
        selected_rows.append(eligible)
        audit_rows.append({"rebalance_date": rebalance, "status": "selected", "sp500_members": len(candidates), "eligible_exact_20": int(((trailing.valid_observations == 20) & (trailing.distinct_dates == 20)).sum()), "selected": len(eligible), "window_dates": len(window_dates), "window_min": window_dates.min(), "window_max": window_dates.max()})
    monthly = pd.concat(selected_rows, ignore_index=True)
    date_map = pd.merge_asof(pd.DataFrame({"Date": ordered_dates}), monthly[["universe_refresh_date"]].drop_duplicates().sort_values("universe_refresh_date"), left_on="Date", right_on="universe_refresh_date", direction="backward").dropna()
    daily = date_map.merge(monthly, on="universe_refresh_date", how="inner", validate="many_to_many")
    daily["universe_member"] = True
    if daily.duplicated(["Date", "canonical_research_symbol"]).any():
        raise ValueError("Historical top-400 daily membership duplicate")
    return daily, pd.DataFrame(audit_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw")); parser.add_argument("--processed-dir", type=Path, default=Path("data/processed")); parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    args = parser.parse_args()
    current = pd.read_csv(args.tables_dir / "phase2_candidate_universe.csv", dtype={"CIK": str})
    changes = pd.read_csv(args.tables_dir / "phase7a_membership_changes_augmented.csv", parse_dates=["effective_date"])
    union = pd.read_csv(args.processed_dir / "phase7a_historical_security_union.csv", dtype={"cik": str}).rename(columns={"security_instance_id": "canonical_research_symbol"})
    event_audit = pd.read_csv(args.tables_dir / "phase7a_membership_reconstruction_event_audit.csv", parse_dates=["effective_date"])
    market = pd.read_parquet(args.processed_dir / "phase7a_yahoo_alias_market.parquet")
    dates = pd.Series(sorted(pd.to_datetime(market["Date"].unique())), name="Date")
    membership = reconstruct_daily_membership(dates, current, changes)
    membership.to_parquet(args.processed_dir / "phase7a_sp500_membership_daily.parquet", index=False)
    membership.groupby("Date").size().rename("sp500_members").reset_index().to_csv(args.tables_dir / "phase7a_membership_counts_by_date.csv", index=False)

    spine = pd.DataFrame({"Date": dates}).merge(union[["canonical_research_symbol"]], how="cross")
    panel = time_dependent_aliases(spine, union, event_audit)
    market = market.copy(); market["adjustment_factor"] = market["Adj Close"] / market["Close"]
    market["adjusted_open"] = market["Open"] * market["adjustment_factor"]; market["adjusted_close"] = market["Adj Close"]
    panel = panel.merge(market, on=["Date", "yahoo_symbol"], how="left", validate="many_to_one", indicator="market_join")
    finra = parse_finra(args.raw_dir, dates, set(panel["finra_symbol"]))
    panel = panel.merge(finra, on=["Date", "finra_symbol"], how="left", validate="many_to_one", indicator="finra_join")
    panel["market_observation_present"] = panel["market_join"].eq("both"); panel["finra_observation_present"] = panel["finra_join"].eq("both")
    ambiguous_tickers = set(pd.read_csv(args.tables_dir / "phase7a_identifier_ambiguities.csv")["source_symbol"])
    duplicate_aliases = panel.groupby(["Date", "source_symbol"])["canonical_research_symbol"].transform("nunique").gt(1)
    panel["identifier_status"] = "resolved_best_effort"; panel.loc[panel["source_symbol"].isin(ambiguous_tickers) | duplicate_aliases, "identifier_status"] = "ambiguous_ticker_or_multiple_security_instances"
    top400, screen_audit = build_top400(panel, membership, dates)
    screen_audit.to_csv(args.tables_dir / "phase7a_top400_monthly_audit.csv", index=False)
    top400.to_parquet(args.processed_dir / "phase7a_top400_daily.parquet", index=False)
    top_keys = top400[["Date", "canonical_research_symbol"]].assign(universe_member=True)
    panel = panel.merge(top_keys, on=["Date", "canonical_research_symbol"], how="left", validate="one_to_one")
    panel["universe_member"] = panel["universe_member"].eq(True)
    panel = add_candidate_history_features(panel)

    calendar_map = pd.DataFrame({"Date": dates, "designated_target_date": dates.shift(-1)}).dropna()
    panel = panel.merge(calendar_map, on="Date", how="left", validate="many_to_one")
    prices = panel[["Date", "canonical_research_symbol", "adjusted_open", "adjusted_close"]].rename(columns={"Date": "designated_target_date", "adjusted_open": "next_session_adjusted_open", "adjusted_close": "next_session_adjusted_close"})
    panel = panel.merge(prices, on=["designated_target_date", "canonical_research_symbol"], how="left", validate="many_to_one")
    panel["forward_oc_return"] = panel["next_session_adjusted_close"] / panel["next_session_adjusted_open"] - 1
    panel["target_available"] = panel["designated_target_date"].notna() & panel["next_session_adjusted_open"].gt(0) & panel["next_session_adjusted_close"].gt(0) & np.isfinite(panel["forward_oc_return"])
    panel.to_parquet(args.processed_dir / "phase7a_candidate_history_panel.parquet", index=False)

    actions = panel.loc[
        panel["Dividends"].fillna(0).ne(0) | panel["Stock Splits"].fillna(0).ne(0),
        ["Date", "canonical_research_symbol", "source_symbol", "yahoo_symbol", "Dividends", "Stock Splits", "universe_member"],
    ]
    actions.to_csv(args.tables_dir / "phase7a_corporate_actions.csv", index=False)
    panel.loc[
        panel["forward_oc_return"].abs().ge(.20),
        ["Date", "designated_target_date", "canonical_research_symbol", "source_symbol", "next_session_adjusted_open", "next_session_adjusted_close", "forward_oc_return", "universe_member"],
    ].sort_values("forward_oc_return").to_csv(args.tables_dir / "phase7a_extreme_forward_returns.csv", index=False)

    eval_member = panel.loc[panel["Date"].between(ADDITIONAL_START, ADDITIONAL_END) & panel["universe_member"]].copy()
    eval_member["complete_market_finra"] = eval_member["market_observation_present"] & eval_member["finra_observation_present"]
    gate_rate = float(eval_member["complete_market_finra"].mean())
    eval_member["s1_preperformance_eligible"] = eval_member["S1"].notna() & eval_member["target_available"]
    overall = pd.DataFrame([{"eligible_stock_days": len(eval_member), "complete_market_finra_rows": int(eval_member.complete_market_finra.sum()), "complete_market_finra_rate": gate_rate, "market_missing": int((~eval_member.market_observation_present).sum()), "finra_missing": int((~eval_member.finra_observation_present).sum()), "target_missing": int((~eval_member.target_available).sum()), "s1_eligible": int(eval_member.s1_preperformance_eligible.sum()), "coverage_gate_threshold": .95, "coverage_gate_pass": gate_rate >= .95}])
    overall.to_csv(args.tables_dir / "phase7a_coverage_gate.csv", index=False)
    eval_member.groupby("Date").agg(rows=("Date", "size"), complete=("complete_market_finra", "sum"), market_present=("market_observation_present", "sum"), finra_present=("finra_observation_present", "sum"), s1_eligible=("s1_preperformance_eligible", "sum")).reset_index().to_csv(args.tables_dir / "phase7a_coverage_by_date.csv", index=False)
    eval_member.groupby(["canonical_research_symbol", "source_symbol", "company_name", "identity_origin", "identifier_status"]).agg(rows=("Date", "size"), complete=("complete_market_finra", "sum"), market_present=("market_observation_present", "sum"), finra_present=("finra_observation_present", "sum"), s1_eligible=("s1_preperformance_eligible", "sum")).reset_index().to_csv(args.tables_dir / "phase7a_coverage_by_security.csv", index=False)
    eval_member.loc[
        ~eval_member["complete_market_finra"],
        ["Date", "canonical_research_symbol", "source_symbol", "yahoo_symbol", "finra_symbol", "market_observation_present", "finra_observation_present", "identifier_status"],
    ].head(100).to_csv(args.tables_dir / "phase7a_representative_unmatched_rows.csv", index=False)
    removed = panel.loc[panel["identity_origin"].str.startswith("removed_table", na=False)].groupby(["canonical_research_symbol", "source_symbol", "company_name"]).agg(rows=("Date", "size"), market_present=("market_observation_present", "sum"), finra_present=("finra_observation_present", "sum"), sp500_member_days=("canonical_research_symbol", lambda series: 0)).reset_index()
    member_days = membership.groupby("canonical_research_symbol").size()
    removed["sp500_member_days"] = removed["canonical_research_symbol"].map(member_days).fillna(0).astype(int)
    removed.to_csv(args.tables_dir / "phase7a_removed_delisted_coverage.csv", index=False)
    gate = {"coverage_gate_pass": gate_rate >= .95, "complete_market_finra_rate": gate_rate, "eligible_rows": len(eval_member), "historical_security_union": len(union), "shared_dates": len(dates), "performance_permitted": gate_rate >= .95}
    (args.processed_dir / "phase7a_coverage_gate.json").write_text(json.dumps(gate, indent=2) + "\n")
    print(json.dumps(gate, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
