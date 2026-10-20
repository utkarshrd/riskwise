import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    dataset_id: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    preprocessing_artifact: Mapped[str] = mapped_column(String(255), nullable=False)
    model_artifact: Mapped[str] = mapped_column(String(255), nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    status: Mapped[str] = mapped_column(String(30), default="candidate")  # candidate, active, archived
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class AssessmentRun(Base):
    __tablename__ = "assessment_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    input_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_band: Mapped[str] = mapped_column(String(20), nullable=False)
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")


class StressRun(Base):
    __tablename__ = "stress_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    input_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_json: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    stressed_metrics_json: Mapped[str] = mapped_column(Text, nullable=False)


class PortfolioDefinition(Base):
    __tablename__ = "portfolio_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    holdings_json: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. [{"symbol": "SPY", "weight": 0.6}]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class MarketDataManifest(Base):
    __tablename__ = "market_data_manifests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    provider: Mapped[str] = mapped_column(String(50), default="offline_snapshot")
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    start_date: Mapped[str] = mapped_column(String(20), nullable=False)
    end_date: Mapped[str] = mapped_column(String(20), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="daily")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_notes_json: Mapped[str] = mapped_column(Text, default="{}")


class MarketRiskRun(Base):
    __tablename__ = "market_risk_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    portfolio_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False)
    lookback: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    data_manifest_ids_json: Mapped[str] = mapped_column(Text, default="[]")


class VaRValidationRun(Base):
    __tablename__ = "var_validation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    portfolio_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False)
    lookback: Mapped[int] = mapped_column(Integer, nullable=False)
    forecast_count: Mapped[int] = mapped_column(Integer, nullable=False)
    exception_count: Mapped[int] = mapped_column(Integer, nullable=False)
    exception_rate: Mapped[float] = mapped_column(Float, nullable=False)
    results_path: Mapped[str] = mapped_column(String(255), nullable=False)


class DriftRun(Base):
    __tablename__ = "drift_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reference_batch_id: Mapped[str] = mapped_column(String(100), nullable=False)
    current_batch_id: Mapped[str] = mapped_column(String(100), nullable=False)
    psi_by_feature_json: Mapped[str] = mapped_column(Text, nullable=False)
    threshold_config_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="completed")


class MonitoringAlert(Base):
    __tablename__ = "monitoring_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    drift_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # info, warning, critical
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    actor_type: Mapped[str] = mapped_column(String(50), default="system")
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}")


class CopilotSession(Base):
    __tablename__ = "copilot_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    last_intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    history_json: Mapped[str] = mapped_column(Text, default="[]")
