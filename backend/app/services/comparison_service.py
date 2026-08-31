"""
Comparison Service
==================

Computes a structured comparison between:
  - BASELINE design (current shelter as simulated)
  - OPTIMIZED design (winning candidate from optimization)

Uses actual simulation result data when available.
Falls back to score-based estimates when simulation hasn't been run.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.project import Project
from app.schemas.contracts import ComparisonResult


def get_comparison(project_id: int, db: Session) -> ComparisonResult:
    """
    Return a structured comparison between the baseline and optimized design.

    Priority:
    1. Use actual simulation kWh values if both exist
    2. Use optimization comparison_data stored on OptimizationRun
    3. Return score-based estimates
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # ── Latest simulation (baseline) ──────────────────────────────────────────
    latest_sim = None
    baseline_heating = 0.0
    baseline_cooling = 0.0
    if project.simulation_runs:
        for run in project.simulation_runs:
            if run.status == "completed" and run.result:
                latest_sim = run
                baseline_heating = run.result.heating_kwh
                baseline_cooling = run.result.cooling_kwh
                break

    # ── Latest optimization ───────────────────────────────────────────────────
    latest_opt = None
    if project.optimization_runs:
        for run in project.optimization_runs:
            if run.status == "completed":
                latest_opt = run
                break

    if not latest_opt:
        raise HTTPException(
            status_code=404,
            detail="No completed optimization found. Run an optimization first.",
        )

    # ── Use stored comparison_data if available ───────────────────────────────
    if latest_opt.comparison_data:
        stored = latest_opt.comparison_data
        # Fill in actual simulation kWh if we have them
        stored["baseline_heating_kwh"] = baseline_heating or stored.get("baseline_heating_kwh", 0)
        stored["baseline_cooling_kwh"] = baseline_cooling or stored.get("baseline_cooling_kwh", 0)

        # Recompute percent savings from actuals if we have them
        if baseline_heating + baseline_cooling > 0:
            stored_opt_heating = stored.get("optimized_heating_kwh", 0)
            stored_opt_cooling = stored.get("optimized_cooling_kwh", 0)
            total_baseline  = baseline_heating + baseline_cooling
            total_optimized = stored_opt_heating + stored_opt_cooling
            if total_baseline > 0:
                stored["energy_saving_kwh"] = round(total_baseline - total_optimized, 3)
                stored["energy_saving_pct"] = round(
                    (total_baseline - total_optimized) / total_baseline * 100, 1
                )

        return ComparisonResult(**stored)

    # ── Fallback: score-based estimate ────────────────────────────────────────
    winner = next((c for c in latest_opt.candidates if c.is_winner), None)
    baseline_score  = latest_opt.baseline_data.get("score", 50.0) if latest_opt.baseline_data else 50.0
    optimized_score = winner.score if winner else baseline_score

    energy_saving_pct   = max(0.0, round((optimized_score - baseline_score) * 0.5, 1))
    comfort_delta_pct   = max(0.0, round((winner.comfort_score - 50) * 0.3, 1)) if winner else 0.0

    return ComparisonResult(
        baseline_heating_kwh=baseline_heating,
        baseline_cooling_kwh=baseline_cooling,
        optimized_heating_kwh=round(baseline_heating * (1 - energy_saving_pct / 100), 3),
        optimized_cooling_kwh=round(baseline_cooling * (1 - energy_saving_pct / 100), 3),
        energy_saving_kwh=round((baseline_heating + baseline_cooling) * energy_saving_pct / 100, 3),
        energy_saving_pct=energy_saving_pct,
        comfort_improvement_pct=comfort_delta_pct,
        cost_saving_pct=max(0.0, round((winner.cost_score - 50) * 0.2, 1)) if winner else 0.0,
        baseline_score=baseline_score,
        optimized_score=optimized_score,
        overall_improvement_pct=round(max(0.0, optimized_score - baseline_score), 1),
    )
