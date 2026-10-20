import json

import numpy as np
from backend.app.db.models import ModelVersion
from backend.app.services.monitoring.engine import MonitoringEngine


def test_psi_hand_calculated_reference_test():
    """
    Hand-calculated Population Stability Index (PSI) verification test.
    
    Setup:
    Reference distribution (10 observations): [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    num_bins = 2
    Percentiles [0, 50, 100] on reference:
      0th = 1.0, 50th = 5.5, 100th = 10.0
      Adjusted bin edges: [-inf, 5.5, inf]
      
    Reference counts:
      Bin 1 (<= 5.5): 5 values (1, 2, 3, 4, 5) -> ref_prop = 5/10 = 0.500
      Bin 2 (> 5.5):  5 values (6, 7, 8, 9, 10) -> ref_prop = 5/10 = 0.500
      
    Current distribution (10 observations): [1.0, 2.0, 3.0, 4.0, 5.0, 5.1, 5.2, 5.3, 8.0, 9.0]
    Current counts:
      Bin 1 (<= 5.5): 8 values (1, 2, 3, 4, 5, 5.1, 5.2, 5.3) -> cur_prop = 8/10 = 0.800
      Bin 2 (> 5.5):  2 values (8, 9)                          -> cur_prop = 2/10 = 0.200
      
    Smoothing epsilon: 1e-4 (not triggered as counts > 0)
    
    PSI contribution formula: (Actual_i - Expected_i) * ln(Actual_i / Expected_i)
      Bin 1: (0.80 - 0.50) * ln(0.80 / 0.50)
             = 0.30 * ln(1.6)
             = 0.30 * 0.47000363
             = 0.14100109
             
      Bin 2: (0.20 - 0.50) * ln(0.20 / 0.50)
             = -0.30 * ln(0.4)
             = -0.30 * (-0.91629073)
             = 0.27488722
             
    Total Hand-Calculated PSI:
      0.14100109 + 0.27488722 = 0.41588831 -> rounded to 5 decimals: 0.41589
    """
    ref = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    cur = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 5.1, 5.2, 5.3, 8.0, 9.0])
    
    psi = MonitoringEngine.calculate_feature_psi(ref, cur, num_bins=2, epsilon=1e-4)
    expected_hand_calc = 0.41589
    assert abs(psi - expected_hand_calc) < 1e-4, f"Expected PSI {expected_hand_calc}, got {psi}"


def test_psi_identical_distributions():
    """Identical reference and current distributions should produce ~0.0 PSI."""
    np.random.seed(42)
    ref = np.random.normal(loc=10.0, scale=2.0, size=5000)
    cur = np.random.normal(loc=10.0, scale=2.0, size=5000)
    psi = MonitoringEngine.calculate_feature_psi(ref, cur)
    assert psi < 0.05


def test_psi_shifted_distribution():
    """Shifted distribution should produce substantial PSI (> 0.25)."""
    np.random.seed(42)
    ref = np.random.normal(loc=10.0, scale=2.0, size=5000)
    cur = np.random.normal(loc=16.0, scale=2.0, size=5000)
    psi = MonitoringEngine.calculate_feature_psi(ref, cur)
    assert psi > 0.25


def test_challenger_promotion_criteria_refusal():
    """
    Ensures that promotion is refused when a challenger model does not meet
    the PRD minimum gain criteria (AUC gain >= 0.005 or F1 gain > 0.01 with >=0 AUC gain).
    """
    champ = ModelVersion(
        id="champion-model-v1",
        model_name="baseline_model",
        version="v1",
        dataset_id="uci",
        feature_schema_version="v1",
        preprocessing_artifact="dummy",
        model_artifact="dummy",
        checksum="dummy",
        metrics_json=json.dumps({"roc_auc": 0.78, "f1_score": 0.52})
    )
    # Inferior challenger (lower AUC)
    inferior_chall = ModelVersion(
        id="inferior-challenger",
        model_name="inferior_model",
        version="v2",
        dataset_id="uci",
        feature_schema_version="v1",
        preprocessing_artifact="dummy",
        model_artifact="dummy",
        checksum="dummy",
        metrics_json=json.dumps({"roc_auc": 0.76, "f1_score": 0.50})
    )
    eval_res = MonitoringEngine.evaluate_challenger(champ, inferior_chall)
    assert eval_res.promotion_eligible is False
    assert "RETAIN_CHAMPION" in eval_res.recommendation
    assert eval_res.auc_difference == -0.02


def test_challenger_promotion_criteria_acceptance():
    """
    Ensures that promotion is eligible when challenger achieves sufficient AUC gain.
    """
    champ = ModelVersion(
        id="champion-model-v1",
        model_name="baseline_model",
        version="v1",
        dataset_id="uci",
        feature_schema_version="v1",
        preprocessing_artifact="dummy",
        model_artifact="dummy",
        checksum="dummy",
        metrics_json=json.dumps({"roc_auc": 0.75, "f1_score": 0.50})
    )
    superior_chall = ModelVersion(
        id="superior-challenger",
        model_name="superior_model",
        version="v2",
        dataset_id="uci",
        feature_schema_version="v1",
        preprocessing_artifact="dummy",
        model_artifact="dummy",
        checksum="dummy",
        metrics_json=json.dumps({"roc_auc": 0.77, "f1_score": 0.53})
    )
    eval_res = MonitoringEngine.evaluate_challenger(champ, superior_chall, min_auc_gain=0.005)
    assert eval_res.promotion_eligible is True
    assert eval_res.auc_difference == 0.02
    assert "PROMOTE" in eval_res.recommendation
