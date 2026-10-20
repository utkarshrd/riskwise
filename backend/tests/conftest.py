"""
Pytest conftest: ensure the database schema is initialized before any test
that exercises code-paths which touch SQLAlchemy models.

The TestClient triggers the FastAPI lifespan which calls init_db(), but
the call path is async and the schema may not be committed to the engine
used by the synchronous Session until the first request. Creating tables
here unconditionally guarantees they exist.
"""
import pytest
from backend.app.db.init_db import init_db


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Idempotently create all tables before the test session starts."""
    init_db()


@pytest.fixture(autouse=True)
def block_network_access(monkeypatch):
    """
    PRD Ground Rule: Tests are strictly offline and deterministic.
    Block all outbound external network connections during tests while
    allowing internal loopback pipes required by asyncio event loop.
    """
    import socket
    real_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) and len(address) > 0 else ""
        if host in ("localhost", "127.0.0.1", "::1", "testserver", ""):
            return real_connect(self, address)
        raise RuntimeError(f"External network access blocked during tests! Attempted connect to: {address}")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
