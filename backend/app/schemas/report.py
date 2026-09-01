"""
Report schema — structured output for GET /api/projects/{id}/report
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.contracts import (
    ComparisonResult,
    ValidationResult,
)


class ReportMaterial(BaseModel):
    id: int | None
    name: str
    category: str
    thermal_conductivity: float
    density: float
    specific_heat: float
    cost_per_unit: float


class ReportClimate(BaseModel):
    location: str
    ambient_temp_c: float
    solar_wm2: float
    wind_ms: float
    humidity_pct: float
    mode: str
    has_time_series: bool = False


class ReportShelter(BaseModel):
    length: float
    width: float
    height: float
    wall_thickness: float
    roof_thickness: float
    floor_thickness: float
    orientation_deg: float
    window_area_m2: float


class ReportSimulation(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    simulation_run_id: int
    status: str
    model_version: str
    heating_kwh: float | None
    cooling_kwh: float | None
    total_energy_kwh: float | None
    min_indoor_temp_c: float | None
    max_indoor_temp_c: float | None
    hours_below_comfort: int | None
    hours_above_comfort: int | None
    execution_mode: str | None
    completed_at: datetime | None


class ReportOptimization(BaseModel):
    optimization_run_id: int
    status: str
    objective_used: str
    reasoning_text: str | None
    winner_config: dict[str, Any] | None
    winner_score: float | None
    candidate_count: int
    execution_mode: str | None
    completed_at: datetime | None


class ReportRecommendation(BaseModel):
    summary: str
    selected_design: str
    why_selected: str
    energy_improvement: str
    comfort_improvement: str
    cost_tradeoff: str
    key_changes: list[str]


class ProjectReport(BaseModel):
    """Top-level report returned by GET /api/projects/{id}/report"""
    schema_version: str = "2.0"
    generated_at: datetime

    project: dict[str, Any]
    climate: ReportClimate | None
    shelter: ReportShelter | None
    materials: dict[str, ReportMaterial | None]

    latest_simulation: ReportSimulation | None
    latest_optimization: ReportOptimization | None

    comparison: ComparisonResult | None
    recommendation: ReportRecommendation | None

    metadata: dict[str, Any] = Field(default_factory=dict)
