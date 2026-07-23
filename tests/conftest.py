from pathlib import Path

import pytest

from csv_snapshot.config import AppConfig


@pytest.fixture
def config() -> AppConfig:
    return AppConfig()


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
