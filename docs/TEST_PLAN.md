# RiskWise Test Plan & Quality Gates

## 1. Objectives

Verify end-to-end correctness, mathematical validity, leakage prevention, and offline reliability across all RiskWise services and UI components.

---

## 2. Testing Levels

### 2.1 Backend Unit Tests (`backend/tests/unit/`)
- **Financial Calculations:**
  - EMI formula tests with known hand-calculated values across standard interest rates, zero rate edge cases, and tenure boundaries.
  - Personal stress tests: monthly surplus, EMI-to-income ratio, emergency runway under base and adverse shocks.
  - Market risk metrics: return series calculations (log vs simple), annualized volatility ($\sqrt{252}$ convention), maximum drawdown peak-to-trough.
  - Value at Risk (VaR): Historical percentile vs Parametric normal VaR and Expected Shortfall (CVaR).
  - Population Stability Index (PSI): Binning logic, smoothing constant for zero counts, and PSI metric summation against verified numerical fixtures.

### 2.2 Schema & Validation Tests (`backend/tests/schemas/`)
- Pydantic models reject negative loan principal, negative interest rate, negative tenure.
- Portfolio analysis rejects mixed-currency holdings or invalid weight allocations (summing to non-standard or negative without configuration).
- Credit scoring schema validation against expected input feature dictionary.

### 2.3 Integration & Leakage Tests (`backend/tests/integration/`)
- **API Endpoints:** Liveness `/health`, system status `/api/v1/system/status`, and all P0 REST endpoints return proper status codes, headers, and error shapes.
- **VaR Out-of-Sample Leakage Test:** Verify rolling backtest window at step $t$ utilizes exclusively historical data $[0, t-1]$ to generate risk threshold, and evaluates against realized loss at $t$.
- **ML Preprocessing Separation:** Assert scaler/imputer transformers fit strictly on training splits.

### 2.4 Agent & Copilot Evaluation (`backend/tests/agents/`)
- Intent routing verification: calculation questions invoke domain tools, educational questions route to RAG corpus, unsupported questions trigger safe rejection.
- Fallback verification: agent operates gracefully without external LLM keys.

### 2.5 Frontend Verification (`frontend/tests/`)
- Dashboard component rendering, navigation, empty states, error states, and offline status indicators.

---

## 3. Execution Commands

- **Backend Tests:** `pytest backend/tests -v`
- **Backend Linting:** `ruff check backend`
- **Backend Type Checks:** `mypy backend` (or Ruff type checker)
- **Frontend Build & Test:** `npm run build` and `npm test` inside `frontend/`
