"""
Scientific Engine Contracts
============================

Re-exports from the global contracts module.
The scientific engine only imports from here — never from app.schemas directly.
This keeps the engine decoupled from FastAPI.
"""

from app.schemas.contracts import (
    ClimateInput,
    ShelterInput,
    MaterialInput,
    SimulationRequest,
    SimulationResult,
    OptimizationRequest,
    OptimizationResult,
    CandidateResult,
    ComparisonResult,
    HeatFlowData,
    ExecutionMode,
)

__all__ = [
    "ClimateInput",
    "ShelterInput",
    "MaterialInput",
    "SimulationRequest",
    "SimulationResult",
    "OptimizationRequest",
    "OptimizationResult",
    "CandidateResult",
    "ComparisonResult",
    "HeatFlowData",
    "ExecutionMode",
]
