import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "MAX_RUNS": 3})
    return app.test_client()
