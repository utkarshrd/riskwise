# RiskWise --- Multi-Domain Financial Risk Intelligence Platform

## Product Requirements Document (PRD) v3.0

**Implementation specification for a final-year B.Tech engineering major
project**\
**Planning assumption:** 3--4 students, approximately 16 weeks,
zero-budget-first, greenfield implementation.\
**Status:** Proposed baseline for mentor review and implementation.

------------------------------------------------------------------------

## Change log: v2.1 → v3.0

This revision deliberately changes the project from a
credit-risk-and-literacy application into a multi-domain risk platform.
It is not a request to implement every feature from the previous PRD.

  -------------------------------------------------------------------------
  Area                    Decision in v3.0        Reason
  ----------------------- ----------------------- -------------------------
  Credit-risk ML, SHAP    Retained and            Preserve the original
  and what-if analysis    strengthened            technical foundation, but
                                                  improve model evaluation
                                                  and auditability.

  Personal financial      Retained                Deterministic, testable
  stress and loan                                 financial computations
  affordability                                   that complement credit
                                                  analysis.

  Portfolio market-risk   Promoted to a committed This is the major scope
  analytics               core module             expansion requested after
                                                  the minor project.

  VaR model backtesting   Added as a committed    Validates risk forecasts
                          evaluation feature      against subsequent
                                                  realized losses; distinct
                                                  from trading-strategy
                                                  backtesting.

  Trading-strategy        Excluded from committed It is a separate trading
  backtester              scope                   research subsystem and
  (SMA/RSI/momentum)                              would dilute the
                                                  platform's core risk
                                                  objective.

  LangGraph agentic       Retained, but bounded   The agent coordinates
  copilot + RAG                                   verified tools; it must
                                                  not invent calculations
                                                  or act as an
                                                  unconstrained autonomous
                                                  financial adviser.

  Model drift and         Retained                Demonstrates the ML
  lifecycle monitoring                            lifecycle beyond a
                                                  one-time model
                                                  prediction.

  Study Mode              Reduced to a            Measure
                          lightweight user        usability/understanding
                          evaluation              without building a
                                                  separate product module.

  Paid APIs, live         Excluded                The project must remain
  trading, bank                                   demonstrable with free
  integrations                                    tools and local
                                                  fallbacks.
  -------------------------------------------------------------------------

**Important distinction:** market-risk analytics and VaR backtesting are
in scope. Trading-strategy backtesting---simulating buy/sell rules such
as SMA or RSI to assess historical trading returns---is not part of the
committed build. It may only be proposed as a future extension after all
acceptance criteria are met.

------------------------------------------------------------------------

## 0. Instructions for the engineering team and Antigravity

Treat this document as the implementation source of truth. Implement one
milestone at a time and do not skip ahead to cosmetic features before
the underlying services and tests work.

1.  Create a new repository. The previous minor-project prototype is a
    baseline for comparison, not assumed reusable code.
2.  Start by creating `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`,
    `docs/DATA_SOURCES.md`, `docs/TEST_PLAN.md` and
    `docs/KNOWN_LIMITATIONS.md`.
3.  Build a modular monolith: one Next.js frontend and one FastAPI
    backend, with clearly separated domain services. Do not introduce
    microservices, Kubernetes, Kafka or a cloud data warehouse.
4.  Do not invent endpoints, database fields, agent tools, data sources
    or user-facing metrics. If a decision is not specified, choose the
    simplest safe implementation and record it in `docs/DECISIONS.md`.
5.  Never commit secrets, API keys, personal financial information,
    model datasets with licensing restrictions, or generated
    credentials.
6.  Never fabricate results. Every score, chart, metric, alert, source
    citation, backtest result and model status must be computed from
    data or a real model artifact. No hard-coded demo metrics, fake ROC
    curves, simulated live market prices, or default "healthy" statuses.
7.  Every external dependency must have a fallback. The app must start
    and demonstrate its core workflows without an LLM key or a
    successful market-data download.
8.  Use deterministic tests and seeded experiments. Do not let a
    model-training test depend on a live API.
9.  Use P0/P1/P2 labels consistently: **P0 = required for project
    acceptance; P1 = important if the P0 foundation is stable; P2 =
    stretch/future work.**
10. Do not mark a milestone complete unless its Definition of Done is
    satisfied and the relevant tests pass.

## 1. Product definition

### 1.1 Vision

RiskWise is an explainable, agentic financial risk intelligence platform
that combines borrower credit-risk analysis, personal financial stress
testing, portfolio market-risk measurement, and source-grounded
financial education in one application. It demonstrates how predictive
ML, deterministic financial calculations, statistical risk validation,
model monitoring, and controlled agentic workflows can work together.

### 1.2 Problem statement

Many simple finance applications display a score or a few charts without
explaining the assumptions, testing adverse conditions, or validating
model quality. A standalone credit-risk model also does not demonstrate
market risk or a complete engineering lifecycle. RiskWise addresses this
gap by providing: - an explainable credit-risk model using a documented
public benchmark dataset; - personal cash-flow, loan affordability and
scenario calculations; - portfolio risk metrics and market-shock
analysis; - rolling validation of Value at Risk (VaR) estimates against
realized losses; - an agentic interface that invokes approved
calculation/retrieval tools; - monitoring for data drift and
reproducible model comparisons; and - a full-stack, testable, documented
application.

### 1.3 Target users

-   **Student / individual user:** wants to understand relative
    credit-risk indicators, affordability, personal cash-flow resilience
    and portfolio risk.
-   **Project evaluator / researcher:** wants to inspect dataset
    provenance, model methodology, assumptions, metrics, limitations and
    reproducibility.
-   **Developer / maintainer:** wants to run tests, reproduce
    experiments, replace model artifacts, inspect logs and understand
    service boundaries.

This is an educational and research prototype, not a lending decision
engine, regulated investment service, credit bureau, or substitute for a
qualified financial adviser.

### 1.4 Project objectives

1.  Train and compare multiple credit-risk classifiers with
    leakage-aware evaluation.
2.  Produce transparent per-record explanations and constrained what-if
    comparisons.
3.  Calculate personal cash-flow resilience and loan affordability with
    deterministic formulas.
4.  Build a portfolio market-risk engine using historical daily prices
    and locally cached data.
5.  Compare historical and parametric VaR, calculate Expected Shortfall,
    run stress scenarios, and validate rolling VaR forecasts.
6.  Use LangGraph to route questions to approved domain tools and a
    source-grounded knowledge retriever.
7.  Detect credit-model input drift and track model versions/evaluation
    results.
8.  Deliver a usable full-stack interface with automated tests,
    reproducible evaluation reports and an offline-capable demo.

### 1.5 Non-goals

-   Real lending decisions, real CIBIL score estimation, or claims of
    calibrated Indian probability of default.
-   Integration with bank accounts, credit bureaus, brokers, UPI, bank
    statements, or paid exchange feeds.
-   Live trading, order placement, paper-trading accounts or investment
    recommendations.
-   Trading-strategy research/optimization, reinforcement learning, or a
    buy/sell signal generator.
-   Guaranteed profitability, return predictions or promises that VaR is
    a maximum possible loss.
-   A general-purpose autonomous agent that can execute arbitrary code
    or access arbitrary websites.
-   A production banking deployment or a claim of regulatory compliance.

## 2. Product scope and priorities

### 2.1 Committed P0 modules

  -----------------------------------------------------------------------
  ID                      Module                  Required outcome
  ----------------------- ----------------------- -----------------------
  M1                      Credit Risk             Train/evaluate models;
                          Intelligence            score an input record;
                                                  show relative risk
                                                  framing, SHAP
                                                  explanations and
                                                  controlled what-if
                                                  analysis.

  M2                      Personal Financial      Compute EMI,
                          Stress & Loan           EMI-to-income ratio,
                          Affordability           emergency runway and
                                                  user-defined adverse
                                                  cash-flow scenarios.

  M3                      Portfolio Market Risk   Load supported daily
                          Lab                     price history,
                                                  calculate portfolio
                                                  risk metrics, run
                                                  stress scenarios and
                                                  visualize portfolio
                                                  exposures.

  M4                      VaR Validation          Perform rolling
                                                  out-of-sample VaR
                                                  forecasts, count
                                                  exceptions and compare
                                                  exception frequency
                                                  with the selected
                                                  confidence level.

  M5                      Agentic Risk Copilot    Use LangGraph for
                                                  bounded routing to
                                                  M1--M4 tools and
                                                  curated RAG; return
                                                  grounded answers and
                                                  citations when
                                                  relevant.

  M6                      ML Monitoring & Model   Track model versions,
                          Registry                evaluation metadata and
                                                  PSI-based input drift;
                                                  run a reproducible
                                                  drift experiment and
                                                  compare challenger
                                                  models.

  M7                      Full-stack integration, Frontend, API,
                          tests and evaluation    persistence,
                                                  reproducibility,
                                                  limitations and project
                                                  evaluation.
  -----------------------------------------------------------------------

### 2.2 P1 features

-   Lightweight account/session persistence if needed for the demo; no
    third-party OAuth requirement.
-   Downloadable report (CSV/JSON; PDF only if time permits).
-   India-context information cards with official source links, clearly
    separated from model output.
-   Statistical unconditional-coverage test for VaR exceptions (e.g.,
    Kupiec proportion-of-failures) if the basic rolling validation is
    stable.
-   Local LLM/RAG fallback that gives a useful response without a hosted
    LLM.
-   Model card and experiment comparison page.
-   Pre/post financial-literacy or usability survey.

### 2.3 P2 / deferred

-   Additional credit datasets/adapters and bring-your-own-data
    retraining UI.
-   Multiple market-data providers and intraday prices.
-   Monte Carlo portfolio simulation, factor risk models, portfolio
    optimization and advanced attribution.
-   Trading-strategy backtesting (SMA, RSI, momentum), paper trading,
    live broker connections and reinforcement learning.
-   Hindi response generation, multi-user enterprise roles, advanced
    notifications and production cloud deployment.
-   Real-world drift monitoring using a live labeled borrower
    population.

Do not begin P2 work until all P0 acceptance criteria pass.

## 3. End-to-end user journeys

### Journey A --- Credit-risk assessment

1.  User opens Credit Risk and sees the dataset context and a clear
    educational-use disclaimer.
2.  User enters valid features for the selected supported dataset schema
    or selects a clearly labelled sample record from the held-out demo
    pool.
3.  Backend validates types/ranges and applies the exact persisted
    preprocessing pipeline.
4.  Selected model produces a score. The response includes the model
    version, relative risk band/percentile (if computed against a
    declared reference cohort), top SHAP contributors and a limited
    what-if comparison.
5.  UI distinguishes model output from policy/rule-based educational
    notes. It must not present a proxy score as an Indian CIBIL score or
    a real Indian default probability.

### Journey B --- Personal stress and loan affordability

1.  User enters monthly income, expenses, savings, existing EMIs,
    proposed loan principal/rate/tenure.
2.  Financial service calculates EMI, EMI-to-income ratio, estimated
    monthly surplus and emergency runway.
3.  User selects or configures a shock (income loss, expense increase,
    EMI increase, temporary job loss).
4.  The service recomputes cash-flow measures and reports the
    assumptions and formula used.
5.  No LLM is used as the source of numeric results.

### Journey C --- Portfolio market-risk analysis

1.  User chooses supported symbols from a curated universe or loads a
    local sample portfolio.
2.  Backend loads a cached local snapshot first; it may attempt a data
    refresh only when explicitly requested and enabled.
3.  UI shows data source, retrieval time, date coverage, missing dates
    and any stale-data warning.
4.  User selects portfolio weights or quantities, confidence level,
    historical window and risk method.
5.  Backend computes return series, portfolio value series, volatility,
    drawdown, VaR, Expected Shortfall and correlations.
6.  User runs defined market shocks and sees estimated loss and
    per-asset contribution.
7.  All values are based on the actual cached/fetched dataset and
    selected portfolio inputs.

### Journey D --- VaR validation

1.  User selects a portfolio, historical window, confidence level and
    rolling estimation window.
2.  Engine estimates VaR using only prior observations at each forecast
    date.
3.  The following observation is used to determine whether an exception
    occurred.
4.  UI displays the forecast/realized loss series, exception count/rate,
    expected exception rate and caveats about sample size and
    assumptions.
5.  Validation must be genuinely out-of-sample and must not reuse future
    observations in historical estimates.

### Journey E --- Agentic Risk Copilot

1.  User asks a question in plain language.
2.  Input validation and safety/intent checks run first.
3.  LangGraph classifies the request into a supported intent: credit
    explanation, cash-flow/loan calculation, portfolio-risk explanation,
    VaR validation explanation, or general financial education.
4.  For calculation requests, the graph invokes a typed tool that calls
    the same domain service used by the UI. The LLM must not calculate
    the authoritative value itself.
5.  For educational questions, the retriever searches the approved local
    corpus and returns source metadata.
6.  Response composer explains tool results and cites retrieved sources.
    A validation step checks that numeric claims are traceable to tool
    output.
7.  Unsupported or high-risk requests receive a safe limitation message;
    the app does not recommend specific securities or promise returns.
8.  If the hosted LLM is unavailable, the user can still access all
    deterministic features and a limited template-based response.

### Journey F --- Model health and drift

1.  User opens Model Health and sees the actual active model version,
    evaluation metadata and reference-data window.
2.  User runs a drift experiment using a seeded shift applied to a copy
    of reference features.
3.  PSI is computed per feature and summarized using configurable
    thresholds that are labelled as heuristics, not universal standards.
4.  If drift is detected, system records an alert and recommends review;
    it does not automatically promote a new model without evaluation.
5.  A challenger model can be trained in a controlled experiment,
    compared on the same validation protocol and promoted only through
    an explicit, logged action if it satisfies documented criteria.

## 4. Functional requirements

Priority notation: P0 required; P1 important; P2 deferred/stretch.

### 4.1 M1 --- Credit Risk Intelligence

**FR-CR-01 (P0): Dataset provenance.** The UI and documentation must
identify the dataset, source URL, license/terms, observation period,
target definition, known limitations and local file checksum. The
primary benchmark is UCI Default of Credit Card Clients unless a
documented data audit requires a change. It contains Taiwanese
credit-card clients and is not representative of present-day Indian
borrowers.

**FR-CR-02 (P0): Data pipeline.** Validate schema; separate predictors
from target; identify missing/invalid values; encode categories; fit
transformations only on training folds; persist preprocessing and model
artifacts together. Prevent target leakage and duplicate leakage across
splits.

**FR-CR-03 (P0): Model comparison.** Train at least Logistic Regression,
Random Forest and XGBoost (or a documented compatible alternative if
installation fails). Use a stratified, seeded holdout and
cross-validation on the training partition. Oversampling such as SMOTE,
if used, must occur inside training folds only. Compare class-weighted
and/or resampled approaches without evaluating on synthetic test data.

**FR-CR-04 (P0): Evaluation.** Report ROC-AUC, PR-AUC / average
precision, precision, recall, F1, confusion matrix, and calibration
diagnostics where probabilities are exposed. Include a baseline and
class prevalence. Select thresholds using training/validation data and
documented criteria; do not optimize the final holdout. Store evaluation
results as artifacts, not hard-coded frontend constants.

**FR-CR-05 (P0): Scoring.** Accept only the declared input schema;
validate ranges and missingness; run the exact preprocessing pipeline
and selected model artifact; return score, model version, timestamp and
validation warnings.

**FR-CR-06 (P0): Relative risk framing.** Because the benchmark is proxy
data, label output as an educational relative risk indicator. If a band
or percentile is shown, define its reference cohort and computation. Do
not claim to estimate a user's CIBIL score or real-world Indian default
probability. Do not label uncalibrated model output "probability of
default."

**FR-CR-07 (P0): Explainability.** Display local SHAP contributors for
the scored record and global feature importance for the chosen model.
Explain direction and magnitude carefully; avoid causal claims.
Explanations must be computed from the actual model and input. If SHAP
cannot be computed for a model, display a clear unavailable state rather
than invented contributions.

**FR-CR-08 (P0): What-if analysis.** Allow changes only to a whitelist
of supported fields, with original and modified values shown. Re-score
each scenario through the same model pipeline. Display score delta and
changed feature values. Clearly state that what-if results show model
sensitivity, not causal impact or guaranteed credit improvement.

**FR-CR-09 (P1): Model comparison page.** Compare candidate models with
the same test protocol and show selected-model rationale. Do not select
based on accuracy alone.

**FR-CR-10 (P1): India Context Layer.** Show official financial-literacy
or policy information as separately sourced rules/cards. Store source
title, publisher, URL, access date and applicable date. Never silently
mix these rules into the ML score.

### 4.2 M2 --- Personal Financial Stress and Loan Affordability

**FR-ST-01 (P0): Inputs.** Monthly take-home income, essential expenses,
discretionary expenses, liquid savings, existing monthly EMI, proposed
principal, annual interest rate and tenure. Currency is INR; amounts
must be non-negative and within sensible configured bounds.

**FR-ST-02 (P0): EMI.** Calculate monthly EMI using the standard
amortizing-loan formula. Handle zero-interest and invalid-tenure cases
explicitly. Return formula inputs and assumptions.

**FR-ST-03 (P0): Cash-flow measures.** Compute monthly surplus,
EMI-to-income ratio, savings runway based on defined essential outflows,
and emergency-fund gap against a configurable target (default target
must be clearly described as a configurable planning assumption, not a
universal rule).

**FR-ST-04 (P0): Scenario engine.** Support at least: income reduction,
temporary job loss, essential-expense increase, proposed EMI change, and
combined shock. Scenarios are deterministic and user-configurable.
Return before/after metrics and an explanation of assumptions.

**FR-ST-05 (P0): Loan affordability.** Show affordability indicators,
not a lender approval decision. Include an optional user-defined stress
case such as income reduced by 20%; the percentage must be visible and
editable.

**FR-ST-06 (P1): Macro-linked scenario.** If a suitable official source
is available, allow an explicitly sourced benchmark interest-rate shock;
otherwise use a clearly labelled user-configurable assumption. Do not
depend on a live macro API.

**FR-ST-07 (P0): Validation.** Unit-test formulas against
hand-calculated examples, zero-interest loans, zero income, insufficient
savings, boundary tenures and malformed inputs.

### 4.3 M3 --- Portfolio Market Risk Lab

**FR-MR-01 (P0): Data source and caching.** Use daily historical prices
from `yfinance` as an optional refresh provider. A versioned CSV/Parquet
snapshot is the reliable demo source. The app must work if network
access is absent or the provider changes. Record ticker, source, date
range, retrieval time, currency, frequency and any missing-data
handling.

**FR-MR-02 (P0): Supported universe.** Start with a small, documented
universe of liquid, supported symbols with valid daily history. Allow
the team to add symbols through configuration. Do not promise universal
symbol coverage or live prices. Never mix currencies without explicit FX
conversion; if FX conversion is not implemented, reject mixed-currency
portfolios with a clear message.

**FR-MR-03 (P0): Portfolio inputs.** Support user-entered holdings or
weights. Validate weights, quantities, duplicate tickers, unavailable
data and date overlap. If weights do not sum to 100%, either normalize
with explicit user consent or reject; never silently normalize.

**FR-MR-04 (P0): Return series.** Use a documented daily price field and
return convention consistently. Handle non-trading days and missing
observations explicitly. Align asset dates before aggregation; do not
forward-fill prices across long gaps without warning. Cache normalized
prices and returns with source metadata.

**FR-MR-05 (P0): Risk metrics.** Calculate at minimum: - daily and
annualized volatility (state the annualization assumption); - maximum
drawdown from a portfolio value series; - historical VaR at 95% and
99%; - parametric VaR using a documented distributional assumption; -
historical Expected Shortfall / CVaR; - correlation matrix for portfolio
constituents; and - portfolio value/return series over the selected
period.

Define sign conventions clearly. VaR must be displayed as a loss
magnitude or a quantile consistently, not interchangeably. Explain that
VaR is not a worst-case-loss bound and does not describe losses beyond
its threshold.

**FR-MR-06 (P0): Stress scenarios.** Support a user-defined shock per
asset and at least two named examples (e.g., broad market decline and
concentrated holding shock). Apply shocks to the current portfolio
composition using a transparent one-period approximation. Show absolute
and percentage loss, asset-level contributions and assumptions. Do not
claim a scenario probability unless it is empirically estimated and
documented.

**FR-MR-07 (P0): Explainability.** Provide plain-language definitions, a
short "how calculated" disclosure, selected confidence level, lookback
period, data coverage and caveats beside metrics. Distinguish historical
observations from simulated user-defined shocks.

**FR-MR-08 (P1): Risk decomposition.** Show per-asset contribution to
portfolio volatility or stress loss using a documented method. If
weights/covariance assumptions are insufficient, show the limitation
instead of fabricated attribution.

**FR-MR-09 (P1): Data health.** Show stale-data, insufficient-history,
missing-date and source failure warnings. Do not silently present stale
data as current market data.

**FR-MR-10 (P2): Additional models.** Monte Carlo simulation, factor
models, portfolio optimization and more advanced attribution are
deferred.

### 4.4 M4 --- VaR Validation (risk-model backtesting)

**FR-VB-01 (P0): Rolling out-of-sample design.** For each forecast date,
estimate VaR using only a preceding lookback window. Compare the
forecast with the next realized portfolio return/loss. No future data
may enter the estimation window.

**FR-VB-02 (P0): Exception definition.** Define a VaR exception
consistently: realized loss exceeds the forecast VaR loss threshold.
Include confidence level, number of forecasts, exception count,
empirical exception rate and expected exception rate.

**FR-VB-03 (P0): Visualization.** Plot forecast VaR threshold and
realized loss/return series; mark exceptions; display the rolling window
and forecast dates.

**FR-VB-04 (P0): Interpretation.** Explain that finite samples can
deviate from expected exception rates. Do not declare a model "good"
solely because the observed rate is close to target. State sample-size
limitations.

**FR-VB-05 (P1): Coverage test.** Implement a documented statistical
coverage test such as Kupiec unconditional coverage only after the core
engine and tests are complete. Report assumptions and p-value
interpretation, not just pass/fail.

**FR-VB-06 (P0): Integrity.** Tests must prove each forecast uses only
prior observations and that a synthetic price path yields the expected
exception count under a hand-checkable example.

**Scope boundary:** this module validates risk estimates; it does not
test the profitability of a trading strategy.

### 4.5 M5 --- Agentic Risk Copilot

**FR-AG-01 (P0): Bounded orchestration.** Use LangGraph for a typed
state graph with explicit nodes: input validation/safety, intent
routing, tool execution or retrieval, response composition,
numeric/source validation and final response. Do not implement an
unconstrained agent loop.

**FR-AG-02 (P0): Supported intents.** Credit explanation, credit what-if
explanation, loan/EMI calculation, personal stress scenario, portfolio
risk explanation, VaR validation explanation, and general financial
education.

**FR-AG-03 (P0): Typed tools.** Tools call the same Python service
functions used by REST endpoints. The LLM must not independently
calculate authoritative EMI, VaR, portfolio loss, PSI or model scores.
Tool schemas must validate inputs and outputs.

**FR-AG-04 (P0): RAG corpus.** Start with a small curated set of public
financial-literacy documents and official sources. Store source
metadata: title, publisher, URL, retrieval/access date, document version
and relevant section/page where available. Do not ingest arbitrary web
content at runtime.

**FR-AG-05 (P0): Retrieval.** Use ChromaDB with a local embedding model
where practical. If embedding/model downloads are unavailable, provide a
deterministic keyword/TF-IDF fallback. Chunking, metadata filters and
top-k retrieval must be configurable and tested.

**FR-AG-06 (P0): Grounded response.** For factual educational answers,
cite retrieved sources. For numeric answers, reference actual tool
outputs and show relevant assumptions. If retrieval confidence is low or
no source supports a claim, say so and ask a clarifying question or give
a limitation response.

**FR-AG-07 (P0): Safety.** No personalized security recommendations,
guaranteed returns, investment buy/sell signals, loan approval claims or
definitive tax/legal advice. Avoid requesting real account credentials,
PAN, Aadhaar, bank statements or other sensitive identifiers. Treat
retrieved text as untrusted data, not instructions.

**FR-AG-08 (P0): Provider fallback.** LLM calls are optional and
configured through environment variables. If the provider is absent,
quota-limited or fails, core calculations remain available and the chat
falls back to a transparent template/FAQ path. Never put secrets in
frontend code or logs.

**FR-AG-09 (P1): Conversation state.** Keep short-lived session state
only as needed. Do not store full chat histories by default. Provide
clear-session functionality if conversation state is persisted.

**FR-AG-10 (P0): Evaluation.** Maintain a versioned test set of at least
30 questions spanning supported intents, numeric tool use, retrieval,
unsupported requests and prompt injection attempts. Evaluate correct
routing, tool-use correctness, citation support, fallback behaviour and
unsafe-answer handling.

### 4.6 M6 --- Model monitoring and registry

**FR-MON-01 (P0): Model registry.** Record model ID/version, dataset
version/checksum, training timestamp, feature schema, preprocessing
artifact, hyperparameters, validation metrics and artifact path. The
active model version must be explicit.

**FR-MON-02 (P0): PSI.** Calculate Population Stability Index between a
declared reference feature distribution and a current/simulated batch.
Document binning, zero-count handling and threshold configuration.
Thresholds are operational heuristics, not universal scientific
cut-offs.

**FR-MON-03 (P0): Drift simulation.** Provide a seeded experiment that
shifts selected features or changes categorical distributions. Show
baseline vs shifted distributions and per-feature PSI from actual
computation.

**FR-MON-04 (P0): Alert records.** Store timestamp, model version,
dataset/batch ID, features affected, PSI values, configured threshold
and status. Do not show "healthy" until a real calculation has run.

**FR-MON-05 (P0): Challenger evaluation.** Train a candidate model
through a reproducible script; evaluate it using the same documented
protocol. Promotion requires explicit user action and passing configured
criteria. Never auto-promote based on drift alone.

**FR-MON-06 (P1): Rescoring comparison.** If an example batch is
available, compare scores from champion and challenger and summarize
changed outputs. Label this as a simulated batch, not live borrowers.

**FR-MON-07 (P0): Integrity.** Test PSI against hand-computable examples
and verify that promotion changes the active model version only after a
successful logged action.

### 4.7 M7 --- India context, study evaluation and reports

**FR-IN-01 (P1): Source-cited context.** Official Indian
financial-literacy/policy content is stored as a separate information
layer. Display publisher, URL and access date. It must not modify ML
predictions invisibly.

**FR-EV-01 (P0): Technical evaluation report.** Generate or save a
reproducible report with dataset provenance, split strategy, metrics,
market-risk assumptions, VaR validation results, drift experiment
results and known limitations.

**FR-EV-02 (P1): User study.** Run a small consent-based
usability/understanding exercise if approved by the mentor. Record
anonymized aggregate results only; report sample size and methodology
honestly.

**FR-REP-01 (P1): Export.** Allow export of an assessment/risk result as
JSON or CSV with timestamp, inputs, method, data source, assumptions and
model version. Do not export secrets or unnecessary personal data.

## 5. Data sources, licenses and offline strategy

### 5.1 Credit data

-   Primary benchmark: UCI Default of Credit Card Clients dataset:
    https://archive.ics.uci.edu/dataset/350/defaultofcreditcardclients
-   Keep the original downloaded file unmodified in `data/raw/` where
    license/terms allow; generate cleaned versions under
    `data/processed/`.
-   Record source URL, access date, license/terms, checksum, schema,
    target definition and preprocessing steps.
-   The dataset represents Taiwanese credit-card clients from 2005. It
    is a benchmark, not Indian lending data. The app must not claim
    CIBIL compatibility or real-world Indian default probability.
-   Do not scrape private datasets or bypass gated access.
-   Additional credit datasets are optional and must pass a
    provenance/licensing review before use.

### 5.2 Market data

-   Primary optional refresh: `yfinance` daily historical data for the
    supported ticker universe, subject to provider availability and
    applicable terms.
-   Required fallback: a versioned local CSV/Parquet snapshot containing
    sufficient daily observations for portfolio metrics and rolling VaR
    validation.
-   Include a manifest with ticker, source, date range, currency,
    frequency, retrieval timestamp, adjusted/unadjusted price field,
    missing-data handling and checksum.
-   Do not depend on a free API remaining available at demo time. No
    live price claim unless a successful fetch timestamp supports it.
-   If symbols have different currencies, reject mixed-currency
    portfolio analysis unless FX conversion is explicitly implemented
    and documented.
-   The dataset snapshot must be generated by a documented script, not
    manually fabricated.

### 5.3 Financial education corpus

-   Use a small, curated corpus of public educational materials and
    official sources. Maintain a manifest with title, publisher, URL,
    retrieval date, content type and any reuse/license notes.
-   The corpus must be versioned. Avoid unrestricted scraping,
    copyrighted book ingestion, or documents with unclear reuse rights.
-   Retrieval answers must retain source metadata and must not invent
    page numbers or citations.

### 5.4 Offline-first requirements

  -----------------------------------------------------------------------
  Dependency              Normal mode             Required fallback
  ----------------------- ----------------------- -----------------------
  Market data             Refresh cached history  Local versioned price
                          when explicitly         snapshot
                          requested               

  Hosted LLM              Optional provider       Template/FAQ responses
                          configured via backend  and deterministic tools
                          environment variable    

  Embeddings              Local embedding model,  TF-IDF/keyword
                          downloaded/cached       retrieval
                          before demo             

  Dataset                 Local downloaded        Clear setup
                          benchmark               instructions and
                                                  checksum; do not
                                                  fabricate sample
                                                  records

  Database                SQLite                  Seeded demo database
                                                  created from documented
                                                  fixtures

  Charts                  Computed API response   Error/empty state,
                                                  never placeholder
                                                  metrics
  -----------------------------------------------------------------------

The team must perform an offline demo rehearsal before final submission.

## 6. Technical architecture

### 6.1 Architecture style

Use a modular monolith with domain service boundaries. The frontend
calls REST endpoints. FastAPI routers validate requests and delegate to
services. LangGraph tools call the same service layer as the UI. The ML
pipeline runs as reproducible scripts and saves artifacts that the API
loads read-only during normal scoring.

Logical flow:

`Next.js UI → FastAPI routers → domain services → (ML artifacts | financial calculation engines | market data cache | LangGraph/RAG) → SQLAlchemy/SQLite + artifact store`

The agent must not be a parallel implementation of the financial logic.
It orchestrates domain services.

### 6.2 Frontend

-   Next.js App Router, React and TypeScript.
-   Tailwind CSS and shadcn/ui for accessible UI components.
-   Recharts for charts; TanStack Query for server-state
    fetching/caching; Zod for client form schemas.
-   Responsive desktop-first dashboard with consistent loading, empty,
    stale-data, validation and error states.
-   Pages: Overview, Credit Risk, Financial Stress, Loan Affordability,
    Market Risk, VaR Validation, Risk Copilot, Model Health,
    Methodology/Data Sources.
-   Every chart includes units, date range, methodology, and a clear
    empty/error state. Do not use fake placeholder chart data.
-   Avoid excessive animation or a marketing landing page that takes
    priority over working analysis.

### 6.3 Backend

-   Python 3.11+ (choose a version supported by all selected libraries
    and pin it in the project).
-   FastAPI, Uvicorn, Pydantic v2, pydantic-settings, SQLAlchemy 2.x and
    Alembic migrations.
-   `pandas`, `numpy`, `scipy`, `scikit-learn`, `xgboost`, `shap`,
    `imbalanced-learn`, `joblib`.
-   Market data adapter: `yfinance` optional; local CSV/Parquet data
    required for deterministic tests.
-   Agent/RAG: LangGraph, LangChain Core where useful, one optional
    provider SDK, ChromaDB and a local embedding option. Avoid adding
    multiple agent frameworks.
-   Tests: pytest, httpx/TestClient; frontend tests with the team's
    chosen React testing tool; Playwright smoke tests if time permits.
-   Quality: Ruff formatting/linting, type hints, Pydantic validation,
    structured logging, `.env.example`, dependency lock files.

### 6.4 Persistence and artifact storage

-   SQLite via SQLAlchemy for assessments, model registry metadata,
    monitoring runs, alerts, market-data manifest and user-created
    portfolios if persistence is needed.
-   Store large tabular market snapshots as CSV/Parquet and model
    artifacts as versioned files under a documented artifact directory.
    Store metadata/checksums in SQLite.
-   Do not store raw LLM API keys, bank credentials, or sensitive
    identity documents.
-   Use Alembic for schema migrations once database tables stabilize.
-   Keep training and inference preprocessing artifacts together. An
    artifact version is immutable; new training creates a new version
    rather than overwriting the active artifact in place.

### 6.5 Containerization and reproducibility

-   Docker Compose for local frontend/backend startup where practical.
-   A single command or clearly documented commands must start the app
    from a clean clone.
-   Include `.env.example`, `Makefile` or equivalent scripts, pinned
    dependencies, dataset setup script, model-training script, test
    script and demo-seed script.
-   Do not require a paid cloud account. Deployment to a free tier is
    optional and must not be a prerequisite for grading.

## 7. Proposed repository structure

``` text
riskwise/
├── PRD.md
├── README.md
├── .env.example
├── docker-compose.yml
├── Makefile
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   ├── DATA_SOURCES.md
│   ├── TEST_PLAN.md
│   ├── KNOWN_LIMITATIONS.md
│   ├── MODEL_CARD.md
│   └── API_CONTRACTS.md
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── credit/
│   │   ├── stress/
│   │   ├── loans/
│   │   ├── market-risk/
│   │   ├── var-validation/
│   │   ├── copilot/
│   │   ├── model-health/
│   │   └── methodology/
│   ├── components/
│   ├── lib/
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/              # settings, logging, exceptions
│   │   ├── api/               # routers and dependencies
│   │   ├── schemas/           # request/response models
│   │   ├── db/                # models, sessions, migrations
│   │   ├── services/
│   │   │   ├── credit/
│   │   │   ├── financial_stress/
│   │   │   ├── market_risk/
│   │   │   ├── var_validation/
│   │   │   └── monitoring/
│   │   ├── agents/            # graph, tools, safety, retrieval
│   │   └── tests/
│   └── pyproject.toml
├── ml/
│   ├── data_validation.py
│   ├── preprocessing.py
│   ├── features.py
│   ├── train.py
│   ├── evaluate.py
│   ├── explain.py
│   ├── monitor.py
│   └── registry.py
├── data/
│   ├── raw/                   # downloaded, provenance documented
│   ├── processed/
│   ├── market_snapshots/
│   └── manifests/
├── knowledge/
│   ├── sources/
│   ├── manifest.csv
│   └── README.md
├── artifacts/
│   ├── models/
│   ├── evaluation/
│   └── vector_index/          # generated locally; do not require in Git
├── reports/
└── scripts/
    ├── setup_data.py
    ├── train_models.py
    ├── build_market_snapshot.py
    ├── seed_demo.py
    └── run_evaluation.py
```

This is a target structure, not a reason to create empty files in
advance. Add modules when the corresponding milestone begins.

## 8. API contract proposal

Prefix all endpoints with `/api/v1`. Use Pydantic request/response
models, consistent error responses and generated OpenAPI documentation.
Keep routers thin.

  ------------------------------------------------------------------------------------------
  Method                  Endpoint                                   Purpose
  ----------------------- ------------------------------------------ -----------------------
  GET                     `/health`                                  Liveness check; no
                                                                     claim that models/data
                                                                     are healthy.

  GET                     `/api/v1/system/status`                    Actual
                                                                     model/data/provider
                                                                     status and offline
                                                                     mode.

  GET                     `/api/v1/credit/models`                    List trained model
                                                                     versions and real
                                                                     evaluation metadata.

  POST                    `/api/v1/credit/score`                     Validate features and
                                                                     return score, model
                                                                     version and warnings.

  POST                    `/api/v1/credit/explain`                   Return computed
                                                                     local/global
                                                                     explanation data.

  POST                    `/api/v1/credit/what-if`                   Re-score whitelisted
                                                                     feature scenarios.

  POST                    `/api/v1/finance/emi`                      Compute EMI and
                                                                     repayment summary.

  POST                    `/api/v1/finance/stress-test`              Compute before/after
                                                                     personal cash-flow
                                                                     scenarios.

  GET                     `/api/v1/market/universe`                  Return configured
                                                                     supported symbols and
                                                                     metadata.

  POST                    `/api/v1/market/portfolio/analyze`         Calculate portfolio
                                                                     metrics from cached
                                                                     historical prices.

  POST                    `/api/v1/market/portfolio/stress-test`     Apply specified
                                                                     asset/portfolio shocks.

  POST                    `/api/v1/market/var/validate`              Run rolling
                                                                     out-of-sample VaR
                                                                     validation.

  GET                     `/api/v1/monitoring/models`                List model registry
                                                                     metadata.

  POST                    `/api/v1/monitoring/drift/run`             Run PSI calculation on
                                                                     a selected
                                                                     reference/current
                                                                     batch.

  POST                    `/api/v1/monitoring/challenger/evaluate`   Evaluate a challenger
                                                                     using the documented
                                                                     protocol.

  POST                    `/api/v1/monitoring/challenger/promote`    Explicitly promote a
                                                                     passing challenger and
                                                                     log the decision.

  POST                    `/api/v1/copilot/message`                  Run bounded LangGraph
                                                                     flow and return answer,
                                                                     sources and tool trace
                                                                     summary.

  GET                     `/api/v1/methodology`                      Return method
                                                                     definitions, data
                                                                     limitations and
                                                                     disclaimer text.
  ------------------------------------------------------------------------------------------

Endpoint names may be refined during implementation, but changes must be
recorded in `docs/API_CONTRACTS.md`. Never return internal stack traces
or secrets to the frontend. Add request IDs and structured server logs.

## 9. Data model proposal

Use SQLAlchemy models and migrations; exact fields can be refined in the
first milestone.

-   **ModelVersion:** `id`, `model_name`, `version`, `dataset_id`,
    `feature_schema_version`, `preprocessing_artifact`,
    `model_artifact`, `metrics_json`, `trained_at`, `status`,
    `checksum`.
-   **AssessmentRun:** `id`, `created_at`, `model_version_id`,
    `input_snapshot_json` (minimize personal data), `score`,
    `risk_band`, `warnings_json`.
-   **StressRun:** `id`, `created_at`, `input_snapshot_json`,
    `scenario_json`, `baseline_metrics_json`, `stressed_metrics_json`.
-   **PortfolioDefinition:** `id`, `name`, `currency`, `holdings_json`,
    `created_at`, `updated_at`.
-   **MarketDataManifest:** `id`, `provider`, `symbol`, `currency`,
    `start_date`, `end_date`, `frequency`, `retrieved_at`, `file_path`,
    `checksum`, `quality_notes_json`.
-   **MarketRiskRun:** `id`, `created_at`, `portfolio_snapshot_json`,
    `method`, `confidence_level`, `lookback`, `metrics_json`,
    `data_manifest_ids_json`.
-   **VaRValidationRun:** `id`, `created_at`, `portfolio_snapshot_json`,
    `method`, `confidence_level`, `lookback`, `forecast_count`,
    `exception_count`, `exception_rate`, `results_path`.
-   **DriftRun:** `id`, `created_at`, `model_version_id`,
    `reference_batch_id`, `current_batch_id`, `psi_by_feature_json`,
    `threshold_config_json`, `status`.
-   **MonitoringAlert:** `id`, `created_at`, `model_version_id`,
    `drift_run_id`, `severity`, `message`, `acknowledged_at`.
-   **AuditEvent:** `id`, `created_at`, `actor_type`, `action`,
    `target_type`, `target_id`, `details_json` (no secrets or raw
    sensitive inputs).

Store large arrays and time series in versioned files when more
appropriate than SQLite rows. Document retention policy and avoid
persisting raw chat transcripts by default.

## 10. Core calculations and scientific conventions

### 10.1 Loan EMI

For principal `P`, monthly rate `r = annual_rate / 12`, and number of
monthly payments `n`:

`EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)` for `r > 0`; for `r = 0`,
`EMI = P / n`.

Use decimal-safe rounding for displayed currency; retain full precision
internally. Validate principal, rate and tenure before computation.

### 10.2 Personal stress metrics

-   `monthly_surplus = monthly_income - essential_expenses - discretionary_expenses - existing_EMIs - proposed_EMI`
    (when evaluating a proposed loan).
-   `EMI_to_income = total_monthly_EMIs / monthly_income`, only when
    income is positive; otherwise return an explicit undefined/error
    state.
-   `runway_months = liquid_savings / monthly_essential_outflows`, only
    when essential outflows are positive.
-   Scenario changes must be explicit input parameters. State whether
    income/expenses are monthly and whether EMI is included in runway
    outflows to avoid double-counting.

### 10.3 Market-risk conventions

-   Use a consistent daily price field and daily simple or log return
    convention; document the choice.
-   Portfolio returns must account for holdings/weights and the chosen
    rebalancing assumption. The baseline should use fixed weights over
    the selected analysis window unless the user explicitly selects a
    different supported method.
-   Annualized volatility uses daily standard deviation multiplied by
    `sqrt(252)` as an explicit convention; disclose that 252 is an
    approximation.
-   Maximum drawdown is calculated from the portfolio value/index series
    relative to its running peak.
-   Historical VaR at confidence `c` is derived from the empirical lower
    tail of portfolio returns or equivalent loss distribution. Define
    whether output is a loss-positive magnitude.
-   Parametric VaR assumes a specified return distribution (normal
    baseline); label the assumption and do not imply it captures fat
    tails.
-   Expected Shortfall/CVaR is the mean loss in the tail beyond the VaR
    threshold, using a clearly documented quantile convention.
-   Correlations use aligned return observations and require sufficient
    overlapping history.
-   Stress-test outputs are deterministic scenario losses, not
    probabilities or forecasts.
-   Rolling VaR validation must use a trailing window only. At time `t`,
    estimate using data before `t` and test against the next realized
    observation. State the minimum required observations and fail
    clearly when insufficient data exists.

### 10.4 Population Stability Index

Use declared bins derived from the reference distribution and apply the
same bin edges to reference and current data. Handle zero proportions
with a documented small smoothing constant. Report PSI per feature and
aggregate summaries. Do not use one universal threshold as proof of
model failure; thresholds must be configurable and described as
operational heuristics.

## 11. UX and design requirements

-   Build an analytical product, not only a landing page. The first
    screen should link to the main workflows and show actual system/data
    status.
-   Use a consistent design system, responsive layouts, readable chart
    labels and clear numeric units.
-   Every metric card must expose its definition or provide a nearby
    "How is this calculated?" explanation.
-   Display source, date range, freshness and warning state for market
    data.
-   Display model version, dataset provenance and proxy-data limitation
    in credit risk.
-   Display assumptions beside stress-test and VaR results.
-   Show loading, empty, validation-error, stale-data, offline and
    API-error states.
-   Provide sample/demo inputs from real local fixtures; label them
    "demo data."
-   No decorative charts populated with random values.
-   Use accessible form labels, keyboard navigation, adequate contrast
    and meaningful error messages.

## 12. Security, privacy and responsible use

-   Never collect PAN, Aadhaar, bank login credentials, full card
    numbers or account statements.
-   Use environment variables for secrets; `.env` must be ignored by
    Git. Only `.env.example` with placeholders is committed.
-   Validate and bound all numeric inputs, file sizes and uploaded files
    if uploads are implemented.
-   Limit request sizes and add basic rate limiting to LLM-facing
    endpoints if exposed beyond localhost.
-   Treat RAG documents and user messages as untrusted content; never
    allow them to override system policy or call arbitrary tools.
-   Do not execute generated code or arbitrary shell commands from an
    agent.
-   Log event metadata and errors without logging secrets or unnecessary
    raw financial inputs.
-   Include educational-use and data-provenance notices.
-   No claim of credit approval, investment suitability, guaranteed
    return, or regulatory certification.

## 13. Testing and quality gates

### 13.1 Backend tests

-   Unit tests for EMI, cash flow, runway, stress scenarios, return
    calculations, VaR, Expected Shortfall, drawdown, correlations and
    PSI.
-   Schema tests for invalid types, negative amounts, missing required
    fields, unsupported symbols and mixed currencies.
-   Deterministic tests using local fixtures only; no live market-data
    or LLM dependency.
-   Integration tests for every P0 endpoint, database persistence and
    error responses.
-   ML tests for train/test separation, pipeline persistence, consistent
    inference schema and artifact versioning.
-   VaR leakage test proving each forecast uses only prior data.
-   RAG tests for metadata preservation, empty retrieval, untrusted
    instructions and citations.
-   Agent tests proving calculation intents call tools and unsupported
    requests do not trigger unrelated tools.
-   Monitoring tests proving promotion requires a successful challenger
    evaluation and explicit action.

### 13.2 Frontend tests

-   Form validation and error display.
-   Loading/empty/offline/stale-data states.
-   Correct display of units, confidence levels, date ranges and model
    versions.
-   No chart renders fabricated fallback metrics.
-   End-to-end happy paths for credit scoring, personal stress,
    market-risk analysis, VaR validation and copilot fallback.

### 13.3 Quality gates

A milestone cannot be marked complete until: - linting and type checks
pass for changed modules; - unit and integration tests pass; - API
schemas match frontend usage; - README/setup instructions remain
accurate; - no secrets are committed; - screenshots/demo data are
sourced from actual local fixtures or computed output; - relevant
limitations are documented.

## 14. Evaluation plan and success criteria

These are acceptance criteria, not promised performance results. The
project must report actual values even if performance is modest.

### Credit model

-   At least three candidate model families compared on the same seeded
    split/protocol.
-   Report ROC-AUC, PR-AUC, precision, recall, F1, confusion matrix and
    class prevalence.
-   Explain threshold choice and calibration limitations.
-   Provide computed per-record SHAP explanations for the selected model
    or a documented alternative.
-   Verify no target leakage and no test-set resampling.

### Financial calculations

-   All formulas pass unit tests with hand-calculated examples and
    boundary cases.
-   Scenario results are reproducible for identical inputs.

### Market risk

-   Risk metrics match hand-computable toy portfolio fixtures within a
    documented numerical tolerance.
-   Data provenance, currency and coverage are visible.
-   At least two market stress scenarios are reproducible.
-   VaR validation is rolling and out-of-sample, with exception
    count/rate and caveats.

### Agentic/RAG

-   Versioned question set covers every supported intent and
    unsupported/safety cases.
-   Measure routing accuracy, tool-call correctness, source support and
    fallback success.
-   No unsupported factual claim is marked as cited; no LLM-generated
    number overrides a tool result.

### Monitoring

-   PSI matches hand-computable examples.
-   Drift experiment is seeded and repeatable.
-   Challenger promotion is explicit and logged.
-   Actual model/data status is shown; no hard-coded "healthy" state.

### Engineering

-   Clean-clone setup documented and tested.
-   Core demo works without a hosted LLM key and without a live
    market-data fetch.
-   All P0 acceptance tests pass.
-   A report contains methods, actual results, limitations and
    reproducibility steps.

Do not invent numeric performance targets before a baseline experiment.
Set any project-specific thresholds after measuring baseline behaviour
and record the rationale.

## 15. Milestones and 16-week plan

### Milestone 0 --- Requirements and setup (Weeks 1--2)

**Deliverables:** repository, PRD, architecture, data-source manifest,
environment setup, API contracts, baseline UI wireframe.\
**Definition of Done:** clean clone runs; lint/test commands exist;
dataset and market snapshot setup instructions are documented; no secret
required for startup.

### Milestone 1 --- Data and credit ML (Weeks 3--4)

**Deliverables:** validated data pipeline, baseline models, model
comparison report, saved preprocessing/model artifacts, evaluation
tests.\
**Definition of Done:** deterministic training script runs; metrics are
computed from held-out data; leakage checks pass; artifacts include
metadata.

### Milestone 2 --- Credit API and explanations (Weeks 5--6)

**Deliverables:** scoring, SHAP, what-if endpoints; credit UI and
methodology disclosure.\
**Definition of Done:** score and explanations use the persisted
artifact; invalid input is rejected; no CIBIL/Indian-PD claim is shown.

### Milestone 3 --- Financial engine (Weeks 7--8)

**Deliverables:** EMI, affordability, runway, stress scenarios, unit
tests and UI.\
**Definition of Done:** formulas pass hand-calculated tests and the UI
displays assumptions and before/after results.

### Milestone 4 --- Market Risk Lab (Weeks 9--10)

**Deliverables:** local market snapshot, data adapter, portfolio
metrics, stress scenarios and UI.\
**Definition of Done:** app works with local data; missing/stale data is
reported; core metrics match toy fixtures; no live provider is required
for the demo.

### Milestone 5 --- Rolling VaR validation (Week 11)

**Deliverables:** rolling out-of-sample VaR forecasts, exception
metrics, chart and tests.\
**Definition of Done:** leakage test passes and forecast dates/realized
outcomes align correctly.

### Milestone 6 --- Agentic copilot and RAG (Weeks 12--13)

**Deliverables:** LangGraph state graph, typed tools, curated corpus,
citations, fallback and evaluation question set.\
**Definition of Done:** each supported intent routes correctly; numeric
tools are authoritative; fallback works without provider credentials.

### Milestone 7 --- Monitoring, integration and evaluation (Week 14)

**Deliverables:** PSI, drift experiment, registry, challenger
evaluation, integration tests.\
**Definition of Done:** drift values are computed; active model state is
real; promotion is logged and gated.

### Milestone 8 --- Hardening and submission (Weeks 15--16)

**Deliverables:** UI polish, documentation, model card, evaluation
report, demo script, poster/presentation assets.\
**Definition of Done:** offline rehearsal succeeds; all P0 tests pass;
known limitations are disclosed; no fabricated metrics or broken core
workflow remains.

**Schedule rule:** if behind, reduce visual polish and P1 features
before cutting tests, data provenance, the market-risk core, or the
offline demo path. Do not add trading-strategy backtesting to recover
perceived scope.

## 16. Recommended implementation order and team split

For four students: - **Student A --- ML:** data validation, credit model
training/evaluation, SHAP, model registry. - **Student B ---
backend/financial services:** FastAPI, schemas, SQLite, EMI/stress
engine, API tests. - **Student C --- market risk:** price snapshot/data
adapter, portfolio calculations, stress scenarios, rolling VaR
validation. - **Student D --- frontend/agent integration:** Next.js
dashboards, LangGraph/RAG, UI integration and agent evaluation.

All team members must review integration and contribute to the report.
With three students, combine frontend and agent work, and keep P1 items
deferred.

Use shared contracts and small pull requests. Avoid one person building
the entire application independently in an AI coding tool. Antigravity
should implement bounded milestones, produce tests, explain changed
files and stop for review after each milestone.

## 17. Antigravity execution protocol

At the start of each milestone, Antigravity must: 1. Read `PRD.md`,
`docs/DECISIONS.md`, the relevant architecture/API docs and current
tests. 2. Summarize the planned changes and identify dependencies before
editing. 3. Implement only the current milestone's scope. 4. Add or
update tests with every new service or endpoint. 5. Run relevant
test/lint/type-check commands and report exact results. 6. Update
documentation and `docs/DECISIONS.md` for any necessary deviation. 7.
Stop at the milestone boundary and report: files changed, behaviour
implemented, commands run, pass/fail counts, known limitations and next
milestone.

Antigravity must not: - generate the whole project in one unreviewed
pass; - invent model scores, charts, data, source citations or
successful test results; - substitute mock endpoints for real
calculations; - use paid APIs as required dependencies; - add
unrequested features or dependencies; - silently skip tests or hide
failures; - promote a challenger model automatically; - use an LLM to
calculate authoritative financial metrics; - build the deferred
trading-strategy backtester before P0 acceptance criteria pass.

## 18. Final demo acceptance checklist

-   [ ] Clean setup works using documented commands.
-   [ ] Credit dataset provenance and proxy-data limitations are
    visible.
-   [ ] Three credit model families are compared with real evaluation
    metrics.
-   [ ] Credit score, SHAP explanation and what-if comparison run from
    real artifacts.
-   [ ] EMI, affordability, runway and stress scenarios pass formula
    tests.
-   [ ] Market-risk dashboard computes portfolio metrics from the local
    snapshot.
-   [ ] At least two stress scenarios produce computed results and
    visible assumptions.
-   [ ] Rolling VaR validation uses no future observations.
-   [ ] Copilot routes to tools and RAG sources; offline fallback works.
-   [ ] PSI/drift values and model versions are computed and persisted.
-   [ ] Tests, known limitations, data sources and evaluation report are
    available.
-   [ ] No paid API, live data feed, live broker or secret is required
    for the core demo.
-   [ ] No trading-strategy backtester is presented as a completed
    feature unless separately approved and implemented after P0
    completion.

## 19. Known limitations to disclose in the final report

-   Credit benchmark is non-Indian and historical; outputs are
    educational relative indicators, not real-world Indian default
    probabilities or CIBIL scores.
-   Market history from a free provider may be delayed, incomplete or
    subject to terms and availability; cached data is used for
    reproducibility.
-   VaR depends on the chosen return distribution, confidence level,
    lookback window and historical regime; it does not bound the maximum
    possible loss.
-   Stress scenarios are conditional what-if exercises, not forecasts.
-   PSI detects distribution shift, not necessarily deterioration in
    predictive performance. Real performance monitoring requires later
    outcome labels.
-   LLM responses may be incomplete; source retrieval and deterministic
    tools reduce but do not eliminate errors.
-   A local research prototype is not a production lending or
    investment-advice system.

## 20. References and implementation starting points

-   UCI Default of Credit Card Clients dataset:
    https://archive.ics.uci.edu/dataset/350/defaultofcreditcardclients
-   yfinance project and usage notes:
    https://github.com/ranaroussi/yfinance
-   SHAP documentation: https://shap.readthedocs.io/
-   scikit-learn documentation: https://scikit-learn.org/stable/
-   XGBoost documentation: https://xgboost.readthedocs.io/
-   FastAPI documentation: https://fastapi.tiangolo.com/
-   LangGraph documentation:
    https://docs.langchain.com/oss/python/langgraph/overview
-   Chroma documentation: https://docs.trychroma.com/
-   Next.js documentation: https://nextjs.org/docs
-   Tailwind CSS documentation: https://tailwindcss.com/docs

Check current package compatibility and applicable dataset/provider
terms during implementation. The PRD intentionally specifies stable
capabilities rather than relying on a single API provider or hard-coded
library patch version.

------------------------------------------------------------------------

**Version 3.0 summary:** RiskWise is a multi-domain financial risk
intelligence platform. The committed scope is credit-risk ML +
explainability, personal financial stress/loan affordability, portfolio
market risk, rolling VaR validation, bounded agentic RAG, and model
monitoring. A trading-strategy backtester is explicitly deferred so the
expanded project remains coherent, testable, zero-budget-first and
feasible for a final-year engineering team.
