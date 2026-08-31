from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.project import Project
from app.models.material import Material
from app.models.optimization import OptimizationRun, OptimizationCandidate
from app.schemas.optimization import (
    OptimizationRequest,
    OptimizationRunDetailResponse,
)
from app.services.optimization_service import optimize_design
from app.utils.helpers import model_to_dict

router = APIRouter(tags=["Optimization"])


@router.post(
    "/api/projects/{project_id}/optimize",
    response_model=OptimizationRunDetailResponse,
    status_code=201,
)
def run_optimization(
    project_id: int,
    payload: OptimizationRequest,
    db: Session = Depends(get_db),
):
    """
    Run a multi-objective optimisation for the project's shelter configuration.

    Prerequisites:
    - Project, Climate profile, and Shelter must all be configured.
    """
    # 1. Fetch project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.climate_profile:
        raise HTTPException(
            status_code=422,
            detail="Climate profile is required before running optimization",
        )
    if not project.shelter:
        raise HTTPException(
            status_code=422,
            detail="Shelter configuration is required before running optimization",
        )

    # 2. Create OptimizationRun
    opt_run = OptimizationRun(
        project_id=project_id,
        objective_used=payload.objective,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(opt_run)
    db.commit()
    db.refresh(opt_run)

    try:
        climate_data = model_to_dict(project.climate_profile)
        shelter_data = model_to_dict(project.shelter)

        # Current selected materials
        def _mat(mid: int) -> dict:
            m = db.query(Material).filter(Material.id == mid).first()
            return model_to_dict(m) if m else {}

        s = project.shelter
        materials_data = {
            "wall": _mat(s.wall_material_id),
            "roof": _mat(s.roof_material_id),
            "floor": _mat(s.floor_material_id),
        }

        # All materials for candidate generation
        all_materials = [model_to_dict(m) for m in db.query(Material).all()]

        # 3. Run optimization
        output = optimize_design(
            climate_data, shelter_data, materials_data, payload.objective, all_materials
        )

        # 4. Save candidates
        for cand in output.candidates:
            db_cand = OptimizationCandidate(
                optimization_run_id=opt_run.id,
                config=cand.config,
                score=cand.score,
                comfort_score=cand.comfort_score,
                energy_score=cand.energy_score,
                cost_score=cand.cost_score,
                is_winner=cand.is_winner,
            )
            db.add(db_cand)

        # 5. Finalise run
        opt_run.status = "completed"
        opt_run.reasoning_text = output.reasoning_text
        opt_run.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(opt_run)

    except Exception as exc:
        opt_run.status = "failed"
        opt_run.error_message = str(exc)[:1024]
        opt_run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Optimization failed: {exc}")

    # 6. Build response
    db.refresh(opt_run)
    winner = next((c for c in opt_run.candidates if c.is_winner), None)
    return OptimizationRunDetailResponse(
        id=opt_run.id,
        project_id=opt_run.project_id,
        objective_used=opt_run.objective_used,
        status=opt_run.status,
        reasoning_text=opt_run.reasoning_text,
        error_message=opt_run.error_message,
        started_at=opt_run.started_at,
        completed_at=opt_run.completed_at,
        created_at=opt_run.created_at,
        winner=winner,
        candidates=list(opt_run.candidates),
    )
