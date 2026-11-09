import pandas as pd

from app.customer_intelligence.churn_risk import ChurnRiskThresholds, classify_churn_risk


def test_inactivity_risk_rules_include_explanations_and_no_purchase_state():
    frame = pd.DataFrame({"customer_id": [1, 2, 3, 4], "recency": [120, 50, 10, None], "frequency": [5, 1, 5, 0], "monetary": [500, 10, 300, 0]})
    result = classify_churn_risk(frame, ChurnRiskThresholds(high_recency_days=90, medium_recency_days=45, low_frequency=1, low_monetary=25))
    assert result["churn_risk_level"].tolist() == ["High", "Medium", "Low", "No Purchase History"]
    assert all(result["churn_risk_reason"].str.len() > 0)


def test_purchased_customer_without_usable_recency_is_explicit():
    frame = pd.DataFrame({"customer_id": [1], "recency": [None], "frequency": [2], "monetary": [20]})
    assert classify_churn_risk(frame).iloc[0]["churn_risk_level"] == "Insufficient Date Data"
