"""
Shared pytest fixtures.

Forces a throwaway SQLite file (never the dev/prod DATABASE_URL) and
FORCE_MOCK_PROVIDERS=true *before* any app module is imported, so the
whole suite runs offline with MockProvider - no real Teams/Slack/SMTP
credentials or network access needed (spec's Testing Requirements: unit
tests should not depend on live services).
"""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DB_PATH = BACKEND_DIR / "tests" / "test_notification.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["FORCE_MOCK_PROVIDERS"] = "true"
os.environ["WEBHOOK_SHARED_SECRET"] = "test-secret"

sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from app.db import Base, engine  # noqa: E402


@pytest.fixture
def client():
    """A TestClient bound to a fresh, empty schema for every test."""
    Base.metadata.create_all(bind=engine)
    with TestClient(main.app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


def pytest_sessionfinish(session, exitstatus):
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
