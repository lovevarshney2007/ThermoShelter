from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | running | completed | failed
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="simulation_runs")  # noqa: F821
    result: Mapped["SimulationResult"] = relationship(
        "SimulationResult", back_populates="simulation_run",
        uselist=False, cascade="all, delete-orphan"
    )


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    simulation_run_id: Mapped[int] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Time-series data stored as JSONB arrays
    timestamps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    indoor_temperatures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Heat flow components (JSONB arrays)
    conduction_data: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    convection_data: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    radiation_data: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    solar_data: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Summary energy metrics
    heating_kwh: Mapped[float] = mapped_column(nullable=False, default=0.0)
    cooling_kwh: Mapped[float] = mapped_column(nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    simulation_run: Mapped["SimulationRun"] = relationship(
        "SimulationRun", back_populates="result"
    )
