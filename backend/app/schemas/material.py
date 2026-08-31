from datetime import datetime
from pydantic import BaseModel, Field


class MaterialBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., description="wall | roof | floor | insulation")
    thermal_conductivity: float = Field(..., gt=0, description="W/m·K")
    density: float = Field(..., gt=0, description="kg/m³")
    specific_heat: float = Field(..., gt=0, description="J/kg·K")
    cost_per_unit: float = Field(0.0, ge=0.0, description="Cost per m³ (local currency)")


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    category: str | None = None
    thermal_conductivity: float | None = Field(None, gt=0)
    density: float | None = Field(None, gt=0)
    specific_heat: float | None = Field(None, gt=0)
    cost_per_unit: float | None = Field(None, ge=0.0)


class MaterialResponse(MaterialBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
