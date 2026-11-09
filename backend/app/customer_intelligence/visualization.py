"""RFM, model evaluation, segment, and churn-risk charts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA

sns.set_theme(style="whitegrid", palette="crest")


def generate_customer_visualizations(
    rfm: pd.DataFrame,
    scaled_features,
    evaluations: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    """Save available charts and return only their filenames and titles."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    charts: list[dict[str, str]] = []
    scored = [row for row in evaluations if row.get("inertia") is not None]
    if scored:
        charts.append(_metric_plot(scored, "inertia", output_dir / "rfm_elbow_curve.png", "K-Means elbow curve", "K", "Inertia"))
    silhouette = [row for row in evaluations if row.get("silhouette_score") is not None]
    if silhouette:
        charts.append(_metric_plot(silhouette, "silhouette_score", output_dir / "rfm_silhouette_scores.png", "Silhouette score by K", "K", "Silhouette score"))
    valid = rfm.dropna(subset=["recency", "frequency", "monetary"])
    for feature in ("recency", "frequency", "monetary"):
        if feature in valid:
            fig, ax = plt.subplots(figsize=(7, 4))
            sns.histplot(valid[feature], bins=30, kde=len(valid) >= 5, ax=ax, color="#14966c")
            ax.set(title=f"{feature.title()} distribution", xlabel=feature.title(), ylabel="Customers")
            charts.append(_save(fig, output_dir / f"rfm_{feature}_distribution.png", f"{feature.title()} distribution"))
    if "cluster_id" in valid and valid["cluster_id"].notna().any():
        for x, y, filename in (("recency", "frequency", "cluster_recency_frequency.png"), ("frequency", "monetary", "cluster_frequency_monetary.png"), ("recency", "monetary", "cluster_recency_monetary.png")):
            fig, ax = plt.subplots(figsize=(7, 5))
            sns.scatterplot(data=valid, x=x, y=y, hue="cluster_id", palette="crest", ax=ax, s=45)
            ax.set(title=f"Customer clusters: {x.title()} vs {y.title()}")
            charts.append(_save(fig, output_dir / filename, f"Customer clusters: {x.title()} vs {y.title()}"))
        if scaled_features is not None and len(scaled_features) >= 2 and scaled_features.shape[1] >= 2:
            two_dimensions = PCA(n_components=2, random_state=42).fit_transform(scaled_features)
            pca_frame = pd.DataFrame({"PC1": two_dimensions[:, 0], "PC2": two_dimensions[:, 1], "cluster_id": valid["cluster_id"].astype(str).to_numpy()})
            fig, ax = plt.subplots(figsize=(7, 5))
            sns.scatterplot(data=pca_frame, x="PC1", y="PC2", hue="cluster_id", palette="crest", ax=ax, s=45)
            ax.set(title="Customer clusters projected to PCA space")
            charts.append(_save(fig, output_dir / "customer_clusters_pca.png", "Customer clusters projected to PCA space"))
    segmented = rfm.get("segment_name")
    if segmented is not None and segmented.notna().any():
        charts.append(_distribution_plot(segmented, output_dir / "segment_distribution.png", "Customer segment distribution"))
    risk = rfm.get("churn_risk_level")
    if risk is not None and risk.notna().any():
        charts.append(_distribution_plot(risk, output_dir / "churn_risk_distribution.png", "Inactivity risk indicator distribution"))
    return {"visualization_directory": str(output_dir), "chart_count": len(charts), "charts": charts}


def _metric_plot(rows: list[dict[str, Any]], metric: str, path: Path, title: str, xlabel: str, ylabel: str) -> dict[str, str]:
    frame = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.lineplot(data=frame, x="k", y=metric, marker="o", ax=ax, color="#14966c")
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    return _save(fig, path, title)


def _distribution_plot(series: pd.Series, path: Path, title: str) -> dict[str, str]:
    counts = series.fillna("Unknown").value_counts()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(x=counts.values, y=counts.index.astype(str), ax=ax, color="#14966c")
    ax.set(title=title, xlabel="Customers", ylabel="")
    return _save(fig, path, title)


def _save(fig, path: Path, title: str) -> dict[str, str]:
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return {"chart": path.name, "path": str(path), "title": title}
