from typing import Any

from pydantic import BaseModel, Field


class ModelRegistryItem(BaseModel):
    id: str
    model_name: str
    version: str
    dataset_id: str
    status: str
    trained_at: str
    checksum: str
    metrics: dict[str, Any]


class DriftRunRequest(BaseModel):
    model_version_id: str | None = Field(default=None, description="Model ID to monitor, defaults to active model")
    reference_batch_id: str = Field(default="training_baseline")
    current_batch_id: str = Field(default="monitoring_batch_1")
    warning_threshold: float = Field(default=0.10, ge=0.01)
    critical_threshold: float = Field(default=0.25, ge=0.05)


class FeaturePSISchema(BaseModel):
    feature_name: str
    psi_value: float
    drift_status: str
    reference_count: int
    current_count: int


class DriftRunResponse(BaseModel):
    id: str
    model_version_id: str
    reference_batch_id: str
    current_batch_id: str
    overall_psi: float
    overall_status: str
    drift_source: str = Field(default="synthetic injected drift for pipeline validation")
    features: list[FeaturePSISchema]
    run_timestamp: str


class ChallengerEvaluateRequest(BaseModel):
    challenger_model_id: str


class ChallengerEvaluateResponse(BaseModel):
    champion_model_id: str
    challenger_model_id: str
    champion_roc_auc: float
    challenger_roc_auc: float
    auc_difference: float
    champion_f1: float
    challenger_f1: float
    f1_difference: float
    recommendation: str
    promotion_eligible: bool


from pydantic import AliasChoices, BaseModel, Field


class ChallengerPromoteRequest(BaseModel):
    challenger_model_id: str = Field(
        ...,
        validation_alias=AliasChoices("challenger_model_id", "challenger_version_id"),
        description="ID of candidate challenger model"
    )
    justification: str = Field(
        ...,
        min_length=10,
        validation_alias=AliasChoices("justification", "promotion_reason"),
        description="Audit justification for promotion"
    )
    promoted_by: str = Field(default="admin", description="Identity or role of the actor promoting the model")


class ChallengerPromoteResponse(BaseModel):
    status: str
    promoted_model_id: str
    version: str
    audit_event_id: str
    timestamp: str
