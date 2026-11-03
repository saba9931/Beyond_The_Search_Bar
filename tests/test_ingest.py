import pandas as pd
import pytest
from openpyxl import Workbook

from beyondsearch.errors import DataError
from beyondsearch.ingest import merge_workbook


def _workbook(path):
    wb = Workbook()
    ws = wb.active; ws.title = "response_log"
    ws.append(["run_id", "collector", "engine", "prompt_text", "full_response_text", "citation_urls", "response_status", "run_date", "x (auto)"])
    ws.append(["S1", "Saba", "chatgpt", "q", "answer one", "https://nykaa.com/a", "valid", "2026-10-01", "drop me"])
    ws.append(["S2", "Saba", "gemini", "q", "answer two", None, "api_run", "2026-10-02", "drop me"])
    ws.append(["S3", "Saba", "gemini", "q", None, None, None, None, None])        # not filled in: must be ignored
    st = wb.create_sheet("settings")
    st.append(["collector", "engine", "model_label_shown", "memory_personalisation_off", "logged_in"])
    st.append(["Saba", "chatgpt", "GPT", "yes", "yes"])
    wb.save(path)


def test_merge_maps_status_to_method_and_drops_unfilled_rows(cfg, tmp_path):
    p = tmp_path / "w.xlsx"; _workbook(p)
    df, info = merge_workbook(p, cfg)
    assert list(df["run_id"]) == ["S1", "S2"]
    assert list(df["collection_method"]) == ["single_chat", "api"]
    assert list(df["fresh_chat"]) == ["yes", "n/a"]
    assert list(df["web_search_used"]) == ["yes", "unknown"]
    assert "run_datetime_ist" in df.columns and "prompt_text" not in df.columns and "x (auto)" not in df.columns
    assert info["rows_in_sheet"] == 3 and info["rows_written"] == 2
    assert {"collector": "Saba", "engine": "gemini"} in info["settings_missing_for"]


def test_missing_workbook_gives_clear_error(cfg, tmp_path):
    with pytest.raises(DataError, match="not found"):
        merge_workbook(tmp_path / "nope.xlsx", cfg)


def test_merge_reproduces_the_saved_response_log(cfg):
    """Golden check: the raw workbook in the repo must rebuild exactly the cleaned csv in the repo."""
    df, _ = merge_workbook(cfg.path("raw_workbook"), cfg)
    saved = pd.read_csv(cfg.path("response_log"), dtype=str)
    mine = pd.read_csv(pd.io.common.StringIO(df.to_csv(index=False)), dtype=str)
    assert list(mine.columns) == list(saved.columns)
    pd.testing.assert_frame_equal(mine, saved)
