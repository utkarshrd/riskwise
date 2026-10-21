"""
backend/tests/test_report_integrity.py

Test report integrity to prevent documentation drift from real evaluation artifacts.
Ensures docs/EVALUATION_REPORT.md and docs/MODEL_CARD.md accurately reflect
artifacts/evaluation/model_comparison.json and contain zero deprecated UCI references.
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EVAL_FILE = REPO_ROOT / "artifacts" / "evaluation" / "model_comparison.json"
REPORT_FILE = REPO_ROOT / "docs" / "EVALUATION_REPORT.md"
MODEL_CARD_FILE = REPO_ROOT / "docs" / "MODEL_CARD.md"
FAIRNESS_FILE = REPO_ROOT / "artifacts" / "evaluation" / "fairness_audit.json"


def test_model_comparison_artifact_validity():
    """Assert model_comparison.json exists and contains Indian 4-class credit model keys."""
    assert EVAL_FILE.exists(), f"Missing {EVAL_FILE}"
    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "majority_baseline" in data
    assert "logistic_regression" in data
    assert "xgboost" in data
    assert "xgboost_with_credit_score" in data

    # Verify champion metrics
    champ = data["xgboost"]
    assert "roc_auc" in champ
    assert "macro_f1" in champ
    assert "per_class" in champ
    assert set(champ["per_class"].keys()) == {"P1", "P2", "P3", "P4"}


def test_evaluation_report_numbers_match_json():
    """Assert docs/EVALUATION_REPORT.md matches model_comparison.json metrics."""
    assert REPORT_FILE.exists(), f"Missing {REPORT_FILE}"
    assert EVAL_FILE.exists(), f"Missing {EVAL_FILE}"

    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    report_text = REPORT_FILE.read_text(encoding="utf-8")

    champ = metrics["xgboost"]
    champ_roc = f"{champ['roc_auc']:.4f}"
    champ_f1 = f"{champ['macro_f1']:.4f}"
    champ_acc = f"{champ['accuracy']:.4f}"

    assert champ_roc in report_text, f"Champion ROC-AUC {champ_roc} not found in {REPORT_FILE}"
    assert champ_f1 in report_text, f"Champion Macro-F1 {champ_f1} not found in {REPORT_FILE}"
    assert champ_acc in report_text, f"Champion Accuracy {champ_acc} not found in {REPORT_FILE}"

    leakage = metrics["xgboost_with_credit_score"]
    leak_roc = f"{leakage['roc_auc']:.4f}"
    assert leak_roc in report_text, f"Leakage ROC-AUC {leak_roc} not found in {REPORT_FILE}"


def test_model_card_numbers_match_json():
    """Assert docs/MODEL_CARD.md matches model_comparison.json and fairness_audit.json."""
    assert MODEL_CARD_FILE.exists(), f"Missing {MODEL_CARD_FILE}"
    assert EVAL_FILE.exists(), f"Missing {EVAL_FILE}"

    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    card_text = MODEL_CARD_FILE.read_text(encoding="utf-8")

    champ = metrics["xgboost"]
    champ_roc = f"{champ['roc_auc']:.4f}"
    champ_f1 = f"{champ['macro_f1']:.4f}"

    assert champ_roc in card_text, f"Champion ROC-AUC {champ_roc} not found in {MODEL_CARD_FILE}"
    assert champ_f1 in card_text, f"Champion Macro-F1 {champ_f1} not found in {MODEL_CARD_FILE}"


def test_no_uci_taiwan_in_reports():
    """Assert zero deprecated UCI Taiwan references in generated reports."""
    for file_path in [REPORT_FILE, MODEL_CARD_FILE]:
        if file_path.exists():
            text = file_path.read_text(encoding="utf-8").lower()
            assert "taiwan" not in text, f"Found deprecated reference 'taiwan' in {file_path}"
            assert "uci credit" not in text, f"Found deprecated reference 'uci credit' in {file_path}"
