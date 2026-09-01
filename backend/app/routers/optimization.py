"""
Optimization Router
====================

POST /api/projects/{id}/optimize              → Queue or run optimization
GET  /api/optimization/{run_id}/status        → Poll status
GET  /api/optimization/{run_id}/result        → Get full result
GET  /api/projects/{id}/comparison            → Baseline vs optimized
GET  /api/projects/{id}/recommendation        → Explainable recommendation
GET  /api/projects/{id}/validate              → Pre-flight validation
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.project import Project
from app.models.optimization import OptimizationRun, OptimizationCandidate
from app.schemas.optimization import OptimizationRequest, OptimizationRunDetailResponse
from app.schemas.contracts import (
    JobAcceptedResponse,
    JobStatus,
    OptimizationResult,
    ComparisonResult,
    ExecutionMode,
    ValidationResult,
)
from app.services.project_service import get_project_or_404, build_optimization_request
from app.services.validation_service import validate_project_for_simulation
from app.services.comparison_service import get_comparison
from app.services.recommendation_service import get_recommendation
from app.core.constants import RunStatus

router = APIRouter(tags=["Optimization"])


def _launch_optimization(
    opt_run: OptimizationRun, project_id: int, objective: str, db: Session
) -> ExecutionMode:
    """Queue via Celery or run synchronously with fallback."""
    from app.core.config import settings

    if settings.USE_BACKGROUND_JOBS:
        try:
            from app.workers.optimization_tasks import execute_optimization
            task = execute_optimization.delay(opt_run.id)  # type: ignore[attr-defined]
            opt_run.task_id = task.id
            opt_run.status  = RunStatus.QUEUED
            db.commit()
            return ExecutionMode.ASYNC_CELERY
        except Exception:
            pass

    # ── Synchronous fallback ──────────────────────────────────────────────────
    from app.scientific_engine.optimization.engine import run_optimization

    request = build_optimization_request(project_id, opt_run.id, objective, db)
    result  = run_optimization(request)

    for cand in result.candidates:
        db.add(OptimizationCandidate(
            optimization_run_id=opt_run.id,
            config=cand.config,
            score=cand.score,
            energy_score=cand.energy_score,
            comfort_score=cand.comfort_score,
            cost_score=cand.cost_score,
            is_winner=cand.is_winner,
        ))

    opt_run.status          = RunStatus.COMPLETED
    opt_run.completed_at    = datetime.now(timezone.utc)
    opt_run.reasoning_text  = result.reasoning_text
    opt_run.comparison_data = result.comparison.model_dump() if result.comparison else None
    opt_run.baseline_data   = result.baseline.model_dump()   if result.baseline   else None
    opt_run.execution_mode  = result.execution_mode.value
    db.commit()
    db.refresh(opt_run)
    return ExecutionMode.SYNCHRONOUS_FALLBACK


@router.post(
    "/api/projects/{project_id}/optimize",
    response_model=JobAcceptedResponse,
    status_code=202,
)
def run_optimization(
    project_id: int,
    payload: OptimizationRequest,
    db: Session = Depends(get_db),
):
    """
    Start a multi-objective optimization for the project's shelter design.

    Returns immediately with a run_id. Poll /status for progress.
    """
    get_project_or_404(project_id, db)

    # Pre-flight validation
    validation = validate_project_for_simulation(project_id, db)
    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Project validation failed before optimization",
                "errors": [e.model_dump() for e in validation.errors],
            },
        )

    opt_run = OptimizationRun(
        project_id=project_id,
        objective_used=payload.objective,
        status=RunStatus.PENDING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(opt_run)
    db.commit()
    db.refresh(opt_run)

    try:
        mode = _launch_optimization(opt_run, project_id, payload.objective, db)
    except Exception as exc:
        opt_run.status        = RunStatus.FAILED
        opt_run.error_message = str(exc)[:1024]
        opt_run.completed_at  = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Optimization failed: {exc}")

    from app.core.config import settings
    return JobAcceptedResponse(
        run_id=opt_run.id,
        task_id=opt_run.task_id,
        status=RunStatus(opt_run.status),
        message="Optimization queued successfully" if settings.USE_BACKGROUND_JOBS else "Optimization completed",
        execution_mode=mode,
        poll_url=f"/api/optimization/{opt_run.id}/status",
    )


@router.get(
    "/api/optimization/{optimization_run_id}/status",
    response_model=JobStatus,
)
def get_optimization_status(optimization_run_id: int, db: Session = Depends(get_db)):
    """Poll optimization run status and progress."""
    opt_run = db.query(OptimizationRun).filter(OptimizationRun.id == optimization_run_id).first()
    if not opt_run:
        raise HTTPException(status_code=404, detail="Optimization run not found")

    progress = {
        RunStatus.PENDING:   0,
        RunStatus.QUEUED:    5,
        RunStatus.RUNNING:   50,
        RunStatus.COMPLETED: 100,
        RunStatus.FAILED:    0,
    }.get(RunStatus(opt_run.status), 0)

    return JobStatus(
        run_id=opt_run.id,
        task_id=opt_run.task_id,
        status=RunStatus(opt_run.status),
        progress=progress,
        message=opt_run.error_message or "",
        started_at=opt_run.started_at,
        completed_at=opt_run.completed_at,
        execution_mode=ExecutionMode(opt_run.execution_mode)
            if opt_run.execution_mode else ExecutionMode.SYNCHRONOUS_FALLBACK,
    )


@router.get(
    "/api/optimization/{optimization_run_id}/result",
    response_model=OptimizationRunDetailResponse,
)
def get_optimization_result(optimization_run_id: int, db: Session = Depends(get_db)):
    """Get the full optimization result with candidates and winner."""
    opt_run = db.query(OptimizationRun).filter(OptimizationRun.id == optimization_run_id).first()
    if not opt_run:
        raise HTTPException(status_code=404, detail="Optimization run not found")

    if opt_run.status == RunStatus.FAILED:
        raise HTTPException(status_code=422, detail=f"Optimization failed: {opt_run.error_message}")
    if opt_run.status in (RunStatus.PENDING, RunStatus.QUEUED, RunStatus.RUNNING):
        raise HTTPException(
            status_code=202,
            detail=f"Optimization is {opt_run.status}. Poll /status to check progress.",
        )

    winner = next((c for c in opt_run.candidates if c.is_winner), None)
    from app.schemas.optimization import OptimizationCandidateResponse
    return OptimizationRunDetailResponse(
        id=opt_run.id,
        project_id=opt_run.project_id,
        objective_used=opt_run.objective_used,  # type: ignore[arg-type]
        status=opt_run.status,  # type: ignore[arg-type]
        reasoning_text=opt_run.reasoning_text,
        error_message=opt_run.error_message,
        started_at=opt_run.started_at,
        completed_at=opt_run.completed_at,
        created_at=opt_run.created_at,
        winner=OptimizationCandidateResponse.model_validate(winner, from_attributes=True)
            if winner else None,
        candidates=[
            OptimizationCandidateResponse.model_validate(c, from_attributes=True)
            for c in opt_run.candidates
        ],
    )


@router.get(
    "/api/projects/{project_id}/comparison",
    response_model=ComparisonResult,
)
def get_project_comparison(project_id: int, db: Session = Depends(get_db)):
    """
    Compare baseline simulation vs optimized design.
    Requires at least one completed simulation and one completed optimization.
    """
    return get_comparison(project_id, db)


@router.get(
    "/api/projects/{project_id}/recommendation",
)
def get_project_recommendation(project_id: int, db: Session = Depends(get_db)):
    """
    Return a structured, data-grounded recommendation explaining the
    winning optimized design selection.
    """
    return get_recommendation(project_id, db)


@router.get(
    "/api/projects/{project_id}/validate",
    response_model=ValidationResult,
)
def validate_project(project_id: int, db: Session = Depends(get_db)):
    """
    Run pre-flight engineering validation on the project configuration.
    Returns errors and warnings without creating any runs.
    """
    return validate_project_for_simulation(project_id, db)
