from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.shelter import Shelter


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Thermal properties
    thermal_conductivity: Mapped[float] = mapped_column(Float, nullable=False)  # W/m·K
    density: Mapped[float] = mapped_column(Float, nullable=False)               # kg/m³
    specific_heat: Mapped[float] = mapped_column(Float, nullable=False)         # J/kg·K
    # Cost
    cost_per_unit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # ₹/m³
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Back-references from Shelter (wall/roof/floor)
    wall_shelters: Mapped[list["Shelter"]] = relationship(  # noqa: F821
        "Shelter", back_populates="wall_material", foreign_keys="Shelter.wall_material_id"
    )
    roof_shelters: Mapped[list["Shelter"]] = relationship(  # noqa: F821
        "Shelter", back_populates="roof_material", foreign_keys="Shelter.roof_material_id"
    )
    floor_shelters: Mapped[list["Shelter"]] = relationship(  # noqa: F821
        "Shelter", back_populates="floor_material", foreign_keys="Shelter.floor_material_id"
    )
