from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check():
    """Verify /health returns 200 and 'ok' status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_system_status():
    """Verify /api/v1/system/status returns genuine computed offline and artifact statuses."""
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "offline_mode" in data
    assert isinstance(data["credit_model_loaded"], bool)
    assert isinstance(data["market_snapshot_loaded"], bool)
    assert isinstance(data["market_tickers_available"], list)
    assert isinstance(data["rag_corpus_loaded"], bool)
    # Rag corpus manifest was created, so rag_corpus_loaded should be True
    assert data["rag_corpus_loaded"] is True
    # Model and market snapshots are now loaded
    assert data["credit_model_loaded"] is True
    assert data["active_model_version"] is not None
    assert data["market_snapshot_loaded"] is True

