from datetime import datetime
from sqlalchemy import Float, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Shelter(Base):
    __tablename__ = "shelters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Dimensions (metres)
    length: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)

    # Thicknesses (metres)
    wall_thickness: Mapped[float] = mapped_column(Float, nullable=False)
    roof_thickness: Mapped[float] = mapped_column(Float, nullable=False)
    floor_thickness: Mapped[float] = mapped_column(Float, nullable=False)

    # Geometry
    orientation_deg: Mapped[float] = mapped_column(Float, nullable=False, default=180.0)
    window_area_m2: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Material foreign keys
    wall_material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False)
    roof_material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False)
    floor_material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="shelter")  # noqa: F821
    wall_material: Mapped["Material"] = relationship(  # noqa: F821
        "Material", back_populates="wall_shelters", foreign_keys=[wall_material_id]
    )
    roof_material: Mapped["Material"] = relationship(  # noqa: F821
        "Material", back_populates="roof_shelters", foreign_keys=[roof_material_id]
    )
    floor_material: Mapped["Material"] = relationship(  # noqa: F821
        "Material", back_populates="floor_shelters", foreign_keys=[floor_material_id]
    )
