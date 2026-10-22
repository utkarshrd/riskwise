# RiskWise Improvement Prompt

Paste everything below the line into a fresh Claude Code session at the repo root.

---

You are upgrading **RiskWise** (FastAPI + SQLAlchemy backend in `backend/`, Next.js 16 / React 19 / Tailwind 4 frontend in `frontend/`) from an academic demo into a genuinely useful market-risk product for Indian retail investors and analysts. Work in phases, commit after each phase, run `pytest backend/tests` and `npm run build` in `frontend/` before each commit, and keep the existing "no silent assumptions, no fabricated numbers" ethos (every figure traceable to data or a documented method).

## Findings from the audit (fix or build on these)

**Blockers / correctness**
1. `frontend/.gitignore` line 17 contains `lib/`, so `frontend/lib/api.ts` (imported everywhere as `@/lib/api`) is **not in git**. A fresh clone or `docker compose build` fails. Un-ignore it (`!/lib/`) and commit the file. Then actually run `docker compose build` somewhere Docker exists and record the result in `docs/KNOWN_LIMITATIONS.md` (currently says "not verified").
2. The credit model is now the Indian bank dataset (4-class P1-P4); the UCI Taiwan dataset is no longer used. `model_comparison.json` holds the Indian results, but `docs/EVALUATION_REPORT.md`, `MODEL_CARD.md`, `DATA_SOURCES.md`, `KNOWN_LIMITATIONS.md`, `README.md`, `scripts/generate_evaluation_report.py`, `scripts/audit_fairness.py`, `ml/train.py` and the credit page copy still describe or compute UCI results. Remove or rewrite them, regenerate evaluation and fairness from the Indian model, delete dead UCI code and artifacts, and add a test that fails if report numbers diverge from the JSON. Also confirm the champion is not the "With Credit_Score" variant (ROC-AUC 0.9999 suggests leakage).
3. Market engine `analyze_portfolio` reports `parametric_var` using the sample mean; historical VaR uses `np.percentile` on only ~250 points, so 99% VaR/ES rest on 2-3 observations. Surface this uncertainty (see M2).
4. `var_validation/engine.py` rolling backtest is O(n) Python loops with per-step pandas slicing; the Christoffersen test is independence only (no conditional-coverage joint test); `lr_stat = 999.0` is a magic sentinel; Basel zones use the 250-day table logic only loosely. Fix these.
5. Mixed-currency portfolios are rejected outright. Real investors hold INR + USD assets.

**Product gaps**
- Symbol universe is a hand-curated catalogue of ~67 entries (`ticker_normalizer.py`) plus live yfinance search. Only 15 symbols have offline snapshots. Goal: **every NSE-listed stock** (about 2,000+ EQ series) plus NSE indices and ETFs, and ideally BSE.
- Risk engine has only: historical VaR, Gaussian VaR, ES, max drawdown, correlation matrix, and two derived stress scenarios.
- Frontend has no chart library at all (`package.json` has only lucide-react). Pages are 1,100-1,300 line monoliths (`market-risk/page.tsx`, `var-validation/page.tsx`, `credit/page.tsx`), sidebar shows internal milestone codes ("M1-M2") and "PRD v3.0 Milestone 0 baseline" copy to end users.

## Phase 1: Full NSE universe and data layer
- Build an `instrument master` ingestion script (`scripts/build_instrument_master.py`) that pulls the official NSE equity list (`EQUITY_L.csv` from NSE archives), index constituents (Nifty 50/100/500, sector indices) and ETF list. Store in a DB table `instruments` (symbol, ISIN, name, series, sector, industry, listing date, lot/face value, market cap bucket, index memberships) with an Alembic migration. Include handling for renames/mergers (generalise the existing `CORPORATE_ALIASES`) and delistings.
- Replace the in-code `SYMBOL_CATALOGUE` with DB-backed, indexed, fuzzy search (prefix, name, ISIN; rank by index membership/liquidity). Keep `/market/search` contract-compatible; add pagination, `sector`, `index` and `cap_bucket` filters.
- Make price loading lazy and cached: bulk download (batched `yf.download` with threads and retry/backoff), Parquet or SQLite storage instead of one CSV per symbol, a `refresh` job (background task + status endpoint, not a blocking POST), data-quality checks (gaps, stale prices, zero-volume days, split/dividend spikes via the existing `audit_corporate_actions.py`), and per-symbol freshness shown in the API. Preserve manifest checksums.
- Add FX support: USD/INR series, and a **explicit, opt-in** converted-to-base-currency mode for mixed portfolios (state the FX assumption in the response; keep default strict behaviour).
- Add a benchmark/beta layer: Nifty 50 as default benchmark for INR, S&P 500 for USD.

## Phase 2: Market risk engine (make it rigorous and rich)
Restructure `market_risk/engine.py` into a package (`returns.py`, `var_models.py`, `stress.py`, `attribution.py`, `portfolio.py`) with pydantic schemas and unit tests per module. Add:
- **VaR methods**: historical, parametric Gaussian, parametric Student-t, Cornish-Fisher, EWMA/RiskMetrics (lambda 0.94), GARCH(1,1) (use `arch`), filtered historical simulation, and Monte Carlo (correlated, seeded, with Cholesky + optional t-copula). Horizons 1/5/10-day (sqrt-time with explicit caveat, or simulated multi-day), confidence 90/95/97.5/99.
- **Uncertainty**: bootstrap confidence intervals on VaR/ES, and a warning when the tail has fewer than N effective observations.
- **Risk decomposition**: marginal VaR, component VaR, incremental VaR, diversification ratio, contribution to volatility, concentration (HHI, effective N), top-risk-contributor ranking.
- **Factor / market metrics**: beta, alpha, tracking error, Sharpe, Sortino, Calmar, information ratio, downside deviation, skew, kurtosis, Jarque-Bera, rolling volatility and correlation, drawdown table (depth, duration, recovery), tail ratio, up/down capture. Risk-free rate configurable (default RBI T-bill proxy, documented).
- **Stress testing**: keep the data-derived scenarios, and add named historical replays computed from real data (COVID crash Feb-Mar 2020, 2008 GFC where data exists, Jun 2024 election-day move, Adani Jan-Feb 2023, Sept 2024 to Mar 2025 correction), sector and index shocks (Nifty -10/-20%, beta-scaled), custom shocks, reverse stress test (what shock produces a given loss), and a correlation-breakdown stress.
- **Optimisation tools** (clearly labelled as analytics, not advice): minimum-variance, risk-parity, max-Sharpe, efficient-frontier, and "what-if" trade simulator (add/remove/rebalance a holding and show delta in VaR/ES/vol).
- **Portfolio inputs**: accept CSV upload of holdings (quantity, avg price) and broker exports (Zerodha/Groww style), compute weights from latest prices, and persist named portfolios per session.
- Performance: vectorise everything, cache aligned price matrices, keep analyze latency under ~300 ms for 50-holding portfolios, and add a benchmark test.

## Phase 3: VaR validation (make it a real model-risk tool)
- Vectorise the rolling backtest. Support all new VaR methods and compare them side by side on the same window ("which model is best for this portfolio?").
- Tests: Kupiec POF, Christoffersen independence **and conditional coverage** (joint), Basel traffic-light using the official 250-day exception table, Haas time-between-failures, and a duration-based test. Replace the `999.0` sentinel with proper handling.
- Add ES backtesting (Acerbi-Szekely Z1/Z2 or McNeil-Frey), loss-function scoring (Lopez, quantile/pinball loss, FZ0 for VaR+ES joint), and rolling vs expanding vs EWMA windows.
- Output a clear, plain-English verdict with a recommended model and the reason, plus exportable PDF/CSV of the validation report.
- Persist runs (already in `artifacts/var_validation/*.json`; move to DB, clean up the ~50 tracked JSON UUID files from git and add them to `.gitignore`).

## Phase 4: Frontend redesign and product polish
- Add a design system: Tailwind tokens, a shared `components/ui` library (Card, Stat, Badge, Tabs, DataTable, Modal, Skeleton, EmptyState, Tooltip, Toast), consistent spacing, typography scale, and real light/dark theme toggle (currently only OS-driven).
- Add **Recharts** (or visx) with accessible, theme-aware charts: price and cumulative-return lines vs benchmark, drawdown area chart, return histogram with VaR/ES lines and normal/t overlays, rolling volatility, correlation heatmap, risk-contribution bar/treemap, efficient frontier scatter, VaR backtest chart (losses vs VaR line with exceptions marked), stress-test waterfall. Use the `dataviz` skill for palette and chart conventions.
- Refactor the 1,000+ line page files into feature folders with small components and typed hooks (`useMarketSearch`, `usePortfolioAnalysis`); add React Query/SWR for caching, debounce, abort, and loading/error states. Add a typed API client generated from the FastAPI OpenAPI schema instead of hand-written `lib/api.ts`.
- Market Risk Lab UX: command-palette symbol search over the full NSE universe (sector/index chips, recent, favourites), drag-to-edit weights with live total, portfolio presets by index/sector, saved portfolios, one-click "explain this risk in plain English" via the Copilot, shareable report export (PDF) and CSV.
- Overview dashboard: live portfolio snapshot cards, market regime strip (Nifty trend, India VIX, realised vol), top risks, data-freshness indicator, and quick actions. Remove internal milestone badges ("M1-M2"), PRD copy and "Offline-Ready" jargon from the user-facing UI; move methodology/disclosures into a tidy footer or help drawer.
- Responsive and accessible: mobile layout with collapsible sidebar, keyboard navigation, aria labels, AA contrast, `prefers-reduced-motion`. Add Playwright smoke tests for each page and run Lighthouse.
- Keep the honest-disclosure tone, but present it as contextual info tooltips next to each metric rather than long text blocks.

## Phase 5: Platform hardening
- Auth (simple JWT or session) and per-user saved portfolios; rate limiting; request validation limits (max holdings, max lookback); structured logging already exists, add request IDs and basic metrics.
- CI (GitHub Actions): ruff, mypy, pytest with coverage gate, `npm run lint && npm run build`, `docker compose build` smoke job. Pin the Docker base images and add healthchecks.
- Update `README.md`, `docs/ARCHITECTURE.md`, `docs/API_CONTRACTS.md` (regenerate with `scripts/generate_api_contracts.py`), `docs/KNOWN_LIMITATIONS.md` and add `docs/MARKET_RISK_METHODS.md` with formulas and references for every new metric.

## Acceptance criteria
- Search finds any NSE EQ symbol (e.g. a small-cap not in the current catalogue) and analyses it end-to-end without manual snapshot files.
- Mixed INR/USD portfolio works only in explicit FX mode and states the assumption.
- Each VaR method has unit tests against known analytic or reference values; backtest tests cover Kupiec/Christoffersen edge cases (0 exceptions, all exceptions, clustered exceptions).
- `docker compose up --build` works from a clean clone; `pytest` and `npm run build` pass in CI.
- Every number on screen has a tooltip linking to its method in `docs/MARKET_RISK_METHODS.md`.
- Final summary lists what changed per phase, what was verified (with commands run), and anything left unverified.

Start with Phase 0 (the blockers 1-2 above), then plan Phase 1 in detail before writing code; ask me only for decisions you cannot resolve from the repo.
