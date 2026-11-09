"""K-Means evaluation, silhouette diagnostics, and practical K selection."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


@dataclass(frozen=True)
class KMeansConfig:
    """Repeatable K-Means parameters."""
    k_values: tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8)
    random_state: int = 42
    n_init: int = 10
    silhouette_tolerance: float = 0.02
    minimum_cluster_size: int = 1


def evaluate_kmeans(features: np.ndarray, config: KMeansConfig | None = None) -> tuple[list[dict[str, Any]], dict[int, KMeans]]:
    """Fit requested Ks, record inertia/silhouette, and skip infeasible values."""
    config = config or KMeansConfig()
    array = np.asarray(features, dtype=float)
    if array.ndim != 2:
        raise ValueError("K-Means features must be a two-dimensional numeric matrix.")
    rows = len(array)
    distinct = int(np.unique(array, axis=0).shape[0]) if rows else 0
    evaluations: list[dict[str, Any]] = []
    models: dict[int, KMeans] = {}
    for k in config.k_values:
        entry: dict[str, Any] = {"k": int(k), "inertia": None, "silhouette_score": None, "status": "skipped", "reason": None, "minimum_cluster_size": None, "cluster_sizes": []}
        if k < 2:
            entry["reason"] = "K must be at least 2."
        elif rows < k:
            entry["reason"] = f"Only {rows} eligible customers are available; K={k} needs at least {k}."
        elif distinct < k:
            entry["reason"] = f"Only {distinct} distinct RFM feature vectors are available; K={k} would create duplicate centroids."
        else:
            model = KMeans(n_clusters=int(k), random_state=config.random_state, n_init=config.n_init)
            labels = model.fit_predict(array)
            sizes = np.bincount(labels, minlength=int(k)).astype(int)
            entry.update({"inertia": float(model.inertia_), "cluster_sizes": sizes.tolist(), "minimum_cluster_size": int(sizes.min()), "status": "evaluated"})
            if 1 < len(np.unique(labels)) < rows:
                entry["silhouette_score"] = float(silhouette_score(array, labels))
            else:
                entry["reason"] = "Silhouette requires between 2 and n-1 non-empty clusters."
            models[int(k)] = model
        evaluations.append(entry)
    return evaluations, models


def select_k(evaluations: list[dict[str, Any]], config: KMeansConfig | None = None) -> dict[str, Any]:
    """Select the simplest interpretable K near the best silhouette score."""
    config = config or KMeansConfig()
    valid = [item for item in evaluations if item.get("silhouette_score") is not None and item.get("minimum_cluster_size", 0) >= config.minimum_cluster_size]
    if not valid:
        return {"selected_k": None, "reason": "No candidate K has a valid silhouette score and acceptable cluster size."}
    best = max(float(item["silhouette_score"]) for item in valid)
    near_best = [item for item in valid if float(item["silhouette_score"]) >= best - config.silhouette_tolerance]
    selected = min(near_best, key=lambda item: int(item["k"]))
    if len(near_best) > 1:
        reason = f"Selected the smallest K within {config.silhouette_tolerance:.3f} of the best silhouette ({best:.4f}) to favor simpler, more interpretable segments."
    else:
        reason = f"Selected K={selected['k']} as the best silhouette candidate ({best:.4f}); cluster behavior still requires business review."
    return {"selected_k": int(selected["k"]), "best_silhouette": best, "selection_silhouette": float(selected["silhouette_score"]), "reason": reason, "rule": {"silhouette_tolerance": config.silhouette_tolerance, "minimum_cluster_size": config.minimum_cluster_size}}


def fit_selected_model(models: dict[int, KMeans], selected_k: int | None) -> KMeans | None:
    """Get the already-fitted selected model, if selection succeeded."""
    return models.get(int(selected_k)) if selected_k is not None else None


def model_metadata(config: KMeansConfig | None = None) -> dict[str, Any]:
    """Expose reproducibility parameters for model reports."""
    return asdict(config or KMeansConfig())
