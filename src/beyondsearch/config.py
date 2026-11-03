"""Load and check the YAML configuration. All dataset-specific choices live in the YAML, not in the code."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .errors import ConfigError
from .iotools import sha256_file

REQUIRED_KEYS = ["project", "data_version", "seed", "paths", "columns", "schema", "statuses",
                 "entities", "focal", "comparator", "analysis", "hypotheses", "narrative"]
REQUIRED_PATHS = ["response_log", "prompt_panel", "run_schedule", "output_dir", "log_dir"]
REQUIRED_COLUMNS = ["record_id", "prompt_id", "text", "urls", "status", "engine", "category", "intent", "collector", "method"]


@dataclass(frozen=True)
class Config:
    raw: dict
    root: Path          # repository root; every relative path in the YAML is resolved against it
    source: Path        # the YAML file that was loaded
    sha256: str         # fingerprint of that YAML, written into every run manifest

    @classmethod
    def load(cls, path: str | Path, root: str | Path | None = None) -> "Config":
        path = Path(path).resolve()
        if not path.exists():
            raise ConfigError(f"Configuration file not found: {path}")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ConfigError(f"Configuration is not valid YAML ({path.name}): {exc}") from exc
        if not isinstance(raw, dict):
            raise ConfigError(f"Configuration {path.name} must be a YAML mapping")
        cfg = cls(raw=raw, root=Path(root).resolve() if root else path.parent.parent, source=path, sha256=sha256_file(path))
        cfg._check()
        return cfg

    # --- convenience accessors -------------------------------------------------------------
    def __getitem__(self, key):
        return self.raw[key]

    def get(self, key, default=None):
        return self.raw.get(key, default)

    def path(self, key: str) -> Path:
        return (self.root / self.raw["paths"][key]).resolve()

    def col(self, key: str) -> str:
        return self.raw["columns"][key]

    @property
    def focal(self) -> str:
        return self.raw["focal"]

    @property
    def comparator(self) -> str:
        return self.raw["comparator"]

    def label(self, entity: str) -> str:
        return self.raw["entities"][entity]["label"]

    def short(self, entity: str) -> str:
        return self.raw["entities"][entity].get("short", self.label(entity))

    # --- validation ------------------------------------------------------------------------
    def _check(self) -> None:
        missing = [k for k in REQUIRED_KEYS if k not in self.raw]
        if missing:
            raise ConfigError(f"Configuration is missing sections: {missing}")
        for group, keys in (("paths", REQUIRED_PATHS), ("columns", REQUIRED_COLUMNS)):
            gone = [k for k in keys if k not in self.raw[group]]
            if gone:
                raise ConfigError(f"Configuration section '{group}' is missing: {gone}")
        ents = self.raw["entities"]
        for role in ("focal", "comparator"):
            if self.raw[role] not in ents:
                raise ConfigError(f"'{role}' is '{self.raw[role]}' but 'entities' only has {sorted(ents)}")
        for name, e in ents.items():
            if not {"label", "pattern", "domain"} <= set(e):
                raise ConfigError(f"Entity '{name}' needs label, pattern and domain")
        ids = [h["id"] for h in self.raw["hypotheses"]]
        if len(ids) != len(set(ids)):
            raise ConfigError("Hypothesis ids must be unique")
