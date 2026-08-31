"""
Report Service
==============

Assembles a complete project report snapshot from all related data.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.project import Project
from app.models.material import Material


def generate_report(project_id: int, db: Session) -> dict:
    """
    Build and return a full structured project report as a dict.

    Raises 404 if the project does not exist.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # ── Climate ───────────────────────────────────────────────────────────────
    climate_data = None
    if project.climate_profile:
        cp = project.climate_profile
        climate_data = {
            "id": cp.id,
            "location": cp.location,
            "ambient_temp_c": cp.ambient_temp_c,
            "solar_wm2": cp.solar_wm2,
            "wind_ms": cp.wind_ms,
            "humidity_pct": cp.humidity_pct,
            "mode": cp.mode,
        }

    # ── Shelter + materials ───────────────────────────────────────────────────
    shelter_data = None
    materials_used = {}
    if project.shelter:
        s = project.shelter
        shelter_data = {
            "id": s.id,
            "length": s.length,
            "width": s.width,
            "height": s.height,
            "wall_thickness": s.wall_thickness,
            "roof_thickness": s.roof_thickness,
            "floor_thickness": s.floor_thickness,
            "orientation_deg": s.orientation_deg,
            "window_area_m2": s.window_area_m2,
            "wall_material_id": s.wall_material_id,
            "roof_material_id": s.roof_material_id,
            "floor_material_id": s.floor_material_id,
        }

        def _mat(mid: int) -> dict | None:
            m = db.query(Material).filter(Material.id == mid).first()
            if not m:
                return None
            return {
                "id": m.id, "name": m.name, "category": m.category,
                "thermal_conductivity": m.thermal_conductivity,
                "density": m.density, "specific_heat": m.specific_heat,
                "cost_per_unit": m.cost_per_unit,
            }

        materials_used = {
            "wall": _mat(s.wall_material_id),
            "roof": _mat(s.roof_material_id),
            "floor": _mat(s.floor_material_id),
        }

    # ── Latest simulation ─────────────────────────────────────────────────────
    latest_simulation = None
    latest_simulation_result = None
    if project.simulation_runs:
        sim_run = project.simulation_runs[0]  # ordered by created_at desc
        latest_simulation = {
            "id": sim_run.id,
            "status": sim_run.status,
            "model_version": sim_run.model_version,
            "started_at": sim_run.started_at.isoformat() if sim_run.started_at else None,
            "completed_at": sim_run.completed_at.isoformat() if sim_run.completed_at else None,
            "created_at": sim_run.created_at.isoformat(),
        }
        if sim_run.result:
            r = sim_run.result
            latest_simulation_result = {
                "id": r.id,
                "timestamps": r.timestamps,
                "indoor_temperatures": r.indoor_temperatures,
                "heating_kwh": r.heating_kwh,
                "cooling_kwh": r.cooling_kwh,
                "heat_flow": {
                    "conduction": r.conduction_data,
                    "convection": r.convection_data,
                    "radiation": r.radiation_data,
                    "solar": r.solar_data,
                },
            }

    # ── Latest optimization ───────────────────────────────────────────────────
    latest_optimization = None
    winning_candidate = None
    if project.optimization_runs:
        opt_run = project.optimization_runs[0]  # ordered by created_at desc
        latest_optimization = {
            "id": opt_run.id,
            "objective_used": opt_run.objective_used,
            "status": opt_run.status,
            "reasoning_text": opt_run.reasoning_text,
            "started_at": opt_run.started_at.isoformat() if opt_run.started_at else None,
            "completed_at": opt_run.completed_at.isoformat() if opt_run.completed_at else None,
            "created_at": opt_run.created_at.isoformat(),
        }
        for cand in opt_run.candidates:
            if cand.is_winner:
                winning_candidate = {
                    "id": cand.id,
                    "config": cand.config,
                    "score": cand.score,
                    "comfort_score": cand.comfort_score,
                    "energy_score": cand.energy_score,
                    "cost_score": cand.cost_score,
                }
                break

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        },
        "climate_profile": climate_data,
        "shelter_configuration": shelter_data,
        "materials_used": materials_used,
        "latest_simulation": latest_simulation,
        "latest_simulation_result": latest_simulation_result,
        "latest_optimization": latest_optimization,
        "winning_configuration": winning_candidate,
        "optimization_reasoning": (
            project.optimization_runs[0].reasoning_text
            if project.optimization_runs else None
        ),
    }
