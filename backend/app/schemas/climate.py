from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

ClimateModeType = Literal["preset", "custom"]


class ClimateProfileBase(BaseModel):
    location: str = Field(..., min_length=1, max_length=255)
    ambient_temp_c: float = Field(..., description="Ambient temperature in °C")
    solar_wm2: float = Field(..., ge=0.0, description="Solar irradiance in W/m²")
    wind_ms: float = Field(..., ge=0.0, description="Wind speed in m/s")
    humidity_pct: float = Field(..., ge=0.0, le=100.0, description="Relative humidity 0–100%")
    mode: ClimateModeType = Field("custom", description="'preset' or 'custom'")


class ClimateProfileCreate(ClimateProfileBase):
    pass


class ClimateProfileUpdate(BaseModel):
    location: str | None = Field(None, min_length=1, max_length=255)
    ambient_temp_c: float | None = None
    solar_wm2: float | None = Field(None, ge=0.0)
    wind_ms: float | None = Field(None, ge=0.0)
    humidity_pct: float | None = Field(None, ge=0.0, le=100.0)
    mode: ClimateModeType | None = None


class ClimateProfileResponse(ClimateProfileBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Climate preset (in-memory, not stored in DB) ─────────────────────────────

class ClimatePreset(BaseModel):
    id: str
    label: str
    location: str
    ambient_temp_c: float
    solar_wm2: float
    wind_ms: float
    humidity_pct: float
    mode: ClimateModeType
