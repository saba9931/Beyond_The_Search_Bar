from pathlib import Path

import pytest
import yaml

from beyondsearch.config import Config

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "beauty_india.yaml"


@pytest.fixture(scope="session")
def repo_root():
    return ROOT


@pytest.fixture()
def cfg():
    """The real configuration."""
    return Config.load(CONFIG)


@pytest.fixture()
def tmp_cfg(tmp_path):
    """Real inputs, but outputs and logs go to a temporary folder so tests never touch the repository."""
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    raw["paths"]["output_dir"] = str(tmp_path / "outputs")
    raw["paths"]["log_dir"] = str(tmp_path / "logs")
    p = tmp_path / "cfg" / "test.yaml"
    p.parent.mkdir()
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return Config.load(p, root=ROOT)
