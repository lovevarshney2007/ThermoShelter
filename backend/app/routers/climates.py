from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.init_db import CLIMATE_PRESETS
from app.models.project import Project
from app.models.climate import ClimateProfile
from app.schemas.climate import (
    ClimateProfileCreate,
    ClimateProfileUpdate,
    ClimateProfileResponse,
    ClimatePreset,
)

router = APIRouter(tags=["Climate"])


# ── Climate Presets (no project_id required) ─────────────────────────────────

@router.get("/api/climate-presets", response_model=list[ClimatePreset])
def get_climate_presets():
    """Return all available climate presets for selection in the frontend."""
    return CLIMATE_PRESETS


# ── Project-scoped climate endpoints ─────────────────────────────────────────

def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post(
    "/api/projects/{project_id}/climate",
    response_model=ClimateProfileResponse,
    status_code=201,
)
def create_or_update_climate(
    project_id: int,
    payload: ClimateProfileCreate,
    db: Session = Depends(get_db),
):
    """
    Create or update (upsert) a climate profile for the project.

    If the project already has a climate profile it will be updated rather
    than raising an error — this makes the frontend flow simpler.
    """
    _get_project_or_404(project_id, db)

    existing = (
        db.query(ClimateProfile).filter(ClimateProfile.project_id == project_id).first()
    )

    if existing:
        # Update existing record
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    # Create new
    climate = ClimateProfile(project_id=project_id, **payload.model_dump())
    db.add(climate)
    db.commit()
    db.refresh(climate)
    return climate


@router.get(
    "/api/projects/{project_id}/climate",
    response_model=ClimateProfileResponse,
)
def get_climate(project_id: int, db: Session = Depends(get_db)):
    """Return the climate profile for a project."""
    _get_project_or_404(project_id, db)
    climate = (
        db.query(ClimateProfile).filter(ClimateProfile.project_id == project_id).first()
    )
    if not climate:
        raise HTTPException(
            status_code=404, detail="Climate profile not found for this project"
        )
    return climate


@router.put(
    "/api/projects/{project_id}/climate",
    response_model=ClimateProfileResponse,
)
def update_climate(
    project_id: int,
    payload: ClimateProfileUpdate,
    db: Session = Depends(get_db),
):
    """Partially update a climate profile."""
    _get_project_or_404(project_id, db)
    climate = (
        db.query(ClimateProfile).filter(ClimateProfile.project_id == project_id).first()
    )
    if not climate:
        raise HTTPException(
            status_code=404, detail="Climate profile not found for this project"
        )
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(climate, field, value)
    db.commit()
    db.refresh(climate)
    return climate
