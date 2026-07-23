# Contributing

1. Create a focused branch from `main`.
2. Install development dependencies with `python -m pip install -e ".[dev]"`.
3. Add deterministic fixtures containing synthetic data only.
4. Run `ruff check .`, `ruff format --check .`, `mypy src`, `pytest --cov=csv_snapshot --cov-branch`, `python -m build`, and `twine check dist/*`.
5. Explain metric semantics, privacy effects, compatibility, and tests in the pull request.

Do not add real personal data, secrets, network-dependent tests, random sampling, locale-dependent parsing, or changes that persist raw CSV values in snapshots.
