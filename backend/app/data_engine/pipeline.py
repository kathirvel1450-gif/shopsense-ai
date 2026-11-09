"""Repeatable data engineering workflow for supplied raw CSV files."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from app.data_engine.cleaning import CleaningStrategy, clean_dataframe, detect_numeric_outliers
from app.data_engine.eda import generate_eda
from app.data_engine.ingestion import discover_datasets, load_available
from app.data_engine.profiling import profile_dataframe, write_profile
from app.data_engine.validation import relationship_candidates, validate_dataframe
from app.database.connection import get_engine
from app.database.repository import replace_datasets, validate_database


def project_root() -> Path:
    """Return repository root from this module location."""
    return Path(__file__).resolve().parents[3]


def configured_paths() -> dict[str, Path]:
    """Resolve configurable raw, processed, and output locations."""
    root = project_root()
    load_dotenv(root / ".env", override=False)

    def resolve_configured(name: str, default: Path) -> Path:
        value = os.getenv(name)
        if not value:
            return default.resolve()
        path = Path(value)
        return (path if path.is_absolute() else root / path).resolve()

    return {
        "raw": resolve_configured("SHOPSENSE_RAW_DIR", root / "datasets" / "raw"),
        "processed": resolve_configured("SHOPSENSE_PROCESSED_DIR", root / "datasets" / "processed"),
        "outputs": resolve_configured("SHOPSENSE_OUTPUTS_DIR", root / "outputs"),
    }


def run_pipeline(
    raw_dir: Path | None = None,
    processed_dir: Path | None = None,
    outputs_dir: Path | None = None,
    strategy: CleaningStrategy | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    """Profile, clean, validate, chart, and store discovered CSVs.

    Raw files are never modified. If no CSVs are available, reports that fact and
    leaves SQLite untouched rather than inventing rows or an empty schema.
    """
    paths = configured_paths()
    raw_dir = Path(raw_dir or paths["raw"])
    processed_dir = Path(processed_dir or paths["processed"])
    outputs_dir = Path(outputs_dir or paths["outputs"])
    reports_dir = outputs_dir / "reports"
    visualizations_dir = outputs_dir / "visualizations"
    for directory in (processed_dir, reports_dir, visualizations_dir):
        directory.mkdir(parents=True, exist_ok=True)

    availability = discover_datasets(raw_dir)
    _write_json(reports_dir / "dataset_availability.json", _safe_availability(availability))
    frames, errors = load_available(raw_dir)
    if not frames:
        report = {
            "status": "missing_inputs" if not errors else "input_errors",
            "message": "No readable CSV datasets found. Expected customers.csv, orders.csv, and tickets.csv; provide trainer files in the configured raw directory.",
            "missing_files": availability["missing"],
            "available_files": [],
            "load_errors": errors,
            "datasets": {},
            "database": {"created_or_updated": False, "reason": "No readable input data."},
            "eda": {"chart_count": 0, "charts": []},
        }
        _write_json(reports_dir / "pipeline_report.json", report)
        return report

    reports: dict[str, Any] = {}
    clean_frames: dict[str, pd.DataFrame] = {}
    cleaning_log: list[dict[str, Any]] = []
    dataset_validation: dict[str, Any] = {}
    for name, frame in frames.items():
        profile = profile_dataframe(frame, name)
        write_profile(profile, reports_dir / f"{name}_profiling.json")
        cleaned, events = clean_dataframe(frame, name, strategy)
        cleaned.to_csv(processed_dir / f"{name}.csv", index=False)
        cleaning_log.extend(events)
        outliers = detect_numeric_outliers(cleaned)
        dataset_validation[name] = validate_dataframe(name, cleaned)
        reports[name] = {
            "source_rows": int(len(frame)), "cleaned_rows": int(len(cleaned)),
            "source_columns": int(len(frame.columns)), "cleaned_columns": int(len(cleaned.columns)),
            "removed_exact_duplicate_rows": sum(int(e.get("rows_affected", 0)) for e in events if e.get("operation") == "drop_exact_duplicates"),
            "cleaning_operations": events, "numeric_outliers": outliers,
        }
        clean_frames[name] = cleaned
    _write_json(reports_dir / "cleaning_log.json", {"operations": cleaning_log, "operation_count": len(cleaning_log)})
    _write_json(reports_dir / "validation.json", {"datasets": dataset_validation, "relationship_candidates": relationship_candidates(clean_frames)})
    eda_report = generate_eda(clean_frames, visualizations_dir)
    database_report: dict[str, Any]
    engine = get_engine(database_url)
    try:
        insertion = replace_datasets(engine, clean_frames)
        validation = validate_database(engine)
        database_report = {"created_or_updated": True, **insertion, "validation": validation}
    except Exception as exc:
        database_report = {"created_or_updated": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        engine.dispose()
    report = {
        "status": "complete" if not errors and database_report.get("created_or_updated") and database_report.get("validation", {}).get("valid", False) else "completed_with_warnings",
        "message": "Processed only readable CSV files found in the raw directory.",
        "missing_files": availability["missing"], "available_files": [f"{name}.csv" for name in frames],
        "load_errors": errors, "datasets": reports, "validation": dataset_validation,
        "relationship_candidates": relationship_candidates(clean_frames),
        "database": database_report, "eda": eda_report,
        "reports_directory": str(reports_dir), "processed_directory": str(processed_dir),
    }
    _write_json(reports_dir / "pipeline_report.json", report)
    return report


def _safe_availability(data: dict[str, Any]) -> dict[str, Any]:
    """Avoid exposing absolute local paths in saved/API availability reports."""
    return {key: value for key, value in data.items() if key not in {"raw_directory", "discovered"}}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, (Path, pd.Timestamp)):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")
