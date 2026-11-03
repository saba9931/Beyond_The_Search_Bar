"""The full run in one place: validate -> analyse -> save, with logging and a manifest.

Idempotent: running it again on the same data and settings gives byte-identical results.json and tables.
Safe: inputs are never modified; outputs are written atomically; a failed run still writes its manifest.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .analysis import run_analysis
from .errors import BeyondSearchError
from .iotools import read_csv_checked, write_text
from .logsetup import make_run_id, setup_logging
from .manifest import RunRecorder
from .report import run_report_md, save_outputs
from .validate import validate_inputs


def run_pipeline(cfg, out_dir: Path | None = None, make_pdf: bool = True, verbose: bool = False):
    out_dir = Path(out_dir) if out_dir else cfg.path("output_dir")
    log_dir = cfg.path("log_dir")
    fingerprints = [cfg.sha256] + [_safe_hash(cfg.path(k)) for k in ("response_log", "prompt_panel", "run_schedule")]
    run_id = make_run_id(*fingerprints)
    logger = setup_logging(run_id, log_dir, verbose)
    rec = RunRecorder(run_id, cfg, logger)
    logger.info(f"run {run_id} | {cfg['project']} | data {cfg['data_version']} | output {out_dir}")
    status, validation = "failed", None
    try:
        with rec.step("load inputs"):
            rl = read_csv_checked(cfg.path("response_log"), cfg["schema"]["response_log_required"], "response_log")
            panel = read_csv_checked(cfg.path("prompt_panel"), cfg["schema"]["panel_required"], "prompt_panel")
            sched = read_csv_checked(cfg.path("run_schedule"), cfg["schema"]["schedule_required"], "run_schedule")
            for label, key, df in (("response_log", "response_log", rl), ("prompt_panel", "prompt_panel", panel), ("run_schedule", "run_schedule", sched)):
                rec.add_input(label, cfg.path(key), len(df))
        with rec.step("validate data"):
            validation = validate_inputs(cfg, rl, panel, sched)
            for f in validation.findings:
                getattr(logger, {"ERROR": "error", "WARN": "warning"}.get(f.level, "info"))(f"[{f.check}] {f.message} ({f.count})")
            validation.raise_if_errors()
        with rec.step("analyse"):
            res = run_analysis(cfg, rl, panel, sched, logger)
            rec.note("rows_usable", res.counts["rows_usable"])
            rec.note("rows_excluded", res.counts["rows_excluded"])
            rec.note("primary_sample", res.counts["primary_n"])
        with rec.step("save outputs"):
            files = save_outputs(cfg, res, validation, out_dir, make_pdf=make_pdf, logger=logger)
            for label, path in files.items():
                rec.add_output(label, path)
        status = "ok"
        return res, validation, rec
    except BeyondSearchError:
        raise
    finally:
        manifest_path = out_dir / "run_manifest.json"
        rec.write(manifest_path, status)
        write_text(out_dir / "run_report.md", run_report_md(rec.to_dict(), validation) if validation else f"# Run {run_id} failed before validation finished\n")
        shutil.copyfile(manifest_path, Path(log_dir) / f"{run_id}_manifest.json")   # keep a copy of every run's record
        logger.info(f"run {run_id} finished with status {status}; manifest: {manifest_path}")


def _safe_hash(path: Path) -> str:
    from .iotools import sha256_file
    try:
        return sha256_file(path)
    except OSError:
        return "missing"
