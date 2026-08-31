"""
ThermoShelter API v2 — main application entry point.

Architecture:
  Frontend → FastAPI (orchestration) → Redis/Celery (jobs) → Scientific Engine → PostgreSQL
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.session import SessionLocal
from app.database.init_db import init_db

# Import all models so SQLAlchemy registers them before create_all()
import app.models.project       # noqa: F401
import app.models.climate       # noqa: F401
import app.models.shelter       # noqa: F401
import app.models.material      # noqa: F401
import app.models.simulation    # noqa: F401
import app.models.optimization  # noqa: F401

# Routers
from app.routers import (
    projects,
    climates,
    shelters,
    materials,
    simulations,
    optimization,
    reports,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: seed database. Shutdown: (no-op currently)."""
    db = SessionLocal()
    try:
        init_db(db)
        mode = "async (Celery+Redis)" if settings.USE_BACKGROUND_JOBS else "synchronous fallback"
        print(f"[startup] {settings.APP_NAME} v{settings.API_VERSION} ready — job mode: {mode}")
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "**ThermoShelter API v2** — Shelter thermal analysis and optimisation platform.\n\n"
        "Architecture:\n"
        "- **FastAPI** handles API, validation, orchestration, persistence\n"
        "- **Scientific Engine** (`/scientific_engine`) handles physics, transient simulation, optimization\n"
        "- **Celery + Redis** handles background job execution (configurable)\n\n"
        "Feature flags (`.env`):\n"
        "- `USE_BACKGROUND_JOBS=false` → synchronous mode (no Redis needed)\n"
        "- `USE_MOCK_SIMULATION=true` → mock physics engine\n"
        "- `USE_MOCK_OPTIMIZATION=true` → mock optimizer"
    ),
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check():
    """Liveness probe — returns app version and feature flag state."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.API_VERSION,
        "background_jobs": settings.USE_BACKGROUND_JOBS,
        "mock_simulation": settings.USE_MOCK_SIMULATION,
        "mock_optimization": settings.USE_MOCK_OPTIMIZATION,
    }


app.include_router(projects.router)
app.include_router(climates.router)
app.include_router(shelters.router)
app.include_router(materials.router)
app.include_router(simulations.router)
app.include_router(optimization.router)
app.include_router(reports.router)
