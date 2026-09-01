"""Add v2 fields: task_id, execution_mode, ambient_temps, energy totals,
comfort metrics, comparison_data, baseline_data, time_series_data.

Revision ID: 002_v2_architecture
Revises: 001_initial
Create Date: 2026-08-31
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "002_v2_architecture"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── simulation_runs ───────────────────────────────────────────────────────
    op.add_column("simulation_runs",
        sa.Column("task_id", sa.String(255), nullable=True))
    op.add_column("simulation_runs",
        sa.Column("execution_mode", sa.String(50), nullable=True))

    # Update status CHECK to include 'queued'
    # (PostgreSQL doesn't have native enum constraints here; string column is flexible)

    # ── simulation_results ────────────────────────────────────────────────────
    op.add_column("simulation_results",
        sa.Column("ambient_temperatures", JSONB(), nullable=True, server_default="[]"))
    op.add_column("simulation_results",
        sa.Column("total_energy_kwh", sa.Float(), nullable=False, server_default="0.0"))
    op.add_column("simulation_results",
        sa.Column("hours_below_comfort", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("simulation_results",
        sa.Column("hours_above_comfort", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("simulation_results",
        sa.Column("min_indoor_temp_c", sa.Float(), nullable=True))
    op.add_column("simulation_results",
        sa.Column("max_indoor_temp_c", sa.Float(), nullable=True))
    op.add_column("simulation_results",
        sa.Column("execution_mode", sa.String(50), nullable=True))
    op.add_column("simulation_results",
        sa.Column("validation_status", sa.String(20), nullable=False, server_default="valid"))

    # ── optimization_runs ─────────────────────────────────────────────────────
    op.add_column("optimization_runs",
        sa.Column("task_id", sa.String(255), nullable=True))
    op.add_column("optimization_runs",
        sa.Column("execution_mode", sa.String(50), nullable=True))
    op.add_column("optimization_runs",
        sa.Column("comparison_data", JSONB(), nullable=True))
    op.add_column("optimization_runs",
        sa.Column("baseline_data", JSONB(), nullable=True))

    # ── climate_profiles ──────────────────────────────────────────────────────
    op.add_column("climate_profiles",
        sa.Column("time_series_data", JSONB(), nullable=True))


def downgrade() -> None:
    # climate
    op.drop_column("climate_profiles", "time_series_data")
    # optimization
    op.drop_column("optimization_runs", "baseline_data")
    op.drop_column("optimization_runs", "comparison_data")
    op.drop_column("optimization_runs", "execution_mode")
    op.drop_column("optimization_runs", "task_id")
    # simulation results
    op.drop_column("simulation_results", "validation_status")
    op.drop_column("simulation_results", "execution_mode")
    op.drop_column("simulation_results", "max_indoor_temp_c")
    op.drop_column("simulation_results", "min_indoor_temp_c")
    op.drop_column("simulation_results", "hours_above_comfort")
    op.drop_column("simulation_results", "hours_below_comfort")
    op.drop_column("simulation_results", "total_energy_kwh")
    op.drop_column("simulation_results", "ambient_temperatures")
    # simulation runs
    op.drop_column("simulation_runs", "execution_mode")
    op.drop_column("simulation_runs", "task_id")
