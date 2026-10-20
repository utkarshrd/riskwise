import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.copilot import router as copilot_router
from backend.app.api.v1.credit import router as credit_router
from backend.app.api.v1.finance import router as finance_router
from backend.app.api.v1.market import router as market_router
from backend.app.api.v1.methodology import get_india_context_cards
from backend.app.api.v1.methodology import router as methodology_router
from backend.app.api.v1.monitoring import router as monitoring_router
from backend.app.api.v1.system import router as system_router
from backend.app.core.config import settings
from backend.app.core.logging import logger, request_id_ctx
from backend.app.db.init_db import init_db
from backend.app.schemas.system import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s (Offline Mode: %s)", settings.PROJECT_NAME, settings.VERSION, settings.OFFLINE_MODE)
    # Ensure database schema initialized
    init_db()

    # RAG Vector Index & Knowledge Corpus Startup Verification
    index_meta_path = settings.REPO_ROOT / "artifacts" / "vector_index" / "index_metadata.json"
    manifest_path = settings.REPO_ROOT / "knowledge" / "manifest.csv"
    if index_meta_path.exists() and manifest_path.exists():
        try:
            meta = json.loads(index_meta_path.read_text(encoding="utf-8"))
            chunk_cnt = meta.get("total_chunks", 0)
            logger.info("RAG vector index startup check: VERIFIED (%d indexed chunks ready)", chunk_cnt)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("RAG vector index present but failed reading metadata: %s", e)
    else:
        logger.warning(
            "RAG vector index or manifest missing (meta: %s, manifest: %s). Run scripts/build_index.py to rebuild.",
            index_meta_path.exists(),
            manifest_path.exists()
        )

    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="RiskWise Multi-Domain Financial Risk Intelligence Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def payload_size_limit_and_request_id_middleware(request, call_next):
    # 1. Enforce payload size limit (1MB max per PRD §12)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_048_576:
        return JSONResponse(
            status_code=413,
            content={"detail": "Payload too large. Maximum allowed request body is 1MB."}
        )

    # 2. Extract or generate standard X-Request-ID
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_ctx.set(req_id)
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id
        logger.info(
            "%s %s status=%s duration_ms=%s",
            request.method, request.url.path, response.status_code, duration_ms
        )
        return response
    finally:
        request_id_ctx.reset(token)


# Root liveness check per API contract proposal
@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_liveness():
    """Liveness check; no claim that models/data are healthy."""
    return HealthResponse(status="ok", timestamp=datetime.now(UTC))


# Include v1 routers
app.include_router(system_router, prefix=settings.API_V1_PREFIX)
app.include_router(credit_router, prefix=settings.API_V1_PREFIX)
app.include_router(finance_router, prefix=settings.API_V1_PREFIX)
app.include_router(market_router, prefix=settings.API_V1_PREFIX)
app.include_router(monitoring_router, prefix=settings.API_V1_PREFIX)
app.include_router(copilot_router, prefix=settings.API_V1_PREFIX)
app.include_router(methodology_router, prefix=settings.API_V1_PREFIX)


@app.get(f"{settings.API_V1_PREFIX}/india-context", tags=["India Context"])
def get_india_context():
    """Direct alias for India regulatory and financial literacy context cards."""
    return get_india_context_cards()

