# Known System Limitations and Disclosures

This document details explicit technical and methodology limitations of RiskWise v3.0 to be disclosed in user documentation and academic project evaluation reports.

---

## 1. Credit Risk Benchmark Dataset
- **Dataset Scope:** The credit risk subsystem is trained on the Indian Banking & CIBIL Bureau Merged Dataset (51,336 records) with 4-class multi-tier classification (`Approved_Flag`: P1–P4).
- **Target Leakage Safeguard:** `Credit_Score` (bureau cutoff score) is strictly omitted from the production champion feature suite (42 features) because its inclusion produced an artificial ROC-AUC of 0.9999 due to direct cutoff assignment in underwriting. The champion model evaluates risk strictly from trade-line repayment and inquiry behavior.
- **Decision Support & Educational Framing:** Predicted credit tiers provide relative risk ranking and local TreeSHAP attribution for analyst decision-support. They do NOT constitute an automated sole-decision statutory underwriting system or an official bureau score.

---

## 2. Market Risk & Value at Risk (VaR)
- **Not a Maximum Loss Guarantee:** Value at Risk (VaR) is a probabilistic estimate at a specified confidence level (e.g., 95% or 99%) over a lookback horizon. It does NOT represent the maximum conceivable loss. Extreme tail events ("black swans") can significantly exceed VaR thresholds.
- **Distributional Assumptions:** Parametric VaR assumes a normal return distribution, which underestimates extreme fat-tailed losses in volatile regimes. Historical VaR assumes future shocks will mirror the historical lookback period.
- **Annualization Convention:** Volatility annualization assumes 252 independent and identically distributed (i.i.d.) trading days.
- **Point-in-Time Snapshot (Not Live Market Feed):** All market data series in `data/market_snapshots/` are point-in-time historical downloads fetched via `yfinance` with an explicit ISO retrieval timestamp in `data/manifests/market_manifest.json`. The platform does not maintain a live streaming broker socket or intraday real-time tick feed. Risk analytics describe historical trailing windows up to the snapshot retrieval date.

---

## 3. Financial Stress & Affordability Calculations
- **Deterministic Approximations:** Calculations for EMI, emergency runway, and cash-flow stress assume fixed interest rates, deterministic expenses, and static inflation unless scenario shocks are manually supplied.
- **No Tax or Legal Advisory:** Computations do not constitute qualified personal wealth, tax, or legal advice.

---

## 4. Agentic Copilot & Language Models
- **Bounded Tool Execution:** The copilot cannot execute arbitrary shell code or search unrestricted external web endpoints.
- **Authoritative Calculations:** Any numeric figure generated in chat is sourced strictly from deterministic domain tools. The LLM is prohibited from performing authoritative mental math.
- **Offline Template Mode:** When external hosted LLM provider keys are absent, the copilot reverts to pre-defined structured templates and search matching.

---

## 5. Scope Guarding & Prompt Injection Defense Limitations
- **First-Line Defense Only:** RiskWise employs deterministic input normalization (Unicode NFKD normalization, combining diacritic stripping, leetspeak canonicalization, and whitespace collapsing) alongside structural pattern matching and PII filtering.
- **Incomplete Formal Defense:** Keyword and pattern-based filtering is **not a complete formal defense** against adversarial prompt injections. Sophisticated semantic paraphrasing, zero-day jailbreaks, language switching, or novel multi-turn injection vectors can potentially evade regex/keyword-level screening.
- **Structural Immunity Rule:** To mitigate prompt injection risks beyond regex filters, the system enforces a strict architectural boundary: user inputs are treated exclusively as untrusted data payloads passed to deterministic Python numerical functions. User message content can **never** modify the agent's system policy, alter tool permissions, or trigger arbitrary code execution.

---

## 6. Container & Deployment Verification
- **Container Build Status:** Docker CLI is not installed on this host (`CommandNotFoundException`). Container build is therefore confirmed unavailable in the current host environment. Never claimed.
- **Local Validation Status:** Verified end-to-end locally on host:
  - Backend: **202 passing pytest tests** under Python 3.11 (`backend/tests/`); 0 failures.
  - Frontend: `npm run build` compiles production bundle successfully with Next.js 16.4.0 Turbopack (0 TypeScript errors).

---

## 7. Multi-Model VaR Limitations (Tier A Upgrade — A2–A4)

- **GARCH(1,1) MLE Convergence:** GARCH fitting uses `arch` library's default SLSQP solver. On very short or stationary series (< 60 observations), the optimizer may converge to boundary values (α or β → 0). The backend falls back to EWMA volatility if `α + β ≥ 1` (non-stationary).
- **Student-t DoF Estimation:** Degrees-of-freedom fitting via `scipy.stats.t.fit` on portfolio composite returns; results may be imprecise for small samples (< 100 observations). DoF is clamped to [3, 100].
- **Monte Carlo Seed Determinism:** MC VaR uses `np.random.seed(42)` for reproducibility. Two analysts running identical inputs will receive identical results; this is intentional for auditability.
- **Cornish-Fisher Range:** The Cornish-Fisher expansion is a 4th-order asymptotic approximation and may give biased results for very high skewness (|S| > 2) or excess kurtosis (E > 10). The API clips |S| ≤ 3, E ≤ 10 as a guard.
- **Backtest Minimum N:** Kupiec and Christoffersen tests require at least 30 out-of-sample forecasts for the asymptotic χ² approximation to hold. The API enforces a 60-day minimum lookback and warns when fewer than 30 forecasts are available.
- **Benchmark Beta Estimation:** Beta is estimated using the full aligned historical window; short joint histories (< 60 days overlap) produce unreliable CAPM betas. The API reports `beta_to_benchmark = null` in those cases.
- **Recharts Cumulative-Return Curves:** The curves rendered in `MarketRiskCharts.tsx` are **pseudo-random simulations seeded from summary statistics** (μ, σ, β), NOT actual price path replays. They illustrate distributional shape and relative beta for educational purposes only. Actual return paths require tick-level data integration not available in the current offline snapshot strategy.

---

## 8. Portfolio Holdings CSV Upload (Tier B — B4)
- **Supported Formats & Broker Exports:** Supports standard holdings exports from Zerodha Kite (`Instrument, Qty., Avg. cost, LTP, Cur. val, P&L`), Groww (`Stock Name, ISIN, Quantity, Average buy price, Buy value, Closing price`), and canonical CSVs (`symbol, quantity, avg_price`).
- **Delimiter & Encoding:** Automatically strips UTF-8 Byte Order Marks (BOM: `\ufeff`), scans metadata header rows (up to 30 rows above real column headers), and detects comma (`,`), semicolon (`;`), and tab (`\t`) delimiters.
- **Number Sanitization:** Automatically parses currency symbols (`₹`, `$`, `€`, `£`, `Rs.`), thousand commas (`1,234.50`), trailing spaces, and accounting negative numbers `(100.0)`.
- **Size & Row Limits:** Enforces a maximum file size of 1 MB and a maximum of 500 rows per upload to maintain sub-second response times and prevent resource exhaustion.
- **Strict Symbol Resolution Hierarchy:**
  1. ISIN match against official database instruments (`instruments.isin`).
  2. Exact symbol match (with or without `.NS` suffix, stripping broker series suffixes like `-EQ`, `-BE`, `-BL`, `-BZ`, `-SM`, `-ST`).
  3. Curated alias match (`CORPORATE_ALIASES` and `Instrument.aliases_json`).
  4. Exact normalized company name match against `Instrument.name` (stripping legal suffixes like Limited, Ltd, Pvt, Inc).
  - **No Silent Fuzzy Matching:** The engine **never** auto-picks a fuzzy match to prevent inadvertent asset misallocation. If no exact match is found, the row is rejected and listed with up to 3 candidate suggestions from `search_symbols`.
- **Price Authority & Weight Computation:** Portfolio weights are computed exclusively from authoritative platform price data (`quantity * latest_price / total_value`), not broker-supplied LTP columns. Duplicate symbols within the same upload are merged with quantity-weighted average prices and reported in warnings.
- **Multi-Currency Policy:** If an uploaded CSV contains mixed Indian (INR) and US (USD) holdings, `inferred_currency` is returned as `null`, requiring the user to explicitly toggle `fx_mode="convert_to_base"` for unified risk analysis.


