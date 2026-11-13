"""Markdown report generator for a simulation run (and A/B comparison)."""

from __future__ import annotations

from .analysis import AnalysisReport
from .crops import get_profile
from .simulator import SimulationResult


def _fmt_hours(hours: float) -> str:
    return f"{hours:.1f} h"


def render_report(
    result: SimulationResult,
    analysis: AnalysisReport,
    baseline: AnalysisReport | None = None,
    comparison: dict[str, float] | None = None,
) -> str:
    """Render the full Markdown report for a run."""
    profile = get_profile(result.crop)
    lines: list[str] = []
    lines.append(f"# Greenhouse Report — {profile.name.title()} ({profile.latin_name})")
    lines.append("")
    lines.append(
        f"Simulated **{result.days} days** (seed {result.seed}, "
        f"dt {result.dt_minutes:.0f} min, {len(result.steps)} steps) with "
        f"control **{'ON' if result.control_enabled else 'OFF'}**. "
        f"Greenhouse {result.config.floor_area_m2:.0f} m2, "
        f"drip flow {result.config.irrigation_flow_l_min:.1f} L/min."
    )
    lines.append("")
    lines.append("## Crop targets (from `docs/RESEARCH.md`)")
    lines.append("")
    lines.append(
        f"- Temperature: day {profile.temp_day_min:.0f}-{profile.temp_day_max:.0f} C, "
        f"night {profile.temp_night_min:.0f}-{profile.temp_night_max:.0f} C"
    )
    lines.append(f"- Relative humidity: {profile.rh_min:.0f}-{profile.rh_max:.0f}%")
    lines.append(
        f"- Soil VWC: irrigate below {profile.soil_irrigate_below:.2f}, "
        f"stop above {profile.soil_stop_above:.2f}"
    )
    lines.append(f"- CO2 target: {profile.co2_target_ppm:.0f} ppm (daylight)")
    lines.append(f"- Light: {profile.ppfd_target:.0f} umol/m2/s, {profile.photoperiod_hours:.0f} h photoperiod")
    lines.append(f"- VPD band: {profile.vpd_min:.1f}-{profile.vpd_max:.1f} kPa")
    lines.append("")
    lines.append("## Water")
    lines.append("")
    lines.append(f"- Total water used: **{analysis.total_water_l:.1f} L** "
                 f"({analysis.water_l_per_day:.1f} L/day)")
    lines.append(f"- Irrigation events: {analysis.irrigation_events} "
                 f"({analysis.irrigation_minutes:.0f} min of valve-open time)")
    lines.append(
        f"- Soil VWC: mean {analysis.mean_soil_vwc:.3f}, "
        f"min {analysis.min_soil_vwc:.3f}, max {analysis.max_soil_vwc:.3f}"
    )
    lines.append("")
    lines.append("## Climate compliance")
    lines.append("")
    lines.append(
        f"- Time in temperature band: **{analysis.pct_time_in_temp_band:.1f}%** "
        f"({analysis.hours_temp_out_of_range:.1f} h out of range over {result.days} days)"
    )
    lines.append(f"- Hours RH out of range: {_fmt_hours(analysis.hours_rh_out_of_range)}")
    lines.append(f"- Hours VPD out of range: {_fmt_hours(analysis.hours_vpd_out_of_range)}")
    lines.append(f"- Mean temperature: {analysis.mean_temp_c:.2f} C, mean RH: {analysis.mean_rh_percent:.1f}%")
    lines.append("")
    lines.append("## Light and CO2")
    lines.append("")
    lines.append(
        f"- Mean DLI: **{analysis.mean_dli:.2f} mol/m2/d** "
        f"(per day: {', '.join(f'{d:.1f}' for d in analysis.dli_per_day)})"
    )
    lines.append(f"- Mean daytime CO2: {analysis.mean_daytime_co2_ppm:.0f} ppm")
    lines.append(f"- Hours CO2 below target: {_fmt_hours(analysis.hours_co2_below_target)}")
    lines.append("")
    lines.append("## Energy and actuator duty")
    lines.append("")
    lines.append(f"- Total energy: **{analysis.total_energy_kwh:.2f} kWh**")
    for name, kwh in analysis.energy_kwh.items():
        lines.append(f"  - {name}: {kwh:.2f} kWh ({analysis.actuator_duty[name]:.1f}% duty)")
    lines.append(f"- Irrigation duty: {analysis.actuator_duty['irrigation']:.1f}%, "
                 f"CO2 injector duty: {analysis.actuator_duty['co2']:.1f}%")
    lines.append("")

    if baseline is not None and comparison is not None:
        lines.append("## Control ON vs OFF (identical weather, same seed)")
        lines.append("")
        lines.append(
            f"- Water: {comparison['water_l_delta']:+.1f} L "
            f"(controlled {analysis.total_water_l:.1f} L vs baseline {baseline.total_water_l:.1f} L) "
            f"-- the baseline waters nothing, so this is the *cost* of keeping the soil in band, not a saving"
        )
        lines.append(
            f"- Hours temperature out of range: {comparison['hours_temp_out_delta']:+.1f} h "
            f"(controlled {analysis.hours_temp_out_of_range:.1f} h vs baseline {baseline.hours_temp_out_of_range:.1f} h)"
        )
        lines.append(
            f"- Hours RH out of range: {comparison['hours_rh_out_delta']:+.1f} h"
        )
        lines.append(
            f"- Hours VPD out of range: {comparison['hours_vpd_out_delta']:+.1f} h"
        )
        lines.append(
            f"- Time in temperature band: {comparison['pct_in_band_delta']:+.1f} percentage points"
        )
        lines.append(
            f"- Mean DLI: {comparison['mean_dli_delta']:+.2f} mol/m2/d "
            f"(supplemental lighting effect)"
        )
        lines.append(
            f"- Energy cost of control: {comparison['energy_kwh_controlled']:.2f} kWh "
            f"over {result.days} days"
        )
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "This is a simulation: the environment model is a first-order "
        "approximation (see `docs/RESEARCH.md` and `docs/CONTROL_DESIGN.md` "
        "for assumptions and limits). Numbers describe the model, not a "
        "real greenhouse."
    )
    lines.append("")
    return "\n".join(lines)
