"""End-to-end checks: results match the saved golden results, runs are repeatable, failures leave a trace."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from beyondsearch.errors import DataError
from beyondsearch.pipeline import run_pipeline

GOLDEN = Path(__file__).parent / "golden"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_results_match_golden(tmp_cfg):
    run_pipeline(tmp_cfg, make_pdf=False)
    got = json.loads((tmp_cfg.path("output_dir") / "results.json").read_text())
    want = json.loads((GOLDEN / "results_data_v0.9.json").read_text())
    assert got == want


def test_refactor_reproduces_the_original_d3_insight_log(tmp_cfg):
    """The original D3 submission (before the refactor) is the reference: evidence, figure and confidence must be identical."""
    run_pipeline(tmp_cfg, make_pdf=False)
    new = pd.read_csv(tmp_cfg.path("output_dir") / "insight_log.csv")
    old = pd.read_csv(GOLDEN / "insight_log_d3_v1.csv")
    for col in ("hypothesis", "insight (evidence)", "figure", "confidence"):
        assert list(new[col]) == list(old[col]), col
    diff = [i for i in range(len(old)) if old.loc[i, "so what for the decision"] != new.loc[i, "so what for the decision"]]
    assert diff == [0]                       # only H1: "about three times" is now computed ("about 3.0 times")
    assert new.loc[0, "so what for the decision"].startswith("Nykaa is named about 3.0 times as often as Sephora India.")


def test_two_runs_give_identical_outputs(tmp_cfg, tmp_path):
    out1, out2 = tmp_path / "a", tmp_path / "b"
    run_pipeline(tmp_cfg, out_dir=out1, make_pdf=False)
    run_pipeline(tmp_cfg, out_dir=out2, make_pdf=False)
    names = ["results.json", "insight_log.csv", "validation.json", "excluded_rows.csv", "summary.html"] + [f"tables/{p.name}" for p in (out1 / "tables").glob("*.csv")]
    for n in names:
        assert sha(out1 / n) == sha(out2 / n), n


def test_inputs_are_never_modified(tmp_cfg):
    paths = [tmp_cfg.path(k) for k in ("response_log", "prompt_panel", "run_schedule")]
    before = [sha(p) for p in paths]
    run_pipeline(tmp_cfg, make_pdf=False)
    assert [sha(p) for p in paths] == before


def test_manifest_records_inputs_outputs_and_settings(tmp_cfg):
    run_pipeline(tmp_cfg, make_pdf=False)
    m = json.loads((tmp_cfg.path("output_dir") / "run_manifest.json").read_text())
    assert m["status"] == "ok" and m["seed"] == 42 and m["config"]["sha256"] == tmp_cfg.sha256
    assert set(m["inputs"]) == {"response_log", "prompt_panel", "run_schedule"} and all(len(v["sha256"]) == 64 for v in m["inputs"].values())
    assert "results" in m["outputs"] and [s["name"] for s in m["steps"]] == ["load inputs", "validate data", "analyse", "save outputs"]
    assert list(tmp_cfg.path("log_dir").glob("*_manifest.json")) and list(tmp_cfg.path("log_dir").glob("*.jsonl"))


def test_bad_data_fails_clearly_and_still_writes_a_manifest(tmp_cfg, tmp_path):
    bad = pd.read_csv(tmp_cfg.path("response_log"))
    bad = pd.concat([bad, bad.iloc[[0]]], ignore_index=True)            # duplicate run_id
    bad_path = tmp_path / "bad.csv"; bad.to_csv(bad_path, index=False)
    cfg_bad = type(tmp_cfg)(raw={**tmp_cfg.raw, "paths": {**tmp_cfg.raw["paths"], "response_log": str(bad_path)}}, root=tmp_cfg.root, source=tmp_cfg.source, sha256=tmp_cfg.sha256)
    with pytest.raises(DataError, match="duplicate"):
        run_pipeline(cfg_bad, make_pdf=False)
    m = json.loads((cfg_bad.path("output_dir") / "run_manifest.json").read_text())
    assert m["status"] == "failed" and any(s["status"] == "failed" for s in m["steps"])
    assert not (cfg_bad.path("output_dir") / "results.json").exists()   # no misleading results from bad data


def test_missing_input_file_gives_clear_message(tmp_cfg, tmp_path):
    cfg2 = type(tmp_cfg)(raw={**tmp_cfg.raw, "paths": {**tmp_cfg.raw["paths"], "prompt_panel": str(tmp_path / "nope.csv")}}, root=tmp_cfg.root, source=tmp_cfg.source, sha256=tmp_cfg.sha256)
    with pytest.raises(DataError, match="not found"):
        run_pipeline(cfg2, make_pdf=False)
