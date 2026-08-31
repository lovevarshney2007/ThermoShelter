"""
Global Data Contracts
======================

This module is the **single source of truth** for all data shapes crossing
the boundaries between:

    Frontend → FastAPI → Scientific Engine → Optimization → PostgreSQL

ALL layers (routers, services, workers, scientific engine) MUST import
their input/output types from here rather than defining their own.

Stable contracts prevent drift between teams.
"""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

from app.core.constants import (
    RunStatus,
    OptimizationObjective,
    ExecutionMode,
    ValidationStatus,
    SIMULATION_MODEL_VERSION,
    OPTIMIZATION_MODEL_VERSION,
)


# ══════════════════════════════════════════════════════════════════════════════
# INPUT CONTRACTS  (FastAPI → Scientific Engine)
# ══════════════════════════════════════════════════════════════════════════════

class MaterialInput(BaseModel):
    """Material properties passed to the scientific engine."""
    id: int | None = None
    name: str
    category: str
    thermal_conductivity: float = Field(..., gt=0, description="W/m·K")
    density: float              = Field(..., gt=0, description="kg/m³")
    specific_heat: float        = Field(..., gt=0, description="J/kg·K")
    cost_per_unit: float        = Field(0.0, ge=0)


class ClimateInput(BaseModel):
    """
    Climate conditions passed to the scientific engine.

    Supports two modes:
      - static   : single set of conditions (ambient_temp_c, solar_wm2, etc.)
      - time_series : list of hourly snapshots in `time_series_data`
    """
    location: str
    ambient_temp_c: float
    solar_wm2: float    = Field(..., ge=0)
    wind_ms: float      = Field(..., ge=0)
    humidity_pct: float = Field(..., ge=0, le=100)
    mode: str           = "custom"

    # Optional time-series override (list of hourly climate dicts)
    # Each entry: {hour: int, temp_c: float, solar_wm2: float, wind_ms: float, humidity_pct: float}
    time_series_data: list[dict[str, float]] = Field(
        default_factory=list,
        description="Hourly climate data for transient simulation replay",
    )


class ShelterInput(BaseModel):
    """Shelter geometry and construction passed to the scientific engine."""
    length: float        = Field(..., gt=0)
    width: float         = Field(..., gt=0)
    height: float        = Field(..., gt=0)
    wall_thickness: float  = Field(..., gt=0)
    roof_thickness: float  = Field(..., gt=0)
    floor_thickness: float = Field(..., gt=0)
    orientation_deg: float = Field(180.0, ge=0, le=360)
    window_area_m2: float  = Field(0.0, ge=0)
    wall_material: MaterialInput
    roof_material: MaterialInput
    floor_material: MaterialInput


class SimulationRequest(BaseModel):
    """
    Complete request object sent to the scientific engine.
    The engine receives this and returns SimulationResult.
    """
    project_id: int
    simulation_run_id: int
    climate: ClimateInput
    shelter: ShelterInput
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional engine-specific parameters (time step, solver, etc.)",
    )


class OptimizationRequest(BaseModel):
    """Complete request object sent to the optimization engine."""
    project_id: int
    optimization_run_id: int
    climate: ClimateInput
    shelter: ShelterInput
    objective: OptimizationObjective = OptimizationObjective.BALANCED
    available_materials: list[MaterialInput] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT CONTRACTS  (Scientific Engine → FastAPI → Frontend)
# ══════════════════════════════════════════════════════════════════════════════

class HeatFlowData(BaseModel):
    """Hourly heat flow component arrays."""
    conduction: list[float] = Field(default_factory=list)
    convection: list[float] = Field(default_factory=list)
    radiation:  list[float] = Field(default_factory=list)
    solar:      list[float] = Field(default_factory=list)


class SimulationResult(BaseModel):
    """
    Result returned by the scientific engine and stored in PostgreSQL.
    This is the canonical simulation output shape used everywhere.
    """
    simulation_run_id: int
    status: RunStatus = RunStatus.COMPLETED

    # Time series
    timestamps: list[float]             = Field(default_factory=list)
    indoor_temp_c: list[float]          = Field(default_factory=list)
    ambient_temp_c: list[float]         = Field(default_factory=list)
    heat_flow: HeatFlowData             = Field(default_factory=HeatFlowData)

    # Energy summary
    heating_kwh: float = 0.0
    cooling_kwh: float = 0.0
    total_energy_kwh: float = 0.0

    # Comfort metrics
    hours_below_comfort: int = 0
    hours_above_comfort: int = 0
    min_indoor_temp_c: float | None = None
    max_indoor_temp_c: float | None = None

    # Metadata
    model_version: str     = SIMULATION_MODEL_VERSION
    validation_status: str = ValidationStatus.VALID
    execution_mode: ExecutionMode = ExecutionMode.SYNCHRONOUS_FALLBACK
    created_at: datetime | None = None

    model_config = ConfigDict(protected_namespaces=())


class CandidateResult(BaseModel):
    """A single candidate design from the optimization engine."""
    rank: int = 0
    config: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    energy_score: float = 0.0
    comfort_score: float = 0.0
    cost_score: float = 0.0
    is_winner: bool = False
    estimated_heating_kwh: float | None = None
    estimated_cooling_kwh: float | None = None


class ComparisonResult(BaseModel):
    """Baseline vs optimized comparison result."""
    baseline_heating_kwh: float = 0.0
    baseline_cooling_kwh: float = 0.0
    optimized_heating_kwh: float = 0.0
    optimized_cooling_kwh: float = 0.0
    energy_saving_kwh: float = 0.0
    energy_saving_pct: float = 0.0
    comfort_improvement_pct: float = 0.0
    cost_saving_pct: float = 0.0
    baseline_score: float = 0.0
    optimized_score: float = 0.0
    overall_improvement_pct: float = 0.0


class OptimizationResult(BaseModel):
    """Result returned by the optimization engine."""
    optimization_run_id: int
    status: RunStatus = RunStatus.COMPLETED
    objective_used: OptimizationObjective = OptimizationObjective.BALANCED
    candidates: list[CandidateResult] = Field(default_factory=list)
    winner: CandidateResult | None = None
    baseline: CandidateResult | None = None
    comparison: ComparisonResult | None = None
    reasoning_text: str = ""
    model_version: str = OPTIMIZATION_MODEL_VERSION
    execution_mode: ExecutionMode = ExecutionMode.SYNCHRONOUS_FALLBACK
    created_at: datetime | None = None


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION CONTRACT
# ══════════════════════════════════════════════════════════════════════════════

class ValidationError(BaseModel):
    field: str
    message: str
    severity: Literal["error", "warning"] = "error"


class ValidationResult(BaseModel):
    """Pre-flight validation result returned before simulation/optimization."""
    valid: bool
    status: ValidationStatus
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)
    checked_at: datetime | None = None


# ══════════════════════════════════════════════════════════════════════════════
# JOB STATUS CONTRACT
# ══════════════════════════════════════════════════════════════════════════════

class JobStatus(BaseModel):
    """Returned by polling endpoints (/status)."""
    run_id: int
    task_id: str | None = None
    status: RunStatus
    progress: int = Field(0, ge=0, le=100, description="Completion percentage 0–100")
    message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    execution_mode: ExecutionMode = ExecutionMode.SYNCHRONOUS_FALLBACK


# ══════════════════════════════════════════════════════════════════════════════
# QUICK-START RESPONSE (returned immediately on POST /simulate or /optimize)
# ══════════════════════════════════════════════════════════════════════════════

class JobAcceptedResponse(BaseModel):
    """202-style response when a job is queued."""
    run_id: int
    task_id: str | None = None
    status: RunStatus = RunStatus.QUEUED
    message: str = ""
    execution_mode: ExecutionMode
    poll_url: str | None = None
