"""Preserve and normalize the public S&P 500 history used by Phase 7A."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


SOURCE_URL = "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500"
PRE_MOVE_URL = "https://en.wikipedia.org/w/index.php?title=List_of_S%26P_500_companies&oldid=1368675864"

# The S&P additions/removals table is not a security master and omits many
# ticker-only corporate actions.  These events were identified during the
# pre-performance identifier audit from company/SEC sources.  They are kept
# separate from the raw S&P table and are only used to reconcile identities.
SUPPLEMENTAL_IDENTITY_EVENTS = [
    ("2026-08-18", "VMRK", "Vivmark Residential", "EQR", "Equity Residential", "same_entity_alias", "https://investors.vivmarkresidential.com/news-events/press-releases/detail/113/vivmark-residential-launches-as-one-of-the-countrys-leading-real-estate-companies"),
    ("2026-06-24", "ECHO", "EchoStar", "SATS", "EchoStar", "same_entity_alias", "https://ir.echostar.com/news-releases/news-release-details/echostar-changing-stocker-ticker-sats-echo-marking-companys-next"),
    ("2026-05-21", "BNY", "BNY Mellon", "BK", "BNY Mellon", "same_entity_alias", "https://www.bny.com/corporate/global/en/about-us/newsroom/press-release/bny-announces-planned-change-of-stock-ticker-symbol-to-bny-130465.html"),
    ("2026-01-14", "MRSH", "Marsh", "MMC", "Marsh McLennan", "same_entity_alias", "https://www.marsh.com/en/corp/about/news/marsh-mclennan-to-change-nyse-symbol-to-mrsh.html"),
    ("2025-11-11", "FISV", "Fiserv", "FI", "Fiserv", "same_entity_alias", "https://investors.fiserv.com/news-releases/news-release-details/fiserv-announces-transfer-stock-exchange-listing-nasdaq"),
    # Paramount Skydance has a new CIK and predecessor shares ceased to exist.
    # It is therefore a distinct historical security instance, not an alias.
    ("2025-08-07", "PSKY", "Paramount Skydance Corporation", "PARA", "Paramount Global Class B", "new_security_predecessor", "https://ir.paramount.com/news-releases/news-release-details/skydance-media-and-paramount-global-complete-merger-creating"),
    ("2024-03-04", "DOC", "Healthpeak Properties", "PEAK", "Healthpeak Properties", "same_entity_alias", "https://www.sec.gov/Archives/edgar/data/765880/000162828024018706/peak-20240331.htm"),
    ("2023-08-30", "COR", "Cencora", "ABC", "AmerisourceBergen", "same_entity_alias", "https://investor.cencora.com/news/news-details/2023/AmerisourceBergen-becomes-Cencora-in-alignment-with-the-companys-growing-global-footprint-and-central-role-in-pharmaceutical-access-and-care/default.aspx"),
    ("2023-07-10", "EG", "Everest Group", "RE", "Everest Re Group", "same_entity_alias", "https://en.wikipedia.org/w/index.php?title=List_of_S%26P_500_companies&oldid=1368675864"),
    ("2023-06-07", "FI", "Fiserv", "FISV", "Fiserv", "same_entity_alias", "https://investors.fiserv.com/news-releases/news-release-details/fiserv-transfer-listing-new-york-stock-exchange"),
    ("2023-05-16", "RVTY", "Revvity", "PKI", "PerkinElmer", "same_entity_alias", "https://ir.revvity.com/news/investor-news/news-details/2023/Launching-Revvity-A-Scientific-Solutions-Company-Powering-Innovation-from-Discovery-to-Cure/default.aspx"),
]


def normalize_name(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    return re.sub(r"[^a-z0-9]", "", text.lower().replace("corporation", "").replace("incorporated", "").replace("company", "").replace("inc.", "").replace("corp.", ""))


def clean_ticker(value: object) -> str | None:
    if pd.isna(value) or not str(value).strip():
        return None
    return str(value).strip()


def yahoo_symbol(ticker: str) -> str:
    return ticker.replace(".", "-")


def finra_symbol(ticker: str) -> str:
    return ticker.replace(".", "/")


def locate_active(active: dict[str, dict[str, object]], ticker: str, name: str) -> tuple[str | None, str]:
    by_ticker = [key for key, value in active.items() if value["active_symbol"] == ticker]
    if len(by_ticker) == 1:
        return by_ticker[0], "exact_ticker"
    wanted_name = normalize_name(name)
    by_name = [key for key, value in active.items() if normalize_name(value["active_name"]) == wanted_name and wanted_name]
    if len(by_name) == 1:
        return by_name[0], "exact_normalized_name"
    return None, "unresolved_or_ambiguous"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-candidates", type=Path, default=Path("results/tables/phase2_candidate_universe.csv"))
    parser.add_argument("--historical-html", type=Path, default=Path("data/raw/phase7a_sp500_historical_components_20260911.html"))
    parser.add_argument("--pre-move-html", type=Path, default=Path("data/raw/phase7a_sp500_pre_move_oldid_1368675864.html"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args(); args.tables_dir.mkdir(parents=True, exist_ok=True); args.processed_dir.mkdir(parents=True, exist_ok=True)
    current = pd.read_csv(args.current_candidates, dtype={"CIK": str})
    tables = pd.read_html(args.historical_html)
    changes = next(table for table in tables if isinstance(table.columns, pd.MultiIndex) and ("Added", "Ticker") in table.columns).copy()
    changes.columns = ["effective_date", "added_ticker", "added_security", "removed_ticker", "removed_security", "reason", "refs"]
    changes["effective_date"] = pd.to_datetime(changes["effective_date"])
    changes = changes.loc[changes["effective_date"].between("2022-09-01", "2026-09-11")].copy()
    for column in ["added_ticker", "removed_ticker"]:
        changes[column] = changes[column].map(clean_ticker)
    changes["change_row_id"] = [f"change_{index:04d}" for index in range(len(changes))]
    lower_reason = changes["reason"].fillna("").str.lower()
    changes["is_ticker_or_name_change"] = lower_reason.str.contains("changed its ticker|changed its name")
    changes["is_merger_or_acquisition"] = lower_reason.str.contains("acquir|merger|privati|receivership")
    changes["is_spinoff_or_splitoff"] = lower_reason.str.contains("spin-off|spun off|split-off")
    changes["is_one_sided"] = changes["added_ticker"].isna() | changes["removed_ticker"].isna()
    changes.to_csv(args.tables_dir / "phase7a_sp500_changes_raw_table.csv", index=False)

    supplemental = pd.DataFrame(
        SUPPLEMENTAL_IDENTITY_EVENTS,
        columns=["effective_date", "added_ticker", "added_security", "removed_ticker", "removed_security", "identity_treatment", "source_url"],
    )
    supplemental["effective_date"] = pd.to_datetime(supplemental["effective_date"])
    supplemental["reason"] = supplemental["identity_treatment"].map({
        "same_entity_alias": "supplemental audited ticker/name change",
        "new_security_predecessor": "supplemental audited merger predecessor; distinct security instance",
    })
    supplemental["refs"] = supplemental["source_url"]
    supplemental["change_row_id"] = [f"supplemental_{index:04d}" for index in range(len(supplemental))]
    supplemental["is_ticker_or_name_change"] = supplemental["identity_treatment"].eq("same_entity_alias")
    supplemental["is_merger_or_acquisition"] = supplemental["identity_treatment"].eq("new_security_predecessor")
    supplemental["is_spinoff_or_splitoff"] = False
    supplemental["is_one_sided"] = False
    supplemental.to_csv(args.tables_dir / "phase7a_supplemental_identity_events.csv", index=False)
    changes = pd.concat([changes, supplemental[changes.columns]], ignore_index=True)
    changes.to_csv(args.tables_dir / "phase7a_membership_changes_augmented.csv", index=False)

    active: dict[str, dict[str, object]] = {}
    registry: dict[str, dict[str, object]] = {}
    aliases: list[dict[str, object]] = []
    for row in current.itertuples(index=False):
        cik = str(row.CIK).zfill(10) if pd.notna(row.CIK) else "missing"
        identity = f"current_cik_{cik}_symbol_{row.source_symbol}"
        record = {"security_instance_id": identity, "active_symbol": row.source_symbol, "active_name": row.security_name, "cik": cik, "identity_origin": "september_2026_snapshot"}
        active[identity] = record.copy(); registry[identity] = record.copy()
        aliases.append({"security_instance_id": identity, "source_symbol": row.source_symbol, "company_name": row.security_name, "cik": cik, "alias_origin": "current_snapshot", "explicit_identity_link": True})

    audit_rows = []
    for effective_date, day in changes.sort_values(["effective_date", "change_row_id"], ascending=[False, False]).groupby("effective_date", sort=False):
        for row in day.itertuples(index=False):
            if row.is_ticker_or_name_change and row.added_ticker and row.removed_ticker:
                identity, method = locate_active(active, row.added_ticker, row.added_security)
                if identity:
                    aliases.append({"security_instance_id": identity, "source_symbol": row.removed_ticker, "company_name": row.removed_security, "cik": registry[identity]["cik"], "alias_origin": f"explicit_change_{row.change_row_id}", "explicit_identity_link": True})
                    active[identity]["active_symbol"] = row.removed_ticker
                    active[identity]["active_name"] = row.removed_security
                audit_rows.append({"effective_date": effective_date, "change_row_id": row.change_row_id, "operation": "reverse_explicit_ticker_or_name_change", "added_ticker": row.added_ticker, "removed_ticker": row.removed_ticker, "match_method": method, "security_instance_id": identity, "active_count_after": len(active)})
                continue
            if row.added_ticker:
                identity, method = locate_active(active, row.added_ticker, row.added_security)
                if identity:
                    active.pop(identity)
                audit_rows.append({"effective_date": effective_date, "change_row_id": row.change_row_id, "operation": "reverse_remove_added_security", "added_ticker": row.added_ticker, "removed_ticker": row.removed_ticker, "match_method": method, "security_instance_id": identity, "active_count_after": len(active)})
            if row.removed_ticker:
                identity = f"historical_{effective_date:%Y%m%d}_{row.change_row_id}_{row.removed_ticker}"
                record = {"security_instance_id": identity, "active_symbol": row.removed_ticker, "active_name": row.removed_security, "cik": pd.NA, "identity_origin": f"removed_table_{row.change_row_id}"}
                active[identity] = record.copy(); registry[identity] = record.copy()
                aliases.append({"security_instance_id": identity, "source_symbol": row.removed_ticker, "company_name": row.removed_security, "cik": pd.NA, "alias_origin": f"removed_table_{row.change_row_id}", "explicit_identity_link": False})
                audit_rows.append({"effective_date": effective_date, "change_row_id": row.change_row_id, "operation": "reverse_add_removed_security", "added_ticker": row.added_ticker, "removed_ticker": row.removed_ticker, "match_method": "new_historical_instance", "security_instance_id": identity, "active_count_after": len(active)})

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(args.tables_dir / "phase7a_membership_reconstruction_event_audit.csv", index=False)
    alias_table = pd.DataFrame(aliases).drop_duplicates(["security_instance_id", "source_symbol"])
    alias_table["yahoo_symbol"] = alias_table["source_symbol"].map(yahoo_symbol)
    alias_table["finra_symbol"] = alias_table["source_symbol"].map(finra_symbol)
    alias_table.to_csv(args.tables_dir / "phase7a_security_identity_aliases.csv", index=False)
    union = pd.DataFrame(registry.values()).rename(columns={"active_symbol": "registry_symbol", "active_name": "registry_company_name"})
    union.to_csv(args.processed_dir / "phase7a_historical_security_union.csv", index=False)

    name_by_ticker = pd.concat([
        current[["source_symbol", "security_name"]].rename(columns={"security_name": "company_name"}),
        changes[["added_ticker", "added_security"]].rename(columns={"added_ticker": "source_symbol", "added_security": "company_name"}),
        changes[["removed_ticker", "removed_security"]].rename(columns={"removed_ticker": "source_symbol", "removed_security": "company_name"}),
    ], ignore_index=True).dropna(subset=["source_symbol"])
    risk = name_by_ticker.assign(normalized_name=lambda frame: frame["company_name"].map(normalize_name)).groupby("source_symbol").agg(distinct_names=("normalized_name", "nunique"), observed_names=("company_name", lambda values: " | ".join(sorted(set(map(str, values)))))).reset_index()
    risk = risk.loc[risk["distinct_names"] > 1].copy()
    risk["risk"] = "ticker_reuse_name_change_or_source_naming_ambiguity_requires_review"
    risk.to_csv(args.tables_dir / "phase7a_identifier_ambiguities.csv", index=False)

    metadata = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(), "current_snapshot_rows": len(current),
        "raw_sp500_change_rows_since_2022_09_01": len(changes) - len(supplemental),
        "supplemental_identity_events": len(supplemental), "augmented_reconstruction_events": len(changes),
        "security_instances_in_union": len(union), "unique_source_aliases": alias_table["source_symbol"].nunique(),
        "unresolved_reverse_addition_matches": int((audit["match_method"] == "unresolved_or_ambiguous").sum()),
        "identifier_ambiguity_tickers": len(risk), "source_url": SOURCE_URL, "pre_move_source_url": PRE_MOVE_URL,
        "historical_html_sha256": hashlib.sha256(args.historical_html.read_bytes()).hexdigest(),
        "pre_move_html_sha256": hashlib.sha256(args.pre_move_html.read_bytes()).hexdigest(),
        "reconstruction_label": "best_effort_public_membership_history_not_licensed_security_master",
    }
    (args.processed_dir / "phase7a_membership_source_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
