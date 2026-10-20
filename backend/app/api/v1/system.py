import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.app.core.config import settings
from backend.app.db.models import ModelVersion
from backend.app.db.session import get_db
from backend.app.schemas.system import HealthResponse, SystemStatusResponse
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Liveness check; makes no claim that models or data are healthy."""
    return HealthResponse(status="ok", timestamp=datetime.now(UTC))


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_db)):
    """
    Returns genuine operational status of model artifacts, cached market data,
    RAG corpus, and offline mode. Never fabricates healthy or active state.
    """
    # 1. Check applied database migration revision
    migration_revision: str | None = None
    try:
        rev = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if rev:
            migration_revision = str(rev)
    except Exception:  # noqa: BLE001
        migration_revision = None

    # 2. Check for credit model artifacts and metadata completeness
    models_dir = settings.ARTIFACTS_DIR / "models"
    model_loaded = False
    model_ready = False
    active_version = None

    active_rec = db.query(ModelVersion).filter(ModelVersion.status == "active").first()
    if active_rec and models_dir.exists():
        model_path = Path(active_rec.model_artifact)
        prep_path = Path(active_rec.preprocessing_artifact)
        if not model_path.is_absolute():
            model_path = settings.REPO_ROOT / model_path
        if not prep_path.is_absolute():
            prep_path = settings.REPO_ROOT / prep_path
        if model_path.exists() and prep_path.exists():
            model_loaded = True
            active_version = active_rec.version
            if active_rec.metrics_json:
                try:
                    meta = json.loads(active_rec.metrics_json)
                    if (
                        "decision_threshold" in meta
                        and "risk_band_cutoffs" in meta
                        and isinstance(meta["risk_band_cutoffs"], dict)
                        and all(k in meta["risk_band_cutoffs"] for k in ["low", "moderate", "elevated"])
                    ):
                        model_ready = True
                except (json.JSONDecodeError, TypeError):
                    model_ready = False

    # 3. Check market snapshot status, manifest parity, and checksum verification
    snapshots_dir = settings.DATA_DIR / "market_snapshots"
    manifest_file = settings.DATA_DIR / "manifests" / "market_manifest.json"
    market_loaded = False
    available_tickers: list[str] = []
    snapshot_checksum_verified = False
    snapshot_retrieval_timestamp: str | None = None

    if snapshots_dir.exists():
        snapshot_files = list(snapshots_dir.glob("*.csv"))
        if snapshot_files:
            market_loaded = True
            available_tickers = sorted(f.stem for f in snapshot_files)

    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            snapshot_retrieval_timestamp = manifest_data.get("retrieval_timestamp")
            snapshots = manifest_data.get("snapshots", {})
            if snapshots:
                all_matched = True
                for sym, info in snapshots.items():
                    rel_p = info.get("file_path")
                    csv_path = (settings.REPO_ROOT / rel_p) if rel_p else (snapshots_dir / f"{sym}.csv")
                    if not csv_path.exists():
                        all_matched = False
                        break
                    expected_sha = info.get("checksum") or info.get("sha256")
                    if expected_sha:
                        with open(csv_path, "rb") as cf:
                            actual_sha = hashlib.sha256(cf.read()).hexdigest()
                        if actual_sha != expected_sha:
                            all_matched = False
                            break
                snapshot_checksum_verified = all_matched
        except Exception:  # noqa: BLE001
            snapshot_checksum_verified = False

    # 4. Check LLM provider availability and copilot mode
    llm_configured = bool(settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY)
    llm_status = "configured" if llm_configured else "offline_deterministic"
    copilot_mode = "online_llm" if llm_configured else "offline_fallback"

    # 5. Check RAG corpus manifest and vector index chunk count
    manifest_path = settings.KNOWLEDGE_DIR / "manifest.csv"
    rag_loaded = manifest_path.exists()
    vector_chunk_count = 0
    vec_meta_path = settings.ARTIFACTS_DIR / "vector_index" / "index_metadata.json"
    if vec_meta_path.exists():
        try:
            with open(vec_meta_path, "r", encoding="utf-8") as f:
                vec_meta = json.load(f)
            vector_chunk_count = len(vec_meta.get("chunks", []))
        except Exception:  # noqa: BLE001
            vector_chunk_count = 0

    overall_status = "operational" if (model_ready and market_loaded and snapshot_checksum_verified) else ("degraded" if market_loaded else "offline")

    return SystemStatusResponse(
        status=overall_status,
        offline_mode=settings.OFFLINE_MODE,
        migration_revision=migration_revision,
        active_model_version=active_version,
        credit_model_loaded=model_loaded,
        credit_model_ready=model_ready,
        market_snapshot_loaded=market_loaded,
        market_tickers_available=available_tickers,
        snapshot_checksum_verified=snapshot_checksum_verified,
        snapshot_retrieval_timestamp=snapshot_retrieval_timestamp,
        vector_index_chunk_count=vector_chunk_count,
        llm_provider_configured=llm_configured,
        llm_status=llm_status,
        copilot_mode=copilot_mode,
        rag_corpus_loaded=rag_loaded,
        timestamp=datetime.now(UTC)
    )

