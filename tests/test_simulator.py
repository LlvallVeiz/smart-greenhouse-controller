"""Tests for simulator.py -- run shape, determinism, A/B comparison."""

import pytest

from smart_greenhouse_controller.simulator import (
    SimulationConfig,
    run_comparison,
    run_simulation,
)


def _cfg(**overrides):
    data = dict(crop="tomato", days=2, seed=42)
    data.update(overrides)
    return SimulationConfig(**data)


def test_one_day_has_288_steps_at_5_min():
    result = run_simulation(_cfg(days=1))
    assert len(result) == 288
    assert result.days == 1
    assert result.crop == "tomato"


def test_different_dt_changes_step_count():
    result = run_simulation(_cfg(days=1, dt_minutes=15.0))
    assert len(result) == 96


def test_run_is_deterministic_for_same_seed():
    a = run_simulation(_cfg(days=2, seed=9))
    b = run_simulation(_cfg(days=2, seed=9))
    assert [s.as_dict() for s in a.steps] == [s.as_dict() for s in b.steps]


def test_different_seeds_give_different_weather():
    a = run_simulation(_cfg(days=7, seed=1))
    b = run_simulation(_cfg(days=7, seed=2))
    temps_a = [s.temp_c for s in a.steps]
    temps_b = [s.temp_c for s in b.steps]
    assert temps_a != temps_b


def test_heater_and_fan_never_both_on_in_a_week():
    result = run_simulation(_cfg(days=7, seed=42))
    assert all(not (s.heater and s.fan) for s in result.steps)


def test_controlled_run_irrigates_and_uses_water():
    result = run_simulation(_cfg(days=7, seed=42))
    assert any(s.irrigation for s in result.steps)
    assert result.steps[-1].water_used_l > 0.0


def test_uncontrolled_run_uses_no_water_or_energy_actuators():
    result = run_simulation(_cfg(days=3, seed=42, control_enabled=False))
    assert not any(s.irrigation for s in result.steps)
    assert not any(s.heater for s in result.steps)
    assert not any(s.fan for s in result.steps)
    assert result.steps[-1].water_used_l == 0.0


def test_comparison_shares_weather_but_differs_in_control():
    on, off = run_comparison(_cfg(days=3, seed=42))
    assert [s.weather for s in on.steps] == [s.weather for s in off.steps]
    assert on.control_enabled is True
    assert off.control_enabled is False
    assert len(on) == len(off)


def test_unknown_crop_raises():
    with pytest.raises(KeyError):
        run_simulation(_cfg(crop="durian"))


def test_config_roundtrip_through_dict():
    cfg = SimulationConfig(crop="lettuce", days=5, seed=3, dt_minutes=10.0)
    rebuilt = SimulationConfig.from_dict(cfg.to_dict())
    assert rebuilt.crop == "lettuce"
    assert rebuilt.days == 5
    assert rebuilt.seed == 3
    assert rebuilt.dt_minutes == 10.0
    assert rebuilt.greenhouse.floor_area_m2 == cfg.greenhouse.floor_area_m2


def test_timestamps_advance_monotonically():
    result = run_simulation(_cfg(days=1))
    stamps = [s.timestamp for s in result.steps]
    assert stamps == sorted(stamps)
    assert (stamps[1] - stamps[0]).total_seconds() == 300.0
