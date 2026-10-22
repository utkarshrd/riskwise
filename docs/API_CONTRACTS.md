# RiskWise API Contracts & Specification (PRD §8)

**Generated:** Automatically extracted from FastAPI OpenAPI v3.0.0  
**Standard:** Strictly adheres to PRD §8 endpoint naming, HTTP methods, Pydantic request/response schemas, and error conventions.  

---

## 1. PRD §8 Endpoints Parity Matrix

| Method | Endpoint | PRD Purpose | OpenAPI Match | Status |
|:---:|:---|:---|:---:|:---:|
| `GET` | `/health` | Liveness check; no claim that models/data are healthy | Yes | **VERIFIED** |
| `GET` | `/api/v1/system/status` | Actual model/data/provider status and offline mode | Yes | **VERIFIED** |
| `GET` | `/api/v1/credit/models` | List trained model versions and real evaluation metadata | Yes | **VERIFIED** |
| `POST` | `/api/v1/credit/score` | Validate features and return score, model version and warnings | Yes | **VERIFIED** |
| `POST` | `/api/v1/credit/explain` | Return computed local/global explanation data | Yes | **VERIFIED** |
| `POST` | `/api/v1/credit/what-if` | Re-score whitelisted feature scenarios | Yes | **VERIFIED** |
| `POST` | `/api/v1/finance/emi` | Compute EMI and repayment summary | Yes | **VERIFIED** |
| `POST` | `/api/v1/finance/stress-test` | Compute before/after personal cash-flow scenarios | Yes | **VERIFIED** |
| `GET` | `/api/v1/market/universe` | Return configured supported symbols and metadata | Yes | **VERIFIED** |
| `POST` | `/api/v1/market/portfolio/analyze` | Calculate portfolio metrics from cached historical prices | Yes | **VERIFIED** |
| `POST` | `/api/v1/market/portfolio/stress-test` | Apply specified asset/portfolio shocks | Yes | **VERIFIED** |
| `POST` | `/api/v1/market/var/validate` | Run rolling out-of-sample VaR validation | Yes | **VERIFIED** |
| `GET` | `/api/v1/monitoring/models` | List model registry metadata | Yes | **VERIFIED** |
| `POST` | `/api/v1/monitoring/drift/run` | Run PSI calculation on a selected reference/current batch | Yes | **VERIFIED** |
| `POST` | `/api/v1/monitoring/challenger/evaluate` | Evaluate a challenger using the documented protocol | Yes | **VERIFIED** |
| `POST` | `/api/v1/monitoring/challenger/promote` | Explicitly promote a passing challenger and log the decision | Yes | **VERIFIED** |
| `POST` | `/api/v1/copilot/message` | Run bounded LangGraph flow and return answer, sources and tool trace summary | Yes | **VERIFIED** |
| `GET` | `/api/v1/methodology` | Return method definitions, data limitations and disclaimer text | Yes | **VERIFIED** |

### Additional endpoints (beyond the PRD)

| Method | Endpoint | Purpose | OpenAPI Match |
|:---:|:---|:---|:---:|
| `GET` | `/api/v1/market/search` | Search the NSE/US instrument master with sector, index and cap filters | Yes |
| `POST` | `/api/v1/market/validate-symbol` | Check that a symbol has usable price history, fetching it lazily if needed | Yes |
| `POST` | `/api/v1/market/var/compare` | Backtest several VaR methods on one window and recommend one | Yes |
| `POST` | `/api/v1/market/portfolio/stress/replay` | Replay COVID 2020, 4 Jun 2024 and Adani 2023 against a portfolio using real prices | Yes |
| `POST` | `/api/v1/market/portfolio/stress/reverse` | Find the shock that produces a chosen portfolio loss | Yes |
| `POST` | `/api/v1/market/portfolio/import` | Import holdings from a broker CSV export (Zerodha, Groww, etc.) with automated symbol resolution and price-derived weights | Yes |

Market endpoints that load prices accept `fx_mode`: `strict` (default) rejects mixed USD/INR portfolios, `convert_to_base` converts into the portfolio currency with daily `USDINR=X` rates and states the FX series and date range in the response `fx` block.

---

## 2. Detailed Endpoint Contracts

### `GET /health`
**Summary:** Health Liveness  
**Description:** Liveness check; no claim that models/data are healthy.  
**Tags:** Health  

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/HealthResponse"
  }
  ```

---

### `GET /api/v1/system/status`
**Summary:** System Status  
**Description:** Returns genuine operational status of model artifacts, cached market data,
RAG corpus, and offline mode. Never fabricates healthy or active state.  
**Tags:** System  

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/SystemStatusResponse"
  }
  ```

---

### `GET /api/v1/credit/models`
**Summary:** List Credit Models  
**Description:** List trained credit model versions and actual real evaluation metadata.  
**Tags:** Credit Risk Intelligence  

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "items": {
      "$ref": "#/components/schemas/CreditModelMetadata"
    },
    "type": "array",
    "title": "Response List Credit Models Api V1 Credit Models Get"
  }
  ```

---

### `POST /api/v1/credit/score`
**Summary:** Score Borrower  
**Description:** Score borrower feature attributes, return predicted tier and class probabilities.  
**Tags:** Credit Risk Intelligence  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/CreditScoreRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/CreditScoreResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/credit/explain`
**Summary:** Explain Credit Score  
**Description:** Compute local SHAP feature contributions for borrower profile.  
**Tags:** Credit Risk Intelligence  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/CreditExplainRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/CreditExplainResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/credit/what-if`
**Summary:** What If Counterfactual  
**Description:** Re-score baseline profile with modified features and compare category & probability shifts.  
**Tags:** Credit Risk Intelligence  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/WhatIfRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/WhatIfResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/finance/emi`
**Summary:** Calculate Loan Emi  
**Description:** Compute EMI, total interest, and repayment schedule with deterministic formulas.  
**Tags:** Personal Financial Stress & Affordability  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/EMIRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/EMIResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/finance/stress-test`
**Summary:** Run Financial Stress Test  
**Description:** Run before/after adverse cash-flow stress test and persist run record.  
**Tags:** Personal Financial Stress & Affordability  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/StressTestRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/StressTestResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `GET /api/v1/market/universe`
**Summary:** Get Market Universe  
**Description:** Return available market symbols, data coverage, currency, provenance, and instrument metadata.  
**Tags:** Portfolio Market Risk Lab & VaR Validation  

**Responses:**
- **`200`**: Successful Response
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/market/portfolio/analyze`
**Summary:** Analyze Portfolio  
**Description:** Calculate portfolio volatility, historical/parametric VaR, CVaR, and max drawdown.  
**Tags:** Portfolio Market Risk Lab & VaR Validation  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/PortfolioAnalyzeRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/PortfolioAnalyzeResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/market/portfolio/stress-test`
**Summary:** Run Market Stress Test  
**Description:** Run historical and custom factor stress tests against portfolio allocations.  
**Tags:** Portfolio Market Risk Lab & VaR Validation  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/PortfolioStressTestRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "items": {
      "$ref": "#/components/schemas/StressScenarioResponse"
    },
    "type": "array",
    "title": "Response Run Market Stress Test Api V1 Market Portfolio Stress Test Post"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/market/var/validate`
**Summary:** Validate Var Model  
**Description:** Perform rolling out-of-sample VaR validation with Kupiec and Christoffersen tests.  
**Tags:** Portfolio Market Risk Lab & VaR Validation  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/VaRValidationRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/VaRValidationResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `GET /api/v1/monitoring/models`
**Summary:** List Registry Models  
**Description:** List all registered models, artifact paths, training metadata, and active status.  
**Tags:** ML Monitoring & Model Registry  

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "items": {
      "$ref": "#/components/schemas/ModelRegistryItem"
    },
    "type": "array",
    "title": "Response List Registry Models Api V1 Monitoring Models Get"
  }
  ```

---

### `POST /api/v1/monitoring/drift/run`
**Summary:** Run Drift Monitoring  
**Description:** Compute Population Stability Index (PSI) drift across features against baseline.  
**Tags:** ML Monitoring & Model Registry  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/DriftRunRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/DriftRunResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/monitoring/challenger/evaluate`
**Summary:** Evaluate Challenger Model  
**Description:** Evaluate a candidate challenger model against the current champion.  
**Tags:** ML Monitoring & Model Registry  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/ChallengerEvaluateRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/ChallengerEvaluateResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/monitoring/challenger/promote`
**Summary:** Promote Challenger Model  
**Description:** Explicitly promote a verified challenger model and record full audit log.
Refuses promotion if challenger does not meet PRD improvement criteria.  
**Tags:** ML Monitoring & Model Registry  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/ChallengerPromoteRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/ChallengerPromoteResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/copilot/message`
**Summary:** Handle Copilot Message  
**Description:** Route user message through bounded state machine, tools, or RAG retriever.  
**Tags:** Agentic Risk Copilot  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/CopilotRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/CopilotMessageResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `GET /api/v1/methodology`
**Summary:** Get Methodology Disclosures  
**Description:** Return scientific conventions, calculation formulas, and legal disclosures.  
**Tags:** Methodology & Disclosures  

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/MethodologyResponse"
  }
  ```

---

### `GET /api/v1/market/search`
**Summary:** Search Market Stocks  
**Description:** Search supported stocks across NSE, BSE, and US markets with sector, index, and cap_bucket filters.
Returns DB-backed ranked fuzzy search results with pagination.  
**Tags:** Portfolio Market Risk Lab & VaR Validation  

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/StockSearchResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/market/validate-symbol`
**Summary:** Validate Market Symbol  
**Description:** Validates a symbol's availability:
- verified_snapshot: Already available as validated local CSV snapshot
- live_validated: Retrieved and validated on-the-fly from live market data provider
- not_available: Quote not found, delisted, insufficient history, or provider error  
**Tags:** Portfolio Market Risk Lab & VaR Validation  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/SymbolValidateRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/SymbolValidateResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/market/var/compare`
**Summary:** Var Model Compare  
**Description:** Side-by-side VaR model comparison using rolling backtests.

Runs the same rolling out-of-sample backtest for each candidate model
(historical, parametric, student_t, cornish_fisher, ewma by default, or
the list provided via the `methods` query parameter) and returns a ranked
scorecard plus a plain-English model recommendation.

Scoring penalises deviation from the expected exception rate, Basel
YELLOW/RED zones, Kupiec POF test failure, and Christoffersen conditional
coverage failure.  
**Tags:** Portfolio Market Risk Lab & VaR Validation  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/VaRCompareRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/VaRCompareResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/market/portfolio/stress/replay`
**Summary:** Replay Named Stress Scenarios  
**Description:** Replay named historical events (COVID Feb-Mar 2020, 4 Jun 2024 election day, Adani Jan-Feb 2023) against the
portfolio using real prices. Holdings with no data in a window are skipped and listed, never filled in.  
**Tags:** Portfolio Market Risk Lab & VaR Validation  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/StressReplayRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "items": {
      "$ref": "#/components/schemas/StressReplayScenario"
    },
    "type": "array",
    "title": "Response Replay Named Stress Scenarios Api V1 Market Portfolio Stress Replay Post"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/market/portfolio/stress/reverse`
**Summary:** Reverse Stress Test  
**Description:** The uniform shock, and the benchmark fall at the portfolio's beta, that produce a given portfolio loss.  
**Tags:** Portfolio Market Risk Lab & VaR Validation  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/ReverseStressRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/ReverseStressResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

### `POST /api/v1/market/portfolio/import`
**Summary:** Import Portfolio Holdings  
**Description:** Import holdings from a broker CSV export (Zerodha, Groww, etc.) with automated
symbol resolution and price-derived weights.  
**Tags:** Portfolio Market Risk Lab & VaR Validation  

**Request Body (application/json):**
```json
{
  "$ref": "#/components/schemas/PortfolioImportRequest"
}
```

**Responses:**
- **`200`**: Successful Response
  ```json
  {
    "$ref": "#/components/schemas/PortfolioImportResponse"
  }
  ```
- **`422`**: Validation Error
  ```json
  {
    "$ref": "#/components/schemas/HTTPValidationError"
  }
  ```

---

## 3. Global Error Responses & Security Standard

- **Standard Error Format:** All 4xx and 5xx errors return `application/json` with standard `{"detail": ...}` format.
- **No Leaked Stack Traces:** Production exceptions are logged server-side and never returned in HTTP bodies.
- **Request ID Tracking:** Every response includes header `X-Request-ID` correlated with structured JSON server logs.
- **Payload Limits:** Request bodies exceeding 1MB (1,048,576 bytes) are rejected with HTTP 413.
- **CORS Configuration:** Strictly validated against configured origins via `ALLOWED_ORIGINS`.