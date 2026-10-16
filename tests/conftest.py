"""Pytest fixtures for database testing."""

import pytest
import config
from src.db import apply_schema, get_connection, require_test_database


@pytest.fixture
def conn():
    """Provide a clean test database connection for each test."""
    test_db = config.DB_TEST_NAME
    require_test_database(test_db)
    apply_schema(test_db)

    connection = get_connection(test_db)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM attendance")
    cursor.execute("DELETE FROM employees")
    connection.commit()
    cursor.close()

    yield connection

    connection.close()
