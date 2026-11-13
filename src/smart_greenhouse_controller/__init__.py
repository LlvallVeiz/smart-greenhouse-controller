"""Smart Greenhouse Controller — sensor simulation, hysteresis control,
time-series analysis and reporting for a small greenhouse.
"""

from .analysis import analyze, compare_runs
from .controller import Controller
from .crops import get_profile, list_profiles
from .physics import (
    daily_light_integral,
    dew_point,
    lux_to_ppfd,
    saturation_vapor_pressure,
    vapor_pressure_deficit,
)
from .sensors import GreenhouseEnvironment
from .simulator import SimulationConfig, run_comparison, run_simulation

__all__ = [
    "analyze",
    "compare_runs",
    "Controller",
    "daily_light_integral",
    "dew_point",
    "get_profile",
    "list_profiles",
    "lux_to_ppfd",
    "saturation_vapor_pressure",
    "vapor_pressure_deficit",
    "GreenhouseEnvironment",
    "SimulationConfig",
    "run_comparison",
    "run_simulation",
]

__version__ = "1.0.0"
