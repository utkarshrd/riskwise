You are continuing an in-progress upgrade of RiskWise (FastAPI backend in `backend/app/`, Next.js 16 frontend in `frontend/`). The full original plan is in `docs/ANTIGRAVITY_PROMPT.md`; read it first, then `git log` and `git status` to see where things stand. Do not redo finished work.

## CURRENT STATE (verified by me, 2026-10-22)
- Phase 0 is committed: `frontend/lib/api.ts` tracked, temporary VaR JSONs untracked, UCI purged with `backend/tests/test_report_integrity.py`, Docker status documented as unavailable on this host. 168 backend tests pass (`.venv/Scripts/python.exe -m pytest backend/tests -q`).
- UNCOMMITTED partial work (review it, finish it, then commit): new `instruments` and `daily_prices` tables in `backend/app/db/models.py` with migration `7d89ecd4f853`, `scripts/build_instrument_master.py`, `data/market_snapshots/USDINR=X.csv`, new schemas in `backend/app/schemas/market.py`, and a new package `backend/app/services/market_risk/pkg/` (returns, var_models, attribution, stress, portfolio) with `backend/tests/unit/test_phase2_risk_engine.py`.
- NOT done: instrument master not wired into `/market/search`; the old `engine.py` and the new `pkg/` coexist; VaR validation upgrades; all frontend work; auth/CI.

## KNOWN LEFTOVERS TO FIX FIRST (small, do these before new features)
1. UCI mentions remain in `backend/app/services/credit/service.py`, `knowledge/sources/uci_credit_card_study.md`, `artifacts/vector_index/index_metadata.json` and `artifacts/evaluation/copilot_rag_eval_results.json`. The copilot knowledge base must not cite the UCI study as a current source. Replace it with a source document describing the Indian bank dataset and rebuild the index with `scripts/build_index.py`. Leave mentions in `docs/DECISIONS.md` and `docs/BACKEND_AUDIT.md` only if they clearly read as history.
2. Rename `pkg/` to something meaningful (for example `risk/`), and make the old `engine.py` a thin facade over it so there is a single implementation. Existing API responses must not change shape.
3. Docker still cannot be verified here. Do not claim otherwise.

## HOW TO WORK
- Work one phase at a time: Phase 1 (finish), Phase 2 (finish), Phase 3, Phase 4, Phase 5, as specified in `docs/ANTIGRAVITY_PROMPT.md`.
- Before each phase, post a short plan (files you will touch, tests you will add, how you will verify). Wait for my "go" only at the start of Phase 1, Phase 3 and Phase 4; between the others continue on your own.
- Definition of done for each phase: tests pass (paste the pytest summary line), `npm run lint && npm run build` pass for frontend changes, the change is committed, and you list what you could NOT verify.
- For every new VaR method or metric, write a test against a known analytic or reference value (for example Gaussian VaR on a normal sample should match `mu - z*sigma`; Kupiec with 0 exceptions must not use a magic sentinel). Show me the test, not just "tests pass".
- Frontend: after each page change, start both servers, open the page in the browser, report console errors, and attach desktop and mobile screenshots.
- If you hit a decision I haven't covered, pick the default, write it in `docs/DECISIONS.md` with one line of reasoning, and tell me in your phase summary.

## END OF EACH PHASE: REPORT FORMAT
1. What changed (files, grouped by purpose).
2. Evidence (commands run and their real output summary).
3. What is still unverified or deferred, and why.
4. One thing you would change about this plan if you could.
