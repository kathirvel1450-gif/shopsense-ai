from pathlib import Path

import pandas as pd

from app.data_engine.ingestion import discover_datasets, load_available, load_csv


def test_discovers_expected_and_extra_csvs(tmp_path: Path) -> None:
    (tmp_path / "customers.csv").write_text("customer_id\n1\n", encoding="utf-8")
    (tmp_path / "transactions.csv").write_text("txn_id\n2\n", encoding="utf-8")
    report = discover_datasets(tmp_path)
    assert report["available"]["customers.csv"] is True
    assert report["missing"] == ["orders.csv", "tickets.csv"]
    assert report["dataset_count"] == 2


def test_loads_csv_without_modifying_source(tmp_path: Path) -> None:
    source = tmp_path / "customers.csv"
    source.write_text("customer_id,city\n1,Chennai\n", encoding="utf-8")
    before = source.read_bytes()
    frame = load_csv(source)
    frames, errors = load_available(tmp_path)
    assert frame.to_dict(orient="records") == [{"customer_id": 1, "city": "Chennai"}]
    assert list(frames) == ["customers"]
    assert errors == {}
    assert source.read_bytes() == before
