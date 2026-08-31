from datetime import datetime
from sqlalchemy import Float, ForeignKey, DateTime, func
from sqlalchemy import String
from app.utils.db_types import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class ClimateProfile(Base):
    __tablename__ = "climate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    ambient_temp_c: Mapped[float] = mapped_column(Float, nullable=False)
    solar_wm2: Mapped[float] = mapped_column(Float, nullable=False)
    wind_ms: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="custom")

    # Time-series support: optional JSON array of hourly climate snapshots
    # Each element: {hour: int, temp_c: float, solar_wm2: float, wind_ms: float, humidity_pct: float}
    time_series_data: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment="Optional hourly time-series data for transient simulation replay"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="climate_profile")  # noqa: F821
