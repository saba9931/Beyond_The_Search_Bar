"""Traceability: a run record that says what went in, what settings and code were used, and what came out."""
from __future__ import annotations

import platform
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from . import __version__
from .iotools import sha256_file, write_json

TRACKED_PACKAGES = ["pandas", "numpy", "scipy", "statsmodels", "matplotlib", "PyYAML", "openpyxl"]


def environment() -> dict:
    pkgs = {}
    for name in TRACKED_PACKAGES:
        try:
            pkgs[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pkgs[name] = None
    return {"python": platform.python_version(), "platform": platform.platform(), "beyondsearch": __version__, "packages": pkgs}


def git_info(root: Path) -> dict:
    """Commit of the code that produced the run. Returns None values if git is not available."""
    def run(*args):
        try:
            return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        except Exception:
            return None
    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain") if commit else None
    return {"commit": commit, "uncommitted_changes": (bool(status) if status is not None else None)}


class RunRecorder:
    """Collects inputs, steps (with timings), counters and outputs, then writes run_manifest.json."""

    def __init__(self, run_id: str, cfg, logger):
        self.run_id, self.cfg, self.log = run_id, cfg, logger
        self.started = datetime.now(timezone.utc)
        self.inputs: dict[str, dict] = {}
        self.outputs: dict[str, dict] = {}
        self.steps: list[dict] = []
        self.facts: dict = {}
        self.status = "running"

    def add_input(self, label: str, path: Path, rows: int | None = None) -> None:
        path = Path(path)
        self.inputs[label] = {"path": _rel(path, self.cfg.root), "sha256": sha256_file(path), "bytes": path.stat().st_size, "rows": rows}
        self.log.info(f"input  {label}: {self.inputs[label]['path']}  rows={rows}  sha256={self.inputs[label]['sha256'][:12]}")

    def add_output(self, label: str, path: Path) -> None:
        path = Path(path)
        self.outputs[label] = {"path": _rel(path, self.cfg.root), "sha256": sha256_file(path), "bytes": path.stat().st_size}

    def note(self, key: str, value) -> None:
        self.facts[key] = value
        self.log.info(f"fact   {key} = {value}")

    @contextmanager
    def step(self, name: str):
        self.log.info(f"START  {name}", extra={"step": name})
        t0 = time.perf_counter()
        record = {"name": name, "status": "ok"}
        try:
            yield
        except BaseException as exc:
            record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            self.log.error(f"FAILED {name}: {exc}", extra={"step": name})
            raise
        finally:
            record["seconds"] = round(time.perf_counter() - t0, 3)
            self.steps.append(record)
        self.log.info(f"DONE   {name} ({record['seconds']}s)", extra={"step": name})

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id, "status": self.status, "started_utc": self.started.isoformat(timespec="seconds"),
            "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "project": self.cfg["project"], "data_version": self.cfg["data_version"], "seed": self.cfg["seed"],
            "config": {"file": _rel(self.cfg.source, self.cfg.root), "sha256": self.cfg.sha256},
            "code": git_info(self.cfg.root), "environment": environment(),
            "inputs": self.inputs, "steps": self.steps, "facts": self.facts, "outputs": self.outputs,
        }

    def write(self, path: Path, status: str) -> Path:
        self.status = status
        return write_json(path, self.to_dict())


def _rel(path: Path, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(path)
