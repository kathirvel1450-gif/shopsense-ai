import numpy as np
import pandas as pd

from app.customer_intelligence.preprocessing import FEATURES, prepare_rfm_features


def test_standard_scaler_uses_only_rfm_and_keeps_ids_separate():
    frame = pd.DataFrame({"customer_id": ["A", "B", "C"], "recency": [1, 10, np.nan], "frequency": [5, 2, 1], "monetary": [100, 40, 10]})
    ids, scaled, scaler, report = prepare_rfm_features(frame)
    assert ids["customer_id"].tolist() == ["A", "B"]
    assert scaled.shape == (2, 3)
    assert np.allclose(scaled.mean(axis=0), 0)
    assert scaler.n_features_in_ == len(FEATURES)
    assert report["excluded_invalid_or_missing_features"] == 1


def test_invalid_negative_features_are_excluded():
    frame = pd.DataFrame({"customer_id": [1, 2], "recency": [2, 3], "frequency": [-1, 1], "monetary": [5, 10]})
    ids, scaled, _, _ = prepare_rfm_features(frame)
    assert ids["customer_id"].tolist() == [2]
    assert scaled.shape == (1, 3)
