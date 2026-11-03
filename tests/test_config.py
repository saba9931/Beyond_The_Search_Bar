import pytest
import yaml

from beyondsearch.config import Config
from beyondsearch.errors import ConfigError


def _write(tmp_path, raw):
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


def test_real_config_loads(cfg):
    assert cfg.focal == "sephora" and cfg.comparator == "nykaa" and len(cfg.sha256) == 64
    assert cfg.path("response_log").name == "response_log.csv"


def test_missing_file():
    with pytest.raises(ConfigError):
        Config.load("does_not_exist.yaml")


def test_missing_section(cfg, tmp_path):
    raw = dict(cfg.raw); raw.pop("entities")
    with pytest.raises(ConfigError, match="missing sections"):
        Config.load(_write(tmp_path, raw))


def test_unknown_focal_entity(cfg, tmp_path):
    raw = dict(cfg.raw); raw["focal"] = "nobody"
    with pytest.raises(ConfigError, match="focal"):
        Config.load(_write(tmp_path, raw))


def test_duplicate_hypothesis_id(cfg, tmp_path):
    raw = dict(cfg.raw); raw["hypotheses"] = raw["hypotheses"] + [raw["hypotheses"][0]]
    with pytest.raises(ConfigError, match="unique"):
        Config.load(_write(tmp_path, raw))
