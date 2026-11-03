"""Quick data profile for ANY csv (a stock-market file, a machine log, survey data...). Same four checks every time:
size, missing values, duplicates, and types, so a new dataset can be understood before it is analysed."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .iotools import write_text


def profile_markdown(df: pd.DataFrame, name: str = "dataset") -> str:
    lines = [f"# Data profile: {name}", "", f"- Rows: {len(df)}  |  Columns: {df.shape[1]}", f"- Fully duplicated rows: {int(df.duplicated().sum())}", "",
             "| column | type | missing | missing % | distinct | example |", "|---|---|---|---|---|---|"]
    for col in df.columns:
        s = df[col]
        ex = s.dropna().iloc[0] if s.notna().any() else ""
        lines.append(f"| {col} | {s.dtype} | {int(s.isna().sum())} | {s.isna().mean():.0%} | {s.nunique(dropna=True)} | {str(ex)[:40]!r} |")
    num = df.select_dtypes("number")
    if not num.empty:
        lines += ["", "## Numeric columns", "", num.describe().T.round(3).to_markdown() if _has_tabulate() else num.describe().T.round(3).to_string()]
    return "\n".join(lines) + "\n"


def _has_tabulate() -> bool:
    try:
        import tabulate  # noqa: F401
        return True
    except ImportError:
        return False


def profile_file(path: Path, out: Path | None = None) -> str:
    df = pd.read_csv(path) if str(path).lower().endswith(".csv") else pd.read_excel(path)
    text = profile_markdown(df, Path(path).name)
    if out:
        write_text(out, text)
    return text
