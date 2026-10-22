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
- **Historical Daily Data, Not a Live Feed:** Prices come from point-in-time daily downloads (`yfinance`) cached in `data/market_snapshots/` with a retrieval timestamp in `data/manifests/market_manifest.json`. A symbol that is not cached is fetched on first use and cached, and the stress-replay windows are fetched separately into `data/stress_windows/`. Both need network access the first time. There is no intraday or streaming feed; analytics describe daily history up to the last download.

---

## 3. Financial Stress & Affordability Calculations
- **Deterministic Approximations:** Calculations for EMI, emergency runway, and cash-flow stress assume fixed interest rates, deterministic expenses, and static inflation unless scenario shocks are manually supplied.
- **No Tax or Legal Advisory:** Computations do not constitute qualified personal wealth, tax, or legal advice.

---

## 4. Agentic Copilot & Language Models
- **Bounded Tool Execution:** The copilot cannot execute arbitrary shell code or search unrestricted external web endpoints.
- **Authoritative Calculations:** Any numeric figure generated in chat is sourced strictly from deterministic domain tools. The LLM is prohibited from performing authoritative mental math.
- **Offline Template Mode:** When external hosted LLM provider keys are absent, the copilot reverts to pre-defined structured templates and search matching. No language model is called today, so every reply is composed from tool results.
- **Number Provenance Guard:** A final step checks every figure in a result-bearing reply against the tool outputs, citations and the user's own message, and removes any line with an unsourced number (see section 11).

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
- **Chart Series:** The cumulative-return, drawdown and histogram charts are computed on the server from the portfolio's actual daily returns (`chart_series` in the analyze response). The portfolio is treated as rebalanced to constant weights every day, the same series that every other metric uses. An earlier version drew these from simulated noise; that was a defect and was removed.

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

---

## 9. USD/INR FX Mode (Tier B — B2)
- **Opt-in only:** portfolios are single-currency by default (`fx_mode="strict"`). `convert_to_base` converts USD or INR assets into the portfolio currency with the daily `USDINR=X` close. No other currency pair is supported, and anything else is rejected rather than guessed.
- **Currency movement is included:** converted returns contain the exchange-rate move, and weights or position values are read as base-currency amounts. Days without a rate on the shared calendar are dropped from the window.
- **The response states what was used:** pair, data source, converted holdings and direction, the exact FX date range and observation count, and the rate at the start and end.

---

## 10. Named Historical Stress Replays and Reverse Stress (Tier B — B3)
- **Fixed events:** COVID-19 (19 Feb to 23 Mar 2020), Indian election result day (3 to 4 Jun 2024) and the Adani sell-off (24 Jan to 28 Feb 2023). A holding's return is its own price move between the last close on or before each date.
- **Gaps are reported, never filled:** a holding that was not listed, or has no provider data, in a window is skipped and listed with the reason. The result then covers only the remaining holdings, re-weighted to 100%, and shows the covered share.
- **Network on first use:** each symbol and window is downloaded once from Yahoo Finance and cached in `data/stress_windows/`. Delisted names may have no data and are skipped.
- **Reverse stress uses historical betas** (252 days by default) against ^NSEI or SPY. Betas are estimates and can change; when the portfolio beta is not positive, or the implied fall is 100% or more, the response says the beta answer does not apply and only the uniform shock does.

---

## 11. Copilot Market Tools and the Provenance Guard (Tier B — B6)
- **Tools:** portfolio analysis, rolling VaR validation, VaR model comparison, historical stress replay and reverse stress. Holdings are recognised from a fixed alias list (SPY, AAPL, MSFT, GOOGL, NIFTYBEES, RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK), not the full instrument master.
- **No silent defaults:** when the user names no holdings, or no target loss for reverse stress, the copilot asks. It never substitutes a sample portfolio.
- **What the guard checks:** each number in a result-bearing reply must match a tool argument or output, a retrieved citation, or the user's message, to the precision displayed. A line with an unsourced number is replaced by a marker and reported in `provenance_flags`. Only 252, 95, 99 and 100 and section references are exempt.
- **What it does not check:** whether the wording around a correct number is a fair description of it. Clarification questions, refusals and error explanations are fixed text and are not gated.

---

## 12. Tests, CI and Dependencies
- **Trained model files are not in git.** `artifacts/models/*` and the raw dataset are gitignored. In a fresh checkout 15 tests that need the credit model (and one retraining test that needs the processed data) skip with a stated reason; run `scripts/train_indian_credit.py` to enable them. A fresh checkout passes 282 tests and skips 16; with the model present all 298 run.
- **CI has not run on GitHub.** Each workflow step was run locally from a clean checkout. The frontend build step fails on its first run with a Next.js security-advisory message (the second run passes). `npm audit` confirms the cause: `next` 16.0.0 to 16.4.0 has critical advisories, including remote code execution in `use cache` functions and in the image optimiser, fixed in 16.4.2. The fix is to upgrade Next.js; it has not been done.
- **Docker was never built or run** in this environment.

---

## 13. Model Registry and Drift Page
- **Drift is a pipeline check, not production evidence.** There is no live traffic, so the PSI check compares two partitions of the training data (the response states this in `drift_source`). It validates that the monitoring code works; it says nothing about real-world drift.
