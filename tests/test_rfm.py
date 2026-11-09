import pandas as pd
import pytest

from app.customer_intelligence.rfm import calculate_rfm, map_rfm_columns


def sample_data():
    customers = pd.DataFrame({"customerId": ["c1", "c2", "c3"]})
    orders = pd.DataFrame({
        "orderId": ["o1", "o2", "o3", "o4"],
        "customerId": ["c1", "c1", "c2", "c3"],
        "orderDate": ["2026-01-01", "2026-02-01", "2026-02-15", "2026-02-20"],
        "orderAmount": [100, 50, 80, 500],
        "orderStatus": ["Completed", "completed", "pending", "cancelled"],
    })
    return customers, orders


def test_rfm_filters_completed_orders_and_keeps_no_order_customers():
    customers, orders = sample_data()
    assert map_rfm_columns(customers, orders).order_id == "orderId"
    result, report = calculate_rfm(customers, orders, "2026-03-01")
    c1 = result.set_index("customer_id").loc["c1"]
    c2 = result.set_index("customer_id").loc["c2"]
    c3 = result.set_index("customer_id").loc["c3"]
    assert c1["recency"] == 28
    assert c1["frequency"] == 2
    assert c1["monetary"] == 150
    assert c2["frequency"] == c3["frequency"] == 0
    assert pd.isna(c2["recency"]) and c2["monetary"] == 0
    assert report["completed_customers"] == 1
    assert report["customers_without_completed_orders"] == 2


def test_invalid_required_schema_is_reported():
    with pytest.raises(ValueError, match="Missing required field"):
        calculate_rfm(pd.DataFrame({"id": [1]}), pd.DataFrame({"status": ["completed"]}))


def test_duplicate_orders_are_counted_once_and_invalid_dates_reported():
    customers = pd.DataFrame({"customer_id": [1]})
    orders = pd.DataFrame({"order_id": [1, 1, 2], "customer_id": [1, 1, 1], "order_date": ["2026-01-02", "2026-01-02", "bad"], "order_amount": [10, 10, 30], "order_status": ["completed"] * 3})
    rfm, report = calculate_rfm(customers, orders, "2026-02-01")
    assert rfm.iloc[0]["frequency"] == 2
    assert rfm.iloc[0]["monetary"] == 40
    assert report["duplicate_order_rows_ignored"] == 1
    assert report["invalid_completed_order_dates"] == 1
