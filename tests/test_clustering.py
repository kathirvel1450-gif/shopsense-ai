import numpy as np

from app.customer_intelligence.clustering import KMeansConfig, evaluate_kmeans, select_k


def test_evaluates_k_2_through_8_and_selects_practical_candidate():
    data = np.array([[i, i % 3, i * i] for i in range(12)], dtype=float)
    config = KMeansConfig()
    evaluations, models = evaluate_kmeans(data, config)
    assert [row["k"] for row in evaluations] == list(range(2, 9))
    assert len(models) == 7
    assert all(row["inertia"] is not None for row in evaluations)
    assert all(row["silhouette_score"] is not None for row in evaluations)
    selected = select_k(evaluations, config)
    assert selected["selected_k"] in range(2, 9)
    assert "smallest K" in selected["reason"] or "best silhouette" in selected["reason"]


def test_skips_infeasible_k_and_silhouette_cases():
    evaluations, models = evaluate_kmeans(np.array([[0, 0, 0], [1, 1, 1]], dtype=float))
    assert len(models) == 1
    assert evaluations[0]["silhouette_score"] is None
    assert all(row["status"] == "skipped" for row in evaluations[1:])
    assert select_k(evaluations)["selected_k"] is None
