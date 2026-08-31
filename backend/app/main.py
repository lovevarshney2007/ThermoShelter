"""
ThermoShelter API — main application entry point.

Startup sequence:
  1. FastAPI app is created with CORS, metadata, and lifespan handler.
  2. On startup: DB tables are created (safety net) and seed data is inserted.
  3. All routers are registered.
  4. Health check endpoint is mounted directly here.
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


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan — startup / shutdown hooks
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run seed tasks on startup."""
    db = SessionLocal()
    try:
        init_db(db)
        print(f"[startup] {settings.APP_NAME} is ready.")
    finally:
        db.close()
    yield
    # shutdown actions (none needed currently)


# ──────────────────────────────────────────────────────────────────────────────
# Application factory
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Backend API for ThermoShelter — a shelter thermal analysis and "
        "optimisation platform. Supports project management, climate "
        "configuration, shelter configuration, thermal simulation, "
        "multi-objective optimisation, and report generation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health_check():
    """Simple liveness probe."""
    return {"status": "healthy", "app": settings.APP_NAME}


# ──────────────────────────────────────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────────────────────────────────────

app.include_router(projects.router)
app.include_router(climates.router)
app.include_router(shelters.router)
app.include_router(materials.router)
app.include_router(simulations.router)
app.include_router(optimization.router)
app.include_router(reports.router)
