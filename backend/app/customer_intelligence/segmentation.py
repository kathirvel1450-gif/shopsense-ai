"""Cluster interpretation using observed RFM medians and supported labels."""
from __future__ import annotations

from typing import Any

import pandas as pd


def label_segments(rfm_with_clusters: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Assign behavior-supported names and cluster-level descriptive statistics."""
    required = {"customer_id", "recency", "frequency", "monetary", "cluster_id"}
    if not required.issubset(rfm_with_clusters.columns):
        raise ValueError(f"Segmentation data missing columns: {sorted(required - set(rfm_with_clusters.columns))}")
    result = rfm_with_clusters.copy()
    clustered = result.dropna(subset=["cluster_id", "recency", "frequency", "monetary"])
    if clustered.empty:
        result["segment_name"] = result["frequency"].eq(0).map({True: "No Purchase History", False: "Insufficient data for clustering"})
        return result, []
    benchmarks = clustered[["recency", "frequency", "monetary"]].median()
    q25_recency = clustered["recency"].quantile(0.25)
    q75_recency = clustered["recency"].quantile(0.75)
    q75_frequency = clustered["frequency"].quantile(0.75)
    q75_monetary = clustered["monetary"].quantile(0.75)
    stats = clustered.groupby("cluster_id").agg(
        customer_count=("customer_id", "size"), recency_mean=("recency", "mean"), recency_median=("recency", "median"),
        frequency_mean=("frequency", "mean"), frequency_median=("frequency", "median"),
        monetary_mean=("monetary", "mean"), monetary_median=("monetary", "median"),
    )
    profiles: list[dict[str, Any]] = []
    used_names: set[str] = set()
    label_by_cluster: dict[int, str] = {}
    for cluster_id, row in stats.iterrows():
        recent = row["recency_median"] <= benchmarks["recency"]
        high_recency = row["recency_median"] >= q75_recency
        high_frequency = row["frequency_median"] >= q75_frequency and row["frequency_median"] > 0
        high_monetary = row["monetary_median"] >= q75_monetary and row["monetary_median"] > 0
        if row["recency_median"] <= q25_recency and high_frequency and high_monetary:
            candidate = "Champions"
            description = "Recent customers with high repeat frequency and high spend relative to this dataset."
        elif recent and high_frequency:
            candidate = "Loyal Customers"
            description = "More recent customers with above-typical repeat purchasing."
        elif high_recency and (row["frequency_median"] >= benchmarks["frequency"] or row["monetary_median"] >= benchmarks["monetary"]):
            candidate = "At Risk"
            description = "Longer-inactive customers whose frequency or spend indicates prior value."
        elif high_recency and row["frequency_median"] <= benchmarks["frequency"] and row["monetary_median"] <= benchmarks["monetary"]:
            candidate = "Hibernating"
            description = "Longer-inactive customers with below-typical repeat frequency and spend."
        elif recent and row["frequency_median"] <= benchmarks["frequency"]:
            candidate = "Potential Loyalists"
            description = "More recent customers with lower repeat frequency who may develop into regulars."
        else:
            descriptor = _behavior_descriptor(row, benchmarks)
            candidate = descriptor
            description = f"Observed cluster profile: median recency {row['recency_median']:.1f} days, frequency {row['frequency_median']:.1f}, monetary {row['monetary_median']:.2f}."
        name = candidate if candidate not in used_names else f"{candidate} (Cluster {int(cluster_id)})"
        used_names.add(name)
        label_by_cluster[int(cluster_id)] = name
        profile = {"cluster_id": int(cluster_id), "segment_name": name, "description": description}
        profile.update({key: int(value) if key == "customer_count" else float(value) for key, value in row.items()})
        profiles.append(profile)
    no_cluster = result["cluster_id"].isna()
    result["segment_name"] = result["cluster_id"].map(lambda value: label_by_cluster.get(int(value), "Insufficient data for clustering") if pd.notna(value) else None)
    result.loc[no_cluster & result["frequency"].eq(0), "segment_name"] = "No Purchase History"
    result.loc[no_cluster & result["frequency"].ne(0), "segment_name"] = "Insufficient data for clustering"
    return result, profiles


def _behavior_descriptor(row: pd.Series, benchmarks: pd.Series) -> str:
    recency = "Recent" if row["recency_median"] <= benchmarks["recency"] else "Less Recent"
    frequency = "Frequent" if row["frequency_median"] > benchmarks["frequency"] else "Occasional"
    spend = "Higher Spend" if row["monetary_median"] > benchmarks["monetary"] else "Lower Spend"
    return f"{recency}, {frequency}, {spend} Customers"
