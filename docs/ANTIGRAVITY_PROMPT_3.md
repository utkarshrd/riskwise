You are finishing the RiskWise upgrade. The full plan is in `docs/ANTIGRAVITY_PROMPT.md` and the last status prompt is `docs/ANTIGRAVITY_PROMPT_2.md`. Read both, then `git log` and `git status`. This prompt overrides them on scope and order: the goal is the best result in the least time, not every item.

## STEP 0: STABILISE (do this before anything else)
1. Two tests fail after the `engine.py` facade switch: `test_market_position_values_and_currency_loss_calculation` and `test_market_portfolio_analyze_api_with_monetary_amount` (VaR amount 1259.53 vs expected 1260.00). Find the root cause (likely the monetary amount is no longer computed from the 4-decimal rounded percentage VaR). Fix the code, never loosen the test.
2. Delete the old `backend/app/services/market_risk/pkg/` once nothing imports it (`risk/` is the real package).
3. Commit everything uncommitted in two or three logical commits with the full suite green. Paste the pytest summary line. Do not start Step 1 until this is done.

## SCOPE: THREE TIERS
Finish a tier completely (tests green, committed, report written) before touching the next. If I say "stop", stop after the current commit.

### TIER A: must finish (highest value per hour)
A1. Wire the instrument master into `/market/search` and `/market/universe`: DB-backed fuzzy search over all NSE symbols with `sector`, `index` and `cap_bucket` filters and pagination; keep response shapes backward compatible. Run the ingest script for real and report how many instruments loaded. If the NSE download is blocked, say so and use whatever official file you can fetch; do not invent symbols.
A2. Lazy price loading for any NSE symbol: if no snapshot exists, fetch via yfinance, validate (positive prices, gaps, staleness), cache, and record freshness. Add retry/backoff. Prove it with a test using a mocked provider, and one real call if the network allows.
A3. Risk engine: confirm `risk/` provides historical, Gaussian, Student-t, EWMA, GARCH(1,1), Cornish-Fisher and seeded Monte Carlo VaR/ES; component and marginal VaR; beta, Sharpe, Sortino, drawdown table. Add whatever is missing. Each method needs a test against a known analytic or reference value. Add a method selector and horizon parameter to `/market/portfolio/analyze`.
A4. VaR validation: add Christoffersen conditional coverage (joint test), the official Basel 250-day traffic-light table, remove the `999.0` sentinel, vectorise the rolling loop, and add a side-by-side comparison endpoint that runs all methods on one window and recommends one with a plain-English reason.
A5. Frontend essentials: add Recharts (pinned) and build these charts on the Market Risk and VaR pages: cumulative return vs benchmark, drawdown, return histogram with VaR/ES lines, correlation heatmap, risk-contribution bars, and VaR backtest chart with exceptions marked. Add a symbol search box over the full NSE universe (debounced, sector and index chips). Remove internal jargon from the sidebar and header ("M1-M2" badges, "PRD v3.0 Milestone 0", "Offline-Ready"). Use the `dataviz` skill for chart design.
A6. Housekeeping: update `README.md`, `docs/API_CONTRACTS.md` (via `scripts/generate_api_contracts.py`), `docs/KNOWN_LIMITATIONS.md`, and add `docs/MARKET_RISK_METHODS.md` with the formula and one reference per method.

### TIER B: do if Tier A is complete and green
B1. USD/INR opt-in FX mode for mixed portfolios (default stays strict, response states the FX assumption).
B2. Named historical stress replays computed from real data (COVID 2020, June 2024 election day, Adani 2023) and a reverse stress test.
B3. Split the 1,000+ line frontend pages into small components and typed hooks; add a light/dark toggle; make the layout work on mobile.
B4. CSV holdings upload with weights from latest prices.
B5. GitHub Actions CI: ruff, pytest, frontend lint and build.

### TIER C: skip unless I explicitly ask
Auth and saved portfolios, optimisation tools (min-variance, risk parity, efficient frontier), PDF export, Playwright suite, OpenAPI client generation, Docker pinning.

## WORKING RULES (to save time and avoid rework)
- Do not ask me for approval between tiers or tasks. Pick sensible defaults, log each in `docs/DECISIONS.md` with one line of reasoning, and keep going. Ask only if you are blocked.
- Run the full suite only at the end of each task; run just the relevant test file while iterating.
- Commit after every task (A1, A2, ...) with a message like `feat(a3): ...`.
- Never fabricate data or numbers. Every figure comes from real data or a documented formula. Keep API changes backward compatible.
- For frontend work, open each changed page in the browser, report console errors, and attach desktop and mobile screenshots. If you cannot run the browser, say so rather than claiming it works.
- Time guard: if a task is taking more than about 45 minutes of effort without progress, write down what is blocking it, mark it deferred, and move on.
- Report honestly: say what you ran and what you could not run (Docker is unavailable on this machine; do not claim a build).

## REPORT AFTER EACH TIER
1. Tasks completed and commit hashes.
2. Evidence: commands run and the real pytest/build output summary lines.
3. Deferred or unverified items and why.
4. One risk you see in the next tier.

Start with Step 0 now.
