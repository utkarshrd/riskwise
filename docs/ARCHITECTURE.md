# RiskWise Architecture Documentation

## 1. System Overview

RiskWise is an explainable, agentic multi-domain financial risk intelligence platform designed as a modular monolith. It unites borrower credit-risk analytics, personal financial stress testing, portfolio market-risk measurement, rolling VaR validation, ML lifecycle drift monitoring, and a bounded agentic copilot.

```
+------------------------------------------------------------------------------------+
|                                Next.js Frontend (App Router)                       |
|  - Overview Dashboard      - Credit Risk & SHAP      - Financial Stress & Loans    |
|  - Market Risk Lab         - VaR Validation          - Model Health & Drift        |
|  - Risk Copilot            - Methodology / Data Disclosures                        |
+------------------------------------------------------------------------------------+
                                           | REST (Fetch / TanStack Query)
                                           v
+------------------------------------------------------------------------------------+
|                                FastAPI Backend Service                             |
|  +------------------------------------------------------------------------------+  |
|  | Routers (/api/v1): system, credit, finance, market, monitoring, copilot       |  |
|  +------------------------------------------------------------------------------+  |
|  | Domain Services Layer:                                                       |  |
|  |  - CreditService         (Inference, SHAP explanation, constrained what-if)  |  |
|  |  - FinancialStressEngine (EMI, runway, scenario cash flow calculations)      |  |
|  |  - MarketRiskEngine      (Historical/Parametric VaR, CVaR, stress shocks)    |  |
|  |  - VaRValidationService  (Rolling out-of-sample backtesting, exceptions)     |  |
|  |  - MonitoringService     (PSI computation, challenger evaluation, registry)  |  |
|  |  - CopilotAgentService   (LangGraph orchestration, tool routing, RAG)        |  |
|  +------------------------------------------------------------------------------+  |
|  | Persistence & Storage:                                                       |  |
|  |  - SQLite (SQLAlchemy 2.x) for runs, manifests, drift logs, audit events     |  |
|  |  - File Artifacts: models/ (*.joblib), market_snapshots/ (*.csv), knowledge/ |  |
+------------------------------------------------------------------------------------+
```

## 2. Core Architectural Principles

1. **Modular Monolith:** Single Next.js frontend, single FastAPI backend. Enforced separation of concerns via domain service packages.
2. **Deterministic Financial Core:** Authoritative calculations (EMI, runway, VaR, CVaR, PSI) are executed strictly in deterministic Python service routines. The LLM agent orchestrates and explains results; it never performs or overrides arithmetic calculations.
3. **Artifact-Driven ML Inference:** Scoring models load immutable serialized model artifacts (`.joblib`) created by separate, reproducible training scripts (`ml/train.py`, `scripts/train_models.py`).
4. **Strict Temporal Separation (No Look-Ahead Leakage):**
   - Credit model training and evaluation strictly isolate test folds without preprocessing leakage.
   - Rolling VaR validation estimates risk metrics using exclusively prior historical windows ($t < T$) and evaluates against realized return at $T$.
5. **Offline Capability & Fallbacks:** The platform functions completely offline without external API keys or live feeds.

## 3. Directory Layout and Module Boundaries

- `backend/app/api/`: REST routing, parameter validation (Pydantic v2), dependency injection.
- `backend/app/services/`: Pure business logic and calculation engines.
- `backend/app/schemas/`: API request and response data contracts.
- `backend/app/db/`: SQLAlchemy ORM models and database session management.
- `backend/app/agents/`: LangGraph workflow state machine, typed tools, and vector/keyword retrieval.
- `ml/`: Offline training, evaluation, SHAP calculation, and drift monitoring pipelines.
- `frontend/app/`: Next.js App Router pages and UI components.
- `data/`: Raw source data, cleaned snapshots, manifests, and checksums.
- `artifacts/`: Serialized models, evaluation metric reports, and vector indexes.

## 4. Communication Patterns

- **Frontend to Backend:** HTTP REST with JSON payloads over `/api/v1/*`.
- **Backend Internal:** Direct synchronous Python function invocations between routers and domain services.
- **Agent Orchestration:** LangGraph state graph routes user prompts to verified tools matching the domain service APIs.
