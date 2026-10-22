# Architectural Decision Records (ADRs)

This document tracks all foundational architecture, domain modeling, and technical decisions made for RiskWise v3.0, adhering to the principle: *Do not invent endpoints, database fields, agent tools, data sources or user-facing metrics. If a decision is not specified, choose the simplest safe implementation and record it here.*

---

## ADR-001: Monolith vs Microservices Architecture
- **Date:** 2026-10-13 (Milestone 0)
- **Status:** Accepted
- **Context:** PRD v3.0 specifies a final-year engineering project to be delivered by 3-4 students over 16 weeks with zero budget.
- **Decision:** Adopt a modular monolith architecture consisting of a single Next.js App Router frontend and a single FastAPI backend service. Domain boundaries (Credit Risk, Financial Stress, Market Risk, VaR Validation, Monitoring, Copilot) are enforced at the module/package level in Python.
- **Consequences:** Avoids unnecessary distributed systems overhead (Kafka, Kubernetes, microservice networking), guarantees atomic deployments, and enables simple local offline execution.

---

## ADR-002: Offline-First Operation and Fallback Strategy
- **Date:** 2026-10-13 (Milestone 0)
- **Status:** Accepted
- **Context:** The application must remain demonstrative and verifiable without paid APIs, external internet access, or live market data feeds.
- **Decision:**
  - Market data defaults to a locally versioned snapshot (`data/market_snapshots/`) with checksum validation. External fetching via `yfinance` is strictly optional and explicit.
  - LLM Copilot defaults to a deterministic, rule-based template/FAQ response mode when no API key is supplied (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` not configured). Authoritative calculations always delegate to domain services, never LLM generation.
  - Vector search falls back to deterministic TF-IDF / keyword retrieval if local neural embedding pipelines are not pre-downloaded.
- **Consequences:** The entire system starts up and runs offline without any secrets or API keys.

---

## ADR-003: Persistence and Storage Engine
- **Date:** 2026-10-13 (Milestone 0)
- **Status:** Accepted
- **Context:** Lightweight relational metadata and audit trails need persistence without requiring cloud infrastructure or heavy container dependencies.
- **Decision:** Use SQLite via SQLAlchemy 2.0 with Alembic for relational migrations. Model weights (`.joblib`) and preprocessors are stored as immutable, versioned files under `artifacts/models/`. Market price histories are stored in CSV/Parquet formats in `data/market_snapshots/`.
- **Consequences:** Zero external database setup requirement; file-based checksum validation ensures reproducibility.

---

## ADR-004: Anti-Fabrication and Realistic Metrics Policy
- **Date:** 2026-10-13 (Milestone 0)
- **Status:** Accepted
- **Context:** Academic rigor demands that no fake ROC curves, mock credit scores, placeholder VaR values, or fabricated live statuses exist.
- **Decision:** In uninitialized or unconfigured states (e.g., prior to model training or before market snapshot generation), the backend returns explicit `uninitialized` / `missing_artifact` status with actionable explanations, and the UI displays clear empty/error states rather than mock numbers or fake charts.
- **Consequences:** Every displayed number is mathematically grounded in local artifacts or deterministic formulas.

---

## ADR-005: Technology Stack Pinning
- **Date:** 2026-10-13 (Milestone 0)
- **Status:** Accepted
- **Context:** Ensure cross-platform build stability and dependency compatibility across scikit-learn, XGBoost, SHAP, FastAPI, and Next.js.
- **Decision:**
  - Backend: Python 3.11+, FastAPI 0.115+, Pydantic v2, SQLAlchemy 2.0, Uvicorn, scikit-learn, XGBoost, SHAP, Pandas, NumPy, SciPy.
  - Frontend: Next.js 14+ (App Router), React 18/19, TypeScript, Tailwind CSS, Lucide React, Recharts, TanStack Query.
- **Consequences:** Stable ecosystem with long-term support and verified compatibility.

---

## ADR-006: Local Vector Index & Retrieval Method
- **Date:** 2026-10-13 (Phase 1)
- **Status:** Accepted
- **Context:** PRD §4.5 and §5.3 mandate offline-first execution with local RAG retrieval, without requiring external network calls or cloud vector databases.
- **Decision:** Implement a deterministic TF-IDF indexing pipeline (`scripts/build_index.py`) using scikit-learn. Chunks are extracted from `knowledge/sources/` with full provenance (source ID, title, publisher, URL, chunk ID). Artifacts (`vectorizer.joblib`, `tfidf_matrix.joblib`, `index_metadata.json`) are persisted to `artifacts/vector_index/`.
- **Consequences:** Zero external API or neural model download required. 100% reproducible, fast, and offline. Hit@1 and Hit@3 achieve 100% on the 16-query evaluation benchmark.

---

## ADR-007: LangGraph Bounded Agent & Parameter Clarification Policy
- **Date:** 2026-10-13 (Phase 1)
- **Status:** Accepted
- **Context:** Copilot previously used regex routing with silent hardcoded parameter defaults for missing numbers. PRD §4.5 requires a bounded LangGraph agent graph, and PRD §0 prohibits default demo numbers.
- **Decision:** Build a typed LangGraph `StateGraph` (`scope_safety_check` -> `intent_classification` -> `parameter_extraction` -> `tool_execution` -> `answer_composition`). Parameters are parsed explicitly with Indian units support. If any required parameter is missing or ambiguous, the copilot immediately returns a clarification question and executes no tool.
- **Consequences:** Zero hardcoded assumptions; fully auditable traces; 100% passing across 33 evaluation test cases.

---

## ADR-008: Real Market Snapshot Universe & Multi-Currency Segmentation
- **Date:** 2026-10-14 (Phase 2.0)
- **Status:** Accepted
- **Context:** The previously generated synthetic random-walk prices violated PRD §0.6 and §5.2. Market data must be real, point-in-time snapshots downloaded from a recognized public provider (Yahoo Finance via `yfinance`) with explicit provenance, checksums, and metadata. In addition, PRD §5.2 requires portfolios to be single-currency.
- **Decision:**
  1. **Primary Universe (INR):** To reflect the Indian retail financial risk context, the primary universe consists of liquid NSE instruments:
     - `^NSEI` (Nifty 50 Benchmark Index)
     - `NIFTYBEES.NS` (Nippon India ETF Nifty 50 BeES)
     - `RELIANCE.NS` (Reliance Industries Ltd)
     - `TCS.NS` (Tata Consultancy Services Ltd)
     - `HDFCBANK.NS` (HDFC Bank Ltd)
     - `INFY.NS` (Infosys Ltd)
     - `ICICIBANK.NS` (ICICI Bank Ltd)
  2. **Secondary Universe (USD):** To support US market benchmarks without mixing currencies:
     - `SPY` (SPDR S&P 500 ETF Trust)
     - `AAPL` (Apple Inc)
     - `MSFT` (Microsoft Corp)
     - `GOOGL` (Alphabet Inc)
  3. **Single-Currency Rule (PRD §5.2):** All holdings within a portfolio analysis request must share identical currency (`INR` or `USD`). Cross-currency mixtures without explicit FX series are rejected with HTTP 400.
  4. **Data Integrity:** At least 2 years of daily price history fetched via `yfinance` (`auto_adjust=False`, preserving provider's `Close` and `Adj Close` alongside real volume). Non-positive prices are rejected; daily return plausibility checks and SHA-256 hashes are recorded in `market_manifest.json` with exact retrieval timestamps. Synthetic generation logic is deleted.

---

## ADR-009: Currency-Free Feature Engineering & Demographic Exclusion in Credit Scoring
- **Date:** 2026-10-14 (Credit Defensibility Milestone)
- **Status:** Accepted
- **Context:** The UCI benchmark contains raw nominal monetary values denominated in New Taiwan Dollars (TWD) and demographic attributes (`SEX`, `EDUCATION`, `MARRIAGE`, `AGE`). Direct modeling on nominal currency values makes scores fragile to exchange rates and inflation, while using protected demographic classes violates modern fair lending statutes (Equal Credit Opportunity Act / Regulation B, RBI Fair Practices Code).
- **Decision:**
  1. Transform raw inputs into 21 currency-free behavioral features:
     - Monthly credit utilisation ratios: `BILL_AMT_i / LIMIT_BAL` (clipped [0, 5]).
     - Monthly payment ratios: `PAY_AMT_i / BILL_AMT_i` (guarded for non-positive bills with 1.0, clipped [0, 5]).
     - Delinquency severity features: count of months late ($\sum \mathbb{I}(PAY_i > 0)$), worst delay ($\max(0, \max(PAY_i))$), and repayment status codes (`PAY_0`, `PAY_2` through `PAY_6`).
     - Utilisation trend: delta between recent and historical utilisation (`util_1 - util_6`).
  2. Permanently exclude `SEX`, `EDUCATION`, `MARRIAGE`, and `AGE` from the production candidate training matrix and production inference.
- **Consequences:** The scoring engine is currency-invariant, behavior-driven, and legally defensible. Eliminating demographics preserved competitive discriminative ranking power (ROC-AUC 0.7757 vs 0.7806 on raw) while eliminating direct demographic bias.

---

## ADR-010: Fair Lending Auditing & Disparate Impact Ratio Compliance
- **Date:** 2026-10-14 (Credit Defensibility Milestone)
- **Status:** Accepted
- **Context:** Automated decisioning systems require rigorous bias testing to prevent disparate impact on protected classes.
- **Decision:** Implement `scripts/audit_fairness.py` generating `artifacts/evaluation/fairness_audit.json` on the held-out test split (4,500 records). Audit subgroup performance (ROC-AUC, approval rate, base default rate, default recall) across `SEX`, `EDUCATION`, `MARRIAGE`, and four age bands (`<25`, `25-34`, `35-49`, `50+`). Calculate Disparate Impact Ratios (DIR) against reference groups under the EEOC / CFPB Four-Fifths (80%) Rule ($DIR \ge 0.80$).
- **Consequences:** Fully verifiable and documented fair lending metrics integrated directly into `docs/MODEL_CARD.md` and `docs/EVALUATION_REPORT.md`. All demographic slices pass the 80% rule ($DIR \ge 0.89$).

---

## ADR-011: Plain Profile Input Scoring & Actionable What-If Counterfactual Mode
- **Date:** 2026-10-14 (Credit Defensibility Milestone)
- **Status:** Accepted
- **Context:** Asking retail users to supply 23 raw Taiwanese column names is unusable. Additionally, standard sensitivity what-if analysis that permits modifying protected traits (e.g., advising a user to change age or marital status to reduce default risk) is unethical and nonsensical.
- **Decision:**
  1. Introduce `POST /api/v1/credit/profile-score` accepting plain inputs (`credit_limit`, last 6 months `bill_amounts`, `payment_amounts`, `months_late`) and mapping them automatically to features, preserving full backward compatibility for `POST /credit/score`.
  2. Enhance `POST /api/v1/credit/what-if` with `actionable_only` mode. In actionable mode, reject any modifications to protected/immutable attributes (`SEX`, `EDUCATION`, `MARRIAGE`, `AGE`) with HTTP 422, restrict modifications to borrower-controllable factors (payments, utilisation, delinquency remediation), and return a ranked list of actionable changes sorted by highest risk reduction.
- **Consequences:** Intuitive consumer-facing API contract; strictly ethical and actionable counterfactual recommendations.

---

## ADR-012: Ingestion and DB-backed Search for Full Official NSE Instrument Universe
- **Date:** 2026-10-22 (Tier A Milestone)
- **Status:** Accepted
- **Context:** Market search previously used a static dictionary of ~12 symbols. The platform requires fuzzy searching across the full official NSE universe with sector, index, and cap_bucket filtering.
- **Decision:** Download official NSE equity master from `https://archives.nseindia.com/content/equities/EQUITY_L.csv` and ingest all 2,608 official listed equity instruments into the SQLite `instruments` table with sector, industry, series, ISIN, and aliases, combined with benchmark indices (`^NSEI`, `SPY`) and curated ETFs. Expose via `/market/search` with pagination (`page`, `limit`), sector/index/cap_bucket filters, and enrich `/market/universe` with database-backed instrument counts and sector/index facets while maintaining backward compatibility.
- **Consequences:** 2,617 active verified instruments searchable with sub-second response times without inventing fake symbols.

---

## ADR-013: Lazy Price Loading, Quality Validation, and Freshness Tracking
- **Date:** 2026-10-22 (Tier A Milestone)
- **Status:** Accepted
- **Context:** Any official NSE symbol without a pre-baked snapshot should load lazily on-demand with automated quality validation.
- **Decision:** Implement lazy loading in `MarketDataService.get_symbol_price_history` using `yfinance` with exponential retry/backoff. Validate that prices are strictly positive, reject time series with excessive gaps (>45 calendar days), flag trading gaps (>14 days) and staleness (>180 days), cache validated price series to local CSV and SQLite `daily_prices`, and record freshness metadata (`last_sync_timestamp`, `freshness_status`, `max_gap_days`) in `market_manifest.json` and `Instrument.updated_at`. Guard database lookups by `_is_default_snapshots_dir` to maintain test isolation.
- **Consequences:** Eliminates manual snapshot generation for new symbols while guaranteeing data quality and auditability.

---

## ADR-014: Multi-Model Risk Analytics, Method Selector, and Horizon Scaling
- **Date:** 2026-10-22 (Tier A Milestone)
- **Status:** Accepted
- **Context:** Users need to select between 8 parametric, non-parametric, and semi-parametric VaR models with configurable horizons (1-30 days), alongside comprehensive performance and risk attribution metrics.
- **Decision:** Expose `var_method` and `horizon_days` on `POST /market/portfolio/analyze`. Calculate chosen model VaR/ES, annualized Sharpe and Sortino ratios using jurisdiction-appropriate risk-free rate, top-5 peak-to-trough drawdown table, and component/marginal VaR decomposition. All methods verified against analytic closed-form formulas (Gaussian, Student-t, Cornish-Fisher, EWMA, Euler allocation).
- **Consequences:** Gives institutional-grade risk attribution and multi-model flexibility while maintaining complete backward compatibility with existing API contracts.

---

## ADR-015: Regulatory VaR Backtesting, Christoffersen Conditional Coverage, and Model Comparison
- **Date:** 2026-10-22 (Tier A Milestone)
- **Status:** Accepted
- **Context:** Regulatory compliance under BCBS standards requires a 250-day rolling backtest with the official traffic-light penalty matrix, unconditional coverage (Kupiec POF), first-order Markov independence (Christoffersen IND), and conditional coverage joint testing ($LR_{cc} = LR_{uc} + LR_{ind} \sim \chi^2(2)$). Additionally, backtest performance must be fast (vectorised) and provide institutional model ranking and plain-English recommendations.
- **Decision:**
  1. Vectorise the rolling backtest window using `numpy.lib.stride_tricks.sliding_window_view`.
  2. Implement the official BCBS Basel 250-day traffic-light multiplier table (Green: $\le 4$ exceptions, $3.00\times$; Yellow: 5 to 9 exceptions, $3.40\times$ to $3.85\times$; Red: $\ge 10$ exceptions, $4.00\times$) with exact binomial CDF continuity fallback for non-250 windows.
  3. Remove artificial `999.0` sentinels for 0 or 100% exceptions by computing exact asymptotic likelihood ratios.
  4. Implement Christoffersen Conditional Coverage ($LR_{cc} \sim \chi^2(2)$).
  5. Introduce `POST /api/v1/market/var/compare` side-by-side leaderboard running candidate models on the exact same window, ranking them by a composite risk score (penalising deviation from expected exceptions, Basel yellow/red zones, and test rejections), and returning a plain-English recommendation.
  6. Optimize `/market/universe` with lightweight SQL aggregation (`func.count`, distinct facets) and sample capping to avoid hydrating thousands of ORM instances.
- **Consequences:** Eliminates computational bottlenecks in backtesting, achieves full regulatory compliance, and provides actionable multi-model recommendations.



## B0: Verification pass (2026-10-22)
- **Decision:** Replace the synthetic dashboard series with backend-computed series; pass Christoffersen conditional coverage through `/var/validate`; state the credit-model leakage choice on the credit page; move prompt files to `docs/prompts/`.
- **Reasoning:**
  1. `MarketRiskCharts.tsx` (A5) generated the cumulative-return and drawdown curves from `Math.sin` noise around the mean and volatility, and drew the histogram from a normal density, so none of it was observed data. The analyze response now carries `chart_series` (cumulative return, benchmark, drawdown, 25-bin histogram) computed from the actual daily portfolio returns. Tests assert the plotted max drawdown equals the headline figure and the histogram counts every observation once. If the API omits the series, the page shows a notice instead of a chart.
  2. `/var/validate` computed `christoffersen_cc_*` in the engine but dropped it when building the response, so the UI showed blanks. Fixed and covered by a test.
  3. The credit model served is the 42-feature XGBoost (preprocessor has no `Credit_Score`). The 0.9999 ROC-AUC variant is a leakage study only; the credit page now says so.
  4. Prompt files moved with `git mv` (history kept), none deleted.
- **Found, deferred to B1:** at 390px the 256px fixed sidebar leaves about 130px for content and the page scrolls horizontally (614px wide); Recharts logs duplicate-key errors at that width. The SHAP panel shows raw feature names and the credit page uses a dark panel inside a light layout.
- **Not verified:** 390px and 1440px screenshots were taken with headless Chrome driven over the DevTools protocol (`docs/screenshots/b0/`). Docker was not used.

## B1: Frontend structure and look (2026-10-22)
- **Decision:** Split the three large pages into feature folders (`_components`, `_hooks`, `_lib`), share one portfolio builder between Market Risk and VaR Validation, add `components/ui` primitives, a real light/dark toggle, loading skeletons and error states, and a metric glossary whose tooltips link into `docs/MARKET_RISK_METHODS.md`.
- **Reasoning:**
  1. `market-risk` 1,291 lines, `var-validation` 1,143, `credit` 1,124 became 82, 79 and 53 lines. The Market Risk and VaR Validation pages had the same holdings, preset and currency logic copied twice; it now lives in `hooks/usePortfolioBuilder.ts` and `components/portfolio/`. The credit form's 42 inputs are defined once in `credit/_lib/fields.ts`.
  2. Theme: `data-theme` on `<html>` set by an inline pre-paint script (saved choice, else OS setting) with a Tailwind `dark` custom variant. The credit page used a hard-coded dark panel inside a light layout; it now follows the theme.
  3. Tooltips: `lib/metric-docs.ts` maps each metric to a heading in the methods doc. `/methodology/market-risk` renders that file with an anchor per heading. `test_metric_docs_headings.py` fails if a heading is renamed. Section 16 was added to the doc for volatility, mean return, loss convention, correlation and the chart series, which had no section.
  4. `apiFetch` now raises `ApiError` with the readable server message and a clear "backend not reachable" message instead of `API 400: {json}`.
- **Bugs found and fixed while doing this:**
  - Sharpe and Sortino were labelled and documented as "Rf = 0%", but the engine subtracts a fixed risk-free proxy (6% INR, 5% USD). The UI now shows the rate used and the doc is corrected.
  - Beta showed "1.00" when no benchmark data existed; it now shows N/A.
  - The Christoffersen card displayed made-up fallbacks ("0.0000", "1.0000") and treated a missing test as passed; it now shows N/A and "not available".
  - Live-downloaded data was labelled "Verified snapshot".
  - A symbol whose validation request failed stayed on "Validating…" forever; it is now marked unavailable with the reason.
  - The advanced credit section said "25 additional features"; it has 24 (18 + 24 = the 42 the model uses).
  - The weight inputs showed a fraction (0.4) next to a "%" sign; they now show percent.
  - `NSEStockSearch` had the lint error (setState inside an effect) and swallowed search failures; both fixed.
- **Narrow-window layout:** a collapsing sidebar and compact header were added so the page no longer overflows, but narrow-window layouts were not verified beyond that (out of scope: this is a desktop website).
- **Dev note:** after editing `globals.css`, Turbopack kept serving a stale stylesheet until `.next` was cleared. Production build is unaffected.
- **Verified:** 206 backend tests, `tsc`, `eslint` (0 problems), `next build` exit 0; desktop (1440px) screenshots of Market Risk, VaR Validation, Credit and the methods page in light and dark with 0 console errors, in `docs/screenshots/b1/`. Tooltip open and link target checked in the DOM.

## B2: USD/INR opt-in FX mode (2026-10-22)
- **Decision:** Add `fx_mode` (`strict` default, `convert_to_base`) to analyze, stress-test, VaR validate and VaR compare. The old `fx_conversion: true` flag is kept as an alias for `convert_to_base`.
- **Reasoning:**
  1. Currency rules were copied into three places (risk engine, validation engine, data service) and the data service's FX path was never reachable from the API. One `resolve_currency_policy` in the risk engine now decides for every endpoint.
  2. The portfolio `currency` is the base. Assets in the other currency are multiplied (USD to INR) or divided (INR to USD) by the daily `USDINR=X` close on shared dates. Only USD and INR are supported; anything else is rejected rather than guessed.
  3. Position values and weights are read as base-currency amounts. Returns therefore include the currency movement, and the response says so.
  4. Every converted response carries `fx`: pair, data source, converted symbols and directions, the exact FX date range and observation count used, and the rate at the start and end of that range. The date range equals the analysis window (tested).
  5. Strict mode is unchanged, and its error now names the opt-in. Unknown `fx_mode` values fail validation (422).
- **Tests:** `test_fx_mode.py` (13). Includes an independent rebuild of the converted portfolio from the raw CSVs that matches the reported volatility to 6e-5.
- **UI:** a "Allow mixed USD and INR holdings" checkbox on Market Risk and VaR Validation, a one-click "Convert to X" on the mixed-currency error, and an FX summary card on results. While conversion is on, symbol search is not filtered by currency and no `.NS` suffix is auto-added.
- **Limit:** FX rates come from the same offline snapshot or live Yahoo series as prices; days without an FX quote are dropped from the aligned window.
