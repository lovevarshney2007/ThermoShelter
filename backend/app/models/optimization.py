from datetime import datetime
from sqlalchemy import String, Float, Boolean, Integer, ForeignKey, DateTime, Text, func
from app.utils.db_types import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    objective_used: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)   # Celery task ID
    execution_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reasoning_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Comparison and baseline data stored as JSONB
    comparison_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    baseline_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="optimization_runs")  # noqa: F821
    candidates: Mapped[list["OptimizationCandidate"]] = relationship(
        "OptimizationCandidate", back_populates="optimization_run",
        cascade="all, delete-orphan", order_by="OptimizationCandidate.score.desc()"
    )


class OptimizationCandidate(Base):
    __tablename__ = "optimization_candidates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    optimization_run_id: Mapped[int] = mapped_column(
        ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    comfort_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    energy_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_winner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    optimization_run: Mapped["OptimizationRun"] = relationship(
        "OptimizationRun", back_populates="candidates"
    )
