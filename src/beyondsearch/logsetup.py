"""Observability: one readable console log and one machine-readable log file per run."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path


def make_run_id(*fingerprints: str) -> str:
    """UTC time + a short fingerprint of the inputs and config, e.g. 20261103T101500Z-3fa9c2d1."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = hashlib.sha256("|".join(fingerprints).encode()).hexdigest()[:8]
    return f"{stamp}-{short}"


class _JsonLines(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="seconds"),
                   "level": record.levelname, "step": getattr(record, "step", None), "message": record.getMessage()}
        extra = getattr(record, "data", None)
        if extra:
            payload["data"] = extra
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(run_id: str, log_dir: Path | None, verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger(f"beyondsearch.{run_id}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.handlers.clear()
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%H:%M:%S"))
    logger.addHandler(console)
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / f"{run_id}.jsonl", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(_JsonLines())
        logger.addHandler(fh)
    return logger
