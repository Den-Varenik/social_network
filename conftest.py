import pytest
from main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def client():
    with TestClient(app) as client:
        yield client
