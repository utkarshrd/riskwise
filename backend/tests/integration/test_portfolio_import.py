import pytest
from backend.app.api.v1.market import get_portfolio_import_service
from backend.app.main import app
from backend.app.services.market_risk.portfolio_import import (
    PortfolioImportService,
    parse_number,
)
from fastapi.testclient import TestClient


class FakePriceProvider:
    """Mock price provider for deterministic offline testing."""

    def __init__(self, prices: dict[str, float] | None = None, failing_symbols: set[str] | None = None):
        self.prices = prices or {
            "RELIANCE.NS": 2500.0,
            "TCS.NS": 3500.0,
            "INFY.NS": 1500.0,
            "HDFCBANK.NS": 1600.0,
            "AAPL": 200.0,
            "MSFT": 400.0,
            "ETERNAL.NS": 250.0,
        }
        self.failing_symbols = failing_symbols or set()

    def get_latest_price(self, symbol: str) -> float:
        if symbol in self.failing_symbols:
            raise ValueError(f"Provider connection error for {symbol}")
        if symbol in self.prices:
            return self.prices[symbol]
        raise ValueError(f"No price available for {symbol}")


@pytest.fixture
def fake_service():
    return PortfolioImportService(price_provider=FakePriceProvider())


def test_parse_number():
    assert parse_number("1,234.50") == 1234.5
    assert parse_number("₹ 2,450.00") == 2450.0
    assert parse_number("₹2,450.00") == 2450.0
    assert parse_number("Rs. 500") == 500.0
    assert parse_number("$150.25") == 150.25
    assert parse_number("100") == 100.0
    assert parse_number("(50.5)") == -50.5

    with pytest.raises(ValueError):
        parse_number("")
    with pytest.raises(ValueError):
        parse_number("abc")


def test_zerodha_format_import(fake_service):
    csv_text = """Instrument,Qty.,Avg. cost,LTP,Cur. val,P&L
RELIANCE-EQ,10,"2,400.00",2500,25000,1000
TCS-EQ,20,"3,200.00",3500,70000,6000
"""
    res = fake_service.import_csv(csv_text, filename="zerodha_holdings.csv")

    assert res.filename == "zerodha_holdings.csv"
    assert res.header_mapping["symbol"] == "Instrument"
    assert res.header_mapping["quantity"] == "Qty."
    assert res.header_mapping["avg_price"] == "Avg. cost"

    assert len(res.holdings) == 2
    assert len(res.errors) == 0
    assert res.rows.total == 2
    assert res.rows.imported == 2
    assert res.rows.errors == 0
    assert res.rows.merged == 0

    rel = next(h for h in res.holdings if h.symbol == "RELIANCE.NS")
    assert rel.quantity == 10.0
    assert rel.latest_price == 2500.0
    assert rel.position_value == 25000.0
    assert rel.avg_price == 2400.0
    assert rel.unrealized_pnl == 1000.0
    assert rel.unrealized_pnl_pct == pytest.approx(4.17, rel=1e-2)

    tcs = next(h for h in res.holdings if h.symbol == "TCS.NS")
    assert tcs.quantity == 20.0
    assert tcs.latest_price == 3500.0
    assert tcs.position_value == 70000.0

    total_val = 25000.0 + 70000.0
    assert res.total_value == total_val
    assert rel.weight == pytest.approx(25000.0 / total_val, abs=1e-5)
    assert tcs.weight == pytest.approx(70000.0 / total_val, abs=1e-5)
    assert sum(h.weight for h in res.holdings) == pytest.approx(1.0, abs=1e-5)
    assert res.inferred_currency == "INR"


def test_groww_format_with_isin(fake_service):
    csv_text = """Stock Name,ISIN,Quantity,Average buy price,Buy value,Closing price
Reliance Industries Ltd,INE002A01018,10,₹ 2,400.00,24000,2500
Tata Consultancy Services,INE467B01029,5,₹ 3,400.00,17000,3500
"""
    res = fake_service.import_csv(csv_text, filename="groww_portfolio.csv")

    assert res.header_mapping["symbol"] == "Stock Name"
    assert res.header_mapping["isin"] == "ISIN"
    assert res.header_mapping["quantity"] == "Quantity"
    assert res.header_mapping["avg_price"] == "Average buy price"

    assert len(res.holdings) == 2
    assert len(res.errors) == 0
    syms = {h.symbol for h in res.holdings}
    assert syms == {"RELIANCE.NS", "TCS.NS"}


def test_metadata_lines_above_header(fake_service):
    csv_text = """Broker: ABC Securities Ltd
Client ID: 98765432
Date of Export: 2026-10-22
Currency: INR

Instrument,Quantity,Avg Price
RELIANCE,10,2400
INFY,30,1400
"""
    res = fake_service.import_csv(csv_text)
    assert res.rows.total == 2
    assert len(res.holdings) == 2
    assert {h.symbol for h in res.holdings} == {"RELIANCE.NS", "INFY.NS"}


def test_utf8_bom_and_semicolon_delimiter(fake_service):
    csv_text = "\ufeffInstrument;Quantity;Avg Price\nRELIANCE;10;2500\n"
    res = fake_service.import_csv(csv_text)
    assert len(res.holdings) == 1
    assert res.holdings[0].symbol == "RELIANCE.NS"
    assert res.holdings[0].quantity == 10.0


def test_tab_delimiter(fake_service):
    csv_text = "Symbol\tQuantity\tAverage Price\nRELIANCE\t10\t2500\nTCS\t5\t3500\n"
    res = fake_service.import_csv(csv_text)
    assert len(res.holdings) == 2
    assert {h.symbol for h in res.holdings} == {"RELIANCE.NS", "TCS.NS"}


def test_validation_errors_and_unimported_rows(fake_service):
    csv_text = """Instrument,Quantity,Avg Price
RELIANCE,10,2400
,5,2000
TCS,-3,3200
INFY,0,1500
HDFCBANK,not_a_number,1600
AAPL,10,bad_price
UNKNOWNSTOCKXYZ,15,100
"""
    res = fake_service.import_csv(csv_text)

    # 1 valid row (RELIANCE) + 6 error rows = 7 total rows
    assert res.rows.total == 7
    assert res.rows.imported == 1
    assert res.rows.errors == 6
    assert len(res.holdings) == 1
    assert res.holdings[0].symbol == "RELIANCE.NS"

    assert len(res.errors) == 6
    error_fields = {e.field for e in res.errors}
    assert "symbol" in error_fields
    assert "quantity" in error_fields
    assert "avg_price" in error_fields

    # Check unknown symbol suggestions
    unknown_err = next(e for e in res.errors if e.offending_value == "UNKNOWNSTOCKXYZ")
    assert unknown_err.suggestions is not None
    assert len(unknown_err.suggestions) <= 3


def test_missing_price_error(fake_service):
    # Provider without price for INFY
    provider = FakePriceProvider(failing_symbols={"INFY.NS"})
    service = PortfolioImportService(price_provider=provider)

    csv_text = """Instrument,Quantity,Avg Price
RELIANCE,10,2400
INFY,20,1500
"""
    res = service.import_csv(csv_text)
    assert res.rows.total == 2
    assert res.rows.imported == 1
    assert res.rows.errors == 1
    assert len(res.holdings) == 1
    assert res.holdings[0].symbol == "RELIANCE.NS"

    price_err = res.errors[0]
    assert price_err.field == "symbol"
    assert "Price data could not be fetched" in price_err.message
    assert price_err.offending_value == "INFY.NS"


def test_duplicate_symbol_merging(fake_service):
    csv_text = """Instrument,Quantity,Avg Price
RELIANCE,10,2400
TCS,10,3000
RELIANCE,20,2700
TCS,30,3500
"""
    res = fake_service.import_csv(csv_text)

    assert res.rows.total == 4
    assert res.rows.imported == 2
    assert res.rows.merged == 2
    assert res.rows.errors == 0
    assert len(res.holdings) == 2

    rel = next(h in res.holdings and h for h in res.holdings if h.symbol == "RELIANCE.NS")
    assert rel.quantity == 30.0  # 10 + 20
    # Weighted avg: (10*2400 + 20*2700) / 30 = (24000 + 54000) / 30 = 2600.0
    assert rel.avg_price == 2600.0
    assert rel.merged_count == 2

    tcs = next(h in res.holdings and h for h in res.holdings if h.symbol == "TCS.NS")
    assert tcs.quantity == 40.0  # 10 + 30
    # Weighted avg: (10*3000 + 30*3500) / 40 = (30000 + 105000) / 40 = 3375.0
    assert tcs.avg_price == 3375.0
    assert tcs.merged_count == 2

    assert len(res.warnings) == 2
    assert any("Merged duplicate symbol 'RELIANCE.NS'" in w for w in res.warnings)
    assert any("Merged duplicate symbol 'TCS.NS'" in w for w in res.warnings)


def test_hand_calculated_weights_and_total_value(fake_service):
    csv_text = """Instrument,Quantity
RELIANCE,10
TCS,15
"""
    # Prices: RELIANCE = 2500, TCS = 3500
    # Pos values: RELIANCE = 25,000, TCS = 52,500
    # Total = 77,500
    # Weight RELIANCE = 25000 / 77500 = 0.322581
    # Weight TCS = 52500 / 77500 = 0.677419
    res = fake_service.import_csv(csv_text)

    assert res.total_value == 77500.0
    rel = next(h for h in res.holdings if h.symbol == "RELIANCE.NS")
    tcs = next(h for h in res.holdings if h.symbol == "TCS.NS")

    assert rel.position_value == 25000.0
    assert tcs.position_value == 52500.0
    assert rel.weight == pytest.approx(25000.0 / 77500.0, abs=1e-5)
    assert tcs.weight == pytest.approx(52500.0 / 77500.0, abs=1e-5)
    assert sum(h.weight for h in res.holdings) == pytest.approx(1.0, abs=1e-5)


def test_mixed_currency_inferred():
    fake_service = PortfolioImportService(price_provider=FakePriceProvider())
    csv_text = """Instrument,Quantity
RELIANCE,10
AAPL,5
"""
    res = fake_service.import_csv(csv_text)
    assert len(res.holdings) == 2
    assert res.inferred_currency is None  # Mixed INR + USD


def test_size_and_row_limits(fake_service):
    # Test > 1 MB (1.2 MB text)
    huge_csv = "Instrument,Quantity\n" + ("RELIANCE,10\n" * 100000)
    with pytest.raises(ValueError, match="exceeds maximum allowed size of 1 MB"):
        fake_service.import_csv(huge_csv)

    # Test > 500 rows (under 1 MB)
    too_many_rows = "Instrument,Quantity\n" + ("RELIANCE,10\n" * 505)
    with pytest.raises(ValueError, match="exceeds maximum allowed limit of 500 rows"):
        fake_service.import_csv(too_many_rows)


def test_api_endpoint_with_dependency_override():
    client = TestClient(app)
    app.dependency_overrides[get_portfolio_import_service] = lambda: PortfolioImportService(
        price_provider=FakePriceProvider()
    )

    try:
        payload = {
            "csv_text": "Instrument,Qty.,Avg. cost\nRELIANCE-EQ,10,2400\nTCS-EQ,20,3200",
            "filename": "my_portfolio.csv",
        }
        resp = client.post("/api/v1/market/portfolio/import", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["filename"] == "my_portfolio.csv"
        assert len(data["holdings"]) == 2
        assert data["total_value"] == 95000.0
        assert data["inferred_currency"] == "INR"
        assert data["rows"]["imported"] == 2
        assert data["rows"]["errors"] == 0

        # Invalid CSV with no header
        resp_bad = client.post(
            "/api/v1/market/portfolio/import",
            json={"csv_text": "random text line without columns", "filename": "bad.csv"},
        )
        assert resp_bad.status_code == 400
    finally:
        app.dependency_overrides.clear()
