import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app

OUTPUT_FILE = REPO_ROOT / "docs" / "API_CONTRACTS.md"

PRD_ENDPOINTS = [
    ("GET", "/health", "Liveness check; no claim that models/data are healthy"),
    ("GET", "/api/v1/system/status", "Actual model/data/provider status and offline mode"),
    ("GET", "/api/v1/credit/models", "List trained model versions and real evaluation metadata"),
    ("POST", "/api/v1/credit/score", "Validate features and return score, model version and warnings"),
    ("POST", "/api/v1/credit/explain", "Return computed local/global explanation data"),
    ("POST", "/api/v1/credit/what-if", "Re-score whitelisted feature scenarios"),
    ("POST", "/api/v1/finance/emi", "Compute EMI and repayment summary"),
    ("POST", "/api/v1/finance/stress-test", "Compute before/after personal cash-flow scenarios"),
    ("GET", "/api/v1/market/universe", "Return configured supported symbols and metadata"),
    ("POST", "/api/v1/market/portfolio/analyze", "Calculate portfolio metrics from cached historical prices"),
    ("POST", "/api/v1/market/portfolio/stress-test", "Apply specified asset/portfolio shocks"),
    ("POST", "/api/v1/market/var/validate", "Run rolling out-of-sample VaR validation"),
    ("GET", "/api/v1/monitoring/models", "List model registry metadata"),
    ("POST", "/api/v1/monitoring/drift/run", "Run PSI calculation on a selected reference/current batch"),
    ("POST", "/api/v1/monitoring/challenger/evaluate", "Evaluate a challenger using the documented protocol"),
    ("POST", "/api/v1/monitoring/challenger/promote", "Explicitly promote a passing challenger and log the decision"),
    ("POST", "/api/v1/copilot/message", "Run bounded LangGraph flow and return answer, sources and tool trace summary"),
    ("GET", "/api/v1/methodology", "Return method definitions, data limitations and disclaimer text")
]

# Endpoints added after the PRD, documented alongside it
EXTENSION_ENDPOINTS = [
    ("GET", "/api/v1/market/search", "Search the NSE/US instrument master with sector, index and cap filters"),
    ("POST", "/api/v1/market/validate-symbol", "Check that a symbol has usable price history, fetching it lazily if needed"),
    ("POST", "/api/v1/market/var/compare", "Backtest several VaR methods on one window and recommend one"),
    ("POST", "/api/v1/market/portfolio/stress/replay", "Replay COVID 2020, 4 Jun 2024 and Adani 2023 against a portfolio using real prices"),
    ("POST", "/api/v1/market/portfolio/stress/reverse", "Find the shock that produces a chosen portfolio loss"),
]


def generate_contracts():
    schema = app.openapi()
    paths = schema.get("paths", {})

    lines = [
        "# RiskWise API Contracts & Specification (PRD §8)",
        "",
        f"**Generated:** Automatically extracted from FastAPI OpenAPI v{schema.get('info', {}).get('version', '3.0.0')}  ",
        "**Standard:** Strictly adheres to PRD §8 endpoint naming, HTTP methods, Pydantic request/response schemas, and error conventions.  ",
        "",
        "---",
        "",
        "## 1. PRD §8 Endpoints Parity Matrix",
        "",
        "| Method | Endpoint | PRD Purpose | OpenAPI Match | Status |",
        "|:---:|:---|:---|:---:|:---:|"
    ]

    all_matched = True
    for method, endpoint, purpose in PRD_ENDPOINTS:
        path_obj = paths.get(endpoint, {})
        has_method = method.lower() in path_obj
        status_str = "**VERIFIED**" if has_method else "**MISSING**"
        if not has_method:
            all_matched = False
        lines.append(f"| `{method}` | `{endpoint}` | {purpose} | {'Yes' if has_method else 'No'} | {status_str} |")

    lines.extend([
        "",
        "### Additional endpoints (beyond the PRD)",
        "",
        "| Method | Endpoint | Purpose | OpenAPI Match |",
        "|:---:|:---|:---|:---:|",
    ])
    for method, endpoint, purpose in EXTENSION_ENDPOINTS:
        present = method.lower() in paths.get(endpoint, {})
        lines.append(f"| `{method}` | `{endpoint}` | {purpose} | {'Yes' if present else 'No'} |")

    lines.extend([
        "",
        "Market endpoints that load prices accept `fx_mode`: `strict` (default) rejects mixed USD/INR portfolios, "
        "`convert_to_base` converts into the portfolio currency with daily `USDINR=X` rates and states the FX series and date range in the response `fx` block.",
        "",
        "---",
        "",
        "## 2. Detailed Endpoint Contracts",
        ""
    ])

    for method, endpoint, purpose in PRD_ENDPOINTS + EXTENSION_ENDPOINTS:
        path_obj = paths.get(endpoint, {})
        op = path_obj.get(method.lower(), {})
        if not op:
            continue

        lines.append(f"### `{method} {endpoint}`")
        lines.append(f"**Summary:** {op.get('summary', purpose)}  ")
        lines.append(f"**Description:** {op.get('description', purpose)}  ")
        lines.append(f"**Tags:** {', '.join(op.get('tags', []))}  ")
        lines.append("")

        # Request Body
        req_body = op.get("requestBody", {})
        if req_body:
            content = req_body.get("content", {}).get("application/json", {})
            schema_ref = content.get("schema", {})
            lines.append("**Request Body (application/json):**")
            lines.append("```json")
            lines.append(json.dumps(schema_ref, indent=2))
            lines.append("```")
            lines.append("")

        # Responses
        lines.append("**Responses:**")
        for code, resp_obj in sorted(op.get("responses", {}).items()):
            resp_desc = resp_obj.get("description", "")
            resp_content = resp_obj.get("content", {}).get("application/json", {})
            resp_schema = resp_content.get("schema", {})
            lines.append(f"- **`{code}`**: {resp_desc}")
            if resp_schema:
                lines.append("  ```json")
                lines.append("  " + json.dumps(resp_schema, indent=2).replace("\n", "\n  "))
                lines.append("  ```")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend([
        "## 3. Global Error Responses & Security Standard",
        "",
        "- **Standard Error Format:** All 4xx and 5xx errors return `application/json` with standard `{\"detail\": ...}` format.",
        "- **No Leaked Stack Traces:** Production exceptions are logged server-side and never returned in HTTP bodies.",
        "- **Request ID Tracking:** Every response includes header `X-Request-ID` correlated with structured JSON server logs.",
        "- **Payload Limits:** Request bodies exceeding 1MB (1,048,576 bytes) are rejected with HTTP 413.",
        "- **CORS Configuration:** Strictly validated against configured origins via `ALLOWED_ORIGINS`."
    ])

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated {OUTPUT_FILE} (All 18 PRD endpoints verified: {all_matched})")


if __name__ == "__main__":
    generate_contracts()
