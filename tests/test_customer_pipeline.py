from pathlib import Path

import pandas as pd

from app.customer_intelligence.pipeline import run_customer_intelligence


def test_missing_cleaned_datasets_do_not_create_customer_results(tmp_path: Path):
    report = run_customer_intelligence(cleaned_dir=tmp_path / "processed", outputs_dir=tmp_path / "outputs")
    assert report["status"] == "missing_inputs"
    assert report["missing_files"] == ["customers.csv", "orders.csv"]
    assert report["customer_count"] is None
    assert report["selected_k"] is None
    assert not (tmp_path / "outputs" / "models" / "rfm_kmeans.joblib").exists()


def test_invalid_schema_is_reported_without_fake_metrics(tmp_path: Path):
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "customers.csv").write_text("id\n1\n", encoding="utf-8")
    (processed / "orders.csv").write_text("status\ncompleted\n", encoding="utf-8")
    report = run_customer_intelligence(cleaned_dir=processed, outputs_dir=tmp_path / "outputs")
    assert report["status"] == "invalid_data"
    assert report["customer_count"] is None
    assert report["model_evaluation"] == []


def test_controlled_fixture_runs_models_charts_and_local_artifacts(tmp_path: Path):
    processed = tmp_path / "processed"
    processed.mkdir()
    customers = pd.DataFrame({"customer_id": [f"c{i}" for i in range(18)]})
    orders = []
    for customer_index in range(18):
        if customer_index < 6:
            order_count, age_days, amount = 8 + customer_index % 2, customer_index % 6, 120 + customer_index * 3
        elif customer_index < 12:
            order_count, age_days, amount = 4 + customer_index % 3, 20 + customer_index, 45 + customer_index
        else:
            order_count, age_days, amount = 1 + customer_index % 3, 110 + customer_index, 15 + customer_index
        for order_no in range(order_count):
            orders.append({"order_id": f"o{customer_index}_{order_no}", "customer_id": f"c{customer_index}", "order_date": (pd.Timestamp("2026-06-30") - pd.Timedelta(days=age_days + order_no)).date().isoformat(), "order_amount": amount, "order_status": "completed"})
    customers.to_csv(processed / "customers.csv", index=False)
    pd.DataFrame(orders).to_csv(processed / "orders.csv", index=False)
    output_dir = tmp_path / "outputs"

    report = run_customer_intelligence(cleaned_dir=processed, outputs_dir=output_dir, analysis_reference_date="2026-07-01")

    assert report["status"] == "complete"
    assert report["customer_count"] == 18
    assert report["selected_k"] in range(2, 9)
    assert (output_dir / "models" / "rfm_standard_scaler.joblib").is_file()
    assert (output_dir / "models" / "rfm_kmeans.joblib").is_file()
    assert (output_dir / "customer_intelligence" / "customer_segments.csv").is_file()
    assert report["visualizations"]["chart_count"] >= 8
