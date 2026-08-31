from datetime import datetime
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class ClimateProfile(Base):
    __tablename__ = "climate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    ambient_temp_c: Mapped[float] = mapped_column(Float, nullable=False)   # °C
    solar_wm2: Mapped[float] = mapped_column(Float, nullable=False)        # W/m²
    wind_ms: Mapped[float] = mapped_column(Float, nullable=False)          # m/s
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)     # 0–100 %
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="custom")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="climate_profile")  # noqa: F821
