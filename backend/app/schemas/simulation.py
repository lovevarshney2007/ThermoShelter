from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

SimulationStatusType = Literal["pending", "queued", "running", "completed", "failed"]


class SimulationRunResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: int
    project_id: int
    status: SimulationStatusType
    model_version: str
    task_id: str | None = None
    execution_mode: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class SimulationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    simulation_run_id: int
    timestamps: list
    indoor_temperatures: list
    ambient_temperatures: list = Field(default_factory=list)
    conduction_data: list
    convection_data: list
    radiation_data: list
    solar_data: list
    heating_kwh: float
    cooling_kwh: float
    total_energy_kwh: float = 0.0
    hours_below_comfort: int = 0
    hours_above_comfort: int = 0
    min_indoor_temp_c: float | None = None
    max_indoor_temp_c: float | None = None
    execution_mode: str | None = None
    validation_status: str = "valid"
    created_at: datetime


class SimulationRunDetailResponse(SimulationRunResponse):
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)
    result: SimulationResultResponse | None = None
