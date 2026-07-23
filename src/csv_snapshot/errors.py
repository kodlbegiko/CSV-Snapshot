"""Domain errors surfaced by the CLI without tracebacks."""


class CsvSnapshotError(Exception):
    """Base class for expected CSV Snapshot failures."""


class CsvInputError(CsvSnapshotError):
    """The CSV cannot be parsed safely or consistently."""


class ConfigurationError(CsvSnapshotError):
    """The configuration is invalid."""


class OutputError(CsvSnapshotError):
    """An output path or write operation is unsafe or invalid."""


class SnapshotError(CsvSnapshotError):
    """A snapshot is invalid or unsupported."""
