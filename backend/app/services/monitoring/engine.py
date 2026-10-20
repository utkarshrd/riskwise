import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from backend.app.db.models import ModelVersion
from pydantic import BaseModel, Field


class FeaturePSISummary(BaseModel):
    feature_name: str
    psi_value: float
    drift_status: str  # STABLE, MODERATE_DRIFT, SIGNIFICANT_DRIFT
    reference_count: int
    current_count: int


class DriftRunResult(BaseModel):
    model_version_id: str
    reference_batch_id: str
    current_batch_id: str
    overall_psi: float
    overall_status: str
    drift_source: str = "synthetic injected drift for pipeline validation"
    features: list[FeaturePSISummary]
    run_timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ChallengerEvaluationResult(BaseModel):
    champion_model_id: str
    challenger_model_id: str
    champion_roc_auc: float
    challenger_roc_auc: float
    auc_difference: float
    challenger_f1: float
    champion_f1: float
    f1_difference: float
    recommendation: str
    promotion_eligible: bool


class MonitoringEngine:
    @staticmethod
    def calculate_feature_psi(
        reference_values: np.ndarray | list[float],
        current_values: np.ndarray | list[float],
        num_bins: int = 10,
        epsilon: float = 1e-4
    ) -> float:
        """
        Computes Population Stability Index (PSI) using bins derived from reference distribution.
        Handles zero-frequencies with smoothing constant epsilon.
        """
        ref = np.asarray(reference_values, dtype=float)
        cur = np.asarray(current_values, dtype=float)

        # Filter out NaN/infinite
        ref = ref[np.isfinite(ref)]
        cur = cur[np.isfinite(cur)]

        if len(ref) == 0 or len(cur) == 0:
            return 0.0

        # Compute quantiles from reference data
        percentiles = np.linspace(0, 100, num_bins + 1)
        bin_edges = np.percentile(ref, percentiles)
        bin_edges = np.unique(bin_edges)  # Remove duplicates for low cardinality

        if len(bin_edges) < 2:
            return 0.0

        # Bin edge adjustments to include extremes
        bin_edges[0] = -np.inf
        bin_edges[-1] = np.inf

        # Histogram counts
        ref_counts, _ = np.histogram(ref, bins=bin_edges)
        cur_counts, _ = np.histogram(cur, bins=bin_edges)

        # Proportions with epsilon smoothing
        ref_props = ref_counts / len(ref)
        cur_props = cur_counts / len(cur)

        ref_props = np.where(ref_props == 0, epsilon, ref_props)
        cur_props = np.where(cur_props == 0, epsilon, cur_props)

        # Re-normalize to sum to 1
        ref_props = ref_props / np.sum(ref_props)
        cur_props = cur_props / np.sum(cur_props)

        # PSI formula: sum( (Actual - Expected) * ln(Actual / Expected) )
        psi_contributions = (cur_props - ref_props) * np.log(cur_props / ref_props)
        total_psi = float(np.sum(psi_contributions))
        return round(max(0.0, total_psi), 5)

    @classmethod
    def evaluate_batch_drift(
        cls,
        model_version_id: str,
        reference_df: pd.DataFrame,
        current_df: pd.DataFrame,
        feature_columns: list[str] | None = None,
        reference_batch_id: str = "training_baseline",
        current_batch_id: str = "monitoring_batch",
        warning_threshold: float = 0.10,
        critical_threshold: float = 0.25,
        drift_source: str = "synthetic injected drift for pipeline validation"
    ) -> DriftRunResult:
        if feature_columns is None:
            # Common numeric columns
            common_cols = [c for c in reference_df.columns if c in current_df.columns]
            feature_columns = [
                c for c in common_cols
                if pd.api.types.is_numeric_dtype(reference_df[c])
                and c.lower() not in ["id", "target", "default", "label", "prospectid", "approved_flag"]
                and not c.lower().endswith("id")
            ]

        feature_summaries = []
        psi_values = []

        for col in feature_columns:
            ref_vals = reference_df[col].dropna().values
            cur_vals = current_df[col].dropna().values
            psi = cls.calculate_feature_psi(ref_vals, cur_vals)
            psi_values.append(psi)

            if psi >= critical_threshold:
                status = "SIGNIFICANT_DRIFT"
            elif psi >= warning_threshold:
                status = "MODERATE_DRIFT"
            else:
                status = "STABLE"

            feature_summaries.append(FeaturePSISummary(
                feature_name=col,
                psi_value=psi,
                drift_status=status,
                reference_count=len(ref_vals),
                current_count=len(cur_vals)
            ))

        mean_psi = float(np.mean(psi_values)) if psi_values else 0.0
        if mean_psi >= critical_threshold:
            overall_status = "CRITICAL_DRIFT"
        elif mean_psi >= warning_threshold:
            overall_status = "WARNING_DRIFT"
        else:
            overall_status = "STABLE"

        return DriftRunResult(
            model_version_id=model_version_id,
            reference_batch_id=reference_batch_id,
            current_batch_id=current_batch_id,
            overall_psi=round(mean_psi, 4),
            overall_status=overall_status,
            drift_source=drift_source,
            features=feature_summaries
        )

    @staticmethod
    def evaluate_challenger(
        champion: ModelVersion,
        challenger: ModelVersion,
        min_auc_gain: float = 0.005
    ) -> ChallengerEvaluationResult:
        champ_metrics = json.loads(champion.metrics_json)
        chall_metrics = json.loads(challenger.metrics_json)

        if "roc_auc" not in champ_metrics or "f1_score" not in champ_metrics:
            raise ValueError(f"Champion model {champion.id} metrics_json is missing required 'roc_auc' or 'f1_score'.")
        if "roc_auc" not in chall_metrics or "f1_score" not in chall_metrics:
            raise ValueError(f"Challenger model {challenger.id} metrics_json is missing required 'roc_auc' or 'f1_score'.")

        champ_auc = float(champ_metrics["roc_auc"])
        chall_auc = float(chall_metrics["roc_auc"])
        champ_f1 = float(champ_metrics["f1_score"])
        chall_f1 = float(chall_metrics["f1_score"])

        auc_diff = chall_auc - champ_auc
        f1_diff = chall_f1 - champ_f1

        eligible = (auc_diff >= min_auc_gain) or (auc_diff >= 0 and f1_diff > 0.01)

        if eligible:
            rec = f"PROMOTE: Challenger exceeds champion ROC-AUC by {auc_diff:+.4f} (>= threshold {min_auc_gain})."
        else:
            rec = f"RETAIN_CHAMPION: Challenger did not demonstrate sufficient gain (AUC diff {auc_diff:+.4f})."

        return ChallengerEvaluationResult(
            champion_model_id=champion.id,
            challenger_model_id=challenger.id,
            champion_roc_auc=round(champ_auc, 4),
            challenger_roc_auc=round(chall_auc, 4),
            auc_difference=round(auc_diff, 4),
            champion_f1=round(champ_f1, 4),
            challenger_f1=round(chall_f1, 4),
            f1_difference=round(f1_diff, 4),
            recommendation=rec,
            promotion_eligible=eligible
        )
