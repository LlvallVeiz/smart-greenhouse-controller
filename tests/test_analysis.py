"""Tests for analysis.py -- metrics on hand-built time series.

The fixture builds a 1-day run at dt = 60 min where every value is
chosen so the expected metric can be computed by hand:

* 24 steps; day steps (06:00-18:00) at 23 C / 65% RH / VPD 1.0 kPa,
  night steps at 16.5 C -- both inside the tomato bands, so 0 hours
  out of range for temperature, RH and VPD.
* PAR held at 300 / 0.0185 = 16216 lux all day, i.e. PPFD 300, so
  DLI = 300 * 24 * 3600 / 1e6 = 25.92 mol/m2/d.
* Irrigation on for the first 2 steps only: 1 event, 120 min,
  cumulative water 50 L at the last step.
* Heater on for 2 steps: duty 2/24 over 24 h at 1500 W = 3.00 kWh.
* Daytime CO2 held at 1000 ppm: 0 hours below the 950 ppm line.
"""

from datetime import datetime, timedelta

import pytest

from smart_greenhouse_controller.analysis import _count_events, analyze, compare_runs
from smart_greenhouse_controller.simulator import (
    SimulationConfig,
    SimulationResult,
    SimStep,
    run_comparison,
    run_simulation,
)


def _make_steps(**overrides):
    steps = []
    base = datetime(2026, 11, 12, 0, 0)
    for i in range(24):
        minute = i * 60
        is_day = 6 * 60 <= minute < 18 * 60
        steps.append(
            SimStep(
                timestamp=base + timedelta(minutes=minute),
                day_index=0,
                minute_of_day=minute,
                temp_c=23.0 if is_day else 16.5,
                rh_percent=65.0,
                soil_vwc=0.35,
                par_lux=300.0 / 0.0185,
                co2_ppm=1000.0,
                vpd_kpa=1.0,
                irrigation=i < 2,
                fan=False,
                heater=i < 2,
                lights=False,
                co2=False,
                water_used_l=50.0,
                weather="sunny",
            )
        )
    for key, value in overrides.items():
        for s in steps:
            setattr(s, key, value() if callable(value) else value)
    return steps


def _result(**overrides):
    return SimulationResult(
        steps=_make_steps(),
        crop="tomato",
        days=1,
        seed=42,
        control_enabled=True,
        dt_minutes=60.0,
        config=SimulationConfig().greenhouse,
    )


def test_dli_is_hand_computed_value():
    a = analyze(_result())
    assert a.mean_dli == pytest.approx(25.92, abs=0.01)
    assert a.dli_per_day == [pytest.approx(25.92, abs=0.01)]


def test_zero_hours_out_of_range_when_in_band():
    a = analyze(_result())
    assert a.hours_temp_out_of_range == 0.0
    assert a.hours_rh_out_of_range == 0.0
    assert a.hours_vpd_out_of_range == 0.0
    assert a.pct_time_in_temp_band == 100.0


def test_water_and_irrigation_counts():
    a = analyze(_result())
    assert a.total_water_l == 50.0
    assert a.water_l_per_day == 50.0
    assert a.irrigation_events == 1
    assert a.irrigation_minutes == 120.0


def test_energy_from_duty_cycle():
    a = analyze(_result())
    assert a.energy_kwh["heater"] == pytest.approx(3.00, abs=0.01)
    assert a.energy_kwh["fan"] == 0.0
    assert a.total_energy_kwh == pytest.approx(3.00, abs=0.01)
    assert a.actuator_duty["heater"] == pytest.approx(100.0 * 2 / 24, abs=0.1)


def test_means_and_soil_stats():
    a = analyze(_result())
    assert a.mean_temp_c == pytest.approx(19.75, abs=0.01)
    assert a.mean_rh_percent == 65.0
    assert a.mean_soil_vwc == 0.35
    assert a.min_soil_vwc == 0.35
    assert a.max_soil_vwc == 0.35
    assert a.mean_daytime_co2_ppm == 1000.0
    assert a.hours_co2_below_target == 0.0


def test_out_of_range_hours_counted():
    result = _result()
    for s in result.steps:
        s.temp_c = 35.0  # every step out of band
    a = analyze(result)
    assert a.hours_temp_out_of_range == 24.0
    assert a.pct_time_in_temp_band == 0.0


def test_count_events_rising_edges():
    assert _count_events([]) == 0
    assert _count_events([False, False]) == 0
    assert _count_events([True, True, False, True, False]) == 2
    assert _count_events([False, True, True, False]) == 1


def test_analyze_empty_result_raises():
    with pytest.raises(ValueError):
        analyze(SimulationResult(steps=[], crop="tomato", days=0))


def test_compare_runs_arithmetic():
    on = analyze(_result())
    off_result = _result()
    for s in off_result.steps:
        s.temp_c = 35.0
        s.water_used_l = 0.0
    off = analyze(off_result)
    comp = compare_runs(on, off)
    assert comp["water_l_delta"] == 50.0
    assert comp["hours_temp_out_delta"] == -24.0
    assert comp["pct_in_band_delta"] == 100.0


def test_real_runs_control_beats_baseline_on_temperature():
    """End-to-end property: over 7 identical-weather days the
    controller keeps the greenhouse in band far more than no control."""
    on, off = run_comparison(SimulationConfig(crop="tomato", days=7, seed=42))
    on_a, off_a = analyze(on), analyze(off)
    assert on_a.pct_time_in_temp_band > off_a.pct_time_in_temp_band
    assert on_a.hours_temp_out_of_range < off_a.hours_temp_out_of_range
    assert on_a.total_water_l > 0.0
    assert off_a.total_water_l == 0.0
