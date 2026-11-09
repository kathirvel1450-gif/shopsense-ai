import pandas as pd

from app.customer_intelligence.segmentation import label_segments


def test_cluster_labels_follow_observed_behavior():
    frame = pd.DataFrame({
        "customer_id": [1, 2, 3, 4], "recency": [1, 2, 100, 120],
        "frequency": [8, 10, 1, 2], "monetary": [800, 900, 50, 80], "cluster_id": [0, 0, 1, 1],
    })
    labeled, profiles = label_segments(frame)
    labels = labeled.groupby("cluster_id")["segment_name"].first().to_dict()
    assert labels == {0: "Champions", 1: "Hibernating"}
    assert sum(profile["customer_count"] for profile in profiles) == 4
