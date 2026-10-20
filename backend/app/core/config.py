from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "RiskWise API"
    VERSION: str = "3.0.0"
    API_V1_PREFIX: str = "/api/v1"

    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Leave empty to auto-compute from REPO_ROOT (ensures CWD-independent absolute path).
    # Set DATABASE_URL in .env to override (e.g. for a different DB path or Postgres).
    DATABASE_URL: str = ""

    OFFLINE_MODE: bool = True

    # Directories (computed relative to this file's resolved location)
    REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = REPO_ROOT / "data"
    ARTIFACTS_DIR: Path = REPO_ROOT / "artifacts"
    KNOWLEDGE_DIR: Path = REPO_ROOT / "knowledge"

    # Optional external provider keys (default empty for offline fallback)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def _set_database_url(self) -> "Settings":
        """If DATABASE_URL was not set via env, derive an absolute path from REPO_ROOT."""
        if not self.DATABASE_URL:
            db_path = self.REPO_ROOT / "riskwise.db"
            self.DATABASE_URL = f"sqlite:///{db_path.as_posix()}"
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
