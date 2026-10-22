import csv
import io
import json
import logging
import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from sqlalchemy.orm import Session

from backend.app.db.models import Instrument
from backend.app.db.session import SessionLocal
from backend.app.schemas.market import (
    ImportedHolding,
    ImportRowsSummary,
    PortfolioImportResponse,
    RowValidationError,
)
from backend.app.services.market_risk.market_data_service import MarketDataService
from backend.app.services.market_risk.ticker_normalizer import (
    CORPORATE_ALIASES,
    SYMBOL_CATALOGUE,
    get_symbol_currency,
)

logger = logging.getLogger(__name__)

# Maximum file size: 1 MB
MAX_CSV_BYTES = 1_048_576
# Maximum data rows: 500
MAX_CSV_ROWS = 500

HEADER_ALIASES: dict[str, set[str]] = {
    "symbol": {
        "symbol",
        "ticker",
        "instrument",
        "instrument name",
        "stock",
        "stock name",
        "security",
        "security name",
        "scrip",
        "scrip name",
        "company",
        "company name",
        "asset",
        "asset name",
        "trading symbol",
        "tradingsymbol",
        "name",
    },
    "isin": {
        "isin",
        "isin number",
        "isin code",
        "security isin",
    },
    "quantity": {
        "quantity",
        "qty",
        "shares",
        "units",
        "holding",
        "holdings",
        "volume",
        "net qty",
        "total qty",
        "holding qty",
        "available qty",
    },
    "avg_price": {
        "avg price",
        "avg cost",
        "average cost",
        "average price",
        "average buy price",
        "avg buy price",
        "buy price",
        "buy avg",
        "cost price",
        "purchase price",
        "buying price",
        "rate",
        "cost",
        "avg rate",
        "avg. cost",
        "avg. price",
    },
}

BROKER_SUFFIXES = ("-EQ", "-BE", "-BL", "-BZ", "-SM", "-ST")
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


def normalize_header_text(text: str) -> str:
    """Normalize a header string: lowercased, alphanumeric with single spaces."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def parse_number(val: Any) -> float:
    """
    Parses currency or formatted numbers (e.g. '1,234.50', '₹ 1,234.50', '$50', '(100)').
    Raises ValueError on invalid formats or non-finite numbers.
    """
    if val is None:
        raise ValueError("Missing value")
    s = str(val).strip()
    if not s:
        raise ValueError("Empty value")

    # Strip currency symbols and common indicators
    s = re.sub(r"^[₹$€£]|^(rs\.?|inr|usd)\s*", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"[₹$€£]|(rs\.?|inr|usd)$", "", s, flags=re.IGNORECASE).strip()

    # Accounting parentheses for negative numbers: (100.50) -> -100.50
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1].strip()

    # Remove thousand-separators and whitespace
    s = s.replace(",", "").replace(" ", "")

    val_f = float(s)
    if math.isnan(val_f) or math.isinf(val_f):
        raise ValueError("Invalid numeric value (NaN/Inf)")
    return val_f


def normalize_company_name(name: str) -> str:
    """Strip common corporate entity suffixes and punctuation for exact name matching."""
    s = name.upper()
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    s = re.sub(r"\b(LIMITED|LTD|PRIVATE|PVT|CORPORATION|CORP|INC|INCORPORATED|PLC|LLC|HOLDINGS)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class MarketDataPriceProvider:
    """Default price provider that fetches latest prices via MarketDataService."""

    def __init__(self, service: MarketDataService | None = None):
        self.service = service or MarketDataService()

    def get_latest_price(self, symbol: str) -> float:
        df, _ = self.service.get_symbol_price_history(symbol, allow_live=True)
        if df.empty:
            raise ValueError(f"No price observations available for '{symbol}'")
        col = "adj_close" if "adj_close" in df.columns else "close"
        latest = float(df[col].iloc[-1])
        if latest <= 0:
            raise ValueError(f"Latest price for '{symbol}' is non-positive ({latest})")
        return latest


class PortfolioImportService:
    """
    Parses broker CSV exports, handles header tolerance, resolves symbols,
    fetches latest prices, validates row errors, and calculates portfolio weights.
    """

    def __init__(self, price_provider: Any = None, db: Session | None = None):
        self.price_provider = price_provider or MarketDataPriceProvider()
        self.db = db

    def _get_db(self) -> tuple[Session, bool]:
        if self.db is not None:
            return self.db, False
        return SessionLocal(), True

    def _detect_delimiter_and_split(self, csv_text: str) -> tuple[str, list[tuple[int, str]]]:
        """
        Strips UTF-8 BOM, detects delimiter, and returns non-blank lines with 1-based original line numbers.
        """
        clean_text = csv_text.lstrip("\ufeff")
        raw_lines = clean_text.splitlines()

        # Find non-blank lines with 1-indexed original numbers
        indexed_lines: list[tuple[int, str]] = []
        for idx, line in enumerate(raw_lines, start=1):
            if line.strip():
                indexed_lines.append((idx, line))

        if not indexed_lines:
            raise ValueError("CSV file is empty.")

        # Determine delimiter
        sample_lines = [line for _, line in indexed_lines[:15]]
        sample_text = "\n".join(sample_lines)

        try:
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample_text, delimiters=",\t;").delimiter
        except Exception:
            # Fallback heuristic
            comma_count = sample_text.count(",")
            semicolon_count = sample_text.count(";")
            tab_count = sample_text.count("\t")

            if tab_count > comma_count and tab_count > semicolon_count:
                delimiter = "\t"
            elif semicolon_count > comma_count:
                delimiter = ";"
            else:
                delimiter = ","

        return delimiter, indexed_lines

    def _find_header(
        self, indexed_lines: list[tuple[int, str]], delimiter: str
    ) -> tuple[int, int, dict[str, str], dict[str, int]]:
        """
        Scans the first ~30 lines for a line containing both a symbol-like and a quantity-like header.
        Returns:
            header_line_num: 1-indexed original line number
            header_idx_in_list: index in indexed_lines
            header_mapping: canonical column -> actual CSV header text
            col_indices: canonical column -> column index in CSV row
        """
        max_scan = min(30, len(indexed_lines))

        for idx in range(max_scan):
            orig_line_num, line_str = indexed_lines[idx]
            reader = csv.reader([line_str], delimiter=delimiter)
            row = next(reader, [])
            if not row:
                continue

            col_map: dict[str, int] = {}
            found_headers: dict[str, str] = {}

            for col_idx, cell in enumerate(row):
                norm_cell = normalize_header_text(cell)
                if not norm_cell:
                    continue

                for canonical, aliases in HEADER_ALIASES.items():
                    if canonical not in col_map and norm_cell in aliases:
                        col_map[canonical] = col_idx
                        found_headers[canonical] = cell.strip()
                        break

            # Need both symbol-like (either 'symbol' or 'isin') and 'quantity'
            has_symbol = "symbol" in col_map or "isin" in col_map
            has_quantity = "quantity" in col_map

            if has_symbol and has_quantity:
                # If only ISIN was found as symbol-like, map symbol to it as well
                if "symbol" not in col_map and "isin" in col_map:
                    col_map["symbol"] = col_map["isin"]
                    found_headers["symbol"] = found_headers["isin"]

                return orig_line_num, idx, found_headers, col_map

        raise ValueError(
            "Could not find a valid CSV header with symbol/instrument and quantity columns within the first 30 lines."
        )

    def _resolve_symbol(
        self,
        raw_symbol: str,
        isin_hint: str | None,
        db: Session,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """
        Strict symbol resolution in order:
        (1) ISIN match against instruments.isin
        (2) Exact symbol match (with/without .NS and broker suffixes like -EQ)
        (3) Alias match from CORPORATE_ALIASES or Instrument.aliases_json
        (4) Exact normalised company-name match
        Never auto-picks a fuzzy match. Returns (resolved_meta, suggestions).
        """
        raw_sym = raw_symbol.strip()
        raw_upper = raw_sym.upper()

        # 1. ISIN match
        isin_candidate = isin_hint.strip().upper() if isin_hint else None
        if not isin_candidate and ISIN_PATTERN.match(raw_upper):
            isin_candidate = raw_upper

        if isin_candidate:
            inst = db.query(Instrument).filter(Instrument.isin == isin_candidate).first()
            if inst:
                return {
                    "symbol": inst.symbol,
                    "name": inst.name,
                    "currency": inst.currency or "INR",
                }, []

        # 2. Exact symbol match (strip broker suffixes like -EQ, -BE, etc.)
        base_sym = raw_upper
        for suffix in BROKER_SUFFIXES:
            if base_sym.endswith(suffix):
                base_sym = base_sym[: -len(suffix)]
                break

        # Check candidate symbols
        candidates = [raw_upper, base_sym]
        if not raw_upper.endswith(".NS") and not raw_upper.endswith(".BO") and not raw_upper.startswith("^"):
            candidates.append(f"{base_sym}.NS")

        for cand in candidates:
            if cand in SYMBOL_CATALOGUE:
                meta = SYMBOL_CATALOGUE[cand]
                return {
                    "symbol": meta["symbol"],
                    "name": meta["name"],
                    "currency": meta["currency"],
                }, []

            inst = db.query(Instrument).filter(Instrument.symbol == cand).first()
            if inst:
                return {
                    "symbol": inst.symbol,
                    "name": inst.name,
                    "currency": inst.currency or "INR",
                }, []

        # 3. Alias match
        if raw_upper in CORPORATE_ALIASES:
            alias_target = CORPORATE_ALIASES[raw_upper]["target"]
            norm_alias = SYMBOL_CATALOGUE.get(alias_target)
            if norm_alias:
                return {
                    "symbol": norm_alias["symbol"],
                    "name": norm_alias["name"],
                    "currency": norm_alias["currency"],
                }, []
            inst = db.query(Instrument).filter(Instrument.symbol == alias_target).first()
            if inst:
                return {
                    "symbol": inst.symbol,
                    "name": inst.name,
                    "currency": inst.currency or "INR",
                }, []
            return {
                "symbol": alias_target,
                "name": CORPORATE_ALIASES[raw_upper].get("name", alias_target),
                "currency": "INR",
            }, []

        if base_sym in CORPORATE_ALIASES:
            alias_target = CORPORATE_ALIASES[base_sym]["target"]
            norm_alias = SYMBOL_CATALOGUE.get(alias_target)
            if norm_alias:
                return {
                    "symbol": norm_alias["symbol"],
                    "name": norm_alias["name"],
                    "currency": norm_alias["currency"],
                }, []
            inst = db.query(Instrument).filter(Instrument.symbol == alias_target).first()
            if inst:
                return {
                    "symbol": inst.symbol,
                    "name": inst.name,
                    "currency": inst.currency or "INR",
                }, []
            return {
                "symbol": alias_target,
                "name": CORPORATE_ALIASES[base_sym].get("name", alias_target),
                "currency": "INR",
            }, []

        # Check Instrument.aliases_json in DB
        alias_match = db.query(Instrument).filter(Instrument.aliases_json.ilike(f'%"{raw_upper}"%')).first()
        if alias_match:
            return {
                "symbol": alias_match.symbol,
                "name": alias_match.name,
                "currency": alias_match.currency or "INR",
            }, []

        # 4. Exact normalised company-name match
        norm_query_name = normalize_company_name(raw_sym)
        if norm_query_name:
            # Check catalogue names
            for cat_sym, cat_meta in SYMBOL_CATALOGUE.items():
                if normalize_company_name(cat_meta.get("name", "")) == norm_query_name:
                    return {
                        "symbol": cat_meta["symbol"],
                        "name": cat_meta["name"],
                        "currency": cat_meta["currency"],
                    }, []

            # Check DB instruments table
            # Fast query on candidate names
            matched_insts = (
                db.query(Instrument)
                .filter(Instrument.name.ilike(f"%{raw_sym[:6]}%"))
                .limit(20)
                .all()
            )
            for inst in matched_insts:
                if normalize_company_name(inst.name) == norm_query_name:
                    return {
                        "symbol": inst.symbol,
                        "name": inst.name,
                        "currency": inst.currency or "INR",
                    }, []

        # No match found -> never auto-pick fuzzy match!
        # Search suggestions
        try:
            market_service = MarketDataService()
            search_res = market_service.search_symbols(query=raw_sym, limit=3, db=db)
            if isinstance(search_res, tuple):
                search_res = search_res[0]
            suggestions = [{"symbol": s["symbol"], "name": s.get("name", s["symbol"])} for s in search_res[:3]]
        except Exception:
            suggestions = []

        return None, suggestions

    def import_csv(
        self,
        csv_text: str,
        filename: str | None = None,
    ) -> PortfolioImportResponse:
        """
        Parses and validates a broker holdings export.
        """
        # 1. Size guard
        byte_len = len(csv_text.encode("utf-8"))
        if byte_len > MAX_CSV_BYTES:
            raise ValueError(f"CSV file exceeds maximum allowed size of 1 MB (received {byte_len / 1024 / 1024:.2f} MB).")

        delimiter, indexed_lines = self._detect_delimiter_and_split(csv_text)

        header_orig_num, header_idx, header_mapping, col_indices = self._find_header(indexed_lines, delimiter)

        data_lines = indexed_lines[header_idx + 1 :]
        if not data_lines:
            raise ValueError("CSV contains a header but no data rows.")

        if len(data_lines) > MAX_CSV_ROWS:
            raise ValueError(f"CSV exceeds maximum allowed limit of {MAX_CSV_ROWS} rows (received {len(data_lines)} rows).")

        errors: list[RowValidationError] = []
        warnings: list[str] = []

        sym_col = col_indices["symbol"]
        qty_col = col_indices["quantity"]
        avg_col = col_indices.get("avg_price")
        isin_col = col_indices.get("isin")

        db, should_close = self._get_db()

        # Temporary structure for rows that pass structural validation
        # row_info: {row, symbol_meta, quantity, avg_price}
        valid_rows: list[dict[str, Any]] = []

        try:
            for orig_line_num, line_str in data_lines:
                reader = csv.reader([line_str], delimiter=delimiter)
                row = next(reader, [])
                if not row or all(not str(c).strip() for c in row):
                    continue

                # 1. Check symbol
                raw_sym = row[sym_col].strip() if sym_col < len(row) else ""
                raw_isin = row[isin_col].strip() if isin_col is not None and isin_col < len(row) else None

                if not raw_sym and not raw_isin:
                    errors.append(
                        RowValidationError(
                            row=orig_line_num,
                            field="symbol",
                            message="Symbol or instrument name is missing or empty.",
                            offending_value="",
                        )
                    )
                    continue

                # 2. Check quantity
                raw_qty = row[qty_col].strip() if qty_col < len(row) else ""
                if not raw_qty:
                    errors.append(
                        RowValidationError(
                            row=orig_line_num,
                            field="quantity",
                            message="Quantity is required and cannot be empty.",
                            offending_value="",
                        )
                    )
                    continue

                try:
                    qty = parse_number(raw_qty)
                    if qty <= 0:
                        errors.append(
                            RowValidationError(
                                row=orig_line_num,
                                field="quantity",
                                message=f"Quantity must be greater than zero, got {qty}.",
                                offending_value=raw_qty,
                            )
                        )
                        continue
                except ValueError as ve:
                    errors.append(
                        RowValidationError(
                            row=orig_line_num,
                            field="quantity",
                            message=f"Invalid quantity '{raw_qty}': {ve}.",
                            offending_value=raw_qty,
                        )
                    )
                    continue

                # 3. Check avg_price (optional)
                avg_price: float | None = None
                if avg_col is not None and avg_col < len(row):
                    raw_avg = row[avg_col].strip()
                    if raw_avg:
                        try:
                            avg_price = parse_number(raw_avg)
                            if avg_price <= 0:
                                errors.append(
                                    RowValidationError(
                                        row=orig_line_num,
                                        field="avg_price",
                                        message=f"Average price must be greater than zero, got {avg_price}.",
                                        offending_value=raw_avg,
                                    )
                                )
                                continue
                        except ValueError as ve:
                            errors.append(
                                RowValidationError(
                                    row=orig_line_num,
                                    field="avg_price",
                                    message=f"Invalid average price '{raw_avg}': {ve}.",
                                    offending_value=raw_avg,
                                )
                            )
                            continue

                # 4. Resolve symbol
                sym_to_resolve = raw_sym or raw_isin or ""
                resolved_meta, suggestions = self._resolve_symbol(
                    raw_symbol=sym_to_resolve,
                    isin_hint=raw_isin,
                    db=db,
                )

                if not resolved_meta:
                    errors.append(
                        RowValidationError(
                            row=orig_line_num,
                            field="symbol",
                            message=f"Unknown symbol '{sym_to_resolve}'.",
                            offending_value=sym_to_resolve,
                            suggestions=suggestions,
                        )
                    )
                    continue

                valid_rows.append(
                    {
                        "row": orig_line_num,
                        "symbol": resolved_meta["symbol"],
                        "name": resolved_meta["name"],
                        "currency": resolved_meta.get("currency") or get_symbol_currency(resolved_meta["symbol"]),
                        "quantity": qty,
                        "avg_price": avg_price,
                    }
                )

        finally:
            if should_close:
                db.close()

        # 5. Fetch latest prices in parallel (cap 8 workers)
        unique_symbols = list({r["symbol"] for r in valid_rows})
        price_map: dict[str, float] = {}
        price_errors: dict[str, str] = {}

        if unique_symbols:
            max_workers = min(8, len(unique_symbols))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_sym = {
                    executor.submit(self.price_provider.get_latest_price, sym): sym for sym in unique_symbols
                }
                for future in as_completed(future_to_sym):
                    sym = future_to_sym[future]
                    try:
                        price_map[sym] = future.result()
                    except Exception as exc:
                        price_errors[sym] = str(exc)

        # Filter out rows whose price fetch failed
        priced_rows: list[dict[str, Any]] = []
        for r in valid_rows:
            sym = r["symbol"]
            if sym in price_errors:
                errors.append(
                    RowValidationError(
                        row=r["row"],
                        field="symbol",
                        message=f"Price data could not be fetched for '{sym}': {price_errors[sym]}.",
                        offending_value=sym,
                    )
                )
            else:
                r["latest_price"] = price_map[sym]
                priced_rows.append(r)

        # 6. Duplicate merging (sum quantity, quantity-weighted average price)
        grouped_by_symbol: dict[str, list[dict[str, Any]]] = {}
        for r in priced_rows:
            grouped_by_symbol.setdefault(r["symbol"], []).append(r)

        merged_holdings: list[ImportedHolding] = []
        merged_count = 0

        for sym, rows in grouped_by_symbol.items():
            first = rows[0]
            total_qty = sum(r["quantity"] for r in rows)

            # Quantity-weighted average price
            rows_with_avg = [r for r in rows if r["avg_price"] is not None]
            if rows_with_avg:
                weighted_sum = sum(r["quantity"] * r["avg_price"] for r in rows_with_avg)
                weight_qty = sum(r["quantity"] for r in rows_with_avg)
                combined_avg_price: float | None = round(weighted_sum / weight_qty, 4) if weight_qty > 0 else None
            else:
                combined_avg_price = None

            if len(rows) > 1:
                merged_count += len(rows) - 1
                row_nums = ", ".join(str(r["row"]) for r in rows)
                warnings.append(
                    f"Merged duplicate symbol '{sym}' across {len(rows)} rows (rows {row_nums}): combined quantity {total_qty:g}."
                )

            latest_price = first["latest_price"]
            pos_val = total_qty * latest_price

            unrealized_pnl = None
            unrealized_pnl_pct = None
            if combined_avg_price is not None:
                unrealized_pnl = round((latest_price - combined_avg_price) * total_qty, 2)
                if combined_avg_price > 0:
                    unrealized_pnl_pct = round(((latest_price - combined_avg_price) / combined_avg_price) * 100, 2)

            merged_holdings.append(
                ImportedHolding(
                    symbol=sym,
                    name=first["name"],
                    quantity=total_qty,
                    latest_price=round(latest_price, 4),
                    position_value=round(pos_val, 2),
                    weight=0.0,  # calculated below
                    currency=first["currency"],
                    avg_price=combined_avg_price,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    merged_count=len(rows),
                )
            )

        # 7. Compute weights
        total_portfolio_value = sum(h.position_value for h in merged_holdings)

        if total_portfolio_value > 0:
            for h in merged_holdings:
                h.weight = round(h.position_value / total_portfolio_value, 6)

            # Ensure sum of weights equals exactly 1.0 (absorb tiny floating delta into largest holding)
            current_sum = sum(h.weight for h in merged_holdings)
            delta = round(1.0 - current_sum, 6)
            if delta != 0 and merged_holdings:
                largest = max(merged_holdings, key=lambda x: x.weight)
                largest.weight = round(largest.weight + delta, 6)

        # 8. Infer currency
        distinct_currencies = {h.currency for h in merged_holdings}
        inferred_currency = distinct_currencies.pop() if len(distinct_currencies) == 1 else None

        # Sort errors by row number
        errors.sort(key=lambda e: e.row)

        total_rows_count = len(data_lines)
        imported_count = len(merged_holdings)
        error_rows_count = len(errors)

        return PortfolioImportResponse(
            filename=filename,
            header_mapping=header_mapping,
            holdings=merged_holdings,
            errors=errors,
            warnings=warnings,
            rows=ImportRowsSummary(
                total=total_rows_count,
                imported=imported_count,
                errors=error_rows_count,
                merged=merged_count,
            ),
            total_value=round(total_portfolio_value, 2),
            inferred_currency=inferred_currency,
        )
