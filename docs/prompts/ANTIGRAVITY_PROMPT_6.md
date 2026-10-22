Tiers A and B0-B3 are done and committed (HEAD `2d090ce`). Finish **B4, B5, B6** in that order. Do not ask whether to proceed. Pick defaults, log each one in `docs/DECISIONS.md` with a line of reasoning, and keep going. Read `docs/prompts/ANTIGRAVITY_PROMPT_3.md` (working rules) and `docs/prompts/ANTIGRAVITY_PROMPT_5.md` (original B-tier spec); both still apply.

## STATE OF THE REPO (verified at HEAD)
- Backend: 243 tests pass (`python -m pytest backend/tests -q`). `ruff check backend` reports 63 issues (that is B5's job).
- Frontend: `npx tsc --noEmit` clean, `npx eslint .` 0 problems, `npm run build` exit 0.
- Website only. Do **no** mobile or narrow-window work.
- Uncommitted runtime files you must NOT commit: `data/manifests/market_manifest.json`, `data/market_snapshots/{IDEA,POLYCAB,SUZLON}.NS.csv`, `riskwise.db-shm`, `riskwise.db-wal`. `riskwise.db` itself is gitignored.

## THINGS ALREADY BUILT THAT YOU SHOULD REUSE (do not duplicate)
- `frontend/hooks/usePortfolioBuilder.ts` (holdings, presets, currency policy, `fxMode`), `frontend/components/portfolio/*` (HoldingsEditor, PresetPicker, CurrencyAlerts, FxModeToggle, FxSummary).
- `frontend/components/ui/*` (Card, Stat, Badge, Tabs, Skeleton, EmptyState, Tooltip/MetricInfo, Alert, Field). `frontend/lib/metric-docs.ts` maps each metric to a heading in `docs/MARKET_RISK_METHODS.md`; `backend/tests/unit/test_metric_docs_headings.py` fails if a heading disappears.
- `fx_mode` (`strict` default, `convert_to_base`) on analyze, stress-test, var/validate, var/compare, stress/replay and stress/reverse. One policy lives in `MarketRiskEngine.resolve_currency_policy`.
- `apiFetch` in `frontend/lib/api.ts` raises `ApiError` with the readable server message.
- Pattern for testable external data: `StressService` takes a provider; the API gets it via a FastAPI dependency (`get_stress_service`) that tests override with `app.dependency_overrides`. Use the same pattern for anything that touches the network.
- `scripts/generate_api_contracts.py` has an `EXTENSION_ENDPOINTS` list. Add every new endpoint there and re-run it.
- The instrument master is the `instruments` table (columns: `symbol` like `RELIANCE.NS`, `isin`, `name`, `aliases_json`, `sector`, `cap_bucket`). `MarketDataService.search_symbols(...)` does the fuzzy search. `MarketDataService.get_symbol_price_history(symbol)` returns real prices, fetching lazily.

## B4. CSV HOLDINGS UPLOAD
Goal: a user uploads a broker export and gets a ready-to-analyse portfolio.
- **Transport:** `POST /api/v1/market/portfolio/import` with JSON `{"csv_text": "...", "filename": "..."}`. `python-multipart` is not installed, so do not use multipart. Limit: 1 MB, 500 rows. The browser reads the file with `FileReader` and sends the text.
- **Canonical columns:** `symbol,quantity,avg_price`. `avg_price` is optional (used only for unrealised P&L); `symbol` and `quantity` are required.
- **Header tolerance:** match case-, space- and punctuation-insensitively with an alias table. Cover at least Zerodha (`Instrument, Qty., Avg. cost, LTP, Cur. val, P&L`) and Groww (`Stock Name, ISIN, Quantity, Average buy price, Buy value, Closing price`). Exports can have metadata lines above the real header: scan the first ~30 rows for the row that contains a symbol-like and a quantity-like header. Handle a UTF-8 BOM, comma/semicolon/tab delimiters, `1,234.50`, `₹`, and blank lines. Return the header mapping you used.
- **Symbol resolution, in this order:** (1) ISIN match against `instruments.isin`; (2) exact symbol, with or without `.NS`, and broker suffixes like `-EQ`; (3) alias match; (4) exact normalised company-name match. **Never auto-pick a fuzzy match.** If nothing matches, the row is an error that includes up to 3 suggestions from `search_symbols`.
- **Weights:** `weight_i = quantity_i x latest_price_i / sum`. Latest price comes from our price data (not the CSV's LTP column), fetched in parallel (cap 8 workers). A row whose price cannot be fetched is an error with the reason. Duplicate symbols are merged (sum quantity, quantity-weighted average price) and reported as merged.
- **Row-level validation errors** (row number, field, message, offending value): missing symbol, non-numeric / zero / negative quantity, bad `avg_price`, unknown symbol, no price data. Rows with errors are excluded from `holdings` **but listed in `errors`**. Nothing is dropped silently. Also return `warnings`, `rows: {total, imported, errors, merged}`, total value, and the inferred currency (null if mixed; the client then needs `fx_mode`).
- **Frontend:** an "Import holdings" control on the Market Risk page (inside the portfolio form). Show a preview table of imported holdings with weights, a clear list of rejected rows with reasons and suggestions, and a "Use these holdings" button that loads them into `usePortfolioBuilder` (so `payloadHoldings`, currency checks and the FX toggle keep working). Loading, error and empty states required. Add `importHoldings` to `lib/api.ts` and a hook under `app/market-risk/_hooks/`.
- **Tests (offline):** header variants (Zerodha, Groww, metadata lines above the header, BOM, semicolons), number formats, each error type, ISIN and suffix resolution, "unknown symbol is reported with suggestions and not imported", duplicate merge, weights summing to 1 and equal to value shares computed by hand, size limits. Inject a fake price provider via a dependency like `StressService` does.
- Document the format in `docs/KNOWN_LIMITATIONS.md` (what is and is not supported) and add the endpoint to the contract generator.

## B5. CI (GitHub Actions)
- `.github/workflows/ci.yml`: backend job (Python 3.11: install `backend/requirements.txt`, `ruff check backend`, `pytest backend/tests -q`) and frontend job (Node LTS, `npm ci`, `npm run lint`, `npx tsc --noEmit`, `npm run build`), with dependency caching. Run on push and pull request.
- **Fix every ruff issue.** Use `ruff check --fix` for the safe ones and fix the rest by hand. Do not blanket-ignore rules or loosen the config to get green; a targeted per-file ignore needs a one-line reason in the config.
- **The important trap:** the suite passes on this machine partly because of untracked local state (`riskwise.db`, extra snapshot CSVs, trained artifacts). **Prove it passes from a clean checkout:** create a fresh `git worktree` (or clone) of HEAD, install dependencies in a clean venv, and run the suite there. If tests need the instrument master or artifacts that are not in git, either make the tests self-contained or make CI build them (for example run `scripts/build_instrument_master.py` if it works offline, or commit a small fixture), and record which you chose. Tests must not need network access.
- You cannot run GitHub Actions here. Say so, and run each CI step locally in the clean checkout instead. Do not claim the workflow "passes on GitHub".
- If `next build` fails with a message about a Next.js security advisory or asks you to upgrade, do **not** run any upgrade. Record it in `docs/DECISIONS.md` and tell the user.
- Add a README badge only if the repo has a GitHub remote you can read from `git remote -v`; otherwise skip it.

## B6. COPILOT MARKET TOOLS
First read the existing copilot code (`backend/app/agents/`, `backend/app/api/v1/copilot.py`, the copilot page and `backend/tests` for it) before designing anything. Do this only if B4 and B5 are done and green.
- Let the copilot call the portfolio analysis and VaR tools (analyze, VaR compare, stress replay, reverse stress) when the user describes a portfolio, so answers cite computed numbers. The tool trace must be returned and shown in the UI.
- **Provenance guard (the core requirement):** every number in a reply must trace to a tool output or to the user's own message. Implement a post-check that extracts numeric tokens from the answer (percentages, currency amounts, ratios, dates are exempt) and verifies each against the tool results (allow rounding to the displayed precision). A number with no source is removed or the sentence is rewritten, and the response flags it. The LLM must not do its own arithmetic.
- **Tests, offline with a fake model and fake tools:** a reply containing only tool-derived numbers passes unchanged; an invented number is caught and not shown; numbers from the user's message are allowed; rounding tolerance works; the copilot refuses to quote VaR when the tool failed and says why; the existing routing tests still pass. No real LLM calls in the suite.
- Keep API changes backward compatible.

## STILL SKIPPED (Tier C)
Auth, optimisation tools, PDF export, Playwright suite, OpenAPI client generation, Docker pinning.

## ALWAYS
Never fabricate data or numbers. Keep API changes backward compatible. Run the full backend suite, `tsc`, `eslint` and `npm run build` at the end of each task and paste the real summary lines. Commit each task as `feat(b4): ...`, `ci(b5): ...`, `feat(b6): ...`. 45-minute guard per stuck task: record the blocker, mark it deferred, move on. Docker is unavailable here; never claim a Docker build. For UI work, open the page and report console errors with desktop (1440px) screenshots in light and dark; if you cannot run a browser, say so plainly. After editing `frontend/app/globals.css`, the Next dev server may keep serving a stale stylesheet until you stop it and clear the `frontend/.next` folder. When you need to stop a server, stop it by port, never by matching command-line text (that can kill your own shell). If a shell heredoc misbehaves on Windows, write the file with your file-write tool instead.

## REPORT AT THE END OF EACH TASK AND AT THE END
Commit hashes, real command output summaries (pytest, ruff, tsc, eslint, build), screenshots, what you could not verify, and one risk you see in the next task.
