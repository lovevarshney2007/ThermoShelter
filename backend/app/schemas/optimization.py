from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field

OptimizationObjectiveType = Literal["energy", "comfort", "cost", "balanced"]
OptimizationStatusType = Literal["pending", "running", "completed", "failed"]


class OptimizationRequest(BaseModel):
    objective: OptimizationObjectiveType = Field("balanced", description="Optimisation objective")


class OptimizationCandidateResponse(BaseModel):
    id: int
    optimization_run_id: int
    config: dict[str, Any]
    score: float
    comfort_score: float
    energy_score: float
    cost_score: float
    is_winner: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OptimizationRunResponse(BaseModel):
    id: int
    project_id: int
    objective_used: OptimizationObjectiveType
    status: OptimizationStatusType
    reasoning_text: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OptimizationRunDetailResponse(OptimizationRunResponse):
    winner: OptimizationCandidateResponse | None = None
    candidates: list[OptimizationCandidateResponse] = []
