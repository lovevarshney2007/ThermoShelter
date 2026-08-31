"""
Optimization Background Tasks
==============================

Celery tasks that execute multi-objective optimization asynchronously.

Flow:
  FastAPI → queue_optimization_task() → Redis → execute_optimization() → PostgreSQL
"""

from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.core.constants import RunStatus


@celery_app.task(
    bind=True,
    name="optimization_tasks.execute_optimization",
    max_retries=2,
    default_retry_delay=10,
)
def execute_optimization(self, optimization_run_id: int) -> dict:
    """
    Execute optimization for the given run ID.

    Fetches project data, runs the optimization engine,
    saves candidates + winner, updates run status.
    """
    from app.database.session import SessionLocal
    from app.models.optimization import OptimizationRun, OptimizationCandidate
    from app.services.project_service import build_optimization_request
    from app.scientific_engine.optimization.engine import run_optimization

    db = SessionLocal()
    try:
        opt_run = db.query(OptimizationRun).filter(
            OptimizationRun.id == optimization_run_id
        ).first()
        if not opt_run:
            return {"error": f"OptimizationRun {optimization_run_id} not found"}

        # Mark as running
        opt_run.status     = RunStatus.RUNNING
        opt_run.started_at = datetime.now(timezone.utc)
        db.commit()

        # Build request
        request = build_optimization_request(
            opt_run.project_id, optimization_run_id, opt_run.objective_used, db
        )

        # Run optimization engine
        result = run_optimization(request)

        # Save candidates
        for cand in result.candidates:
            db.add(OptimizationCandidate(
                optimization_run_id=optimization_run_id,
                config=cand.config,
                score=cand.score,
                energy_score=cand.energy_score,
                comfort_score=cand.comfort_score,
                cost_score=cand.cost_score,
                is_winner=cand.is_winner,
            ))

        # Save comparison as JSON on the run
        comparison_dict = result.comparison.model_dump() if result.comparison else None
        baseline_dict   = result.baseline.model_dump()   if result.baseline   else None

        opt_run.status        = RunStatus.COMPLETED
        opt_run.completed_at  = datetime.now(timezone.utc)
        opt_run.reasoning_text = result.reasoning_text
        opt_run.comparison_data = comparison_dict
        opt_run.baseline_data   = baseline_dict
        opt_run.execution_mode  = result.execution_mode.value
        db.commit()

        return {"optimization_run_id": optimization_run_id, "status": RunStatus.COMPLETED}

    except Exception as exc:
        db.query(OptimizationRun).filter(OptimizationRun.id == optimization_run_id).update({
            "status": RunStatus.FAILED,
            "error_message": str(exc)[:1024],
            "completed_at": datetime.now(timezone.utc),
        })
        db.commit()
        raise self.retry(exc=exc)

    finally:
        db.close()
