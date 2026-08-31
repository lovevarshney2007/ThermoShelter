from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "ThermoShelter API"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # CORS origins — stored as comma-separated string in .env
    FRONTEND_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql://") and not v.startswith("postgresql+psycopg2://"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
