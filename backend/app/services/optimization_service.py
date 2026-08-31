"""
Optimization Service
====================

Public interface
----------------
    optimize_design(climate_data, shelter_data, materials_data, objective, all_materials)
        -> OptimizationOutput

Strategy
--------
1. Generate N candidate shelter configurations by varying:
   - Wall / roof material selection
   - Wall / roof thickness
2. For each candidate, estimate three scores:
   - energy_score   (lower UA → better insulation → higher score)
   - comfort_score  (narrower indoor temp swings → higher score)
   - cost_score     (cheaper materials + thinner walls → higher score)
3. Combine scores according to the chosen objective.
4. Sort candidates; mark the top-scored one as winner.
5. Return structured output with reasoning text.

Architecture mirrors simulation_service.py:
- USE_MOCK_OPTIMIZATION flag controls real vs mock.
- _real_optimization() is an isolated stub for the real engine.
- _mock_optimization() provides meaningful demo candidates.
"""

import math
import itertools
from dataclasses import dataclass, field

USE_MOCK_OPTIMIZATION: bool = True


# ──────────────────────────────────────────────────────────────────────────────
# DTOs
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class CandidateOutput:
    config: dict
    score: float
    comfort_score: float
    energy_score: float
    cost_score: float
    is_winner: bool = False


@dataclass
class OptimizationOutput:
    candidates: list[CandidateOutput]
    winner: CandidateOutput
    reasoning_text: str


# ──────────────────────────────────────────────────────────────────────────────
# Public interface
# ──────────────────────────────────────────────────────────────────────────────

def optimize_design(
    climate_data: dict,
    shelter_data: dict,
    materials_data: dict,
    objective: str,
    all_materials: list[dict],
) -> OptimizationOutput:
    """
    Run optimisation and return candidates + winning configuration.

    Parameters
    ----------
    climate_data   : climate profile dict
    shelter_data   : current shelter configuration dict
    materials_data : current selected materials (wall/roof/floor)
    objective      : "energy" | "comfort" | "cost" | "balanced"
    all_materials  : full list of material dicts from the DB (for alternatives)
    """
    if USE_MOCK_OPTIMIZATION:
        return _mock_optimization(climate_data, shelter_data, materials_data, objective, all_materials)
    else:
        return _real_optimization(climate_data, shelter_data, materials_data, objective, all_materials)


# ──────────────────────────────────────────────────────────────────────────────
# Scoring helpers
# ──────────────────────────────────────────────────────────────────────────────

def _compute_u_value(lam: float, thickness: float) -> float:
    return lam / max(thickness, 0.01)


def _score_candidate(
    candidate_shelter: dict,
    wall_mat: dict,
    roof_mat: dict,
    floor_mat: dict,
    T_amb: float,
) -> tuple[float, float, float]:
    """Return (energy_score, comfort_score, cost_score) each in 0–100."""
    wall_t = candidate_shelter["wall_thickness"]
    roof_t = candidate_shelter["roof_thickness"]

    U_wall = _compute_u_value(wall_mat["thermal_conductivity"], wall_t)
    U_roof = _compute_u_value(roof_mat["thermal_conductivity"], roof_t)

    # Lower U → better insulation → higher energy score
    U_avg = (U_wall + U_roof) / 2.0
    energy_score = max(0.0, min(100.0, 100.0 - (U_avg * 10)))

    # Comfort: penalise large indoor temp swings (proxy: high UA)
    UA_total = U_wall * 40 + U_roof * 20  # simplified
    temp_swing = abs(T_amb - 20.0) * UA_total / 1000.0
    comfort_score = max(0.0, min(100.0, 100.0 - temp_swing * 5))

    # Cost: cheaper materials + thinner walls = higher cost score
    cost_penalty = (
        wall_mat.get("cost_per_unit", 3000) * wall_t * 40
        + roof_mat.get("cost_per_unit", 3000) * roof_t * 20
    ) / 100_000
    cost_score = max(0.0, min(100.0, 100.0 - cost_penalty * 10))

    return energy_score, comfort_score, cost_score


def _weighted_score(
    energy_score: float,
    comfort_score: float,
    cost_score: float,
    objective: str,
) -> float:
    weights = {
        "energy":   (0.70, 0.15, 0.15),
        "comfort":  (0.15, 0.70, 0.15),
        "cost":     (0.15, 0.15, 0.70),
        "balanced": (0.34, 0.33, 0.33),
    }
    we, wc, wco = weights.get(objective, weights["balanced"])
    return round(we * energy_score + wc * comfort_score + wco * cost_score, 2)


# ──────────────────────────────────────────────────────────────────────────────
# [MOCK IMPLEMENTATION]
# ──────────────────────────────────────────────────────────────────────────────

def _mock_optimization(
    climate_data: dict,
    shelter_data: dict,
    materials_data: dict,
    objective: str,
    all_materials: list[dict],
) -> OptimizationOutput:
    """
    ⚠️  MOCK IMPLEMENTATION — generate candidate variations for demo purposes.
    """
    T_amb = climate_data.get("ambient_temp_c", 15.0)

    # Pick wall/roof candidate materials from the DB pool
    wall_candidates = [m for m in all_materials if m["category"] in ("wall", "insulation")][:4]
    roof_candidates = [m for m in all_materials if m["category"] in ("roof", "wall")][:3]

    if not wall_candidates:
        wall_candidates = [materials_data.get("wall", {"name": "Brick", "thermal_conductivity": 0.72,
                                                        "density": 1800, "specific_heat": 840,
                                                        "cost_per_unit": 2800, "id": 2})]
    if not roof_candidates:
        roof_candidates = [materials_data.get("roof", {"name": "Concrete", "thermal_conductivity": 1.7,
                                                        "density": 2300, "specific_heat": 880,
                                                        "cost_per_unit": 3500, "id": 1})]

    thickness_variants = [0.15, 0.20, 0.30, 0.40]

    candidates: list[CandidateOutput] = []

    for wall_mat, roof_mat, wall_t, roof_t in itertools.product(
        wall_candidates[:3], roof_candidates[:2], thickness_variants[:3], thickness_variants[:2]
    ):
        if len(candidates) >= 10:
            break

        cand_shelter = {**shelter_data, "wall_thickness": wall_t, "roof_thickness": roof_t}
        floor_mat = materials_data.get("floor", wall_mat)

        es, cs, cos = _score_candidate(cand_shelter, wall_mat, roof_mat, floor_mat, T_amb)
        total = _weighted_score(es, cs, cos, objective)

        candidates.append(
            CandidateOutput(
                config={
                    "wall_material": wall_mat.get("name", "Unknown"),
                    "wall_material_id": wall_mat.get("id"),
                    "roof_material": roof_mat.get("name", "Unknown"),
                    "roof_material_id": roof_mat.get("id"),
                    "floor_material_id": shelter_data.get("floor_material_id"),
                    "wall_thickness": wall_t,
                    "roof_thickness": roof_t,
                    "floor_thickness": shelter_data.get("floor_thickness", 0.2),
                    "length": shelter_data.get("length"),
                    "width": shelter_data.get("width"),
                    "height": shelter_data.get("height"),
                    "orientation_deg": shelter_data.get("orientation_deg", 180),
                    "window_area_m2": shelter_data.get("window_area_m2", 0),
                },
                score=total,
                comfort_score=round(cs, 2),
                energy_score=round(es, 2),
                cost_score=round(cos, 2),
            )
        )

    # Sort descending by combined score
    candidates.sort(key=lambda c: c.score, reverse=True)
    winner = candidates[0]
    winner.is_winner = True

    reasoning = _build_reasoning(winner, objective, T_amb)

    return OptimizationOutput(candidates=candidates, winner=winner, reasoning_text=reasoning)


def _build_reasoning(winner: CandidateOutput, objective: str, T_amb: float) -> str:
    wall_name = winner.config.get("wall_material", "selected material")
    roof_name = winner.config.get("roof_material", "selected material")
    wall_t = winner.config.get("wall_thickness", 0.3)
    roof_t = winner.config.get("roof_thickness", 0.2)

    context = "cold" if T_amb < 10 else "hot" if T_amb > 30 else "moderate"

    return (
        f"For a {context} climate ({T_amb}°C ambient) with objective '{objective}', "
        f"the winning configuration uses {wall_name} walls ({wall_t*100:.0f} cm thick) "
        f"and {roof_name} roof ({roof_t*100:.0f} cm thick). "
        f"This achieved an energy score of {winner.energy_score:.1f}/100, "
        f"comfort score of {winner.comfort_score:.1f}/100, "
        f"and cost score of {winner.cost_score:.1f}/100 "
        f"(combined: {winner.score:.1f}/100). "
        f"The configuration was selected by evaluating {10} candidate designs and "
        f"applying the '{objective}' weighting strategy."
    )


# ──────────────────────────────────────────────────────────────────────────────
# [REAL IMPLEMENTATION] — stub
# ──────────────────────────────────────────────────────────────────────────────

def _real_optimization(
    climate_data: dict,
    shelter_data: dict,
    materials_data: dict,
    objective: str,
    all_materials: list[dict],
) -> OptimizationOutput:
    """
    🔬 REAL OPTIMISATION ENGINE — implement this when ready.
    """
    raise NotImplementedError(
        "Real optimisation engine not yet implemented. "
        "Set USE_MOCK_OPTIMIZATION = True to use the mock."
    )
