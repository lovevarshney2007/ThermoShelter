"""Initial schema — all ThermoShelter tables.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-08-31

Tables created:
  - materials
  - projects
  - climate_profiles
  - shelters
  - simulation_runs
  - simulation_results
  - optimization_runs
  - optimization_candidates
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── materials ─────────────────────────────────────────────────────────────
    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("thermal_conductivity", sa.Float(), nullable=False),
        sa.Column("density", sa.Float(), nullable=False),
        sa.Column("specific_heat", sa.Float(), nullable=False),
        sa.Column("cost_per_unit", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_materials_category", "materials", ["category"])
    op.create_index("ix_materials_id", "materials", ["id"])

    # ── projects ──────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_projects_id", "projects", ["id"])

    # ── climate_profiles ──────────────────────────────────────────────────────
    op.create_table(
        "climate_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("ambient_temp_c", sa.Float(), nullable=False),
        sa.Column("solar_wm2", sa.Float(), nullable=False),
        sa.Column("wind_ms", sa.Float(), nullable=False),
        sa.Column("humidity_pct", sa.Float(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False, server_default="custom"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_climate_profiles_id", "climate_profiles", ["id"])
    op.create_index("ix_climate_profiles_project_id", "climate_profiles", ["project_id"])

    # ── shelters ──────────────────────────────────────────────────────────────
    op.create_table(
        "shelters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("length", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("wall_thickness", sa.Float(), nullable=False),
        sa.Column("roof_thickness", sa.Float(), nullable=False),
        sa.Column("floor_thickness", sa.Float(), nullable=False),
        sa.Column("orientation_deg", sa.Float(), nullable=False, server_default="180.0"),
        sa.Column("window_area_m2", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "wall_material_id",
            sa.Integer(),
            sa.ForeignKey("materials.id"),
            nullable=False,
        ),
        sa.Column(
            "roof_material_id",
            sa.Integer(),
            sa.ForeignKey("materials.id"),
            nullable=False,
        ),
        sa.Column(
            "floor_material_id",
            sa.Integer(),
            sa.ForeignKey("materials.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_shelters_id", "shelters", ["id"])
    op.create_index("ix_shelters_project_id", "shelters", ["project_id"])

    # ── simulation_runs ───────────────────────────────────────────────────────
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("model_version", sa.String(50), nullable=False, server_default="1.0"),
        sa.Column("error_message", sa.String(1024), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_simulation_runs_id", "simulation_runs", ["id"])
    op.create_index("ix_simulation_runs_project_id", "simulation_runs", ["project_id"])

    # ── simulation_results ────────────────────────────────────────────────────
    op.create_table(
        "simulation_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "simulation_run_id",
            sa.Integer(),
            sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("timestamps", JSONB(), nullable=False, server_default="[]"),
        sa.Column("indoor_temperatures", JSONB(), nullable=False, server_default="[]"),
        sa.Column("conduction_data", JSONB(), nullable=False, server_default="[]"),
        sa.Column("convection_data", JSONB(), nullable=False, server_default="[]"),
        sa.Column("radiation_data", JSONB(), nullable=False, server_default="[]"),
        sa.Column("solar_data", JSONB(), nullable=False, server_default="[]"),
        sa.Column("heating_kwh", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cooling_kwh", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_simulation_results_id", "simulation_results", ["id"])
    op.create_index(
        "ix_simulation_results_simulation_run_id",
        "simulation_results",
        ["simulation_run_id"],
    )

    # ── optimization_runs ─────────────────────────────────────────────────────
    op.create_table(
        "optimization_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("objective_used", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reasoning_text", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(1024), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_optimization_runs_id", "optimization_runs", ["id"])
    op.create_index("ix_optimization_runs_project_id", "optimization_runs", ["project_id"])

    # ── optimization_candidates ───────────────────────────────────────────────
    op.create_table(
        "optimization_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "optimization_run_id",
            sa.Integer(),
            sa.ForeignKey("optimization_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("config", JSONB(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("comfort_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("energy_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cost_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_winner", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_optimization_candidates_id", "optimization_candidates", ["id"]
    )
    op.create_index(
        "ix_optimization_candidates_optimization_run_id",
        "optimization_candidates",
        ["optimization_run_id"],
    )


def downgrade() -> None:
    op.drop_table("optimization_candidates")
    op.drop_table("optimization_runs")
    op.drop_table("simulation_results")
    op.drop_table("simulation_runs")
    op.drop_table("shelters")
    op.drop_table("climate_profiles")
    op.drop_table("projects")
    op.drop_table("materials")
