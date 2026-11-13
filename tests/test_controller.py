"""Tests for controller.py -- hysteresis, interlocks and safety limits.

The hysteresis tests are the heart of this project: a controller with a
single threshold would chatter; the latched controller must hold its
state across the dead-band.  All readings below are built for the
tomato profile: day temp band 20-27 C, night 15-18 C, RH 60-70%,
soil irrigate < 0.30 / stop > 0.44, CO2 target 1000 ppm.
"""

import pytest

from smart_greenhouse_controller.controller import Controller
from smart_greenhouse_controller.crops import get_profile
from smart_greenhouse_controller.sensors import SensorReading

DAY = 12 * 60  # noon
NIGHT = 2 * 60  # 02:00


def _reading(**overrides):
    base = dict(
        temp_c=23.0,
        rh_percent=65.0,
        soil_vwc=0.35,
        par_lux=30_000.0,
        co2_ppm=900.0,
        vpd_kpa=1.0,
    )
    base.update(overrides)
    return SensorReading(**base)


@pytest.fixture
def tomato():
    return Controller(get_profile("tomato"))


def test_irrigation_starts_below_threshold(tomato):
    act = tomato.decide(_reading(soil_vwc=0.25), DAY, 0)
    assert act.irrigation is True


def test_irrigation_stays_on_inside_deadband(tomato):
    """Soil 0.32 is above the start threshold but below the stop one:
    the valve must stay open (no chatter)."""
    tomato.decide(_reading(soil_vwc=0.25), DAY, 0)
    act = tomato.decide(_reading(soil_vwc=0.32), DAY, 0)
    assert act.irrigation is True


def test_irrigation_stops_at_stop_threshold(tomato):
    tomato.decide(_reading(soil_vwc=0.25), DAY, 0)
    act = tomato.decide(_reading(soil_vwc=0.45), DAY, 0)
    assert act.irrigation is False


def test_irrigation_does_not_restart_until_dry_again(tomato):
    tomato.decide(_reading(soil_vwc=0.25), DAY, 0)
    tomato.decide(_reading(soil_vwc=0.45), DAY, 0)
    # 0.35 is between the thresholds: must NOT restart.
    act = tomato.decide(_reading(soil_vwc=0.35), DAY, 0)
    assert act.irrigation is False
    act = tomato.decide(_reading(soil_vwc=0.29), DAY, 0)
    assert act.irrigation is True


def test_irrigation_never_runs_when_soil_is_wet(tomato):
    act = tomato.decide(_reading(soil_vwc=0.50), DAY, 0)
    assert act.irrigation is False


def test_irrigation_blocked_outside_window(tomato):
    # 02:00 is outside the default 05:00-19:00 window.
    act = tomato.decide(_reading(soil_vwc=0.10), NIGHT, 0)
    assert act.irrigation is False


def test_irrigation_max_duration_stops_valve(tomato):
    """With soil pinned at 0.10 the valve must stop after 20 minutes
    (4 steps of 5 min) even though the soil is still dry."""
    states = [
        tomato.decide(_reading(soil_vwc=0.10), DAY, 0, dt_minutes=5.0).irrigation
        for _ in range(8)
    ]
    assert states[:4] == [True, True, True, True]
    assert states[4] is False
    # Cool-down: it must not restart on the very next step.
    assert states[5] is False


def test_irrigation_event_counter_resets_daily(tomato):
    tomato.decide(_reading(soil_vwc=0.10), DAY, 0)
    assert tomato.state.irrigation_events_today == 1
    tomato.decide(_reading(soil_vwc=0.35), DAY, 1)
    assert tomato.state.irrigation_events_today == 0


def test_heater_hysteresis(tomato):
    # Day band min is 20 C: heater on at <= 19, off at >= 21.
    assert tomato.decide(_reading(temp_c=18.0), DAY, 0).heater is True
    assert tomato.decide(_reading(temp_c=20.0), DAY, 0).heater is True
    assert tomato.decide(_reading(temp_c=21.5), DAY, 0).heater is False
    assert tomato.decide(_reading(temp_c=20.5), DAY, 0).heater is False
    assert tomato.decide(_reading(temp_c=18.5), DAY, 0).heater is True


def test_fan_hysteresis_on_temperature(tomato):
    # Day band max is 27 C: fan on at >= 28, off at <= 26.
    assert tomato.decide(_reading(temp_c=29.0), DAY, 0).fan is True
    assert tomato.decide(_reading(temp_c=27.0), DAY, 0).fan is True
    assert tomato.decide(_reading(temp_c=25.5), DAY, 0).fan is False


def test_fan_hysteresis_on_humidity(tomato):
    # RH max 70%: fan on at >= 75, off once back to <= 65.
    assert tomato.decide(_reading(rh_percent=80.0), DAY, 0).fan is True
    assert tomato.decide(_reading(rh_percent=72.0), DAY, 0).fan is True
    assert tomato.decide(_reading(rh_percent=64.0, temp_c=23.0), DAY, 0).fan is False


def test_heater_and_fan_never_on_together(tomato):
    # Sweep the temperature from freezing to scorching: the interlock
    # must hold at every step.
    for temp in [x * 0.5 for x in range(0, 80)]:
        act = tomato.decide(_reading(temp_c=temp), DAY, 0)
        assert not (act.heater and act.fan), f"both on at {temp} C"


def test_no_oscillation_at_fixed_near_threshold_reading(tomato):
    """A constant reading just inside the dead-band must not toggle
    the heater more than once."""
    states = [
        tomato.decide(_reading(temp_c=19.5), DAY, 0).heater for _ in range(20)
    ]
    transitions = sum(
        1 for a, b in zip(states, states[1:]) if a != b
    )
    assert transitions <= 1


def test_lights_on_when_dark_in_photoperiod(tomato):
    act = tomato.decide(_reading(par_lux=0.0), DAY, 0)
    assert act.lights is True


def test_lights_off_when_bright_or_at_night(tomato):
    assert tomato.decide(_reading(par_lux=60_000.0), DAY, 0).lights is False
    assert tomato.decide(_reading(par_lux=0.0), NIGHT, 0).lights is False


def test_co2_on_in_daylight_with_fan_off(tomato):
    act = tomato.decide(_reading(co2_ppm=800.0), DAY, 0)
    assert act.co2 is True


def test_co2_off_when_fan_is_running(tomato):
    # Hot + low CO2: the fan must run and CO2 must stay off (venting
    # would dump the enriched air outside).
    act = tomato.decide(_reading(temp_c=30.0, co2_ppm=700.0), DAY, 0)
    assert act.fan is True
    assert act.co2 is False


def test_co2_off_at_night_and_at_target(tomato):
    assert tomato.decide(_reading(co2_ppm=800.0), NIGHT, 0).co2 is False
    assert tomato.decide(_reading(co2_ppm=1100.0), DAY, 0).co2 is False


def test_manual_mode_forces_states_but_keeps_interlock():
    ctrl = Controller(
        get_profile("tomato"),
        mode="manual",
        manual={"heater": True, "fan": True, "irrigation": True},
    )
    act = ctrl.decide(_reading(), DAY, 0)
    assert act.irrigation is True
    assert act.fan is True
    assert act.heater is False  # interlock: fan wins


def test_manual_mode_defaults_everything_off():
    ctrl = Controller(get_profile("tomato"), mode="manual")
    act = ctrl.decide(_reading(), DAY, 0)
    assert act.as_dict() == {
        "irrigation": False,
        "fan": False,
        "heater": False,
        "lights": False,
        "co2": False,
    }


def test_bad_mode_rejected():
    with pytest.raises(ValueError):
        Controller(get_profile("tomato"), mode="weird")
    ctrl = Controller(get_profile("tomato"))
    with pytest.raises(ValueError):
        ctrl.set_mode("weird")


def test_night_temperature_band_is_used():
    # 16 C at night is inside the night band (15-18): no heater, no fan.
    ctrl = Controller(get_profile("tomato"))
    act = ctrl.decide(_reading(temp_c=16.0), NIGHT, 0)
    assert act.heater is False
    assert act.fan is False
    # 16 C at noon is below the day band: heater on.
    ctrl2 = Controller(get_profile("tomato"))
    act2 = ctrl2.decide(_reading(temp_c=16.0), DAY, 0)
    assert act2.heater is True


def test_lettuce_uses_cooler_thresholds():
    ctrl = Controller(get_profile("lettuce"))
    # 19 C is below tomato's day min but inside lettuce's day band.
    act = ctrl.decide(_reading(temp_c=19.0), DAY, 0)
    assert act.heater is False
    assert act.fan is False
