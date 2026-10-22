Tier A is verified complete (202 tests pass, 2,617 instruments loaded, Recharts present, sidebar jargon gone). Do not ask whether to proceed: continue with the list below in order. Read `docs/ANTIGRAVITY_PROMPT_3.md` for the working rules, which still apply.

## CORRECTION
Your last message listed a Tier B (snapshot pre-fetch, PSI drift dashboard, CAGR/alpha, copilot tools, PDF export) that is not the Tier B I defined. Use the list below instead. Lazy loading already makes the snapshot pre-fetch unnecessary, and PDF export stays Tier C. Also: you asked me for a go-ahead despite the "no approval pauses" rule. Pick defaults, log them in `docs/DECISIONS.md`, and keep going.

## B0: VERIFY WHAT YOU CLAIMED (first, 45 minutes max)
1. Visual proof: the build passing does not prove the pages look right. Start backend and frontend, open `/`, `/market-risk`, `/var-validation`, `/credit` in the browser and attach desktop (1440px) and mobile (390px) screenshots. List every console error, layout overflow, empty chart or unreadable label you see, and fix them. If you cannot run the browser, say so plainly.
2. Real-data proof: run a portfolio of three small or mid-cap NSE stocks that were not in the original 15 snapshots (for example pick any from the instrument master) through analyze, VaR compare and backtest, and report the actual outputs and any data-quality warnings.
3. Credit leakage check: `model_comparison.json` has an "XGBoost (With Credit_Score)" variant at ROC-AUC 0.9999. State which variant the app serves and why, and make `docs/MODEL_CARD.md` and the credit page say it plainly.
4. Remove prompt files from version control if they clutter the repo (keep them in `docs/prompts/` or untracked); do not delete them.

## TIER B (in this order; commit each as `feat(bN): ...`)
- **B1. Frontend structure and look:** split `market-risk/page.tsx`, `var-validation/page.tsx` and `credit/page.tsx` into feature folders with small components and typed hooks; add shared `components/ui` primitives (Card, Stat, Badge, Tabs, Skeleton, EmptyState, Tooltip); add a real light/dark toggle; make the sidebar collapse on mobile; add loading skeletons and error states for every data fetch. Every metric gets a tooltip linking to its section in `docs/MARKET_RISK_METHODS.md`. Screenshots required.
- **B2. USD/INR opt-in FX mode:** mixed portfolios allowed only when `fx_mode=convert_to_base` is set; the response states the FX series and date range used; default stays strict. Tests for both modes.
- **B3. Named historical stress replays and reverse stress test:** COVID Feb-Mar 2020, June 4 2024 election day, Adani Jan-Feb 2023, computed from real price data for the portfolio's holdings (skip a holding with no data in that window and say so). Reverse stress: the uniform market shock that produces a user-given portfolio loss. Add a stress page section with a waterfall chart.
- **B4. CSV holdings upload:** columns `symbol,quantity,avg_price` (tolerant of Zerodha/Groww export headers), weights computed from latest prices, clear row-level validation errors, unknown symbols reported not dropped silently.
- **B5. CI:** GitHub Actions running ruff, pytest and the frontend lint and build. Fix whatever ruff reports.
- **B6. Copilot market tools** (only if B1-B5 are done): let the copilot call the VaR and portfolio-analysis tools so chat answers cite computed numbers, with tests that no number appears in a reply unless a tool produced it.

## STILL SKIPPED (Tier C)
Auth, optimisation tools, PDF export, Playwright suite, OpenAPI client generation, Docker pinning.

## ALWAYS
Never fabricate data or numbers. Keep API changes backward compatible. Full test suite at the end of each task. 45-minute guard per stuck task: record the blocker, mark deferred, move on. Docker is unavailable here; never claim a build.

## REPORT AFTER B0, AFTER B3 AND AT THE END
Commit hashes, real command output summaries (pytest, build, lint), screenshots, and what remains unverified.
