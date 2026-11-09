import pandas as pd

from app.data_engine.cleaning import CleaningStrategy, clean_dataframe, detect_numeric_outliers


def test_cleaning_is_logged_and_raw_is_unchanged() -> None:
    raw = pd.DataFrame({"customer_id": [1, 2, 2], "gender": ["m", "Female", "other"], "city": [" chennai ", "BANGALORE", "Bengaluru"], "signup_date": ["2025-01-01", "bad", "2025-02-01"], "order_amount": [10, -3, 9000]})
    original = raw.copy(deep=True)
    cleaned, events = clean_dataframe(raw, "customers", CleaningStrategy(city_aliases={"Bengaluru": "Bengaluru"}))
    assert len(cleaned) == 3
    assert cleaned.loc[0, "gender"] == "Male"
    assert cleaned.loc[2, "gender"] == "Unknown"
    assert cleaned.loc[0, "city"] == "Chennai"
    assert pd.isna(cleaned.loc[1, "signup_date"])
    assert pd.isna(cleaned.loc[1, "order_amount"])
    assert {entry["operation"] for entry in events} >= {"normalize_gender", "standardize_city", "coerce_invalid_dates", "null_impossible_numeric"}
    pd.testing.assert_frame_equal(raw, original)


def test_exact_duplicate_removal_is_logged_and_outliers_are_only_flagged() -> None:
    frame = pd.DataFrame({"order_id": [1, 2, 2], "order_amount": [10, 20, 20]})
    cleaned, events = clean_dataframe(frame, "orders")
    assert len(cleaned) == 2
    assert events[0]["operation"] == "drop_exact_duplicates"
    outliers = detect_numeric_outliers(pd.DataFrame({"amount": [1, 2, 2, 3, 100]}))
    assert outliers["amount"]["outlier_count"] == 1
    assert outliers["amount"]["removed"] == 0
