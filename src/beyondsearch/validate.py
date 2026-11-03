"""Step 2 (data understanding): checks that must pass before any analysis runs.

Errors stop the run. Warnings and info are written to the run report so nothing is hidden.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .errors import DataError


@dataclass
class Finding:
    level: str            # ERROR | WARN | INFO
    check: str
    message: str
    count: int = 0
    examples: list = field(default_factory=list)


@dataclass
class ValidationReport:
    findings: list[Finding] = field(default_factory=list)

    def add(self, level, check, message, count=0, examples=None):
        self.findings.append(Finding(level, check, message, int(count), list(examples or [])[:5]))

    @property
    def errors(self):
        return [f for f in self.findings if f.level == "ERROR"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {"ok": self.ok, "findings": [f.__dict__ for f in self.findings]}

    def raise_if_errors(self) -> None:
        if self.errors:
            lines = "; ".join(f"{f.check}: {f.message}" for f in self.errors)
            raise DataError(f"Data validation failed ({len(self.errors)} error(s)): {lines}")


def validate_inputs(cfg, rl: pd.DataFrame, panel: pd.DataFrame, sched: pd.DataFrame) -> ValidationReport:
    r, c, sch = ValidationReport(), cfg["columns"], cfg["schema"]
    rid, pid, eng, st, txt = c["record_id"], c["prompt_id"], c["engine"], c["status"], c["text"]

    # 1. structure
    for name, df, req in (("response_log", rl, sch["response_log_required"]), ("prompt_panel", panel, sch["panel_required"]),
                          ("run_schedule", sched, sch["schedule_required"])):
        missing = [x for x in req if x not in df.columns]
        if missing:
            r.add("ERROR", f"{name}.columns", f"missing columns {missing}", len(missing))
    if not r.ok:
        return r                                     # later checks need these columns

    # 2. keys and duplicates
    for col in sch["key_columns_not_blank"]:
        n = rl[col].isna().sum()
        if n:
            r.add("ERROR", "blank_key", f"response_log has {n} blank '{col}'", n, rl.index[rl[col].isna()].tolist())
    dup = rl[rid][rl[rid].duplicated()]
    if len(dup):
        r.add("ERROR", "duplicate_run_id", "duplicate run_id in response_log", len(dup), dup.tolist())
    dup_p = panel[pid][panel[pid].duplicated()]
    if len(dup_p):
        r.add("ERROR", "duplicate_prompt_id", "duplicate prompt_id in prompt panel", len(dup_p), dup_p.tolist())

    # 3. links between tables
    bad_prompt = set(rl[pid].dropna()) - set(panel[pid])
    if bad_prompt:
        r.add("ERROR", "unknown_prompt", "prompt_id not in the prompt panel", len(bad_prompt), sorted(bad_prompt))
    bad_run = set(rl[rid].dropna()) - set(sched[rid])
    if bad_run:
        r.add("ERROR", "unplanned_run", "run_id not in the run schedule", len(bad_run), sorted(bad_run))
    m = rl.merge(sched, on=rid, suffixes=("", "_plan"))
    mism = m[(m[pid] != m[f"{pid}_plan"]) | (m[eng] != m[f"{eng}_plan"])]
    if len(mism):
        r.add("ERROR", "schedule_mismatch", "prompt or engine differs from the schedule", len(mism), mism[rid].tolist())
    if c["collector"] in sched.columns and f"{c['collector']}_plan" in m.columns:
        diff = m[m[c["collector"]] != m[f"{c['collector']}_plan"]]
        if len(diff):
            r.add("WARN", "collector_differs", "collector differs from the schedule (allowed, but note why)", len(diff))

    # 4. values
    allowed = set(cfg["statuses"]["allowed"])
    bad_status = rl[~rl[st].isin(allowed) & rl[st].notna()]
    if len(bad_status):
        r.add("ERROR", "unknown_status", f"response_status not in {sorted(allowed)}", len(bad_status), bad_status[st].unique().tolist())
    genuine = rl[rl[st].isin(cfg["statuses"]["genuine"])]
    no_text = genuine[genuine[txt].isna()]
    if len(no_text):
        r.add("WARN", "genuine_without_text", "genuine rows without answer text (excluded from analysis)", len(no_text), no_text[rid].tolist())
    for col in ("memory_personalisation_off", "logged_in", "model_label_shown"):
        if col in rl.columns:
            n = rl[col].isna().sum()
            if n:
                r.add("WARN", "setting_not_recorded", f"'{col}' is blank for {n} rows (blank means not recorded, not no)", n)
    if txt in rl.columns:
        n = rl[txt].astype(str).str.contains(r"&#x[0-9a-fA-F]+;|&amp;|&nbsp;", regex=True).sum()
        if n:
            r.add("INFO", "html_entities", "answer text contains HTML codes such as &#x20; (harmless for the rules used)", n)

    # 5. coverage
    r.add("INFO", "progress", f"{len(rl)} answers logged of {len(sched)} planned ({len(rl) / max(len(sched), 1):.0%})", len(rl))
    return r
