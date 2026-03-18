from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:secret@localhost:5433/yoagent"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    # Redis
    REDIS_URL: str = "redis://localhost:6380/0"

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def sync_database_url(self) -> str:
        """Sync database URL for Alembic (replaces asyncpg with psycopg2)."""
        return self.DATABASE_URL.replace("+asyncpg", "")

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")


settings = Settings()
