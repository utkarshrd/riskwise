"""Initial schema for PRD Section 9 tables

Revision ID: 264c9e5f32e5
Revises: 
Create Date: 2026-10-13 22:46:07.483366

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '264c9e5f32e5'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. model_versions
    op.create_table(
        'model_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('dataset_id', sa.String(length=100), nullable=False),
        sa.Column('feature_schema_version', sa.String(length=50), nullable=False),
        sa.Column('preprocessing_artifact', sa.String(length=255), nullable=False),
        sa.Column('model_artifact', sa.String(length=255), nullable=False),
        sa.Column('metrics_json', sa.Text(), nullable=False),
        sa.Column('trained_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version')
    )

    # 2. assessment_runs
    op.create_table(
        'assessment_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('model_version_id', sa.String(length=36), nullable=False),
        sa.Column('input_snapshot_json', sa.Text(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('risk_band', sa.String(length=20), nullable=False),
        sa.Column('warnings_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. stress_runs
    op.create_table(
        'stress_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('input_snapshot_json', sa.Text(), nullable=False),
        sa.Column('scenario_json', sa.Text(), nullable=False),
        sa.Column('baseline_metrics_json', sa.Text(), nullable=False),
        sa.Column('stressed_metrics_json', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. portfolio_definitions
    op.create_table(
        'portfolio_definitions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('holdings_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. market_data_manifests
    op.create_table(
        'market_data_manifests',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('symbol', sa.String(length=30), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('start_date', sa.String(length=20), nullable=False),
        sa.Column('end_date', sa.String(length=20), nullable=False),
        sa.Column('frequency', sa.String(length=20), nullable=True),
        sa.Column('retrieved_at', sa.DateTime(), nullable=True),
        sa.Column('file_path', sa.String(length=255), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('quality_notes_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. market_risk_runs
    op.create_table(
        'market_risk_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('portfolio_snapshot_json', sa.Text(), nullable=False),
        sa.Column('method', sa.String(length=50), nullable=False),
        sa.Column('confidence_level', sa.Float(), nullable=False),
        sa.Column('lookback', sa.Integer(), nullable=False),
        sa.Column('metrics_json', sa.Text(), nullable=False),
        sa.Column('data_manifest_ids_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. var_validation_runs
    op.create_table(
        'var_validation_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('portfolio_snapshot_json', sa.Text(), nullable=False),
        sa.Column('method', sa.String(length=50), nullable=False),
        sa.Column('confidence_level', sa.Float(), nullable=False),
        sa.Column('lookback', sa.Integer(), nullable=False),
        sa.Column('forecast_count', sa.Integer(), nullable=False),
        sa.Column('exception_count', sa.Integer(), nullable=False),
        sa.Column('exception_rate', sa.Float(), nullable=False),
        sa.Column('results_path', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. drift_runs
    op.create_table(
        'drift_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('model_version_id', sa.String(length=36), nullable=False),
        sa.Column('reference_batch_id', sa.String(length=100), nullable=False),
        sa.Column('current_batch_id', sa.String(length=100), nullable=False),
        sa.Column('psi_by_feature_json', sa.Text(), nullable=False),
        sa.Column('threshold_config_json', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 9. monitoring_alerts
    op.create_table(
        'monitoring_alerts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('model_version_id', sa.String(length=36), nullable=False),
        sa.Column('drift_run_id', sa.String(length=36), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 10. audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('actor_type', sa.String(length=50), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.String(length=100), nullable=False),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 11. copilot_sessions
    op.create_table(
        'copilot_sessions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_intent', sa.String(length=50), nullable=True),
        sa.Column('parameters_json', sa.Text(), nullable=True),
        sa.Column('history_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('copilot_sessions')
    op.drop_table('audit_events')
    op.drop_table('monitoring_alerts')
    op.drop_table('drift_runs')
    op.drop_table('var_validation_runs')
    op.drop_table('market_risk_runs')
    op.drop_table('market_data_manifests')
    op.drop_table('portfolio_definitions')
    op.drop_table('stress_runs')
    op.drop_table('assessment_runs')
    op.drop_table('model_versions')
