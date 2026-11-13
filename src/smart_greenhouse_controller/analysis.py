"""Analysis of a simulation run: water, climate compliance, energy.

Metrics computed from the recorded time series:

* **Water**: total litres, irrigation events (rising edges of the
  valve signal), litres per day.
* **Climate compliance**: hours the air temperature, RH and VPD spent
  outside the crop's optimal band (day/night temperature bands are
  applied by time of day), and the share of time inside the band.
* **Light**: daily light integral (DLI) per day from the PPFD series.
* **Energy**: kWh per actuator from duty cycle x rated power.
* **CO2**: mean daytime CO2 and hours below the enrichment target.

``compare_runs`` summarises the same metrics for a control-ON run
against the uncontrolled baseline run on identical weather.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .crops import CropProfile, get_profile
from .physics import daily_light_integral, lux_to_ppfd
from .simulator import SimulationResult


@dataclass
class AnalysisReport:
    crop: str
    days: int
    control_enabled: bool
    total_water_l: float
    water_l_per_day: float
    irrigation_events: int
    irrigation_minutes: float
    hours_temp_out_of_range: float
    hours_rh_out_of_range: float
    hours_vpd_out_of_range: float
    pct_time_in_temp_band: float
    mean_temp_c: float
    mean_rh_percent: float
    mean_soil_vwc: float
    min_soil_vwc: float
    max_soil_vwc: float
    mean_daytime_co2_ppm: float
    hours_co2_below_target: float
    dli_per_day: list[float] = field(default_factory=list)
    mean_dli: float = 0.0
    energy_kwh: dict[str, float] = field(default_factory=dict)
    total_energy_kwh: float = 0.0
    actuator_duty: dict[str, float] = field(default_factory=dict)


def _count_events(flags: list[bool]) -> int:
    """Number of rising edges (False -> True) in a boolean series."""
    return sum(1 for prev, cur in zip(flags, flags[1:]) if cur and not prev) + (
        1 if flags and flags[0] else 0
    )


def analyze(result: SimulationResult) -> AnalysisReport:
    """Compute all metrics for one completed run."""
    if not result.steps:
        raise ValueError("cannot analyse an empty simulation result")
    profile: CropProfile = get_profile(result.crop)
    dt_h = result.dt_minutes / 60.0
    steps = result.steps

    temps = [s.temp_c for s in steps]
    rhs = [s.rh_percent for s in steps]
    soils = [s.soil_vwc for s in steps]
    vpds = [s.vpd_kpa for s in steps]

    hours_temp_out = 0.0
    hours_rh_out = 0.0
    hours_vpd_out = 0.0
    for s in steps:
        is_day = 6 * 60 <= s.minute_of_day < 18 * 60
        t_min = profile.temp_day_min if is_day else profile.temp_night_min
        t_max = profile.temp_day_max if is_day else profile.temp_night_max
        if not (t_min <= s.temp_c <= t_max):
            hours_temp_out += dt_h
        if not (profile.rh_min <= s.rh_percent <= profile.rh_max):
            hours_rh_out += dt_h
        if not (profile.vpd_min <= s.vpd_kpa <= profile.vpd_max):
            hours_vpd_out += dt_h

    # DLI per day from the PPFD series.
    steps_per_day = int(24 * 60 / result.dt_minutes)
    dli_per_day: list[float] = []
    for d in range(result.days):
        day_steps = steps[d * steps_per_day : (d + 1) * steps_per_day]
        ppfd = [lux_to_ppfd(s.par_lux) for s in day_steps]
        dli_per_day.append(
            round(daily_light_integral(ppfd, result.dt_minutes * 60.0), 2)
        )

    # Energy from duty cycles.
    cfg = result.config
    duty = {
        "heater": sum(1 for s in steps if s.heater) / len(steps),
        "fan": sum(1 for s in steps if s.fan) / len(steps),
        "lights": sum(1 for s in steps if s.lights) / len(steps),
        "irrigation": sum(1 for s in steps if s.irrigation) / len(steps),
        "co2": sum(1 for s in steps if s.co2) / len(steps),
    }
    total_hours = len(steps) * dt_h
    energy = {
        "heater": round(duty["heater"] * total_hours * cfg.heater_power_w / 1000.0, 2),
        "fan": round(duty["fan"] * total_hours * cfg.fan_power_w / 1000.0, 2),
        "lights": round(duty["lights"] * total_hours * cfg.lights_power_w / 1000.0, 2),
    }

    day_co2 = [s.co2_ppm for s in steps if 6 * 60 <= s.minute_of_day < 18 * 60]
    hours_co2_below = sum(
        dt_h
        for s in steps
        if 6 * 60 <= s.minute_of_day < 18 * 60
        and s.co2_ppm < profile.co2_target_ppm - 50.0
    )

    irrigation_flags = [s.irrigation for s in steps]
    return AnalysisReport(
        crop=result.crop,
        days=result.days,
        control_enabled=result.control_enabled,
        total_water_l=round(steps[-1].water_used_l, 1),
        water_l_per_day=round(steps[-1].water_used_l / result.days, 1),
        irrigation_events=_count_events(irrigation_flags),
        irrigation_minutes=round(sum(irrigation_flags) * result.dt_minutes, 1),
        hours_temp_out_of_range=round(hours_temp_out, 1),
        hours_rh_out_of_range=round(hours_rh_out, 1),
        hours_vpd_out_of_range=round(hours_vpd_out, 1),
        pct_time_in_temp_band=round(
            100.0 * (1.0 - hours_temp_out / total_hours), 1
        ),
        mean_temp_c=round(sum(temps) / len(temps), 2),
        mean_rh_percent=round(sum(rhs) / len(rhs), 1),
        mean_soil_vwc=round(sum(soils) / len(soils), 3),
        min_soil_vwc=round(min(soils), 3),
        max_soil_vwc=round(max(soils), 3),
        mean_daytime_co2_ppm=round(sum(day_co2) / len(day_co2), 0) if day_co2 else 0.0,
        hours_co2_below_target=round(hours_co2_below, 1),
        dli_per_day=dli_per_day,
        mean_dli=round(sum(dli_per_day) / len(dli_per_day), 2) if dli_per_day else 0.0,
        energy_kwh=energy,
        total_energy_kwh=round(sum(energy.values()), 2),
        actuator_duty={k: round(v * 100.0, 1) for k, v in duty.items()},
    )


def compare_runs(
    controlled: AnalysisReport, baseline: AnalysisReport
) -> dict[str, float]:
    """Delta (controlled minus baseline) for the headline metrics.

    Read the water and energy deltas as the *cost* of control: the
    uncontrolled baseline waters nothing, so its water use is 0 L and
    the delta is positive by construction.  Negative out-of-range
    hours = climate improved; positive in-band percentage = better
    control.
    """
    return {
        "water_l_delta": round(
            controlled.total_water_l - baseline.total_water_l, 1
        ),
        "hours_temp_out_delta": round(
            controlled.hours_temp_out_of_range - baseline.hours_temp_out_of_range, 1
        ),
        "hours_rh_out_delta": round(
            controlled.hours_rh_out_of_range - baseline.hours_rh_out_of_range, 1
        ),
        "hours_vpd_out_delta": round(
            controlled.hours_vpd_out_of_range - baseline.hours_vpd_out_of_range, 1
        ),
        "pct_in_band_delta": round(
            controlled.pct_time_in_temp_band - baseline.pct_time_in_temp_band, 1
        ),
        "energy_kwh_controlled": controlled.total_energy_kwh,
        "mean_dli_delta": round(controlled.mean_dli - baseline.mean_dli, 2),
    }
