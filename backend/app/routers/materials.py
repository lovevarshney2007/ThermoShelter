from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.models.material import Material
from app.schemas.material import MaterialCreate, MaterialUpdate, MaterialResponse

router = APIRouter(prefix="/api/materials", tags=["Materials"])


@router.get("", response_model=list[MaterialResponse])
def list_materials(
    category: Optional[str] = Query(None, description="Filter by category: wall|roof|floor|insulation"),
    db: Session = Depends(get_db),
):
    """Return all materials, optionally filtered by category."""
    query = db.query(Material)
    if category:
        query = query.filter(Material.category == category)
    return query.order_by(Material.category, Material.name).all()


@router.get("/{material_id}", response_model=MaterialResponse)
def get_material(material_id: int, db: Session = Depends(get_db)):
    """Return a single material by ID."""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@router.post("", response_model=MaterialResponse, status_code=201)
def create_material(payload: MaterialCreate, db: Session = Depends(get_db)):
    """Create a new material entry."""
    # Check for name collision
    existing = db.query(Material).filter(Material.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Material with name '{payload.name}' already exists"
        )
    material = Material(**payload.model_dump())
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.put("/{material_id}", response_model=MaterialResponse)
def update_material(material_id: int, payload: MaterialUpdate, db: Session = Depends(get_db)):
    """Update an existing material."""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(material, field, value)
    db.commit()
    db.refresh(material)
    return material
