"""
Simulations Router
==================

POST /api/projects/{id}/simulate          → Queue or run simulation
GET  /api/projects/{id}/simulations       → List all runs
GET  /api/simulations/{run_id}            → Get run + result (detail)
GET  /api/simulations/{run_id}/status     → Poll status + progress
GET  /api/simulations/{run_id}/result     → Get full result (completed only)
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.project import Project
from app.models.simulation import SimulationRun, SimulationResult
from app.schemas.simulation import SimulationRunResponse, SimulationRunDetailResponse
from app.schemas.contracts import (
    JobAcceptedResponse,
    JobStatus,
    SimulationResult as SimulationResultContract,
    HeatFlowData,
    ExecutionMode,
)
from app.services.project_service import get_project_or_404, build_simulation_request
from app.services.validation_service import validate_project_for_simulation
from app.core.constants import RunStatus

router = APIRouter(tags=["Simulation"])


def _launch_simulation(sim_run: SimulationRun, project_id: int, db: Session) -> ExecutionMode:
    """
    Queue via Celery if USE_BACKGROUND_JOBS=True, else run synchronously.
    Returns the execution mode used.
    """
    from app.core.config import settings

    if settings.USE_BACKGROUND_JOBS:
        try:
            from app.workers.simulation_tasks import execute_simulation
            task = execute_simulation.delay(sim_run.id)  # type: ignore[attr-defined]
            sim_run.task_id = task.id
            sim_run.status  = RunStatus.QUEUED
            db.commit()
            return ExecutionMode.ASYNC_CELERY
        except Exception:
            pass  # Fall through to synchronous

    # ── Synchronous fallback ──────────────────────────────────────────────────
    from app.scientific_engine.physics.engine import run_transient_simulation

    request = build_simulation_request(project_id, sim_run.id, db)
    output  = run_transient_simulation(request)

    db_result = SimulationResult(
        simulation_run_id=sim_run.id,
        timestamps=output.timestamps,
        indoor_temperatures=output.indoor_temp_c,
        ambient_temperatures=output.ambient_temp_c,
        conduction_data=output.heat_flow.conduction,
        convection_data=output.heat_flow.convection,
        radiation_data=output.heat_flow.radiation,
        solar_data=output.heat_flow.solar,
        heating_kwh=output.heating_kwh,
        cooling_kwh=output.cooling_kwh,
        total_energy_kwh=output.total_energy_kwh,
        hours_below_comfort=output.hours_below_comfort,
        hours_above_comfort=output.hours_above_comfort,
        min_indoor_temp_c=output.min_indoor_temp_c,
        max_indoor_temp_c=output.max_indoor_temp_c,
        execution_mode=output.execution_mode.value,
        validation_status=output.validation_status,
    )
    db.add(db_result)
    sim_run.status        = RunStatus.COMPLETED
    sim_run.completed_at  = datetime.now(timezone.utc)
    sim_run.model_version = output.model_version
    sim_run.execution_mode = output.execution_mode.value
    db.commit()
    db.refresh(sim_run)
    return ExecutionMode.SYNCHRONOUS_FALLBACK


@router.post(
    "/api/projects/{project_id}/simulate",
    response_model=JobAcceptedResponse,
    status_code=202,
)
def run_project_simulation(project_id: int, db: Session = Depends(get_db)):
    """
    Start a thermal simulation for the project.

    - Validates project data first.
    - If USE_BACKGROUND_JOBS=True: queues via Celery, returns immediately.
    - If USE_BACKGROUND_JOBS=False: runs synchronously, returns when done.
    - Poll GET /api/simulations/{run_id}/status for progress.
    """
    project = get_project_or_404(project_id, db)

    # Pre-flight validation
    validation = validate_project_for_simulation(project_id, db)
    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Project validation failed",
                "errors": [e.model_dump() for e in validation.errors],
            },
        )

    # Create SimulationRun record
    sim_run = SimulationRun(
        project_id=project_id,
        status=RunStatus.PENDING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(sim_run)
    db.commit()
    db.refresh(sim_run)

    try:
        mode = _launch_simulation(sim_run, project_id, db)
    except Exception as exc:
        sim_run.status        = RunStatus.FAILED
        sim_run.error_message = str(exc)[:1024]
        sim_run.completed_at  = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}")

    from app.core.config import settings
    return JobAcceptedResponse(
        run_id=sim_run.id,
        task_id=sim_run.task_id,
        status=RunStatus(sim_run.status),
        message="Simulation queued successfully" if settings.USE_BACKGROUND_JOBS else "Simulation completed",
        execution_mode=mode,
        poll_url=f"/api/simulations/{sim_run.id}/status",
    )


@router.get(
    "/api/simulations/{simulation_run_id}/status",
    response_model=JobStatus,
)
def get_simulation_status(simulation_run_id: int, db: Session = Depends(get_db)):
    """Poll the status and progress of a simulation run."""
    sim_run = db.query(SimulationRun).filter(SimulationRun.id == simulation_run_id).first()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    progress = {
        RunStatus.PENDING:   0,
        RunStatus.QUEUED:    5,
        RunStatus.RUNNING:   50,
        RunStatus.COMPLETED: 100,
        RunStatus.FAILED:    0,
    }.get(RunStatus(sim_run.status), 0)

    return JobStatus(
        run_id=sim_run.id,
        task_id=sim_run.task_id,
        status=RunStatus(sim_run.status),
        progress=progress,
        message=sim_run.error_message or "",
        started_at=sim_run.started_at,
        completed_at=sim_run.completed_at,
        execution_mode=ExecutionMode(sim_run.execution_mode)
            if sim_run.execution_mode else ExecutionMode.SYNCHRONOUS_FALLBACK,
    )


@router.get(
    "/api/simulations/{simulation_run_id}/result",
)
def get_simulation_result(simulation_run_id: int, db: Session = Depends(get_db)):
    """
    Get the full simulation result (only available when status = completed).
    Returns the canonical SimulationResult contract shape.
    """
    sim_run = db.query(SimulationRun).filter(SimulationRun.id == simulation_run_id).first()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    if sim_run.status == RunStatus.FAILED:
        raise HTTPException(status_code=422, detail=f"Simulation failed: {sim_run.error_message}")
    if sim_run.status in (RunStatus.PENDING, RunStatus.QUEUED, RunStatus.RUNNING):
        raise HTTPException(
            status_code=202,
            detail=f"Simulation is {sim_run.status}. Poll /status to check progress.",
        )
    if not sim_run.result:
        raise HTTPException(status_code=404, detail="Simulation result not yet available")

    r = sim_run.result
    return SimulationResultContract(
        simulation_run_id=simulation_run_id,
        status=RunStatus.COMPLETED,
        timestamps=r.timestamps,
        indoor_temp_c=r.indoor_temperatures,
        ambient_temp_c=r.ambient_temperatures or [],
        heat_flow=HeatFlowData(
            conduction=r.conduction_data,
            convection=r.convection_data,
            radiation=r.radiation_data,
            solar=r.solar_data,
        ),
        heating_kwh=r.heating_kwh,
        cooling_kwh=r.cooling_kwh,
        total_energy_kwh=r.total_energy_kwh,
        hours_below_comfort=r.hours_below_comfort,
        hours_above_comfort=r.hours_above_comfort,
        min_indoor_temp_c=r.min_indoor_temp_c,
        max_indoor_temp_c=r.max_indoor_temp_c,
        model_version=sim_run.model_version,
        validation_status=r.validation_status or "valid",
        execution_mode=ExecutionMode(r.execution_mode)
            if r.execution_mode else ExecutionMode.SYNCHRONOUS_FALLBACK,
        created_at=r.created_at,
    )


@router.get(
    "/api/projects/{project_id}/simulations",
    response_model=list[SimulationRunResponse],
)
def list_project_simulations(project_id: int, db: Session = Depends(get_db)):
    """Return all simulation runs for a project (most recent first)."""
    get_project_or_404(project_id, db)
    return (
        db.query(SimulationRun)
        .filter(SimulationRun.project_id == project_id)
        .order_by(SimulationRun.created_at.desc())
        .all()
    )


@router.get(
    "/api/simulations/{simulation_run_id}",
    response_model=SimulationRunDetailResponse,
)
def get_simulation(simulation_run_id: int, db: Session = Depends(get_db)):
    """Return a single simulation run with its full result (backward-compatible)."""
    sim_run = db.query(SimulationRun).filter(SimulationRun.id == simulation_run_id).first()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return sim_run
