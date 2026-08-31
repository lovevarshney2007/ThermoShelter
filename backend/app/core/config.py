from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "ThermoShelter API"
    DEBUG: bool = False
    API_VERSION: str = "2.0.0"

    # Database
    DATABASE_URL: str

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Feature flags
    USE_BACKGROUND_JOBS: bool = False   # True = queue via Celery; False = synchronous fallback
    USE_MOCK_SIMULATION: bool = True    # True = mock physics; False = real engine
    USE_MOCK_OPTIMIZATION: bool = True  # True = mock optimizer; False = real engine

    # CORS origins — stored as comma-separated string in .env
    FRONTEND_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql://") and not v.startswith("sqlite:///"):
            raise ValueError("DATABASE_URL must be a PostgreSQL or SQLite connection string")
        return v

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
