"""
Project Service
===============

Orchestration helpers used by routers and Celery workers alike.

Functions here assemble typed scientific-engine request objects from DB data,
keeping that logic OUT of routers and OUT of workers.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.project import Project
from app.models.material import Material
from app.schemas.contracts import (
    SimulationRequest,
    OptimizationRequest,
    ClimateInput,
    ShelterInput,
    MaterialInput,
)
from app.core.constants import OptimizationObjective
from app.utils.helpers import model_to_dict


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _material_input(material_id: int, db: Session) -> MaterialInput:
    mat = db.query(Material).filter(Material.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=422, detail=f"Material id={material_id} not found")
    return MaterialInput(
        id=mat.id,
        name=mat.name,
        category=mat.category,
        thermal_conductivity=mat.thermal_conductivity,
        density=mat.density,
        specific_heat=mat.specific_heat,
        cost_per_unit=mat.cost_per_unit,
    )


def _climate_input(project: Project) -> ClimateInput:
    cp = project.climate_profile
    return ClimateInput(
        location=cp.location,
        ambient_temp_c=cp.ambient_temp_c,
        solar_wm2=cp.solar_wm2,
        wind_ms=cp.wind_ms,
        humidity_pct=cp.humidity_pct,
        mode=cp.mode,
        time_series_data=cp.time_series_data or [],
    )


def _shelter_input(project: Project, db: Session) -> ShelterInput:
    s = project.shelter
    return ShelterInput(
        length=s.length,
        width=s.width,
        height=s.height,
        wall_thickness=s.wall_thickness,
        roof_thickness=s.roof_thickness,
        floor_thickness=s.floor_thickness,
        orientation_deg=s.orientation_deg,
        window_area_m2=s.window_area_m2,
        wall_material=_material_input(s.wall_material_id, db),
        roof_material=_material_input(s.roof_material_id, db),
        floor_material=_material_input(s.floor_material_id, db),
    )


def build_simulation_request(
    project_id: int,
    simulation_run_id: int,
    db: Session,
) -> SimulationRequest:
    """
    Build a fully typed SimulationRequest from database records.
    Used by both the router (sync path) and the Celery task (async path).
    """
    project = get_project_or_404(project_id, db)
    return SimulationRequest(
        project_id=project_id,
        simulation_run_id=simulation_run_id,
        climate=_climate_input(project),
        shelter=_shelter_input(project, db),
    )


def build_optimization_request(
    project_id: int,
    optimization_run_id: int,
    objective: str,
    db: Session,
) -> OptimizationRequest:
    """
    Build a fully typed OptimizationRequest from database records.
    Used by both the router (sync path) and the Celery task (async path).
    """
    project = get_project_or_404(project_id, db)
    all_materials = [
        MaterialInput(
            id=m.id,
            name=m.name,
            category=m.category,
            thermal_conductivity=m.thermal_conductivity,
            density=m.density,
            specific_heat=m.specific_heat,
            cost_per_unit=m.cost_per_unit,
        )
        for m in db.query(Material).all()
    ]
    return OptimizationRequest(
        project_id=project_id,
        optimization_run_id=optimization_run_id,
        climate=_climate_input(project),
        shelter=_shelter_input(project, db),
        objective=OptimizationObjective(objective),
        available_materials=all_materials,
    )
