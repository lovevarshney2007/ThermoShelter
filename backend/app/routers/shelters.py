from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.project import Project
from app.models.shelter import Shelter
from app.models.material import Material
from app.schemas.shelter import ShelterCreate, ShelterUpdate, ShelterResponse

router = APIRouter(tags=["Shelter"])


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _validate_materials(payload_dict: dict, db: Session) -> None:
    """Ensure all referenced material IDs exist in the database."""
    for key in ("wall_material_id", "roof_material_id", "floor_material_id"):
        mid = payload_dict.get(key)
        if mid is not None:
            mat = db.query(Material).filter(Material.id == mid).first()
            if not mat:
                raise HTTPException(
                    status_code=422,
                    detail=f"Material with id={mid} ({key}) does not exist",
                )


@router.post(
    "/api/projects/{project_id}/shelter",
    response_model=ShelterResponse,
    status_code=201,
)
def create_or_update_shelter(
    project_id: int,
    payload: ShelterCreate,
    db: Session = Depends(get_db),
):
    """
    Create or update (upsert) a shelter configuration for the project.

    Material IDs must reference existing materials.
    """
    _get_project_or_404(project_id, db)
    _validate_materials(payload.model_dump(), db)

    existing = db.query(Shelter).filter(Shelter.project_id == project_id).first()
    if existing:
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    shelter = Shelter(project_id=project_id, **payload.model_dump())
    db.add(shelter)
    db.commit()
    db.refresh(shelter)
    return shelter


@router.get(
    "/api/projects/{project_id}/shelter",
    response_model=ShelterResponse,
)
def get_shelter(project_id: int, db: Session = Depends(get_db)):
    """Return the shelter configuration for a project."""
    _get_project_or_404(project_id, db)
    shelter = db.query(Shelter).filter(Shelter.project_id == project_id).first()
    if not shelter:
        raise HTTPException(
            status_code=404, detail="Shelter configuration not found for this project"
        )
    return shelter


@router.put(
    "/api/projects/{project_id}/shelter",
    response_model=ShelterResponse,
)
def update_shelter(
    project_id: int,
    payload: ShelterUpdate,
    db: Session = Depends(get_db),
):
    """Partially update a shelter configuration."""
    _get_project_or_404(project_id, db)
    shelter = db.query(Shelter).filter(Shelter.project_id == project_id).first()
    if not shelter:
        raise HTTPException(
            status_code=404, detail="Shelter configuration not found for this project"
        )
    update_data = payload.model_dump(exclude_none=True)
    _validate_materials(update_data, db)
    for field, value in update_data.items():
        setattr(shelter, field, value)
    db.commit()
    db.refresh(shelter)
    return shelter
