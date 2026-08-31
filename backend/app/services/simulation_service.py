"""
Simulation Service
==================

Public interface
----------------
    run_simulation(climate_data, shelter_data, materials_data) -> SimulationOutput

Architecture
------------
This module defines the clean interface between the FastAPI layer and the
physics engine.  The actual thermal computation is isolated into one of two
implementations:

  1. _real_simulation()  — plug in the real physics code here when ready.
                           Currently raises NotImplementedError so it is
                           never called accidentally.

  2. _mock_simulation()  — realistic stand-in used until the real engine is
                           available.  Clearly marked and entirely isolated.

To switch to the real engine: set USE_MOCK_SIMULATION = False and implement
_real_simulation().
"""

import math
import random
from dataclasses import dataclass, field

# ──────────────────────────────────────────────────────────────────────────────
# Feature flag: flip to False once the real physics engine is ready
# ──────────────────────────────────────────────────────────────────────────────
USE_MOCK_SIMULATION: bool = True


# ──────────────────────────────────────────────────────────────────────────────
# Data transfer objects
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SimulationOutput:
    """Structured output returned by run_simulation()."""
    timestamps: list[float]           # hours from 0..23
    indoor_temperatures: list[float]  # °C per hour
    conduction_data: list[float]      # W/m² per hour
    convection_data: list[float]      # W/m² per hour
    radiation_data: list[float]       # W/m² per hour
    solar_data: list[float]           # W/m² per hour
    heating_kwh: float
    cooling_kwh: float
    model_version: str = "1.0"


# ──────────────────────────────────────────────────────────────────────────────
# Public interface
# ──────────────────────────────────────────────────────────────────────────────

def run_simulation(
    climate_data: dict,
    shelter_data: dict,
    materials_data: dict,
) -> SimulationOutput:
    """
    Run a thermal simulation for the given shelter/climate inputs.

    Parameters
    ----------
    climate_data   : dict with keys matching ClimateProfile fields
    shelter_data   : dict with keys matching Shelter fields
    materials_data : dict with keys 'wall', 'roof', 'floor' → Material dicts

    Returns
    -------
    SimulationOutput
    """
    if USE_MOCK_SIMULATION:
        return _mock_simulation(climate_data, shelter_data, materials_data)
    else:
        return _real_simulation(climate_data, shelter_data, materials_data)


# ──────────────────────────────────────────────────────────────────────────────
# [MOCK IMPLEMENTATION] — replace with real physics when ready
# ──────────────────────────────────────────────────────────────────────────────

def _mock_simulation(
    climate_data: dict,
    shelter_data: dict,
    materials_data: dict,
) -> SimulationOutput:
    """
    ⚠️  MOCK IMPLEMENTATION — realistic-looking output for frontend integration.

    Physics model (simplified):
    - Hourly ambient temperature varies sinusoidally around the daily mean.
    - Wall U-value = λ / thickness for each element.
    - Indoor temperature is estimated from a simple thermal resistance model.
    - Heat flows are approximated proportionally.
    - Energy totals are integrated over 24 hours.

    Replace this entire function with _real_simulation() when ready.
    """
    T_amb_mean: float = climate_data["ambient_temp_c"]
    solar: float = climate_data["solar_wm2"]
    wind: float = climate_data["wind_ms"]

    wall_mat = materials_data.get("wall", {})
    roof_mat = materials_data.get("roof", {})
    floor_mat = materials_data.get("floor", {})

    length: float = shelter_data["length"]
    width: float = shelter_data["width"]
    height: float = shelter_data["height"]
    wall_t: float = shelter_data["wall_thickness"]
    roof_t: float = shelter_data["roof_thickness"]
    floor_t: float = shelter_data["floor_thickness"]
    window_area: float = shelter_data.get("window_area_m2", 0.0)
    orientation: float = shelter_data.get("orientation_deg", 180.0)

    # Surface areas (m²)
    wall_area = 2 * (length + width) * height - window_area
    roof_area = length * width
    floor_area = length * width

    # U-values (W/m²·K)  — U = λ / thickness
    wall_lam = wall_mat.get("thermal_conductivity", 0.7)
    roof_lam = roof_mat.get("thermal_conductivity", 1.7)
    floor_lam = floor_mat.get("thermal_conductivity", 1.7)
    window_U = 3.0  # standard double glazing

    U_wall = wall_lam / max(wall_t, 0.01)
    U_roof = roof_lam / max(roof_t, 0.01)
    U_floor = floor_lam / max(floor_t, 0.01)

    # Overall UA (W/K)
    UA_total = (
        U_wall * wall_area
        + U_roof * roof_area
        + U_floor * floor_area
        + window_U * window_area
    )

    # Solar gain factor — south-facing (180°) gives max gain
    orient_factor = max(0.0, math.cos(math.radians(orientation - 180))) * 0.8 + 0.2
    solar_gain_W = solar * window_area * orient_factor * 0.7  # SHGC ≈ 0.7

    # Internal heat gain (people + equipment, W)
    internal_gain_W = 100.0

    # Hourly simulation
    T_target = 20.0   # desired indoor temperature for comfort
    DELTA_T = 10.0    # daily temperature swing amplitude

    timestamps: list[float] = []
    indoor_temps: list[float] = []
    conduction: list[float] = []
    convection: list[float] = []
    radiation: list[float] = []
    solar_vals: list[float] = []

    total_heating_Wh = 0.0
    total_cooling_Wh = 0.0

    for h in range(24):
        # Ambient temperature sine wave (min at 4am, max at 2pm)
        T_amb = T_amb_mean + DELTA_T * math.sin(math.pi * (h - 4) / 12)

        # Solar irradiance profile (bell curve, peak at noon)
        solar_h = solar * max(0.0, math.sin(math.pi * h / 24) * 2.0 - 0.0)
        solar_h_gain = solar_h * window_area * orient_factor * 0.7

        # Simplified steady-state indoor temp estimate
        T_indoor_free = T_amb + (solar_h_gain + internal_gain_W) / max(UA_total, 1.0)
        T_indoor = round(T_indoor_free + random.uniform(-0.3, 0.3), 2)

        # Heat flow components (W/m²)
        Q_cond = U_wall * (T_indoor - T_amb)
        Q_conv = 0.6 * wind * (T_indoor - T_amb)
        Q_rad = 0.03 * (T_indoor + 273.15) ** 4 / 1e9  # simplified
        Q_solar = solar_h_gain / max(roof_area, 1.0)

        # HVAC load
        if T_indoor < T_target:
            Q_hvac = UA_total * (T_target - T_indoor)
            total_heating_Wh += Q_hvac
        else:
            Q_hvac = UA_total * (T_indoor - T_target)
            total_cooling_Wh += Q_hvac

        timestamps.append(float(h))
        indoor_temps.append(round(T_indoor, 2))
        conduction.append(round(Q_cond, 2))
        convection.append(round(Q_conv, 2))
        radiation.append(round(Q_rad, 4))
        solar_vals.append(round(Q_solar, 2))

    heating_kwh = round(total_heating_Wh / 1000.0, 3)
    cooling_kwh = round(total_cooling_Wh / 1000.0, 3)

    return SimulationOutput(
        timestamps=timestamps,
        indoor_temperatures=indoor_temps,
        conduction_data=conduction,
        convection_data=convection,
        radiation_data=radiation,
        solar_data=solar_vals,
        heating_kwh=heating_kwh,
        cooling_kwh=cooling_kwh,
        model_version="1.0-mock",
    )


# ──────────────────────────────────────────────────────────────────────────────
# [REAL IMPLEMENTATION] — implement this function with actual physics
# ──────────────────────────────────────────────────────────────────────────────

def _real_simulation(
    climate_data: dict,
    shelter_data: dict,
    materials_data: dict,
) -> SimulationOutput:
    """
    🔬 REAL PHYSICS IMPLEMENTATION — replace this stub with actual simulation.

    Expected inputs:
        climate_data   : { location, ambient_temp_c, solar_wm2, wind_ms, humidity_pct, mode }
        shelter_data   : { length, width, height, wall_thickness, roof_thickness,
                           floor_thickness, orientation_deg, window_area_m2 }
        materials_data : { wall: {thermal_conductivity, density, specific_heat},
                           roof: {...}, floor: {...} }

    Expected return: SimulationOutput with 24-hour hourly arrays.
    """
    raise NotImplementedError(
        "Real simulation engine not yet implemented. "
        "Set USE_MOCK_SIMULATION = True to use the mock, or implement this function."
    )
