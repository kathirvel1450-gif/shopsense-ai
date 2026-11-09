import pandas as pd
import pytest
from sqlalchemy.exc import IntegrityError

from app.database.connection import get_engine
from app.database.repository import database_statistics, replace_datasets, validate_database


def test_database_loads_rows_and_checks_relationships() -> None:
    engine = get_engine("sqlite:///:memory:")
    try:
        frames = {
            "customers": pd.DataFrame({"customer_id": [1, 2], "city": ["Chennai", "Delhi"]}),
            "orders": pd.DataFrame({"order_id": [10, 11], "customer_id": [1, 2], "order_amount": [100.0, 250.0]}),
        }
        result = replace_datasets(engine, frames)
        stats = database_statistics(engine)
        validation = validate_database(engine)
        assert result["tables"]["customers"]["rows_inserted"] == 2
        assert stats["tables"]["orders"]["rows"] == 2
        assert validation["valid"] is True
        assert validation["primary_keys"] == {"customers": ["customer_id"], "orders": ["order_id"]}
    finally:
        engine.dispose()


def test_duplicate_primary_key_is_rejected() -> None:
    engine = get_engine("sqlite:///:memory:")
    try:
        with pytest.raises(IntegrityError):
            replace_datasets(engine, {"customers": pd.DataFrame({"customer_id": [1, 1], "city": ["A", "B"]})})
    finally:
        engine.dispose()
