Finish **everything that remains**, in the order below, without asking whether to proceed. Pick defaults, log each in `docs/DECISIONS.md` with a line of reasoning, and keep going. `docs/prompts/ANTIGRAVITY_PROMPT_6.md` holds the full specs for B5 and B6 and its rules still apply; this prompt adds the current state and the closing steps. Also read `docs/prompts/ANTIGRAVITY_PROMPT_3.md` (working rules).

## WHERE THINGS STAND (checked against the working tree)
- Committed: Tier A, B0, B1, B2, B3 and **B4 (`c85f81c`)**.
- **B5 is half-done and uncommitted.** `.github/workflows/ci.yml` exists, `ruff check backend` passes (63 issues fixed across about 22 files), and `pytest` shows 256 passed. Not yet shown: that the suite passes from a **clean checkout**, that the workflow's `scripts/build_instrument_master.py` step really works offline from tracked files, and that the frontend job's steps pass. The README was edited and has not been reviewed.
- **B6 is not started.**
- Not committed on purpose, never commit these: `data/manifests/market_manifest.json`, `data/market_snapshots/{IDEA,POLYCAB,SUZLON}.NS.csv`, `riskwise.db-shm`, `riskwise.db-wal`. `riskwise.db` is gitignored.
- Website only. No mobile or narrow-window work.

## STEP 1: FINISH AND COMMIT B5
1. Review `git diff` for the ruff fixes. Confirm they are behaviour-preserving (no logic changes hiding in "fixes", no deleted tests, no assertions loosened). If a test was changed, say why.
2. **Prove it from a clean checkout.** Make a fresh `git worktree` of the current commit plus your B5 changes (commit them first on a branch if needed). In a clean venv: `pip install -r backend/requirements.txt`, then run exactly the workflow's backend steps: `ruff check backend`, `python scripts/build_instrument_master.py`, `python -m pytest backend/tests -q`. Tests must not need the network and must not depend on untracked local files. If something is missing from git, fix it (self-contained test fixtures, or a tracked small data file) and record the choice.
3. Run the frontend steps in the same clean checkout: `npm ci`, `npm run lint`, `npx tsc --noEmit`, `npm run build`. If `next build` fails with a message about a Next.js security advisory or asks for an upgrade, do **not** run any upgrade: log it in `docs/DECISIONS.md` and tell the user.
4. You cannot run GitHub Actions here. In the report, say the workflow was verified step by step locally and has not run on GitHub.
5. Review the README edit; add a CI badge only if `git remote -v` shows a GitHub remote. Commit as `ci(b5): ...`.

## STEP 2: B6, COPILOT MARKET TOOLS
Implement exactly as specified in `ANTIGRAVITY_PROMPT_6.md` (read the existing copilot code first; tool calls for analyze, VaR compare, stress replay and reverse stress; tool trace shown in the UI; the **number provenance guard** with offline tests using a fake model and fake tools; no real LLM calls in the suite). Commit as `feat(b6): ...`.

## STEP 3: CLOSING PASS (nothing here may change behaviour except to fix a real defect)
1. **Browser check of every page**, desktop 1440px, light and dark: `/`, `/credit`, `/stress`, `/loans`, `/market-risk` (run an analysis, open the Stress Lab and the CSV import), `/var-validation` (run a backtest), `/copilot` (ask a portfolio question and confirm the tool trace and cited numbers), `/model-health`, `/methodology`, `/methodology/market-risk`. List every console error, unreadable contrast in dark mode, empty chart or broken layout, and fix them. `/`, `/stress`, `/loans`, `/copilot` and `/model-health` have not been restyled or checked since the theme toggle was added, so expect some dark-mode issues there. Save screenshots under `docs/screenshots/final/`.
2. **Docs match reality:** `README.md` (features, how to run, how to test), `docs/KNOWN_LIMITATIONS.md` (CSV import limits, replay needs network on first run, copilot guard limits), `docs/MARKET_RISK_METHODS.md` if anything changed, and regenerate `docs/API_CONTRACTS.md` with `python scripts/generate_api_contracts.py` (every new endpoint must be in `EXTENSION_ENDPOINTS`). Make sure `docs/TEST_PLAN.md` and `docs/MODEL_CARD.md` do not contradict the code. Do not leave stale numbers (test counts, instrument counts): re-derive them from real command output.
3. **Repo hygiene:** commit the prompt files under `docs/prompts/` in one `docs:` commit; make sure `git status` shows only the intentional runtime files listed above.
4. **Final full run, from the clean worktree:** `ruff check backend`, `pytest backend/tests -q`, `npm ci && npm run lint && npx tsc --noEmit && npm run build`. Paste the real summary lines.

## STILL SKIPPED (Tier C)
Auth, optimisation tools, PDF export, Playwright suite, OpenAPI client generation, Docker pinning. Do not start these.

## ALWAYS
Never fabricate data or numbers. Keep API changes backward compatible. Commit after each step with `ci(b5): ...`, `feat(b6): ...`, `docs: ...` or `fix(final): ...`. 45-minute guard per stuck task: record the blocker, mark it deferred, move on. Docker is unavailable here; never claim a Docker build. For UI checks, if you cannot run a browser, say so plainly instead of claiming the pages work. After editing `frontend/app/globals.css`, stop the Next dev server (by port, never by matching command-line text) and clear the `frontend/.next` folder, because a stale stylesheet is served otherwise. If a shell heredoc misbehaves on Windows, write the file with your file-write tool.

## FINAL REPORT
1. Commit hashes for B5, B6 and the closing pass.
2. Real output summaries: ruff, pytest, eslint, tsc, build, all from the clean worktree.
3. Screenshots list and every issue found and fixed in the closing pass.
4. What remains unverified (GitHub Actions run, Docker, anything needing network) and why.
5. One sentence on the biggest remaining risk in the project.
