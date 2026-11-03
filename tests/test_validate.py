import pandas as pd
import pytest

from beyondsearch.errors import DataError
from beyondsearch.iotools import read_csv_checked
from beyondsearch.validate import validate_inputs


@pytest.fixture()
def data(cfg):
    return (read_csv_checked(cfg.path("response_log")), read_csv_checked(cfg.path("prompt_panel")), read_csv_checked(cfg.path("run_schedule")))


def levels(report, check):
    return [f.level for f in report.findings if f.check == check]


def test_real_data_passes(cfg, data):
    assert validate_inputs(cfg, *data).ok


def test_duplicate_run_id_is_an_error(cfg, data):
    rl, panel, sched = data
    rl = pd.concat([rl, rl.iloc[[0]]], ignore_index=True)
    assert "ERROR" in levels(validate_inputs(cfg, rl, panel, sched), "duplicate_run_id")


def test_unknown_prompt_is_an_error(cfg, data):
    rl, panel, sched = data
    rl = rl.copy(); rl.loc[0, "prompt_id"] = "NOPE"
    assert "ERROR" in levels(validate_inputs(cfg, rl, panel, sched), "unknown_prompt")


def test_unknown_status_is_an_error(cfg, data):
    rl, panel, sched = data
    rl = rl.copy(); rl.loc[0, "response_status"] = "weird"
    assert "ERROR" in levels(validate_inputs(cfg, rl, panel, sched), "unknown_status")


def test_missing_column_stops_early(cfg, data):
    rl, panel, sched = data
    rep = validate_inputs(cfg, rl.drop(columns=["engine"]), panel, sched)
    assert not rep.ok and "ERROR" in levels(rep, "response_log.columns")


def test_raise_if_errors(cfg, data):
    rl, panel, sched = data
    rep = validate_inputs(cfg, rl.drop(columns=["engine"]), panel, sched)
    with pytest.raises(DataError):
        rep.raise_if_errors()


def test_blank_values_are_warnings_not_errors(cfg, data):
    rl, panel, sched = data
    rep = validate_inputs(cfg, rl, panel, sched)
    assert "WARN" in levels(rep, "setting_not_recorded")
