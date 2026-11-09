"""System and data-engineering API routes."""
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.data_engine.cleaning import CleaningStrategy
from app.data_engine.eda import generate_eda
from app.data_engine.ingestion import discover_datasets, load_available
from app.data_engine.pipeline import configured_paths, run_pipeline
from app.data_engine.profiling import profile_dataframe, write_profile
from app.database.connection import default_database_url, get_engine
from app.database.repository import database_statistics

router = APIRouter()


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return a lightweight liveness response for the UI and operators."""
    return {"status": "ok", "service": "shopsense-ai-api"}


class CleaningRequest(BaseModel):
    """Optional user-approved cleaning rules for this pipeline execution."""
    drop_exact_duplicates: bool = True
    city_aliases: dict[str, str] = Field(default_factory=dict)
    missing_rules: dict[str, dict[str, dict[str, Any]]] = Field(default_factory=dict)
    impossible_numeric_min: dict[str, float] = Field(default_factory=dict)
    date_columns: list[str] = Field(default_factory=list)
    infer_numeric_columns: bool = True


@router.get("/datasets/availability", tags=["data engineering"])
def dataset_availability() -> dict[str, Any]:
    """List which expected source files exist, without returning local paths."""
    data = discover_datasets(configured_paths()["raw"])
    return {key: value for key, value in data.items() if key not in {"raw_directory", "discovered"}}


@router.get("/data/profiling", tags=["data engineering"])
def data_profiling() -> dict[str, Any]:
    """Profile available CSVs; direct identifiers and their values are suppressed."""
    paths = configured_paths()
    frames, errors = load_available(paths["raw"])
    profiles = {}
    for name, frame in frames.items():
        report = profile_dataframe(frame, name)
        write_profile(report, paths["outputs"] / "reports" / f"{name}_profiling.json")
        profiles[name] = report
    return {"status": "complete" if profiles and not errors else "missing_inputs" if not profiles else "completed_with_warnings", "datasets": profiles, "load_errors": errors, "missing_files": discover_datasets(paths["raw"])["missing"]}


@router.post("/data/cleaning", tags=["data engineering"])
def data_cleaning(request: CleaningRequest | None = None) -> dict[str, Any]:
    """Run configured cleaning, audit, EDA, and database loading for source CSVs."""
    values = request.model_dump() if request else {}
    strategy = CleaningStrategy(**values)
    return run_pipeline(strategy=strategy)


@router.get("/data/eda", tags=["data engineering"])
def data_eda() -> dict[str, Any]:
    """Generate schema-available EDA charts and return chart names, not data rows."""
    paths = configured_paths()
    frames, errors = load_available(paths["raw"])
    result = generate_eda(frames, paths["outputs"] / "visualizations")
    return {"status": "complete" if result["chart_count"] else "no_charts_available", "chart_count": result["chart_count"], "charts": [{"chart": item["chart"], "title": item["title"]} for item in result["charts"]], "load_errors": errors}


@router.get("/database/statistics", tags=["data engineering"])
def database_stats() -> dict[str, Any]:
    """Return aggregate table counts and schemas; never return row values."""
    url = default_database_url()
    if url.startswith("sqlite:///"):
        db_path = Path(url.removeprefix("sqlite:///"))
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        if not db_path.exists():
            return {"exists": False, "database": db_path.name, "table_count": 0, "tables": {}}
    engine = get_engine(url)
    try:
        stats = database_statistics(engine)
        return {"exists": True, **stats}
    finally:
        engine.dispose()
