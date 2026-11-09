from app.main import app


def test_ticket_endpoints_are_registered():
    registered = {(method, route.path) for route in app.routes if hasattr(route, "methods") for method in route.methods}
    assert {("POST", "/api/tickets/validate"), ("POST", "/api/tickets/classify"), ("POST", "/api/tickets/process"), ("GET", "/api/tickets/summary")}.issubset(registered)
