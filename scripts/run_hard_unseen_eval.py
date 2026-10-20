import json
from pathlib import Path

from backend.app.agents.copilot import RiskCopilotService

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = REPO_ROOT / "artifacts" / "evaluation" / "unseen_hard_15_cases.json"
RESULTS_PATH = REPO_ROOT / "artifacts" / "evaluation" / "unseen_hard_15_first_run_results.json"

with open(CASES_PATH, "r", encoding="utf-8") as f:
    cases = json.load(f)

service = RiskCopilotService()
results = []
passed_count = 0

print(f"Running Hard Unseen Suite ({len(cases)} cases) ONCE...")

for case in cases:
    try:
        res = service.route_and_execute(case["query"], session_id=case.get("session_id"))
        failures = []

        if res.intent != case["expected_intent"]:
            failures.append(f"Intent mismatch: got {res.intent}, expected {case['expected_intent']}")

        actual_tool = res.tool_trace[0].tool_name if res.tool_trace else None
        if case["expected_tool"] is not None and actual_tool != case["expected_tool"]:
            failures.append(f"Tool mismatch: got {actual_tool}, expected {case['expected_tool']}")
        elif case["expected_tool"] is None and actual_tool is not None and case.get("should_reject", False):
            failures.append(f"Tool unexpectedly executed: {actual_tool}")

        for text in case.get("must_have_in_answer", []):
            if text.lower() not in res.answer.lower():
                failures.append(f"Answer missing expected text: '{text}'")

        passed = len(failures) == 0
        if passed:
            passed_count += 1
            print(f"  [PASS] {case['id']}: {case['description']}")
        else:
            print(f"  [FAIL] {case['id']}: {case['description']} -> {failures}")

        results.append({
            "id": case["id"],
            "query": case["query"],
            "passed": passed,
            "failures": failures,
            "actual_intent": res.intent,
            "actual_tool": actual_tool,
            "answer": res.answer[:200]
        })
    except Exception as e:  # noqa: BLE001
        print(f"  [ERROR] {case['id']}: {e}")
        results.append({"id": case["id"], "query": case["query"], "passed": False, "failures": [str(e)]})

pass_rate = passed_count / len(cases)
print(f"\nReal First-Run Score on 15 Hard Unseen Cases: {passed_count}/{len(cases)} ({pass_rate:.1%})\n")

with open(RESULTS_PATH, "w", encoding="utf-8") as f:
    json.dump({
        "frozen_sha256": "9A9AF7F9258FF823CFCD368632BD3CB23D6DBB0D185BC31EB8091CDAB20B2E42",
        "total_cases": len(cases),
        "passed": passed_count,
        "failed": len(cases) - passed_count,
        "pass_rate": round(pass_rate, 4),
        "results": results
    }, f, indent=2)

print(f"Recorded first run results to {RESULTS_PATH}")
