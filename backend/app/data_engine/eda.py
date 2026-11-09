"""Schema-aware exploratory charts; each chart requires the needed columns."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", palette="crest")


def generate_eda(frames: dict[str, pd.DataFrame], output_dir: Path) -> dict[str, Any]:
    """Create available customer/order/ticket charts and return report paths."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    charts: list[dict[str, str]] = []
    customers, orders, tickets = frames.get("customers"), frames.get("orders"), frames.get("tickets")
    if customers is not None:
        gender = _column(customers, r"gender")
        city = _column(customers, r"city")
        signup = _column(customers, r"signup|register|created.*(date|at)|joined")
        if gender:
            charts.append(_count_plot(customers, gender, output_dir, "customers_gender_distribution.png", "Customer gender distribution"))
        if city:
            charts.append(_count_plot(customers, city, output_dir, "customers_city_distribution.png", "Customers by city", top=20))
        if signup:
            charts.append(_trend_plot(customers, signup, output_dir, "customers_signup_trend.png", "Customer signups over time"))
    if orders is not None:
        status = _column(orders, r"status")
        value = _column(orders, r"amount|total|order_value|price|revenue|value")
        date = _column(orders, r"date|time|created.*at|timestamp")
        city = _column(orders, r"city")
        if status:
            charts.append(_count_plot(orders, status, output_dir, "orders_status_distribution.png", "Order status distribution"))
        if value and pd.api.types.is_numeric_dtype(orders[value]):
            charts.append(_hist_plot(orders, value, output_dir, "orders_value_distribution.png", "Order value distribution"))
        if date and value and pd.api.types.is_numeric_dtype(orders[value]):
            charts.append(_trend_plot(orders, date, output_dir, "revenue_trend.png", "Revenue over time", value_column=value))
        if city:
            charts.append(_count_plot(orders, city, output_dir, "orders_by_city.png", "Orders by city", top=20))
        elif customers is not None:
            customer_id = _column(orders, r"^customer_id$")
            customer_pk = _column(customers, r"^(customer_id|id)$")
            customer_city = _column(customers, r"city")
            if customer_id and customer_pk and customer_city:
                mapping = customers[[customer_pk, customer_city]].drop_duplicates(customer_pk)
                joined = orders.merge(mapping, left_on=customer_id, right_on=customer_pk, how="left")
                charts.append(_count_plot(joined, customer_city, output_dir, "orders_by_city.png", "Orders by customer city", top=20))
    if tickets is not None:
        category = _column(tickets, r"category|type|reason|topic")
        status = _column(tickets, r"status")
        date = _column(tickets, r"date|time|created.*at|timestamp")
        if category:
            charts.append(_count_plot(tickets, category, output_dir, "tickets_category_distribution.png", "Ticket category distribution", top=20))
        if status:
            charts.append(_count_plot(tickets, status, output_dir, "tickets_status_distribution.png", "Ticket status distribution"))
        if date:
            charts.append(_trend_plot(tickets, date, output_dir, "tickets_volume_trend.png", "Ticket volume over time"))
    return {"visualization_directory": str(output_dir), "chart_count": len(charts), "charts": charts}


def _column(frame: pd.DataFrame, pattern: str) -> str | None:
    for column in frame.columns:
        source = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(column))
        if re.search(pattern, source.lower().replace(" ", "_")):
            return str(column)
    return None


def _save(fig, directory: Path, filename: str, title: str) -> dict[str, str]:
    fig.tight_layout()
    target = directory / filename
    fig.savefig(target, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return {"chart": filename, "path": str(target), "title": title}


def _count_plot(frame: pd.DataFrame, column: str, directory: Path, filename: str, title: str, top: int | None = None) -> dict[str, str]:
    counts = frame[column].astype("string").fillna("Unknown").value_counts().head(top)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    sns.barplot(x=counts.values, y=counts.index.astype(str), ax=ax, color="#15966b")
    ax.set(title=title, xlabel="Records", ylabel=column.replace("_", " ").title())
    return _save(fig, directory, filename, title)


def _hist_plot(frame: pd.DataFrame, column: str, directory: Path, filename: str, title: str) -> dict[str, str]:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.histplot(frame[column].dropna(), bins=30, kde=True, ax=ax, color="#15966b")
    ax.set(title=title, xlabel=column.replace("_", " ").title(), ylabel="Orders")
    return _save(fig, directory, filename, title)


def _trend_plot(frame: pd.DataFrame, date_column: str, directory: Path, filename: str, title: str, value_column: str | None = None) -> dict[str, str]:
    dates = pd.to_datetime(frame[date_column], errors="coerce", format="mixed")
    temp = pd.DataFrame({"date": dates})
    temp["period"] = temp["date"].dt.to_period("M").dt.to_timestamp()
    if value_column:
        temp["value"] = pd.to_numeric(frame[value_column], errors="coerce")
        grouped = temp.dropna(subset=["period"]).groupby("period", as_index=False)["value"].sum()
        y, ylabel = "value", value_column.replace("_", " ").title()
    else:
        grouped = temp.dropna(subset=["period"]).groupby("period", as_index=False).size()
        y, ylabel = "size", "Records"
    fig, ax = plt.subplots(figsize=(9, 4.5))
    if not grouped.empty:
        sns.lineplot(data=grouped, x="period", y=y, marker="o", ax=ax, color="#15966b")
    ax.set(title=title, xlabel="Month", ylabel=ylabel)
    return _save(fig, directory, filename, title)
