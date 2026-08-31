"""
Optimization Engine Boundary
=============================

PUBLIC INTERFACE
----------------
    run_optimization(request: OptimizationRequest) -> OptimizationResult

SCIENTIFIC TEAM OWNERSHIP
--------------------------
The scientific team owns and implements _real_optimization_engine().
The FastAPI team must NOT modify the interface signature.

OPTIMIZATION SCOPE (real engine must implement):
  - Multi-objective design space search
  - Material + thickness candidate generation
  - Energy / comfort / cost scoring per candidate
  - Pareto front or weighted sum selection
  - Winner selection and ranking
"""

import math
import itertools
from datetime import datetime, timezone

from app.scientific_engine.contracts import (
    OptimizationRequest,
    OptimizationResult,
    CandidateResult,
    ComparisonResult,
    ExecutionMode,
)
from app.core.constants import (
    RunStatus,
    OPTIMIZATION_MODEL_VERSION,
)


# ──────────────────────────────────────────────────────────────────────────────
# Public interface
# ──────────────────────────────────────────────────────────────────────────────

def run_optimization(request: OptimizationRequest) -> OptimizationResult:
    """Run optimization and return candidates, winner, and comparison."""
    from app.core.config import settings

    if settings.USE_MOCK_OPTIMIZATION:
        result = _mock_optimization_engine(request)
        result.execution_mode = ExecutionMode.SYNCHRONOUS_FALLBACK
        return result
    else:
        try:
            result = _real_optimization_engine(request)
            result.execution_mode = ExecutionMode.ASYNC_CELERY
            return result
        except NotImplementedError:
            result = _mock_optimization_engine(request)
            result.execution_mode = ExecutionMode.SYNCHRONOUS_FALLBACK
            return result


# ──────────────────────────────────────────────────────────────────────────────
# Scoring helpers (shared by mock and real engines)
# ──────────────────────────────────────────────────────────────────────────────

def _u_value(lam: float, thickness: float) -> float:
    return lam / max(thickness, 0.01)


def _score_candidate(wall_mat: dict, roof_mat: dict, floor_mat: dict,
                     wall_t: float, roof_t: float, T_amb: float) -> tuple[float, float, float]:
    U_wall  = _u_value(wall_mat["thermal_conductivity"], wall_t)
    U_roof  = _u_value(roof_mat["thermal_conductivity"], roof_t)
    U_avg   = (U_wall + U_roof) / 2.0

    energy_score  = max(0.0, min(100.0, 100.0 - U_avg * 10))
    UA            = U_wall * 40 + U_roof * 20
    temp_swing    = abs(T_amb - 20.0) * UA / 1000.0
    comfort_score = max(0.0, min(100.0, 100.0 - temp_swing * 5))
    cost_penalty  = (wall_mat.get("cost_per_unit", 3000) * wall_t * 40
                     + roof_mat.get("cost_per_unit", 3000) * roof_t * 20) / 100_000
    cost_score    = max(0.0, min(100.0, 100.0 - cost_penalty * 10))
    return energy_score, comfort_score, cost_score


def _weighted(es: float, cs: float, cos: float, objective: str) -> float:
    weights = {
        "energy":   (0.70, 0.15, 0.15),
        "comfort":  (0.15, 0.70, 0.15),
        "cost":     (0.15, 0.15, 0.70),
        "balanced": (0.34, 0.33, 0.33),
    }
    we, wc, wco = weights.get(objective, weights["balanced"])
    return round(we * es + wc * cs + wco * cos, 2)


# ──────────────────────────────────────────────────────────────────────────────
# [MOCK OPTIMIZATION ENGINE]
# ──────────────────────────────────────────────────────────────────────────────

def _mock_optimization_engine(request: OptimizationRequest) -> OptimizationResult:
    """⚠️  MOCK OPTIMIZATION ENGINE — generates scored candidate designs."""
    T_amb     = request.climate.ambient_temp_c
    objective = request.objective.value
    s         = request.shelter

    # Baseline (current design)
    baseline_wall  = {"thermal_conductivity": s.wall_material.thermal_conductivity,
                      "cost_per_unit": s.wall_material.cost_per_unit,
                      "name": s.wall_material.name}
    baseline_roof  = {"thermal_conductivity": s.roof_material.thermal_conductivity,
                      "cost_per_unit": s.roof_material.cost_per_unit,
                      "name": s.roof_material.name}
    baseline_floor = {"thermal_conductivity": s.floor_material.thermal_conductivity,
                      "cost_per_unit": s.floor_material.cost_per_unit,
                      "name": s.floor_material.name}

    b_es, b_cs, b_cos = _score_candidate(
        baseline_wall, baseline_roof, baseline_floor,
        s.wall_thickness, s.roof_thickness, T_amb
    )
    baseline_score = _weighted(b_es, b_cs, b_cos, objective)

    baseline_candidate = CandidateResult(
        rank=0,
        config={
            "wall_material": s.wall_material.name,
            "roof_material": s.roof_material.name,
            "wall_thickness": s.wall_thickness,
            "roof_thickness": s.roof_thickness,
        },
        score=baseline_score,
        energy_score=round(b_es, 2),
        comfort_score=round(b_cs, 2),
        cost_score=round(b_cos, 2),
    )

    # Generate candidates from available materials pool
    available = [m.model_dump() for m in request.available_materials]
    wall_pool = [m for m in available if m["category"] in ("wall", "insulation")][:4] or [baseline_wall]
    roof_pool = [m for m in available if m["category"] in ("roof", "wall")][:3]        or [baseline_roof]
    thickness_variants = [0.15, 0.20, 0.25, 0.30, 0.40]

    candidates: list[CandidateResult] = []
    for wall_mat, roof_mat, wall_t, roof_t in itertools.product(
        wall_pool[:3], roof_pool[:2], thickness_variants[:3], thickness_variants[:2]
    ):
        if len(candidates) >= 10:
            break
        es, cs, cos = _score_candidate(wall_mat, roof_mat, baseline_floor, wall_t, roof_t, T_amb)
        total = _weighted(es, cs, cos, objective)
        candidates.append(CandidateResult(
            rank=0,
            config={
                "wall_material": wall_mat.get("name", "Unknown"),
                "wall_material_id": wall_mat.get("id"),
                "roof_material": roof_mat.get("name", "Unknown"),
                "roof_material_id": roof_mat.get("id"),
                "floor_material_id": getattr(s.floor_material, "id", None),
                "wall_thickness": wall_t,
                "roof_thickness": roof_t,
                "floor_thickness": s.floor_thickness,
                "length": s.length, "width": s.width, "height": s.height,
                "orientation_deg": s.orientation_deg,
                "window_area_m2": s.window_area_m2,
            },
            score=total,
            energy_score=round(es, 2),
            comfort_score=round(cs, 2),
            cost_score=round(cos, 2),
        ))

    candidates.sort(key=lambda c: c.score, reverse=True)
    for i, c in enumerate(candidates):
        c.rank = i + 1
    if candidates:
        candidates[0].is_winner = True

    winner = candidates[0] if candidates else baseline_candidate

    # Comparison
    context = "cold" if T_amb < 10 else "hot" if T_amb > 30 else "moderate"
    energy_saving_pct = round(max(0.0, (winner.energy_score - b_es) / max(b_es, 1) * 100), 1)
    comfort_delta_pct = round(max(0.0, (winner.comfort_score - b_cs) / max(b_cs, 1) * 100), 1)

    comparison = ComparisonResult(
        baseline_heating_kwh=0.0,
        baseline_cooling_kwh=0.0,
        optimized_heating_kwh=0.0,
        optimized_cooling_kwh=0.0,
        energy_saving_pct=energy_saving_pct,
        comfort_improvement_pct=comfort_delta_pct,
        cost_saving_pct=round(max(0.0, winner.cost_score - b_cos) / max(b_cos, 1) * 100, 1),
        baseline_score=baseline_score,
        optimized_score=winner.score,
        overall_improvement_pct=round(max(0.0, winner.score - baseline_score), 1),
    )

    reasoning = (
        f"For a {context} climate ({T_amb}°C) with '{objective}' objective, "
        f"the winning design uses {winner.config.get('wall_material')} walls "
        f"({winner.config.get('wall_thickness', 0)*100:.0f} cm) and "
        f"{winner.config.get('roof_material')} roof "
        f"({winner.config.get('roof_thickness', 0)*100:.0f} cm). "
        f"Combined score: {winner.score:.1f}/100 vs baseline {baseline_score:.1f}/100 "
        f"(+{comparison.overall_improvement_pct:.1f}% improvement). "
        f"Evaluated {len(candidates)} candidate configurations."
    )

    return OptimizationResult(
        optimization_run_id=request.optimization_run_id,
        status=RunStatus.COMPLETED,
        objective_used=request.objective,
        candidates=candidates,
        winner=winner,
        baseline=baseline_candidate,
        comparison=comparison,
        reasoning_text=reasoning,
        model_version=f"{OPTIMIZATION_MODEL_VERSION}-mock",
        created_at=datetime.now(timezone.utc),
    )


# ──────────────────────────────────────────────────────────────────────────────
# [REAL OPTIMIZATION ENGINE STUB]
# ──────────────────────────────────────────────────────────────────────────────

def _real_optimization_engine(request: OptimizationRequest) -> OptimizationResult:
    """
    🔬 REAL OPTIMIZATION ENGINE

    OWNED BY: Scientific / ML Team
    DO NOT MODIFY THIS SIGNATURE.

    Suggested approach:
      - Optuna / scipy.optimize for multi-objective search
      - Thermal simulation per candidate (call run_transient_simulation)
      - Pareto front selection or weighted Tchebycheff aggregation
    """
    raise NotImplementedError(
        "Real optimization engine not implemented. "
        "Set USE_MOCK_OPTIMIZATION=True in .env."
    )
