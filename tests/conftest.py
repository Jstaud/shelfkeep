from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_DIR = Path(tempfile.mkdtemp(prefix="shelfkeep-test-"))
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DIR / 'shelfkeep.db'}"
os.environ["DATA_DIR"] = str(TEST_DIR)
os.environ["SHELFKEEP_USERNAME"] = "admin"
os.environ["SHELFKEEP_PASSWORD"] = "testhook"
os.environ["SESSION_SECRET"] = "test-secret-not-for-production"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    response = client.post(
        "/login",
        data={"username": "admin", "password": "testhook"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return client
