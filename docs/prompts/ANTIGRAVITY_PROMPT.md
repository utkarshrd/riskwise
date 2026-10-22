# Antigravity Build Prompt: RiskWise Upgrade

Paste everything below the line into an Antigravity agent session opened at the repo root. For best results run it in Planning mode, and approve the plan phase by phase.

---

## ROLE
You are a senior full-stack engineer and quant-risk developer. You will upgrade the existing repo **RiskWise** into a production-quality market-risk product for Indian retail investors and analysts. You have no prior context, so start by orienting yourself, then follow the phases in order.

## REPO ORIENTATION (read first, do not skip)
- Backend: FastAPI + SQLAlchemy + Alembic in `backend/app/` (`api/v1/*.py` routes, `services/*` engines, `agents/*` copilot, `db/`, `schemas/`). Tests in `backend/tests/`. Python deps in `backend/requirements.txt`.
- Market risk: `backend/app/services/market_risk/{engine.py, market_data_service.py, ticker_normalizer.py}`. VaR backtesting: `backend/app/services/var_validation/engine.py`. Routes: `backend/app/api/v1/market.py`.
- Market data: `data/market_snapshots/*.csv` (15 symbols), `data/manifests/market_manifest.json`, fetched via yfinance.
- Frontend: Next.js 16 / React 19 / Tailwind 4 in `frontend/` (`app/*/page.tsx`, `components/`, `lib/api.ts`). Only dependency besides React/Next is lucide-react; there is no chart library.
- Docs in `docs/` (ARCHITECTURE, API_CONTRACTS, KNOWN_LIMITATIONS, EVALUATION_REPORT, MODEL_CARD). Scripts in `scripts/`. Credit models in `ml/` and `artifacts/`.
- Read `README.md`, `PRD.md`, `docs/ARCHITECTURE.md` and `docs/KNOWN_LIMITATIONS.md`, then skim the files above before planning.

## GROUND RULES
1. Never fabricate numbers. Every metric must be computed from real data or a documented formula. Keep the repo's "honest disclosure" tone, shown as contextual tooltips.
2. Keep existing API response shapes backward compatible; add fields or new endpoints rather than breaking old ones. Update `docs/API_CONTRACTS.md` via `scripts/generate_api_contracts.py`.
3. Every backend change ships with pytest tests (use known analytic values or reference results). Run `pytest backend/tests` and, in `frontend/`, `npm run lint && npm run build` before finishing each phase. Fix failures; do not skip or delete tests.
4. Commit at the end of each phase with a clear message. Do not push. Do not commit secrets, `.env`, `riskwise.db`, or large generated data.
5. Be honest in reports: say what you ran and what you could not run (for example Docker may be unavailable). Do not claim something works unless you executed it.
6. If something is ambiguous, choose the sensible default, record it in `docs/DECISIONS.md`, and continue. Ask only for decisions you truly cannot resolve.
7. Use browser verification: after UI changes, start both servers, open each page in the Antigravity browser, check for console errors, and capture screenshots as artifacts at desktop and mobile widths.

## PHASE 0: Blockers (do first)
- `frontend/.gitignore` line 17 ignores `lib/`, so `frontend/lib/api.ts` is untracked and a fresh clone or Docker build breaks. Un-ignore it and commit the file.
- **The project's credit model is now the Indian bank dataset (4-class P1-P4, files in `Dataset/` and `scripts/train_indian_credit.py`). The UCI Taiwan dataset is no longer used.** `artifacts/evaluation/model_comparison.json` already holds the Indian results, but `docs/EVALUATION_REPORT.md`, `docs/MODEL_CARD.md`, `docs/DATA_SOURCES.md`, `docs/KNOWN_LIMITATIONS.md` (section 1 says "Taiwan 2005 proxy, no Indian equivalent"), `README.md`, `scripts/generate_evaluation_report.py`, `scripts/audit_fairness.py` (and `artifacts/evaluation/fairness_audit.json`), `ml/train.py`, `ml/preprocessing.py` and the UCI-based tests/frontend credit page copy still describe or compute UCI results. Remove or rewrite all UCI references, retrain/regenerate fairness and evaluation from the Indian model, fix the report generator to read the Indian JSON keys, drop dead UCI code and artifacts (`credit_xgboost_v1*`, `data/` UCI files) once nothing depends on them, and add a test that fails when report numbers diverge from the JSON. Check for target leakage: the "With Credit_Score" variant scores ROC-AUC 0.9999, so confirm which variant is the champion and document why.
- Stop tracking the ~50 `artifacts/var_validation/*.json` files (move to DB in Phase 3, add to `.gitignore`).
- Run `docker compose build` if Docker exists; record the real result in `docs/KNOWN_LIMITATIONS.md` (currently "not verified").

## PHASE 1: Full NSE universe and data layer
- Add `scripts/build_instrument_master.py` to ingest the official NSE equity list (`EQUITY_L.csv`), index constituents (Nifty 50/100/500 and sector indices) and ETFs into a new `instruments` table (symbol, ISIN, name, series, sector, industry, listing date, cap bucket, index memberships) with an Alembic migration. Handle renames, mergers and delistings (generalise `CORPORATE_ALIASES`).
- Replace the hardcoded `SYMBOL_CATALOGUE` with DB-backed indexed fuzzy search (symbol prefix, name, ISIN; ranked by index membership). Keep `/market/search` compatible; add pagination and `sector`/`index`/`cap_bucket` filters.
- Lazy, cached price loading: batched threaded yfinance downloads with retry/backoff, Parquet or SQLite storage instead of one CSV per symbol, a background refresh job with a status endpoint, data-quality checks (gaps, stale or zero-volume days, split/dividend spikes via `scripts/audit_corporate_actions.py`), per-symbol freshness in API responses, and preserved manifest checksums.
- USD/INR FX series plus an explicit opt-in base-currency conversion mode for mixed portfolios (default stays strict; the response states the FX assumption).
- Benchmark layer: Nifty 50 for INR, S&P 500 for USD.

## PHASE 2: Market risk engine
Split `market_risk/engine.py` into a package (`returns`, `var_models`, `stress`, `attribution`, `portfolio`) with pydantic schemas and per-module tests. Add:
- VaR methods: historical, Gaussian, Student-t, Cornish-Fisher, EWMA (lambda 0.94), GARCH(1,1) via `arch`, filtered historical simulation, seeded correlated Monte Carlo (Cholesky, optional t-copula). Horizons 1/5/10 days, confidence 90/95/97.5/99. ES for each.
- Uncertainty: bootstrap confidence intervals for VaR/ES and a warning when the tail has too few observations.
- Decomposition: marginal, component and incremental VaR, diversification ratio, volatility contribution, HHI, effective N.
- Metrics: beta, alpha, tracking error, Sharpe, Sortino, Calmar, information ratio, downside deviation, skew, kurtosis, Jarque-Bera, rolling vol/correlation, drawdown table (depth, duration, recovery), up/down capture. Configurable risk-free rate (documented default).
- Stress: keep data-derived scenarios; add historical replays computed from real data (COVID Feb-Mar 2020, 2008 where data exists, June 2024 election day, Adani Jan-Feb 2023), beta-scaled index shocks, sector shocks, custom shocks, reverse stress test, correlation-breakdown stress.
- Analytics tools (labelled not-advice): minimum-variance, risk-parity, max-Sharpe, efficient frontier, and a what-if trade simulator showing change in VaR/ES/vol.
- Inputs: CSV holdings upload (quantity, average price, broker-export friendly) with weights from latest prices; saved named portfolios.
- Vectorise everything; 50-holding analyze under ~300 ms with a benchmark test.

## PHASE 3: VaR validation
- Vectorise the rolling backtest. Run every VaR method side by side on the same window and recommend one with a plain-English reason.
- Tests: Kupiec POF, Christoffersen independence and conditional coverage (joint), Basel traffic light using the official 250-day table, Haas time-between-failures. Remove the `999.0` sentinel and handle edge cases (0 exceptions, all exceptions, clustered exceptions) correctly.
- ES backtests (Acerbi-Szekely or McNeil-Frey), loss scoring (Lopez, pinball, FZ0), rolling vs expanding vs EWMA windows.
- Persist runs in the DB; export a PDF/CSV validation report.

## PHASE 4: Frontend redesign
- Design system: Tailwind tokens, shared `components/ui` (Card, Stat, Badge, Tabs, DataTable, Modal, Skeleton, EmptyState, Tooltip, Toast), type scale, and a real light/dark toggle.
- Add Recharts (pinned version) with theme-aware accessible charts: price and cumulative return vs benchmark, drawdown area, return histogram with VaR/ES lines and normal/t overlays, rolling vol, correlation heatmap, risk-contribution bars, efficient frontier, VaR backtest chart (losses vs VaR line, exceptions marked), stress waterfall.
- Break up the 1,000+ line pages (`market-risk`, `var-validation`, `credit`) into feature folders with small components and typed hooks; add SWR or React Query (caching, debounce, abort, loading/error states); generate the API client types from FastAPI's OpenAPI schema.
- Market Risk Lab UX: command-palette search across the full NSE universe with sector/index chips, recents and favourites; editable weights with live total; presets by index/sector; saved portfolios; "explain this in plain English" via the Copilot; PDF/CSV export.
- Overview dashboard: portfolio snapshot cards, market regime strip (Nifty trend, India VIX if obtainable, realised vol), top risks, data freshness, quick actions.
- Remove internal jargon from the UI (milestone badges like "M1-M2", "PRD v3.0 Milestone 0", "Offline-Ready"). Put methodology and disclosures in a help drawer and per-metric tooltips linking to `docs/MARKET_RISK_METHODS.md`.
- Responsive (collapsible sidebar on mobile), keyboard accessible, AA contrast, `prefers-reduced-motion`. Add Playwright smoke tests for every page.

## PHASE 5: Hardening and docs
- Simple JWT or session auth with per-user saved portfolios, rate limiting, input limits (max holdings, max lookback), request IDs.
- GitHub Actions CI: ruff, mypy, pytest with a coverage gate, frontend lint and build, `docker compose build` smoke job. Pin Docker base images and add healthchecks.
- Update `README.md`, `docs/ARCHITECTURE.md`, `docs/API_CONTRACTS.md`, `docs/KNOWN_LIMITATIONS.md`; add `docs/MARKET_RISK_METHODS.md` with formulas and references for every metric.

## DELIVERABLES AND ACCEPTANCE
- A small-cap NSE stock not in the old catalogue can be searched and analysed end to end with no manual snapshot files.
- Mixed INR/USD portfolios work only in explicit FX mode and state the assumption.
- Each VaR method has tests against analytic or reference values; backtest edge cases are covered.
- `pytest`, `npm run lint`, `npm run build` pass; `docker compose up --build` works from a clean clone, or the report states honestly that Docker was unavailable.
- Every on-screen number has a tooltip linking to its documented method.
- Produce a final walkthrough artifact: per-phase summary, commands run with results, screenshots of each page (desktop and mobile), and a list of anything unverified or deferred.

Begin by producing a task list and implementation plan for Phase 0 and Phase 1, wait for approval, then execute phase by phase.
