from datetime import datetime
from pydantic import BaseModel, Field


class ShelterBase(BaseModel):
    length: float = Field(..., gt=0, description="Shelter length in metres")
    width: float = Field(..., gt=0, description="Shelter width in metres")
    height: float = Field(..., gt=0, description="Shelter height in metres")

    wall_thickness: float = Field(..., gt=0, description="Wall thickness in metres")
    roof_thickness: float = Field(..., gt=0, description="Roof thickness in metres")
    floor_thickness: float = Field(..., gt=0, description="Floor thickness in metres")

    orientation_deg: float = Field(180.0, ge=0.0, le=360.0, description="Facing direction in degrees (0=N, 180=S)")
    window_area_m2: float = Field(0.0, ge=0.0, description="Total window area in m²")

    wall_material_id: int = Field(..., description="FK to Material")
    roof_material_id: int = Field(..., description="FK to Material")
    floor_material_id: int = Field(..., description="FK to Material")


class ShelterCreate(ShelterBase):
    pass


class ShelterUpdate(BaseModel):
    length: float | None = Field(None, gt=0)
    width: float | None = Field(None, gt=0)
    height: float | None = Field(None, gt=0)
    wall_thickness: float | None = Field(None, gt=0)
    roof_thickness: float | None = Field(None, gt=0)
    floor_thickness: float | None = Field(None, gt=0)
    orientation_deg: float | None = Field(None, ge=0.0, le=360.0)
    window_area_m2: float | None = Field(None, ge=0.0)
    wall_material_id: int | None = None
    roof_material_id: int | None = None
    floor_material_id: int | None = None


class ShelterResponse(ShelterBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
