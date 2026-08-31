"""
Physics Engine Boundary
========================

PUBLIC INTERFACE
----------------
    run_transient_simulation(request: SimulationRequest) -> SimulationResult

ARCHITECTURE
------------
This is the ONLY entry point the rest of the application uses to execute
thermal physics calculations.

The implementation is selected by the feature flag in settings:
  - USE_MOCK_SIMULATION = True  →  _mock_engine() (demo/dev mode)
  - USE_MOCK_SIMULATION = False →  _real_engine()  (plug in real physics here)

SCIENTIFIC TEAM OWNERSHIP
--------------------------
The scientific team owns and implements _real_engine().
The FastAPI team must NOT modify the interface signature.

PHYSICS SCOPE (real engine must implement):
  - Transient thermal simulation (24–72 hour)
  - Heat conduction through walls, roof, floor
  - Natural and forced convection
  - Long-wave radiation exchange
  - Solar gain through windows
  - HVAC load calculation
  - Energy balance
"""

import math
import random
from datetime import datetime, timezone

from app.scientific_engine.contracts import (
    SimulationRequest,
    SimulationResult,
    HeatFlowData,
    ExecutionMode,
)
from app.core.constants import (
    RunStatus,
    ValidationStatus,
    DEFAULT_COMFORT_TEMP_C,
    DEFAULT_INTERNAL_GAIN_W,
    DEFAULT_WINDOW_U_VALUE,
    DEFAULT_WINDOW_SHGC,
    SIMULATION_MODEL_VERSION,
    SIMULATION_HOURS,
)


# ──────────────────────────────────────────────────────────────────────────────
# Public interface — called by workers and services
# ──────────────────────────────────────────────────────────────────────────────

def run_transient_simulation(request: SimulationRequest) -> SimulationResult:
    """
    Execute a transient thermal simulation.

    Parameters
    ----------
    request : SimulationRequest
        Fully populated request including climate, shelter, and materials.

    Returns
    -------
    SimulationResult
        24-hour hourly arrays + energy summary + comfort metrics.
    """
    from app.core.config import settings

    if settings.USE_MOCK_SIMULATION:
        result = _mock_engine(request)
        result.execution_mode = ExecutionMode.SYNCHRONOUS_FALLBACK
        return result
    else:
        try:
            result = _real_engine(request)
            result.execution_mode = ExecutionMode.ASYNC_CELERY
            return result
        except NotImplementedError:
            # Explicit fallback — clearly marked
            result = _mock_engine(request)
            result.execution_mode = ExecutionMode.SYNCHRONOUS_FALLBACK
            result.validation_status = ValidationStatus.WARNING + "_fallback_used"
            return result


# ──────────────────────────────────────────────────────────────────────────────
# [MOCK ENGINE] — realistic stand-in, clearly isolated
# ──────────────────────────────────────────────────────────────────────────────

def _mock_engine(request: SimulationRequest) -> SimulationResult:
    """
    ⚠️  MOCK PHYSICS ENGINE

    Simplified quasi-steady-state model:
    - Sinusoidal ambient temperature profile
    - U-value computed from λ / thickness per element
    - Indoor temperature from thermal resistance model
    - Hourly HVAC load integration
    - Comfort metrics derived from indoor temperature

    Replace entirely with _real_engine() when real physics is ready.
    """
    c = request.climate
    s = request.shelter

    T_mean = c.ambient_temp_c
    solar  = c.solar_wm2
    wind   = c.wind_ms

    wall_m = s.wall_material
    roof_m = s.roof_material
    floor_m = s.floor_material

    # Surface areas (m²)
    wall_area  = 2 * (s.length + s.width) * s.height - s.window_area_m2
    roof_area  = s.length * s.width
    floor_area = s.length * s.width

    # U-values (W/m²·K)
    U_wall  = wall_m.thermal_conductivity  / max(s.wall_thickness, 0.01)
    U_roof  = roof_m.thermal_conductivity  / max(s.roof_thickness, 0.01)
    U_floor = floor_m.thermal_conductivity / max(s.floor_thickness, 0.01)

    UA_total = (
        U_wall  * wall_area
        + U_roof  * roof_area
        + U_floor * floor_area
        + DEFAULT_WINDOW_U_VALUE * s.window_area_m2
    )

    # Solar orientation factor (max at south-facing 180°)
    orient_factor = max(0.0, math.cos(math.radians(s.orientation_deg - 180))) * 0.8 + 0.2

    DELTA_T  = 10.0
    hours    = SIMULATION_HOURS

    timestamps: list[float] = []
    indoor_temps: list[float] = []
    ambient_temps: list[float] = []
    conduction: list[float] = []
    convection: list[float] = []
    radiation: list[float] = []
    solar_vals: list[float] = []

    total_heating_Wh = 0.0
    total_cooling_Wh = 0.0
    comfort_below = 0
    comfort_above = 0

    for h in range(hours):
        # ── Climate time-series override ──────────────────────────────────
        if c.time_series_data and h < len(c.time_series_data):
            ts = c.time_series_data[h]
            T_amb   = ts.get("temp_c", T_mean + DELTA_T * math.sin(math.pi * (h - 4) / 12))
            solar_h = ts.get("solar_wm2", solar * max(0.0, math.sin(math.pi * h / 24) * 2))
        else:
            T_amb   = T_mean + DELTA_T * math.sin(math.pi * (h - 4) / 12)
            solar_h = solar * max(0.0, math.sin(math.pi * h / 24) * 2)

        solar_gain = solar_h * s.window_area_m2 * orient_factor * DEFAULT_WINDOW_SHGC

        T_indoor_free = T_amb + (solar_gain + DEFAULT_INTERNAL_GAIN_W) / max(UA_total, 1.0)
        T_indoor = round(T_indoor_free + random.uniform(-0.3, 0.3), 2)

        # Heat flow components (W/m²)
        Q_cond  = round(U_wall  * (T_indoor - T_amb), 2)
        Q_conv  = round(0.6 * wind * (T_indoor - T_amb), 2)
        Q_rad   = round(0.03 * (T_indoor + 273.15) ** 4 / 1e9, 4)
        Q_solar = round(solar_gain / max(roof_area, 1.0), 2)

        # HVAC load
        if T_indoor < DEFAULT_COMFORT_TEMP_C:
            total_heating_Wh += UA_total * (DEFAULT_COMFORT_TEMP_C - T_indoor)
            comfort_below += 1
        else:
            total_cooling_Wh += UA_total * (T_indoor - DEFAULT_COMFORT_TEMP_C)
            comfort_above += 1

        timestamps.append(float(h))
        indoor_temps.append(T_indoor)
        ambient_temps.append(round(T_amb, 2))
        conduction.append(Q_cond)
        convection.append(Q_conv)
        radiation.append(Q_rad)
        solar_vals.append(Q_solar)

    heating_kwh      = round(total_heating_Wh / 1000.0, 3)
    cooling_kwh      = round(total_cooling_Wh / 1000.0, 3)
    total_energy_kwh = round(heating_kwh + cooling_kwh, 3)

    return SimulationResult(
        simulation_run_id=request.simulation_run_id,
        status=RunStatus.COMPLETED,
        timestamps=timestamps,
        indoor_temp_c=indoor_temps,
        ambient_temp_c=ambient_temps,
        heat_flow=HeatFlowData(
            conduction=conduction,
            convection=convection,
            radiation=radiation,
            solar=solar_vals,
        ),
        heating_kwh=heating_kwh,
        cooling_kwh=cooling_kwh,
        total_energy_kwh=total_energy_kwh,
        hours_below_comfort=comfort_below,
        hours_above_comfort=comfort_above,
        min_indoor_temp_c=min(indoor_temps) if indoor_temps else None,
        max_indoor_temp_c=max(indoor_temps) if indoor_temps else None,
        model_version=f"{SIMULATION_MODEL_VERSION}-mock",
        validation_status=ValidationStatus.VALID,
        created_at=datetime.now(timezone.utc),
    )


# ──────────────────────────────────────────────────────────────────────────────
# [REAL ENGINE STUB] — scientific team implements this
# ──────────────────────────────────────────────────────────────────────────────

def _real_engine(request: SimulationRequest) -> SimulationResult:
    """
    🔬 REAL TRANSIENT THERMAL SIMULATION ENGINE

    OWNED BY: Scientific / Physics Team
    DO NOT MODIFY THIS SIGNATURE.

    Expected inputs  : SimulationRequest (climate, shelter, materials, parameters)
    Expected output  : SimulationResult  (24+ hour arrays, energy totals, comfort metrics)

    Physics to implement:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  1. Transient heat conduction (wall/roof/floor)                     │
    │  2. Convective heat transfer (natural + wind-driven)                │
    │  3. Long-wave radiation (grey-body approximation)                   │
    │  4. Solar gain through windows (SHGC, orientation, shading)         │
    │  5. Thermal mass effect (density × specific_heat × volume)          │
    │  6. HVAC energy balance (heating / cooling load)                    │
    │  7. 24–72 hour hourly time-stepping                                 │
    └─────────────────────────────────────────────────────────────────────┘

    Suggested libraries:
      numpy, scipy.integrate, scipy.linalg (for FDM/FEM solvers)
    """
    raise NotImplementedError(
        "Real physics engine not yet implemented. "
        "Set USE_MOCK_SIMULATION=True in .env to use the mock engine."
    )
