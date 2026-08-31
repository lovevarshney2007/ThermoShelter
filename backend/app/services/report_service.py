"""
Report Service (v2)
====================

Assembles a complete, structured project report using the v2 schema.
Integrates: project info, climate, shelter, materials, simulation results,
optimization results, comparison, recommendation, and metadata.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.project import Project
from app.models.material import Material
from app.schemas.report import (
    ProjectReport,
    ReportClimate,
    ReportShelter,
    ReportMaterial,
    ReportSimulation,
    ReportOptimization,
)
from app.schemas.contracts import SIMULATION_MODEL_VERSION, OPTIMIZATION_MODEL_VERSION


def _mat_report(mid: int | None, db: Session) -> "ReportMaterial | None":
    if not mid:
        return None
    m = db.query(Material).filter(Material.id == mid).first()
    if not m:
        return None
    from app.schemas.report import ReportMaterial
    return ReportMaterial(
        id=m.id, name=m.name, category=m.category,
        thermal_conductivity=m.thermal_conductivity,
        density=m.density, specific_heat=m.specific_heat,
        cost_per_unit=m.cost_per_unit,
    )


def generate_report(project_id: int, db: Session) -> ProjectReport:
    """
    Build a complete v2 project report.
    Also triggers comparison and recommendation services if data is available.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # ── Climate ───────────────────────────────────────────────────────────────
    report_climate = None
    if project.climate_profile:
        cp = project.climate_profile
        report_climate = ReportClimate(
            location=cp.location,
            ambient_temp_c=cp.ambient_temp_c,
            solar_wm2=cp.solar_wm2,
            wind_ms=cp.wind_ms,
            humidity_pct=cp.humidity_pct,
            mode=cp.mode,
            has_time_series=bool(cp.time_series_data),
        )

    # ── Shelter ───────────────────────────────────────────────────────────────
    report_shelter = None
    materials = {"wall": None, "roof": None, "floor": None}
    if project.shelter:
        s = project.shelter
        report_shelter = ReportShelter(
            length=s.length, width=s.width, height=s.height,
            wall_thickness=s.wall_thickness, roof_thickness=s.roof_thickness,
            floor_thickness=s.floor_thickness,
            orientation_deg=s.orientation_deg, window_area_m2=s.window_area_m2,
        )
        materials = {
            "wall":  _mat_report(s.wall_material_id, db),
            "roof":  _mat_report(s.roof_material_id, db),
            "floor": _mat_report(s.floor_material_id, db),
        }

    # ── Latest simulation ─────────────────────────────────────────────────────
    report_sim = None
    for sim_run in project.simulation_runs:
        if sim_run.status == "completed":
            r = sim_run.result
            report_sim = ReportSimulation(
                simulation_run_id=sim_run.id,
                status=sim_run.status,
                model_version=sim_run.model_version,
                heating_kwh=r.heating_kwh if r else None,
                cooling_kwh=r.cooling_kwh if r else None,
                total_energy_kwh=r.total_energy_kwh if r else None,
                min_indoor_temp_c=r.min_indoor_temp_c if r else None,
                max_indoor_temp_c=r.max_indoor_temp_c if r else None,
                hours_below_comfort=r.hours_below_comfort if r else None,
                hours_above_comfort=r.hours_above_comfort if r else None,
                execution_mode=r.execution_mode if r else None,
                completed_at=sim_run.completed_at,
            )
            break

    # ── Latest optimization ───────────────────────────────────────────────────
    report_opt = None
    for opt_run in project.optimization_runs:
        if opt_run.status == "completed":
            winner = next((c for c in opt_run.candidates if c.is_winner), None)
            report_opt = ReportOptimization(
                optimization_run_id=opt_run.id,
                status=opt_run.status,
                objective_used=opt_run.objective_used,
                reasoning_text=opt_run.reasoning_text,
                winner_config=winner.config if winner else None,
                winner_score=winner.score if winner else None,
                candidate_count=len(opt_run.candidates),
                execution_mode=opt_run.execution_mode,
                completed_at=opt_run.completed_at,
            )
            break

    # ── Comparison ────────────────────────────────────────────────────────────
    comparison = None
    if report_opt:
        try:
            from app.services.comparison_service import get_comparison
            comparison = get_comparison(project_id, db)
        except Exception:
            pass

    # ── Recommendation ────────────────────────────────────────────────────────
    recommendation = None
    if report_opt:
        try:
            from app.services.recommendation_service import get_recommendation
            recommendation = get_recommendation(project_id, db)
        except Exception:
            pass

    return ProjectReport(
        schema_version="2.0",
        generated_at=datetime.now(timezone.utc),
        project={
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        },
        climate=report_climate,
        shelter=report_shelter,
        materials=materials,
        latest_simulation=report_sim,
        latest_optimization=report_opt,
        comparison=comparison,
        recommendation=recommendation,
        metadata={
            "simulation_model_version":   SIMULATION_MODEL_VERSION,
            "optimization_model_version": OPTIMIZATION_MODEL_VERSION,
            "has_background_jobs": False,
        },
    )
