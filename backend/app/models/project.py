from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships (one-to-one and one-to-many)
    climate_profile: Mapped["ClimateProfile"] = relationship(  # noqa: F821
        "ClimateProfile", back_populates="project", uselist=False,
        cascade="all, delete-orphan"
    )
    shelter: Mapped["Shelter"] = relationship(  # noqa: F821
        "Shelter", back_populates="project", uselist=False,
        cascade="all, delete-orphan"
    )
    simulation_runs: Mapped[list["SimulationRun"]] = relationship(  # noqa: F821
        "SimulationRun", back_populates="project",
        cascade="all, delete-orphan", order_by="SimulationRun.created_at.desc()"
    )
    optimization_runs: Mapped[list["OptimizationRun"]] = relationship(  # noqa: F821
        "OptimizationRun", back_populates="project",
        cascade="all, delete-orphan", order_by="OptimizationRun.created_at.desc()"
    )
