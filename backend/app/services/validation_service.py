"""
Validation Service
==================

Pre-flight engineering validation before simulation or optimization.

Returns a structured ValidationResult with errors and warnings.
This runs BEFORE any SimulationRun or OptimizationRun is created.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.material import Material
from app.schemas.contracts import ValidationResult, ValidationError
from app.core.constants import ValidationStatus


def validate_project_for_simulation(project_id: int, db: Session) -> ValidationResult:
    """
    Validate that a project is fully configured for simulation.

    Checks:
    - Project exists
    - Climate profile exists and values are in valid ranges
    - Shelter configuration exists with valid dimensions
    - All referenced material IDs exist in the database
    - Material thermal properties are physically plausible
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return ValidationResult(
            valid=False,
            status=ValidationStatus.INVALID,
            errors=[ValidationError(field="project", message="Project not found")],
            checked_at=datetime.now(timezone.utc),
        )

    # ── Climate ───────────────────────────────────────────────────────────────
    cp = project.climate_profile
    if not cp:
        errors.append(ValidationError(field="climate", message="Climate profile is required"))
    else:
        if not (-60 <= cp.ambient_temp_c <= 60):
            warnings.append(ValidationError(
                field="climate.ambient_temp_c",
                message=f"Temperature {cp.ambient_temp_c}°C is outside typical range (-60 to 60°C)",
                severity="warning",
            ))
        if cp.solar_wm2 > 1400:
            warnings.append(ValidationError(
                field="climate.solar_wm2",
                message=f"Solar irradiance {cp.solar_wm2} W/m² exceeds maximum solar constant",
                severity="warning",
            ))
        if cp.wind_ms > 100:
            errors.append(ValidationError(
                field="climate.wind_ms",
                message=f"Wind speed {cp.wind_ms} m/s is physically unrealistic",
            ))

    # ── Shelter ───────────────────────────────────────────────────────────────
    s = project.shelter
    if not s:
        errors.append(ValidationError(field="shelter", message="Shelter configuration is required"))
    else:
        for dim_name, dim_val in [
            ("length", s.length), ("width", s.width), ("height", s.height)
        ]:
            if dim_val <= 0:
                errors.append(ValidationError(
                    field=f"shelter.{dim_name}",
                    message=f"{dim_name} must be greater than 0"
                ))
            elif dim_val > 200:
                warnings.append(ValidationError(
                    field=f"shelter.{dim_name}",
                    message=f"{dim_name} = {dim_val}m is unusually large",
                    severity="warning",
                ))

        for t_name, t_val in [
            ("wall_thickness", s.wall_thickness),
            ("roof_thickness", s.roof_thickness),
            ("floor_thickness", s.floor_thickness),
        ]:
            if t_val <= 0:
                errors.append(ValidationError(
                    field=f"shelter.{t_name}",
                    message=f"{t_name} must be greater than 0"
                ))
            elif t_val > 3.0:
                warnings.append(ValidationError(
                    field=f"shelter.{t_name}",
                    message=f"{t_name} = {t_val}m is unusually thick",
                    severity="warning",
                ))

        wall_area = 2 * (s.length + s.width) * s.height
        if s.window_area_m2 > wall_area * 0.8:
            errors.append(ValidationError(
                field="shelter.window_area_m2",
                message="Window area exceeds 80% of total wall area — geometrically invalid",
            ))

        # ── Materials ─────────────────────────────────────────────────────────
        for role, mid in [
            ("wall_material_id", s.wall_material_id),
            ("roof_material_id", s.roof_material_id),
            ("floor_material_id", s.floor_material_id),
        ]:
            mat = db.query(Material).filter(Material.id == mid).first()
            if not mat:
                errors.append(ValidationError(
                    field=f"shelter.{role}",
                    message=f"Material id={mid} does not exist in the database",
                ))
            else:
                if mat.thermal_conductivity <= 0:
                    errors.append(ValidationError(
                        field=f"material.{mat.name}.thermal_conductivity",
                        message="Thermal conductivity must be > 0",
                    ))
                if mat.density <= 0:
                    errors.append(ValidationError(
                        field=f"material.{mat.name}.density",
                        message="Density must be > 0",
                    ))
                if mat.thermal_conductivity > 500:
                    warnings.append(ValidationError(
                        field=f"material.{mat.name}.thermal_conductivity",
                        message=f"Thermal conductivity {mat.thermal_conductivity} W/m·K is unusually high",
                        severity="warning",
                    ))

    valid = len(errors) == 0
    status = ValidationStatus.VALID if valid else ValidationStatus.INVALID
    if valid and warnings:
        status = ValidationStatus.WARNING

    return ValidationResult(
        valid=valid,
        status=status,
        errors=errors,
        warnings=warnings,
        checked_at=datetime.now(timezone.utc),
    )
