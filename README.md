# RiskWise — Multi-Domain Financial Risk Intelligence Platform

[![CI](https://github.com/utkarshrd/riskwise/actions/workflows/ci.yml/badge.svg)](https://github.com/utkarshrd/riskwise/actions/workflows/ci.yml)

RiskWise is an explainable, agentic financial risk intelligence platform combining borrower credit-risk analysis, personal financial stress testing, portfolio market-risk measurement (8 VaR/ES models), rolling Value-at-Risk model validation (Kupiec + Christoffersen), and source-grounded educational guidance.

Built as a modular monolith adhering to PRD v3.0 specifications.

**What it does today**
- 2,617 NSE and US instruments in the instrument master, with prices fetched and cached on first use.
- Portfolio market risk by eight VaR methods, expected shortfall, drawdown, correlation and charts computed from the portfolio's actual returns.
- Rolling VaR validation (Kupiec, Christoffersen, Basel traffic light) and a side-by-side model comparison.
- Opt-in USD/INR conversion for mixed portfolios, named historical stress replays (COVID 2020, election day 2024, Adani 2023), reverse stress, and broker CSV import (Zerodha, Groww).
- A copilot that calls the same tools and removes any number no tool produced.
- Light and dark themes, and a methods reference that every metric tooltip links to.

---

## Architecture at a Glance

- **Frontend:** Next.js (App Router, TypeScript, Tailwind CSS)
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite
- **ML / Risk Engine:** scikit-learn, XGBoost, SHAP, NumPy, SciPy, Pandas
- **Agent Orchestrator:** LangGraph bounded tool-calling & RAG retriever
- **Zero-Secret Startup:** Fully operational offline mode; no external API key or paid feed required.

For in-depth architectural details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Directory Layout

```text
├── PRD.md                       # Implementation source of truth (v3.0)
├── README.md                    # Project documentation & setup instructions
├── .env.example                 # Environment variables template (offline defaults)
├── Makefile                     # Task runner
├── docker-compose.yml           # Containerized orchestration
├── docs/                        # Architectural documentation
│   ├── ARCHITECTURE.md          # Modular monolith design & data flow
│   ├── DECISIONS.md             # Architectural Decision Records (ADRs)
│   ├── DATA_SOURCES.md          # Benchmark provenance & offline strategy
│   ├── TEST_PLAN.md             # Testing strategy & quality gates
│   ├── KNOWN_LIMITATIONS.md     # Disclosures & academic boundaries
│   ├── MODEL_CARD.md            # Credit model card template
│   └── API_CONTRACTS.md         # FastAPI endpoint specifications
├── backend/                     # FastAPI backend service
│   ├── app/
│   │   ├── main.py              # Application entrypoint & CORS
│   │   ├── core/                # Settings, logging, exceptions
│   │   ├── api/                 # API routers (/api/v1)
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── db/                  # SQLAlchemy models & sessions
│   │   └── services/            # Domain calculation & ML services
│   ├── tests/                   # Pytest suite
│   ├── requirements.txt         # Pinned Python dependencies
│   └── pyproject.toml           # Project metadata & linter configuration
├── frontend/                    # Next.js App Router application
├── data/                        # Datasets, snapshots, manifests
│   ├── raw/                     # Raw input benchmarks
│   ├── processed/               # Cleaned data partitions
│   ├── market_snapshots/        # Local offline daily price snapshots
│   ├── reference/               # EQUITY_L.csv — official NSE listed equities (2,608)
│   └── manifests/               # Data verification manifests
├── knowledge/                   # Curated RAG documents & manifest
└── scripts/                     # Setup, data ingestion, evaluation scripts
    ├── setup_data.py            # Data setup & status verification utility
    └── build_instrument_master.py  # Ingests EQUITY_L.csv → instruments SQLite table
```

### Key Documentation

| File | Purpose |
|---|---|
| [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) | Auto-generated FastAPI endpoint specifications (the 18 PRD endpoints plus the additions since) |
| [docs/MARKET_RISK_METHODS.md](docs/MARKET_RISK_METHODS.md) | Formulas & references for all 8 VaR/ES models + backtest tests |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architectural Decision Records (ADR-001 – ADR-015) |
| [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | Explicit methodology disclosures and system boundaries |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Modular monolith design and data flow |

---

## Quick Start

### Option A: Run with Docker (Recommended for Friends / Easy Setup)
The backend image bundles the trained credit models, retrieval index, knowledge corpus and market snapshots, so no Python/Node, API keys or dataset are needed on the target machine. Full details: [docs/DOCKER.md](docs/DOCKER.md).

1. **Start** (from a checkout that has `artifacts/models/`, or after `docker load -i riskwise-docker.tar`):
   ```bash
   docker compose up -d --build   # or just: docker compose up -d   after docker load
   ```
2. **Access the application:**
   - **Frontend UI:** [http://localhost:3000](http://localhost:3000)
   - **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

To stop the containers:
```bash
docker compose down
```

---

### Option B: Local Development Setup (Manual)
- Python 3.11+
- Node.js 18+ & npm
- Git

### 1. Environment Configuration
Copy the sample environment file (no secrets required):
```bash
cp .env.example .env
```

### 2. Backend Setup
Create and activate a virtual environment, then install dependencies:
```bash
# On Windows
py -3.11 -m venv backend/venv
.\backend\venv\Scripts\pip install -r backend/requirements.txt
.\backend\venv\Scripts\alembic upgrade head
.\backend\venv\Scripts\python scripts/register_models.py

# On Linux/macOS
python3.11 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
alembic upgrade head
python scripts/register_models.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install
cd ..
```

### 4. Verify Data Setup & Status
```bash
# Check current dataset and market snapshot status
python scripts/setup_data.py --info
```

---

## Running the Application

### Start Backend
```bash
# Windows
.\backend\venv\Scripts\uvicorn backend.app.main:app --reload --port 8000

# Linux/macOS
uvicorn backend.app.main:app --reload --port 8000
```
- Interactive API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Liveness Check: [http://localhost:8000/health](http://localhost:8000/health)
- System Status: [http://localhost:8000/api/v1/system/status](http://localhost:8000/api/v1/system/status)

### Start Frontend
```bash
cd frontend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the RiskWise dashboard.

---

## Testing & Quality Gates

Run all quality checks before committing:

```powershell
# Run full backend test suite
.\.venv\Scripts\pytest backend/tests -v

# Run backend linter
.\.venv\Scripts\ruff check backend

# Run frontend build (TypeScript type-check + Next.js compile)
cd frontend; npm run build
```

**Test baseline (2026-10-23):** with the trained credit model present, 298 passing and 0 failing. In a fresh clone (no `riskwise.db`, no trained model) 282 pass and 16 skip with a stated reason, because the model files are gitignored; run `scripts/train_indian_credit.py` to enable those. A fresh clone also needs `python scripts/build_instrument_master.py` and `python scripts/build_index.py` before the tests, as the CI workflow does.

The CI workflow has not yet run on GitHub. Its frontend build step currently fails on its first run because the pinned Next.js version has a known critical advisory; see [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) section 12.

---

## Ethical Disclosure & Academic Scope

RiskWise is an educational engineering prototype developed for research and evaluation.
- Outputs represent **relative risk indicators** within the context of historical benchmark distributions.
- It does **not** estimate Indian CIBIL credit scores, guarantee investment returns, or act as an autonomous financial adviser.
- For complete disclosures, consult [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).
