from pathlib import Path

from app.data_engine.pipeline import run_pipeline


def test_missing_inputs_are_reported_without_creating_database(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    report = run_pipeline(
        raw_dir=raw,
        processed_dir=tmp_path / "processed",
        outputs_dir=tmp_path / "outputs",
        database_url=f"sqlite:///{(tmp_path / 'shopsense.db').as_posix()}",
    )
    assert report["status"] == "missing_inputs"
    assert report["missing_files"] == ["customers.csv", "orders.csv", "tickets.csv"]
    assert report["database"]["created_or_updated"] is False
    assert not (tmp_path / "shopsense.db").exists()
    assert (tmp_path / "outputs" / "reports" / "pipeline_report.json").is_file()
