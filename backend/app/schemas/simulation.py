from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

SimulationStatusType = Literal["pending", "running", "completed", "failed"]


class SimulationRunResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: int
    project_id: int
    status: SimulationStatusType
    model_version: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SimulationResultResponse(BaseModel):
    id: int
    simulation_run_id: int
    timestamps: list
    indoor_temperatures: list
    conduction_data: list
    convection_data: list
    radiation_data: list
    solar_data: list
    heating_kwh: float
    cooling_kwh: float
    created_at: datetime

    model_config = {"from_attributes": True}


class SimulationRunDetailResponse(SimulationRunResponse):
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)
    result: SimulationResultResponse | None = None
