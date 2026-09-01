from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, DateTime, Float, func
from app.utils.db_types import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="2.0")
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)   # Celery task ID
    execution_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
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
    ambient_temperatures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Heat flow components (JSONB arrays)
    conduction_data: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    convection_data: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    radiation_data: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    solar_data: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Energy summary
    heating_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cooling_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Comfort metrics
    hours_below_comfort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hours_above_comfort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_indoor_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_indoor_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Traceability
    execution_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="valid")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    simulation_run: Mapped["SimulationRun"] = relationship(
        "SimulationRun", back_populates="result"
    )
