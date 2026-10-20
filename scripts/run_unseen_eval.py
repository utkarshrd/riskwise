#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.agents.copilot import RiskCopilotService

cases_path = REPO_ROOT / "artifacts" / "evaluation" / "unseen_challenge_cases.json"
with open(cases_path) as f:
    cases = json.load(f)

service = RiskCopilotService()
passed_count = 0
results = []

print(f"Evaluating {len(cases)} Unseen Cases against CURRENT classifier:")
for case in cases:
    try:
        session_id = case.get("session_id")
        res = service.route_and_execute(case["query"], session_id=session_id)
        passed = True
        failures = []

        if res.intent != case["expected_intent"]:
            passed = False
            failures.append(f"Intent mismatch: got {res.intent}, expected {case['expected_intent']}")

        actual_tool = res.tool_trace[0].tool_name if res.tool_trace else None
        if actual_tool != case["expected_tool"]:
            passed = False
            failures.append(f"Tool mismatch: got {actual_tool}, expected {case['expected_tool']}")

        for text in case.get("must_have_in_answer", []):
            if text.lower() not in res.answer.lower():
                passed = False
                failures.append(f"Missing text: {text}")

        if passed:
            passed_count += 1
            print(f"  [PASS] {case['id']}")
        else:
            print(f"  [FAIL] {case['id']}: {'; '.join(failures)}")

        results.append({
            "id": case["id"],
            "query": case["query"],
            "passed": passed,
            "failures": failures,
            "actual_intent": res.intent,
            "actual_tool": actual_tool,
            "answer": res.answer[:150]
        })
    except Exception as e:  # noqa: BLE001
        print(f"  [ERROR] {case['id']}: {e}")
        results.append({"id": case["id"], "query": case["query"], "passed": False, "failures": [str(e)]})

pass_rate = passed_count / len(cases)
print(f"\nFirst-Run Score on Unseen Suite: {passed_count}/{len(cases)} ({pass_rate:.1%})\n")

out_path = REPO_ROOT / "artifacts" / "evaluation" / "unseen_first_run_results.json"
with open(out_path, "w") as f:
    json.dump({
        "passed_count": passed_count,
        "total": len(cases),
        "pass_rate": round(pass_rate, 4),
        "results": results
    }, f, indent=2)

print(f"First-run results written to {out_path}")
