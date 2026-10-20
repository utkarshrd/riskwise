from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

PRD_ENDPOINTS = [
    ("GET", "/health"),
    ("GET", "/api/v1/system/status"),
    ("GET", "/api/v1/credit/models"),
    ("POST", "/api/v1/credit/score"),
    ("POST", "/api/v1/credit/explain"),
    ("POST", "/api/v1/credit/what-if"),
    ("POST", "/api/v1/finance/emi"),
    ("POST", "/api/v1/finance/stress-test"),
    ("GET", "/api/v1/market/universe"),
    ("POST", "/api/v1/market/portfolio/analyze"),
    ("POST", "/api/v1/market/portfolio/stress-test"),
    ("POST", "/api/v1/market/var/validate"),
    ("GET", "/api/v1/monitoring/models"),
    ("POST", "/api/v1/monitoring/drift/run"),
    ("POST", "/api/v1/monitoring/challenger/evaluate"),
    ("POST", "/api/v1/monitoring/challenger/promote"),
    ("POST", "/api/v1/copilot/message"),
    ("GET", "/api/v1/methodology")
]


def test_openapi_schema_contains_all_18_prd_endpoints():
    schema = app.openapi()
    paths = schema.get("paths", {})

    for method, path in PRD_ENDPOINTS:
        assert path in paths, f"PRD endpoint {path} missing from OpenAPI schema"
        path_item = paths[path]
        assert method.lower() in path_item, f"Method {method} missing for endpoint {path}"


def test_api_contract_request_id_header_present():
    res = client.get("/health")
    assert res.status_code == 200
    assert "x-request-id" in res.headers
    assert len(res.headers["x-request-id"]) > 0


def test_api_contract_payload_size_limit_rejection():
    big_body = "a" * (2 * 1024 * 1024)  # 2MB
    res = client.post("/api/v1/copilot/message", content=big_body, headers={"Content-Length": str(len(big_body))})
    assert res.status_code == 413
    assert "Payload too large" in res.json()["detail"]


def test_api_contract_system_status_honesty():
    res = client.get("/api/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "migration_revision" in data
    assert "snapshot_checksum_verified" in data
    assert "snapshot_retrieval_timestamp" in data
    assert "vector_index_chunk_count" in data
    assert "llm_status" in data
    assert "copilot_mode" in data
    assert data["snapshot_checksum_verified"] is True
    assert data["vector_index_chunk_count"] > 0
