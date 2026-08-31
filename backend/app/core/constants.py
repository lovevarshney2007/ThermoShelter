"""
Application-wide constants.

Centralised here so they can be imported by any layer (routers, services,
scientific engine, workers) without creating circular dependencies.
"""

from enum import Enum


# ── Job / Run status ─────────────────────────────────────────────────────────

class RunStatus(str, Enum):
    PENDING   = "pending"
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


# ── Optimization objectives ───────────────────────────────────────────────────

class OptimizationObjective(str, Enum):
    ENERGY   = "energy"
    COMFORT  = "comfort"
    COST     = "cost"
    BALANCED = "balanced"


# ── Execution mode ────────────────────────────────────────────────────────────

class ExecutionMode(str, Enum):
    ASYNC_CELERY         = "async_celery"
    SYNCHRONOUS_FALLBACK = "synchronous_fallback"


# ── Climate modes ─────────────────────────────────────────────────────────────

class ClimateMode(str, Enum):
    PRESET     = "preset"
    CUSTOM     = "custom"
    TIME_SERIES = "time_series"


# ── Validation status ─────────────────────────────────────────────────────────

class ValidationStatus(str, Enum):
    VALID   = "valid"
    INVALID = "invalid"
    WARNING = "warning"


# ── Engine / model versions ───────────────────────────────────────────────────

SIMULATION_MODEL_VERSION   = "2.0"
OPTIMIZATION_MODEL_VERSION = "2.0"
REPORT_SCHEMA_VERSION      = "2.0"

# ── Simulation defaults ───────────────────────────────────────────────────────

DEFAULT_COMFORT_TEMP_C      = 20.0   # Target indoor temperature for HVAC calcs
DEFAULT_INTERNAL_GAIN_W     = 100.0  # People + equipment baseline
DEFAULT_WINDOW_U_VALUE      = 3.0    # W/m²·K — standard double glazing
DEFAULT_WINDOW_SHGC         = 0.7    # Solar heat gain coefficient
SIMULATION_HOURS            = 24     # Hours simulated per run
