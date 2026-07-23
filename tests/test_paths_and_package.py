from pathlib import Path, PurePosixPath, PureWindowsPath

from csv_snapshot.config import AppConfig
from csv_snapshot.profiling import profile_csv


def test_windows_path_shape() -> None:
    path = PureWindowsPath(r"C:\data\export.csv")
    assert path.name == "export.csv"


def test_posix_path_shape() -> None:
    path = PurePosixPath("/data/export.csv")
    assert path.name == "export.csv"


def test_source_saves_filename_only(tmp_path: Path) -> None:
    nested = tmp_path / "private" / "home" / "data.csv"
    nested.parent.mkdir(parents=True)
    nested.write_text("id\n1\n", encoding="utf-8")
    snapshot = profile_csv(nested, AppConfig())
    assert snapshot.source.file_name == "data.csv"
    assert str(tmp_path) not in snapshot.source.file_name
