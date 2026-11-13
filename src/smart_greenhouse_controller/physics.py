"""Physics helpers for greenhouse climate: vapour pressure, VPD, light.

All formulas are the standard ones used in horticulture and irrigation
science:

* Saturation vapour pressure (SVP): Tetens equation as used by FAO
  Irrigation and Drainage Paper 56 (Allen et al., 1998).
* Vapour pressure deficit (VPD): SVP * (1 - RH/100).
* Dew point: Magnus formula (the inverse of the Tetens equation).
* Daily light integral (DLI): time integral of PPFD.
* Lux <-> PPFD: sunlight conversion factor 0.0185 umol/m^2/s per lux
  (commonly cited for sunlight; LED spectra differ, see RESEARCH.md).
"""

from __future__ import annotations

import math

# Tetens / FAO 56 constants.
_TETENS_A = 0.6108  # kPa
_TETENS_B = 17.27
_TETENS_C = 237.3  # deg C

#: Approximate PPFD (umol/m^2/s) produced by 1 lux of sunlight.
LUX_TO_PPFD_SUNLIGHT = 0.0185


def saturation_vapor_pressure(temp_c: float) -> float:
    """Saturation vapour pressure (kPa) at ``temp_c`` (Tetens / FAO 56).

    SVP = 0.6108 * exp(17.27 * T / (T + 237.3))
    """
    return _TETENS_A * math.exp(_TETENS_B * temp_c / (temp_c + _TETENS_C))


def vapor_pressure_deficit(temp_c: float, rh_percent: float) -> float:
    """Vapour pressure deficit (kPa) from air temperature and RH.

    VPD = SVP * (1 - RH/100).  At 25 C and 60% RH this is ~1.27 kPa.
    """
    if not 0.0 <= rh_percent <= 100.0:
        raise ValueError(f"RH must be 0..100, got {rh_percent}")
    svp = saturation_vapor_pressure(temp_c)
    return svp * (1.0 - rh_percent / 100.0)


def dew_point(temp_c: float, rh_percent: float) -> float:
    """Dew point (deg C) from air temperature and RH (Magnus formula).

    Inverse of the Tetens equation; undefined at RH = 0.
    """
    if not 0.0 < rh_percent <= 100.0:
        raise ValueError(f"RH must be in (0, 100], got {rh_percent}")
    svp = saturation_vapor_pressure(temp_c)
    avp = svp * rh_percent / 100.0
    ln_ratio = math.log(avp / _TETENS_A)
    return _TETENS_C * ln_ratio / (_TETENS_B - ln_ratio)


def lux_to_ppfd(lux: float, factor: float = LUX_TO_PPFD_SUNLIGHT) -> float:
    """Convert illuminance (lux) to PPFD (umol/m^2/s)."""
    if lux < 0:
        raise ValueError(f"lux must be >= 0, got {lux}")
    return lux * factor


def ppfd_to_lux(ppfd: float, factor: float = LUX_TO_PPFD_SUNLIGHT) -> float:
    """Convert PPFD (umol/m^2/s) to illuminance (lux)."""
    if ppfd < 0:
        raise ValueError(f"ppfd must be >= 0, got {ppfd}")
    return ppfd / factor


def daily_light_integral(ppfd_values: list[float], dt_seconds: float) -> float:
    """Daily light integral (mol/m^2/day) from a PPFD series.

    DLI = sum(PPFD * dt) / 1e6.  Example: 300 umol/m^2/s held for 12 h
    gives 300 * 12 * 3600 / 1e6 = 12.96 mol/m^2/d.
    """
    if dt_seconds <= 0:
        raise ValueError(f"dt_seconds must be > 0, got {dt_seconds}")
    return sum(ppfd_values) * dt_seconds / 1_000_000.0


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into [``low``, ``high``]."""
    return max(low, min(high, value))
