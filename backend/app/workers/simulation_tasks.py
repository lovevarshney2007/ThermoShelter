"""
Simulation Background Tasks
============================

Celery tasks that execute thermal simulations asynchronously.

Flow:
  FastAPI → queue_simulation_task() → Redis → execute_simulation() → PostgreSQL
"""

from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.core.constants import RunStatus


@celery_app.task(
    bind=True,
    name="simulation_tasks.execute_simulation",
    max_retries=2,
    default_retry_delay=10,
)
def execute_simulation(self, simulation_run_id: int) -> dict:
    """
    Execute thermal simulation for the given run ID.

    Fetches project data from DB, runs the scientific engine,
    saves result, updates run status.
    """
    # Import inside task to avoid circular imports at module load time
    from app.database.session import SessionLocal
    from app.models.simulation import SimulationRun, SimulationResult
    from app.models.material import Material
    from app.services.project_service import build_simulation_request
    from app.scientific_engine.physics.engine import run_transient_simulation

    db = SessionLocal()
    try:
        sim_run = db.query(SimulationRun).filter(SimulationRun.id == simulation_run_id).first()
        if not sim_run:
            return {"error": f"SimulationRun {simulation_run_id} not found"}

        # Mark as running
        sim_run.status = RunStatus.RUNNING
        sim_run.started_at = datetime.now(timezone.utc)
        db.commit()

        # Build typed request
        request = build_simulation_request(sim_run.project_id, simulation_run_id, db)

        # Run the scientific engine
        result = run_transient_simulation(request)

        # Persist result
        db_result = db.query(SimulationResult).filter(
            SimulationResult.simulation_run_id == simulation_run_id
        ).first()

        if not db_result:
            db_result = SimulationResult(simulation_run_id=simulation_run_id)
            db.add(db_result)

        db_result.timestamps           = result.timestamps
        db_result.indoor_temperatures  = result.indoor_temp_c
        db_result.conduction_data      = result.heat_flow.conduction
        db_result.convection_data      = result.heat_flow.convection
        db_result.radiation_data       = result.heat_flow.radiation
        db_result.solar_data           = result.heat_flow.solar
        db_result.heating_kwh          = result.heating_kwh
        db_result.cooling_kwh          = result.cooling_kwh
        db_result.total_energy_kwh     = result.total_energy_kwh
        db_result.ambient_temperatures = result.ambient_temp_c
        db_result.hours_below_comfort  = result.hours_below_comfort
        db_result.hours_above_comfort  = result.hours_above_comfort
        db_result.min_indoor_temp_c    = result.min_indoor_temp_c
        db_result.max_indoor_temp_c    = result.max_indoor_temp_c
        db_result.execution_mode       = result.execution_mode.value

        sim_run.status        = RunStatus.COMPLETED
        sim_run.completed_at  = datetime.now(timezone.utc)
        sim_run.model_version = result.model_version
        db.commit()

        return {"simulation_run_id": simulation_run_id, "status": RunStatus.COMPLETED}

    except Exception as exc:
        db.query(SimulationRun).filter(SimulationRun.id == simulation_run_id).update({
            "status": RunStatus.FAILED,
            "error_message": str(exc)[:1024],
            "completed_at": datetime.now(timezone.utc),
        })
        db.commit()
        raise self.retry(exc=exc)

    finally:
        db.close()
