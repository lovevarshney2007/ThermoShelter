"""
Database initialisation helpers.

Called once on application startup:
  1. Ensures all tables exist (safety net alongside Alembic).
  2. Seeds default materials if the table is empty.
  3. Seeds climate presets (stored as a module-level constant used by the
     /api/climate-presets endpoint — no DB table needed for presets).
"""

from sqlalchemy.orm import Session
from app.database.base import Base
from app.database.session import engine


# ---------------------------------------------------------------------------
# Default seed data
# ---------------------------------------------------------------------------

DEFAULT_MATERIALS = [
    # ── Structural / Wall materials ──────────────────────────────────────
    {
        "name": "Concrete",
        "category": "wall",
        "thermal_conductivity": 1.7,   # W/m·K
        "density": 2300.0,             # kg/m³
        "specific_heat": 880.0,        # J/kg·K
        "cost_per_unit": 3500.0,       # ₹/m³ (indicative)
    },
    {
        "name": "Brick",
        "category": "wall",
        "thermal_conductivity": 0.72,
        "density": 1800.0,
        "specific_heat": 840.0,
        "cost_per_unit": 2800.0,
    },
    {
        "name": "Wood",
        "category": "wall",
        "thermal_conductivity": 0.14,
        "density": 600.0,
        "specific_heat": 1700.0,
        "cost_per_unit": 8000.0,
    },
    {
        "name": "Stone",
        "category": "wall",
        "thermal_conductivity": 2.2,
        "density": 2600.0,
        "specific_heat": 820.0,
        "cost_per_unit": 4000.0,
    },
    {
        "name": "AAC Block",
        "category": "wall",
        "thermal_conductivity": 0.16,
        "density": 600.0,
        "specific_heat": 1000.0,
        "cost_per_unit": 3200.0,
    },
    # ── Insulation materials ─────────────────────────────────────────────
    {
        "name": "Rock Wool",
        "category": "insulation",
        "thermal_conductivity": 0.038,
        "density": 100.0,
        "specific_heat": 840.0,
        "cost_per_unit": 1200.0,
    },
    {
        "name": "Glass Wool",
        "category": "insulation",
        "thermal_conductivity": 0.035,
        "density": 25.0,
        "specific_heat": 840.0,
        "cost_per_unit": 900.0,
    },
    {
        "name": "EPS (Expanded Polystyrene)",
        "category": "insulation",
        "thermal_conductivity": 0.036,
        "density": 20.0,
        "specific_heat": 1450.0,
        "cost_per_unit": 700.0,
    },
    {
        "name": "XPS (Extruded Polystyrene)",
        "category": "insulation",
        "thermal_conductivity": 0.030,
        "density": 35.0,
        "specific_heat": 1500.0,
        "cost_per_unit": 1100.0,
    },
    # ── Roof materials ───────────────────────────────────────────────────
    {
        "name": "RCC Slab",
        "category": "roof",
        "thermal_conductivity": 1.7,
        "density": 2400.0,
        "specific_heat": 880.0,
        "cost_per_unit": 4000.0,
    },
    {
        "name": "Corrugated Iron Sheet",
        "category": "roof",
        "thermal_conductivity": 50.0,
        "density": 7800.0,
        "specific_heat": 500.0,
        "cost_per_unit": 1500.0,
    },
    # ── Floor materials ──────────────────────────────────────────────────
    {
        "name": "Concrete Slab",
        "category": "floor",
        "thermal_conductivity": 1.7,
        "density": 2300.0,
        "specific_heat": 880.0,
        "cost_per_unit": 3000.0,
    },
    {
        "name": "Packed Earth",
        "category": "floor",
        "thermal_conductivity": 0.52,
        "density": 1500.0,
        "specific_heat": 1480.0,
        "cost_per_unit": 200.0,
    },
]


# Climate presets are served from memory (no DB table required)
CLIMATE_PRESETS = [
    {
        "id": "leh_winter",
        "label": "Leh – Winter",
        "location": "Leh",
        "ambient_temp_c": -15.0,
        "solar_wm2": 300.0,
        "wind_ms": 5.0,
        "humidity_pct": 40.0,
        "mode": "preset",
    },
    {
        "id": "leh_summer",
        "label": "Leh – Summer",
        "location": "Leh",
        "ambient_temp_c": 25.0,
        "solar_wm2": 750.0,
        "wind_ms": 3.5,
        "humidity_pct": 30.0,
        "mode": "preset",
    },
    {
        "id": "jaisalmer_summer",
        "label": "Jaisalmer – Summer",
        "location": "Jaisalmer",
        "ambient_temp_c": 45.0,
        "solar_wm2": 950.0,
        "wind_ms": 4.0,
        "humidity_pct": 15.0,
        "mode": "preset",
    },
    {
        "id": "jaisalmer_winter",
        "label": "Jaisalmer – Winter",
        "location": "Jaisalmer",
        "ambient_temp_c": 10.0,
        "solar_wm2": 400.0,
        "wind_ms": 3.0,
        "humidity_pct": 35.0,
        "mode": "preset",
    },
    {
        "id": "mumbai_monsoon",
        "label": "Mumbai – Monsoon",
        "location": "Mumbai",
        "ambient_temp_c": 30.0,
        "solar_wm2": 200.0,
        "wind_ms": 8.0,
        "humidity_pct": 90.0,
        "mode": "preset",
    },
    {
        "id": "shimla_winter",
        "label": "Shimla – Winter",
        "location": "Shimla",
        "ambient_temp_c": -5.0,
        "solar_wm2": 250.0,
        "wind_ms": 6.0,
        "humidity_pct": 55.0,
        "mode": "preset",
    },
]


# ---------------------------------------------------------------------------
# Initialisation functions
# ---------------------------------------------------------------------------

def create_tables() -> None:
    """Create all tables that don't exist yet (used as a safety net)."""
    Base.metadata.create_all(bind=engine)


def seed_materials(db: Session) -> None:
    """Insert default materials if the materials table is empty."""
    from app.models.material import Material  # lazy import avoids circular deps

    if db.query(Material).count() > 0:
        return  # Already seeded

    for mat_data in DEFAULT_MATERIALS:
        db.add(Material(**mat_data))
    db.commit()
    print(f"[init_db] Seeded {len(DEFAULT_MATERIALS)} default materials.")


def init_db(db: Session) -> None:
    """Run all initialisation steps.

    create_tables() acts as a safety net: SQLAlchemy's create_all() is a
    no-op for tables that already exist, so it never conflicts with Alembic.
    It protects against Railway deployments where Alembic's alembic_version
    row exists but the DDL was never committed (e.g. first-deploy failures).
    """
    create_tables()   # safety net — idempotent, never drops existing tables
    seed_materials(db)
