# Known System Limitations and Disclosures

This document details explicit technical and methodology limitations of RiskWise v3.0 to be disclosed in user documentation and academic project evaluation reports.

---

## 1. Credit Risk Benchmark Dataset
- **Proxy Nature:** The credit dataset utilizes historical Taiwanese credit card client records from 2005. It is solely an academic reference benchmark.
- **No Indian Credit Score Equivalent:** The output risk score and probability estimates do NOT correspond to Indian credit bureaus (e.g., CIBIL scores) or Indian banking default likelihoods.
- **Educational Framing:** All credit outputs represent relative risk classifications within the context of the dataset distribution.

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
- **Container Build Status:** Backend container build not verified (Docker unavailable on the dev machine). Local evaluation and test suites run directly via virtual environment.

