from app.api import customer_routes
from app.main import app


def test_customer_endpoints_are_registered():
    registered = {(method, route.path) for route in app.routes if hasattr(route, "methods") for method in route.methods}
    expected = {
        ("GET", "/api/customers/rfm"), ("GET", "/api/customers/segments"),
        ("GET", "/api/customers/churn-risk"), ("GET", "/api/customers/model-evaluation"),
        ("GET", "/api/customers/summary"),
    }
    assert expected.issubset(registered)


def test_customer_summary_api_returns_aggregates_without_ids(monkeypatch):
    monkeypatch.setattr(customer_routes, "_customer_report", lambda: {
        "status": "complete", "customer_count": 12, "selected_k": 2,
        "rfm": {"completed_customers": 10, "customers_without_completed_orders": 2},
        "cluster_profiles": [{"segment_name": "Loyal Customers", "customer_count": 4, "customer_ids": ["secret"]}],
        "churn_risk": {"distribution": {"Low": 8, "High": 2}},
        "visualizations": {"chart_count": 7},
    })
    result = customer_routes.customers_summary()
    assert result["customer_count"] == 12
    assert result["segment_counts"] == [{"segment_name": "Loyal Customers", "customer_count": 4}]
    assert "secret" not in str(result)
    assert "customer_ids" not in str(result)
