"""Safe file helpers. Reliability rule: never leave a half-written output behind and never overwrite an input."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import pandas as pd

from .errors import DataError


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    """Write to a temporary file in the same folder, then rename. A crash never leaves a broken file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_text(path: str | Path, text: str) -> Path:
    path = Path(path)
    _atomic_write(path, text.encode("utf-8"))
    return path


def write_json(path: str | Path, obj) -> Path:
    """Stable JSON (sorted keys, fixed indent) so two identical runs give byte-identical files."""
    return write_text(path, json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")


def write_csv(path: str | Path, df: pd.DataFrame) -> Path:
    return write_text(path, df.to_csv(index=False, lineterminator="\n"))


def read_csv_checked(path: str | Path, required: list[str] | None = None, label: str = "file") -> pd.DataFrame:
    """Read a CSV and fail with a clear message if it is missing or lacks required columns."""
    path = Path(path)
    if not path.exists():
        raise DataError(f"{label} not found: {path}. Check 'paths' in the configuration.")
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - pandas gives several different errors
        raise DataError(f"{label} could not be read ({path}): {exc}") from exc
    missing = [c for c in (required or []) if c not in df.columns]
    if missing:
        raise DataError(f"{label} {path.name} is missing columns {missing}. Columns found: {list(df.columns)}")
    return df
