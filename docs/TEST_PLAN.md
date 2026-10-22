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

### 2.5 Frontend Verification
- There is **no automated component or end-to-end test suite** for the frontend (a Playwright suite is out of scope). The frontend is verified by ESLint, the TypeScript type-check, a production build, and manual browser checks of every page in light and dark themes at desktop width, with screenshots kept under `docs/screenshots/`.
- Logic that matters for correctness is kept on the server and covered by the backend tests (for example the chart series, FX conversion, stress replays and the copilot's number provenance guard).

---

## 3. Execution Commands

- **Backend setup in a fresh clone:** `python scripts/build_instrument_master.py` (creates the schema and loads the instrument master from `data/reference/EQUITY_L.csv`) and `python scripts/build_index.py` (RAG index from the tracked knowledge corpus).
- **Backend Tests:** `pytest backend/tests -v`. Tests are offline: network access is blocked by `conftest.py`. Tests marked `requires_trained_model` skip, with a stated reason, when `artifacts/models/credit_indian_xgboost_v1.joblib` is absent (the model files are gitignored; `scripts/train_indian_credit.py` creates them).
- **Backend Linting:** `ruff check backend`
- **Frontend:** `npm run lint`, `npx tsc --noEmit` and `npm run build` inside `frontend/` (there is no `npm test`).
- **CI:** `.github/workflows/ci.yml` runs the steps above. Each step has been run from a clean checkout locally; the workflow itself has not yet run on GitHub.
