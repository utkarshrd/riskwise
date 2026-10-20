from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Liveness indicator")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SystemStatusResponse(BaseModel):
    status: str = Field(description="Operational status indicator")
    offline_mode: bool = Field(description="Whether running in zero-dependency offline mode")
    migration_revision: str | None = Field(default=None, description="Current applied database migration revision")
    active_model_version: str | None = Field(default=None, description="Active credit model version if loaded")
    credit_model_loaded: bool = Field(description="True if serialized model artifact is present and loaded")
    credit_model_ready: bool = Field(default=False, description="True if model artifact and complete metadata (decision_threshold, risk_band_cutoffs) are verified")
    market_snapshot_loaded: bool = Field(description="True if historical market price snapshot exists")
    market_tickers_available: list[str] = Field(default_factory=list, description="Available market tickers")
    snapshot_checksum_verified: bool = Field(default=False, description="Whether market snapshot files match manifest SHA256 checksums")
    snapshot_retrieval_timestamp: str | None = Field(default=None, description="ISO timestamp of market data snapshot download from real provider")
    vector_index_chunk_count: int = Field(default=0, description="Total indexed chunks in RAG retrieval vector store")
    llm_provider_configured: bool = Field(description="True if valid LLM API key is present in environment")
    llm_status: str = Field(default="offline_deterministic", description="Configured status of external LLM providers")
    copilot_mode: str = Field(default="offline_fallback", description="Operating execution mode of Agentic Copilot")
    rag_corpus_loaded: bool = Field(description="True if curated RAG corpus manifest exists")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

