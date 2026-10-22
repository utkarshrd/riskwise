You are finishing the RiskWise upgrade. Plan history: `docs/ANTIGRAVITY_PROMPT.md` (full plan), `docs/ANTIGRAVITY_PROMPT_3.md` (tiers and working rules, which still apply). Read both and `git log`, then continue from the state below. Do not redo finished work.

## STATE (verified 2026-10-22)
DONE and committed: Step 0 (stabilise), A1 instrument master wired into search/universe (c6ce889), A2 lazy yfinance loading with validation/backoff/freshness (6008420), A3 multi-model risk analytics with method selector and reference tests (034461e).
IN PROGRESS, uncommitted: edits to `backend/app/api/v1/market.py` and `backend/app/schemas/market.py` (likely A4). Review, finish and commit them first.
NOT STARTED: A4 (if not covered by the edits above), A5 frontend charts and jargon removal, A6 docs, all of Tier B.

## FIRST: QUICK AUDIT OF A1-A3 (30 minutes max, then move on)
- Report the real number of instruments loaded by `scripts/build_instrument_master.py` and the source file used. If it is under ~1,500 NSE equities, say so and explain why.
- `/market/universe` currently appears to load every active `Instrument` row into memory (`db.query(Instrument).filter(...).all()`). With ~2,000+ rows this is wasteful: paginate or return counts plus a capped sample, keeping the response shape compatible.
- Confirm A3 covers: historical, Gaussian, Student-t, EWMA, GARCH(1,1), Cornish-Fisher, seeded Monte Carlo; component and marginal VaR; beta, Sharpe, Sortino, drawdown table. List any that are missing and add them with tests against analytic values.
- Run the full suite and paste the summary line.

## REMAINING WORK
### Tier A (finish in order)
A4. VaR validation: Christoffersen conditional coverage (joint test), the official Basel 250-day traffic-light table, remove the `999.0` sentinel, vectorise the rolling loop, and a side-by-side comparison endpoint that runs all methods on one window and recommends one in plain English. Test edge cases: 0 exceptions, all exceptions, clustered exceptions.
A5. Frontend: add Recharts (pinned version) and build on the Market Risk and VaR pages: cumulative return vs benchmark, drawdown, return histogram with VaR/ES lines, correlation heatmap, risk-contribution bars, VaR backtest chart with exceptions marked. Add a debounced full-NSE symbol search with sector and index chips, a VaR method selector, and the model-comparison view from A4. Remove internal jargon from the sidebar and header ("M1-M2" badges, "PRD v3.0 Milestone 0", "Offline-Ready"). Use the `dataviz` skill for chart design. Verify each page in the browser (console errors, desktop and mobile screenshots); if you cannot run the browser, say so.
A6. Docs: `README.md`, `docs/API_CONTRACTS.md` (via `scripts/generate_api_contracts.py`), `docs/KNOWN_LIMITATIONS.md`, and a new `docs/MARKET_RISK_METHODS.md` with each method's formula and one reference.

### Tier B (only after Tier A is green and committed)
B1 USD/INR opt-in FX mode. B2 named historical stress replays (COVID 2020, June 2024, Adani 2023) and reverse stress test. B3 split big frontend pages, light/dark toggle, mobile layout. B4 CSV holdings upload. B5 GitHub Actions CI (ruff, pytest, frontend lint and build).

### Tier C: skip unless I ask
Auth, optimisation tools, PDF export, Playwright, OpenAPI client generation, Docker pinning.

## RULES (unchanged)
No approval pauses; log defaults in `docs/DECISIONS.md`. Commit per task (`feat(a4): ...`). Full suite at the end of each task, relevant file while iterating. Never fabricate data; keep API changes backward compatible. 45-minute guard per stuck task: record the blocker, mark deferred, move on. Docker is unavailable here; never claim a build.

## REPORT AFTER EACH TIER
1. Tasks done with commit hashes. 2. Real command output summaries (pytest, build). 3. Deferred or unverified items and why. 4. One risk in the next tier.

Begin with the in-progress edits, then the audit, then A4.
