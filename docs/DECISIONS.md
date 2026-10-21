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


