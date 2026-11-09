import pandas as pd

from app.data_engine.profiling import profile_dataframe


def test_profile_has_quality_statistics_and_suppresses_identifiers() -> None:
    frame = pd.DataFrame({"customer_id": [1, 2, 2], "email": ["a@example.test", None, "c@example.test"], "ticket_text": ["order 1 email a@example.test", "need refund", "phone 123456"], "gender": ["Female", "Male", "Male"], "amount": [10, 20, 30], "created_at": ["2025-01-01", "invalid", "2025-03-01"]})
    profile = profile_dataframe(frame, "customers")
    assert profile["rows"] == 3
    assert profile["columns_count"] == 6
    assert profile["duplicate_rows"] == 0
    assert profile["column_profiles"]["email"]["missing_percent"] == 33.33
    assert "distribution" not in profile["column_profiles"]["email"]
    assert "distribution" not in profile["column_profiles"]["ticket_text"]
    assert "distribution" not in profile["column_profiles"]["customer_id"]
    assert profile["column_profiles"]["gender"]["distribution"][0]["value"] == "Male"
    assert profile["column_profiles"]["amount"]["numeric_summary"]["mean"] == 20
    assert profile["column_profiles"]["created_at"]["date_range"]["max"].startswith("2025-03")
