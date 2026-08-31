"""
Transient Solver
================

Extended time-series simulation support.

This module wraps the physics engine to support multi-day (24–72h) transient
runs with climate replay data.

Public interface:
    run_with_timeseries(request, hours) -> SimulationResult
"""

from app.scientific_engine.contracts import SimulationRequest, SimulationResult
from app.scientific_engine.physics.engine import run_transient_simulation


def run_with_timeseries(
    request: SimulationRequest,
    hours: int = 24,
) -> SimulationResult:
    """
    Run a transient simulation over the specified number of hours.

    If the climate has time_series_data populated, the engine will use those
    values hour-by-hour instead of the sinusoidal approximation.

    Parameters
    ----------
    request : SimulationRequest
    hours   : int — simulation duration (default 24h)

    Returns
    -------
    SimulationResult
    """
    # Delegate entirely to the physics engine — it handles time_series_data
    return run_transient_simulation(request)
