from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.project import Project
from app.models.simulation import SimulationRun, SimulationResult
from app.models.material import Material
from app.schemas.simulation import (
    SimulationRunResponse,
    SimulationRunDetailResponse,
)
from app.services.simulation_service import run_simulation
from app.utils.helpers import model_to_dict

router = APIRouter(tags=["Simulation"])


def _build_materials_dict(shelter, db: Session) -> dict:
    """Fetch wall/roof/floor materials and return as dicts keyed by role."""
    result = {}
    for role, mid in [
        ("wall", shelter.wall_material_id),
        ("roof", shelter.roof_material_id),
        ("floor", shelter.floor_material_id),
    ]:
        mat = db.query(Material).filter(Material.id == mid).first()
        if mat:
            result[role] = model_to_dict(mat)
    return result


@router.post(
    "/api/projects/{project_id}/simulate",
    response_model=SimulationRunDetailResponse,
    status_code=201,
)
def run_project_simulation(project_id: int, db: Session = Depends(get_db)):
    """
    Run a full thermal simulation for the project.

    Prerequisites:
    - Project must exist
    - Climate profile must be configured
    - Shelter must be configured with valid materials
    """
    # 1. Fetch project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Validate prerequisites
    if not project.climate_profile:
        raise HTTPException(
            status_code=422,
            detail="Climate profile is required before running simulation",
        )
    if not project.shelter:
        raise HTTPException(
            status_code=422,
            detail="Shelter configuration is required before running simulation",
        )

    # 3. Create SimulationRun record (status=running)
    sim_run = SimulationRun(
        project_id=project_id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(sim_run)
    db.commit()
    db.refresh(sim_run)

    try:
        # 4. Prepare inputs
        climate_data = model_to_dict(project.climate_profile)
        shelter_data = model_to_dict(project.shelter)
        materials_data = _build_materials_dict(project.shelter, db)

        # 5. Call simulation service
        output = run_simulation(climate_data, shelter_data, materials_data)

        # 6. Save result
        result = SimulationResult(
            simulation_run_id=sim_run.id,
            timestamps=output.timestamps,
            indoor_temperatures=output.indoor_temperatures,
            conduction_data=output.conduction_data,
            convection_data=output.convection_data,
            radiation_data=output.radiation_data,
            solar_data=output.solar_data,
            heating_kwh=output.heating_kwh,
            cooling_kwh=output.cooling_kwh,
        )
        db.add(result)

        # 7. Update run status
        sim_run.status = "completed"
        sim_run.completed_at = datetime.now(timezone.utc)
        sim_run.model_version = output.model_version
        db.commit()
        db.refresh(sim_run)

    except Exception as exc:
        sim_run.status = "failed"
        sim_run.error_message = str(exc)[:1024]
        sim_run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {exc}",
        )

    # 8. Return full detail (run + result)
    db.refresh(sim_run)
    return sim_run


@router.get(
    "/api/projects/{project_id}/simulations",
    response_model=list[SimulationRunResponse],
)
def list_project_simulations(project_id: int, db: Session = Depends(get_db)):
    """Return all simulation runs for a project (most recent first)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
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
    """Return a single simulation run with its full result."""
    sim_run = db.query(SimulationRun).filter(SimulationRun.id == simulation_run_id).first()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return sim_run
