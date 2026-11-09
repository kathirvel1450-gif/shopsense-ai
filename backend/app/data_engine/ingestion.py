"""Configurable CSV discovery and loading without assuming a fixed schema."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_FILES = ("customers.csv", "orders.csv", "tickets.csv")


def discover_datasets(raw_dir: Path) -> dict[str, Any]:
    """Return expected-file availability and discovered CSV paths."""
    raw_dir = Path(raw_dir)
    paths = sorted(raw_dir.glob("*.csv")) if raw_dir.exists() else []
    found = {path.stem.lower(): path for path in paths}
    return {
        "raw_directory": str(raw_dir),
        "available": {name: (raw_dir / name).is_file() for name in EXPECTED_FILES},
        "missing": [name for name in EXPECTED_FILES if not (raw_dir / name).is_file()],
        "discovered": [str(path) for path in paths],
        "dataset_count": len(paths),
        "dataset_names": sorted(found),
    }


def load_csv(path: Path, **read_csv_options: Any) -> pd.DataFrame:
    """Load one CSV as a DataFrame, raising an actionable error on failure."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file does not exist: {path}")
    try:
        return pd.read_csv(path, **read_csv_options)
    except (pd.errors.ParserError, UnicodeDecodeError, OSError, ValueError) as exc:
        raise ValueError(f"Could not read CSV '{path}': {exc}") from exc


def load_available(raw_dir: Path) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Load all CSVs found in raw_dir, preserving filename stems as keys."""
    frames: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    if not Path(raw_dir).exists():
        return frames, errors
    for path in sorted(Path(raw_dir).glob("*.csv")):
        try:
            frames[path.stem.lower()] = load_csv(path)
        except ValueError as exc:
            errors[path.name] = str(exc)
    return frames, errors
