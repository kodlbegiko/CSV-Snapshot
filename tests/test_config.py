from pathlib import Path

import pytest

from csv_snapshot.config import AppConfig, DEFAULT_CONFIG, discover_config, load_config
from csv_snapshot.errors import ConfigurationError


def test_default_config() -> None:
    config = AppConfig()
    assert config.snapshot.delimiter == ","
    assert config.thresholds.null_rate_absolute_change == 0.05


def test_load_valid_config(tmp_path: Path) -> None:
    path = tmp_path / "csv-snapshot.toml"
    path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    config = load_config(path)
    assert config.comparison.removed_columns == "error"


def test_discover_config(tmp_path: Path) -> None:
    assert discover_config(tmp_path) is None
    path = tmp_path / "csv-snapshot.toml"
    path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    assert discover_config(tmp_path) == path


def test_missing_config(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_config(tmp_path / "missing.toml")


def test_malformed_toml(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("[broken", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="invalid TOML"):
        load_config(path)


@pytest.mark.parametrize(
    "content",
    [
        "[snapshot]\ndelimiter = '||'\n",
        "[comparison]\nremoved_columns = 'critical'\n",
        "[thresholds]\nnull_rate_absolute_change = 2\n",
        "[columns.age]\nmin = 10\nmax = 1\n",
        "[unknown]\nvalue = 1\n",
    ],
)
def test_invalid_config_values(tmp_path: Path, content: str) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigurationError, match="invalid configuration"):
        load_config(path)


def test_column_rules_load(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        "[columns.age]\ntype='integer'\nnullable=true\nmin=0\nmax=130\nmax_null_rate=0.1\n",
        encoding="utf-8",
    )
    rule = load_config(path).columns["age"]
    assert rule.type == "integer"
    assert rule.max == 130
