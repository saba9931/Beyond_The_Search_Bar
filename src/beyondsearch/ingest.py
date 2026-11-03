"""Step 1 (data preparation): turn the shared collection workbook into one clean row per answer (response_log.csv).

Replaces the old merge_runs.py script. Same logic, but: settings come from the YAML, problems are reported
instead of printed, and the output is written safely.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .errors import DataError
from .iotools import write_csv


def merge_workbook(workbook: Path, cfg, logger: logging.Logger | None = None) -> tuple[pd.DataFrame, dict]:
    ing, c = cfg["ingest"], cfg["columns"]
    workbook = Path(workbook)
    if not workbook.exists():
        raise DataError(f"Workbook not found: {workbook}")
    try:
        d = pd.read_excel(workbook, sheet_name=ing["response_sheet"], dtype=str)
        st = pd.read_excel(workbook, sheet_name=ing["settings_sheet"], dtype=str)
    except ValueError as exc:
        raise DataError(f"Workbook {workbook.name} needs sheets '{ing['response_sheet']}' and '{ing['settings_sheet']}': {exc}") from exc
    if c["status"] not in d.columns:
        raise DataError(f"Sheet '{ing['response_sheet']}' has no '{c['status']}' column")

    n_all = len(d)
    d = d[d[c["status"]].notna()]                       # only rows that were actually filled in
    n_filled = len(d)
    suffix = ing.get("drop_column_suffix", "(auto)")
    d = d.drop(columns=list(ing.get("drop_columns", [])) + [col for col in d.columns if col.endswith(suffix)], errors="ignore")
    d = d.merge(st, on=ing["join_keys"], how="left")
    d["fresh_chat"] = d[c["status"]].map(ing["fresh_chat_by_status"]).fillna("n/a")
    d[c["method"]] = d[c["status"]].map(ing["method_by_status"]).fillna("other")
    d["web_search_used"] = d[c["urls"]].notna().map({True: "yes", False: "unknown"})
    d = d.rename(columns=ing.get("rename", {}))

    needed = [x for x in ("model_label_shown", "memory_personalisation_off", "logged_in") if x in d.columns]
    miss = d[d[needed].isna().any(axis=1)][ing["join_keys"]].drop_duplicates() if needed else pd.DataFrame()
    info = {"rows_in_sheet": n_all, "rows_filled": n_filled, "rows_written": len(d),
            "settings_missing_for": miss.to_dict("records")}
    if logger:
        logger.info(f"ingest: {n_all} rows in sheet, {n_filled} filled, {len(d)} written")
        if len(miss):
            logger.warning(f"fill the '{ing['settings_sheet']}' sheet for: {info['settings_missing_for']}")
    return d.reset_index(drop=True), info


def write_response_log(df: pd.DataFrame, cfg) -> Path:
    return write_csv(cfg.path("response_log"), df)
