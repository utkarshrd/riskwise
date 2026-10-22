"""
test_market_search_and_universe.py

Validates Task A1:
- DB-backed fuzzy search over all official NSE symbols
- Filters: sector, index, cap_bucket, currency
- Pagination: page and limit
- Universe endpoint: returns total_instruments, sectors, cap_buckets, indices
- Backward compatibility of response shapes
"""

from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_market_universe_db_backed_metadata():
    """Verify /market/universe returns full instrument master metrics while maintaining backward compatibility."""
    res = client.get("/api/v1/market/universe")
    assert res.status_code == 200
    data = res.json()

    # Core backward-compatible fields
    assert "provider" in data
    assert "supported_currencies" in data
    assert "INR" in data["supported_currencies"]
    assert "USD" in data["supported_currencies"]
    assert "frequency" in data
    assert "price_field" in data
    assert data["price_field"] == "adj_close"
    assert "supported_symbols" in data
    assert len(data["supported_symbols"]) > 20
    assert "symbol_currencies" in data

    # New instrument master fields
    assert "total_instruments" in data
    assert data["total_instruments"] >= 2600
    assert "sectors" in data
    assert len(data["sectors"]) > 0
    assert "cap_buckets" in data
    assert len(data["cap_buckets"]) > 0
    assert "indices" in data
    assert len(data["indices"]) > 0


def test_search_fuzzy_official_nse_symbols():
    """Verify searching for an official NSE equity ingested from EQUITY_L.csv."""
    res = client.get("/api/v1/market/search?q=20MICRONS")
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == "20MICRONS"
    assert data["total"] >= 1
    assert any(r["symbol"] == "20MICRONS.NS" for r in data["results"])
    match = next(r for r in data["results"] if r["symbol"] == "20MICRONS.NS")
    assert match["currency"] == "INR"
    assert match["exchange"] == "NSE"


def test_search_pagination():
    """Verify pagination returns the expected slice and total count."""
    res_p1 = client.get("/api/v1/market/search?limit=5&page=1")
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert data_p1["page"] == 1
    assert data_p1["page_size"] == 5
    assert len(data_p1["results"]) == 5
    assert data_p1["total"] >= 2600

    res_p2 = client.get("/api/v1/market/search?limit=5&page=2")
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert data_p2["page"] == 2
    assert len(data_p2["results"]) == 5

    # Check distinct pages
    syms_p1 = [r["symbol"] for r in data_p1["results"]]
    syms_p2 = [r["symbol"] for r in data_p2["results"]]
    assert syms_p1 != syms_p2


def test_search_filter_by_sector():
    """Verify sector filter restricts results to matched sector."""
    res = client.get("/api/v1/market/search?sector=Information%20Technology")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["results"]:
        assert "Information Technology" in (item["sector"] or "")


def test_search_filter_by_index():
    """Verify index filter restricts results to index constituents."""
    res = client.get("/api/v1/market/search?index=NIFTY%2050")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["results"]:
        assert any("NIFTY 50" in idx for idx in (item.get("index_memberships") or []))


def test_search_filter_by_cap_bucket():
    """Verify cap_bucket filter restricts results to the specified cap bucket."""
    res = client.get("/api/v1/market/search?cap_bucket=Large%20Cap")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["results"]:
        assert item["cap_bucket"] == "Large Cap"
