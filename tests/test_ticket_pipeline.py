from pathlib import Path

import pandas as pd

from app.guardrails.model_gateway import GatewaySettings, GuardrailGateway
from app.guardrails.token_counter import TokenCount
from app.guardrails.pipeline import run_ticket_pipeline


def test_missing_ticket_dataset_is_reported_without_claiming_processing(tmp_path: Path):
    report = run_ticket_pipeline(cleaned_dir=tmp_path / "processed", outputs_dir=tmp_path / "outputs")
    assert report["status"] == "missing_inputs"
    assert report["missing_files"] == ["tickets.csv"]
    assert report["ticket_rows"] is None
    assert report["classification_accuracy"] is None


def test_batch_pipeline_uses_schema_mapping_and_saves_no_ticket_text(tmp_path: Path):
    class WordCounter:
        def __call__(self, text, model):
            return TokenCount(len(text.split()), "test", True)

    class Provider:
        def complete(self, prompt):
            assert "ORD123456" not in prompt.user
            assert "alice@example.com" not in prompt.user
            return {"category": "LATE_DELIVERY", "confidence": 0.8, "rationale": "Delivery delay."}

    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame({"ticketId": ["t-1", "t-2"], "description": ["Order ORD123456 is late; email alice@example.com", "   "]}).to_csv(processed / "tickets.csv", index=False)
    gateway = GuardrailGateway(Provider(), GatewaySettings(1000, 100, 1000), token_counter=WordCounter())

    report = run_ticket_pipeline(cleaned_dir=processed, outputs_dir=tmp_path / "outputs", gateway=gateway)

    result_file = tmp_path / "outputs" / "ticket_intelligence" / "ticket_results.csv"
    saved = result_file.read_text(encoding="utf-8")
    assert report["ticket_rows"] == 2
    assert report["classified_count"] == 1
    assert report["rejected_count"] == 1
    assert report["pii_mask_counts"]["order_id"] == 1
    assert "ORD123456" not in saved
    assert "alice@example.com" not in saved
    assert "description" not in saved
