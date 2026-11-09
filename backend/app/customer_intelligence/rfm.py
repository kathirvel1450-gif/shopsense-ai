"""RFM computation over completed orders with schema-aware column mapping."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RFMColumns:
    customer_id: str
    order_customer_id: str
    order_id: str | None
    order_date: str
    order_amount: str
    order_status: str


def map_rfm_columns(customers: pd.DataFrame, orders: pd.DataFrame) -> RFMColumns:
    """Resolve common field aliases from observed headers; raise clear errors."""
    customer_id = resolve_column(customers, ("customer_id", "customerid", "customer_key", "id"))
    order_customer_id = resolve_column(orders, ("customer_id", "customerid", "customer_key", "customer"))
    order_id = resolve_column(orders, ("order_id", "orderid", "order_number", "id"), required=False)
    order_date = resolve_column(orders, ("order_date", "order_datetime", "created_at", "order_time", "date"))
    order_amount = resolve_column(orders, ("order_amount", "amount", "total_amount", "order_total", "transaction_amount", "order_value", "total", "revenue"))
    order_status = resolve_column(orders, ("order_status", "status", "fulfillment_status"))
    return RFMColumns(customer_id, order_customer_id, order_id, order_date, order_amount, order_status)


def resolve_column(frame: pd.DataFrame, aliases: Iterable[str], required: bool = True) -> str | None:
    """Match a canonical field alias against normalized observed headers."""
    aliases_normalized = {_normalize(alias) for alias in aliases}
    for column in frame.columns:
        if _normalize(str(column)) in aliases_normalized:
            return str(column)
    if required:
        raise ValueError(f"Missing required field; expected one of {sorted(aliases_normalized)}. Available columns: {list(map(str, frame.columns))}")
    return None


def calculate_rfm(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    analysis_reference_date: str | pd.Timestamp | None = None,
    completed_statuses: Iterable[str] = ("completed", "complete", "delivered"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Calculate Recency (days), distinct completed-order Frequency, and Monetary.

    Customers without completed orders remain in the output with frequency and
    monetary equal to zero and recency missing. Invalid/future dates do not supply
    a recency but their valid completed orders still contribute to F and M.
    """
    columns = map_rfm_columns(customers, orders)
    customer_ids = customers[columns.customer_id].dropna().drop_duplicates()
    if customer_ids.empty:
        raise ValueError("Customer dataset contains no non-missing customer identifiers.")
    work = orders.copy()
    status_values = {str(value).strip().casefold() for value in completed_statuses}
    completed = work[columns.order_status].astype("string").str.strip().str.casefold().isin(status_values)
    completed_orders = work.loc[completed].copy()
    source_completed_rows = int(len(completed_orders))
    missing_customer_ids = int(completed_orders[columns.order_customer_id].isna().sum())
    completed_orders = completed_orders.loc[completed_orders[columns.order_customer_id].notna()].copy()
    completed_orders["__customer_key"] = completed_orders[columns.order_customer_id].astype("string").str.strip()
    if columns.order_id:
        duplicate_mask = completed_orders.duplicated(subset=["__customer_key", columns.order_id], keep="first") & completed_orders[columns.order_id].notna()
        duplicate_order_rows = int(duplicate_mask.sum())
        completed_orders = completed_orders.loc[~duplicate_mask].copy()
    else:
        duplicate_order_rows = 0
    parsed_dates = pd.to_datetime(completed_orders[columns.order_date], errors="coerce", format="mixed", utc=True).dt.tz_convert(None)
    invalid_dates = int((completed_orders[columns.order_date].notna() & parsed_dates.isna()).sum())
    completed_orders["__parsed_order_date"] = parsed_dates
    amounts = pd.to_numeric(completed_orders[columns.order_amount], errors="coerce")
    invalid_amounts = int((completed_orders[columns.order_amount].notna() & amounts.isna()).sum())
    completed_orders["__amount"] = amounts.where(amounts.ge(0))
    negative_amounts = int(amounts.lt(0).sum())
    if analysis_reference_date is None:
        valid_dates = parsed_dates.dropna()
        if valid_dates.empty:
            reference = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
            reference_source = "current date (no valid completed-order dates found)"
        else:
            reference = valid_dates.max().normalize()
            reference_source = "latest valid completed-order date"
    else:
        reference = pd.Timestamp(analysis_reference_date)
        if reference.tzinfo is not None:
            reference = reference.tz_convert(None)
        reference = reference.normalize()
        reference_source = "configured analysis reference date"
    future_date_mask = completed_orders["__parsed_order_date"].notna() & (completed_orders["__parsed_order_date"] > reference)
    future_date_count = int(future_date_mask.sum())
    dated = completed_orders.loc[~future_date_mask & completed_orders["__parsed_order_date"].notna()]
    most_recent = dated.groupby("__customer_key")["__parsed_order_date"].max()
    recency = (reference - most_recent).dt.days.rename("recency")
    if columns.order_id:
        frequency = completed_orders.groupby("__customer_key")[columns.order_id].nunique(dropna=True)
        missing_order_ids = int(completed_orders[columns.order_id].isna().sum())
        if missing_order_ids:
            frequency = frequency.add(completed_orders.loc[completed_orders[columns.order_id].isna()].groupby("__customer_key").size(), fill_value=0)
    else:
        frequency = completed_orders.groupby("__customer_key").size()
        missing_order_ids = 0
    monetary = completed_orders.groupby("__customer_key")["__amount"].sum(min_count=1).fillna(0)
    base = pd.DataFrame({"customer_id": customer_ids.to_numpy()})
    base["__customer_key"] = base["customer_id"].astype("string").str.strip()
    if base["__customer_key"].duplicated().any():
        raise ValueError("Customer identifiers collide after whitespace/type normalization; resolve duplicate IDs in cleaned source data.")
    base = base.merge(recency.reset_index(), how="left", on="__customer_key")
    base = base.merge(frequency.rename("frequency").reset_index(), how="left", on="__customer_key")
    base = base.merge(monetary.rename("monetary").reset_index(), how="left", on="__customer_key")
    base["frequency"] = base["frequency"].fillna(0).astype(int)
    base["monetary"] = base["monetary"].fillna(0.0).astype(float)
    report = {
        "analysis_reference_date": reference.date().isoformat(), "reference_date_source": reference_source,
        "completed_statuses": sorted(status_values), "input_customers": int(len(customers)),
        "unique_customers": int(len(base)), "input_orders": int(len(orders)),
        "completed_order_rows_in_source": source_completed_rows, "completed_order_rows_after_duplicate_handling": int(len(completed_orders)), "completed_customers": int(base["frequency"].gt(0).sum()),
        "customers_without_completed_orders": int(base["frequency"].eq(0).sum()),
        "duplicate_order_rows_ignored": duplicate_order_rows, "missing_customer_id_order_rows_ignored": missing_customer_ids,
        "invalid_completed_order_dates": invalid_dates, "future_completed_order_dates": future_date_count,
        "invalid_amounts_treated_as_missing": invalid_amounts, "negative_amounts_ignored": negative_amounts,
        "missing_order_ids_counted_as_rows": missing_order_ids,
    }
    return base[["customer_id", "recency", "frequency", "monetary"]], report


def _normalize(value: str) -> str:
    source = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_")
