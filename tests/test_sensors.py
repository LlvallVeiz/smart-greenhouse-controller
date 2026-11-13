"""Tests for sensors.py -- environment dynamics and determinism."""

import pytest

from smart_greenhouse_controller.physics import saturation_vapor_pressure
from smart_greenhouse_controller.sensors import (
    AMBIENT_CO2_PPM,
    Actuators,
    GreenhouseEnvironment,
    WeatherGenerator,
)


def _quiet_env(**kwargs):
    """Environment with zero sensor noise for exact assertions."""
    from smart_greenhouse_controller.sensors import GreenhouseConfig

    cfg = GreenhouseConfig(
        noise_temp_c=0.0,
        noise_rh_percent=0.0,
        noise_soil_vwc=0.0,
        noise_par_lux=0.0,
        noise_co2_ppm=0.0,
    )
    return GreenhouseEnvironment(config=cfg, **kwargs)


def test_outdoor_temp_max_at_14h_min_at_02h():
    env = _quiet_env()
    assert env.outdoor_temp_c(14 * 60) == pytest.approx(25.0, abs=1e-9)
    assert env.outdoor_temp_c(2 * 60) == pytest.approx(15.0, abs=1e-9)
    assert env.outdoor_temp_c(8 * 60) == pytest.approx(20.0, abs=1e-9)


def test_solar_par_zero_at_night_and_peak_at_noon():
    env = _quiet_env()
    assert env.solar_par_lux(0) == 0.0
    assert env.solar_par_lux(5 * 60) == 0.0
    assert env.solar_par_lux(12 * 60) == pytest.approx(60_000.0, abs=1e-6)
    assert env.solar_par_lux(18 * 60) == 0.0
    assert 0.0 < env.solar_par_lux(9 * 60) < 60_000.0


def test_weather_generator_is_deterministic():
    a = WeatherGenerator(seed=7)
    b = WeatherGenerator(seed=7)
    seq_a = [a.next_day().condition for _ in range(30)]
    seq_b = [b.next_day().condition for _ in range(30)]
    assert seq_a == seq_b
    assert set(seq_a) <= {"sunny", "cloudy", "rainy"}


def test_weather_day_parameters_are_sane():
    gen = WeatherGenerator(seed=3)
    for _ in range(20):
        day = gen.next_day()
        assert 0.15 <= day.cloud_factor <= 1.0
        assert 30.0 <= day.outdoor_rh <= 98.0


def test_soil_dries_without_irrigation():
    env = _quiet_env(initial_soil_vwc=0.40)
    before = env.true_state()["soil_vwc"]
    for _ in range(12):  # one hour, no irrigation
        env.step(Actuators(), dt_minutes=5.0)
    after = env.true_state()["soil_vwc"]
    assert after < before
    assert after > 0.30  # one hour of drying is modest


def test_irrigation_raises_soil_by_flow_over_volume():
    # 2 L/min for 5 min into 500 L wetted volume = +0.02 VWC per step,
    # minus a small evapotranspiration loss.
    env = _quiet_env(initial_soil_vwc=0.30, initial_temp_c=20.0)
    env.step(Actuators(irrigation=True), dt_minutes=5.0)
    after = env.true_state()["soil_vwc"]
    assert after == pytest.approx(0.30 + 0.02, abs=0.002)
    assert env.water_used_l == pytest.approx(10.0, abs=1e-9)


def test_soil_drainage_above_field_capacity():
    env = _quiet_env(initial_soil_vwc=0.50)
    env.step(Actuators(), dt_minutes=5.0)
    assert env.true_state()["soil_vwc"] < 0.50


def test_heater_warms_and_fan_cools():
    hot = _quiet_env(initial_temp_c=30.0)
    hot.step(Actuators(fan=True), dt_minutes=5.0)
    assert hot.true_state()["temp_c"] < 30.0

    cold = _quiet_env(initial_temp_c=15.0)
    cold.step(Actuators(heater=True), dt_minutes=5.0)
    assert cold.true_state()["temp_c"] > 15.0


def test_co2_injector_raises_co2_and_vent_resets_toward_ambient():
    env = _quiet_env(initial_co2_ppm=400.0)
    env.step(Actuators(co2=True), dt_minutes=5.0)
    assert env.true_state()["co2_ppm"] > 400.0
    assert env.co2_used_g == pytest.approx(25.0, abs=1e-9)

    env2 = _quiet_env(initial_co2_ppm=900.0)
    env2.step(Actuators(fan=True), dt_minutes=5.0)
    after = env2.true_state()["co2_ppm"]
    assert AMBIENT_CO2_PPM < after < 900.0


def test_environment_is_deterministic_with_same_seed():
    def run():
        env = GreenhouseEnvironment(seed=11)
        readings = []
        for _ in range(50):
            readings.append(env.step(Actuators(irrigation=True)).as_dict())
        return readings

    assert run() == run()


def test_readings_stay_in_physical_ranges():
    env = GreenhouseEnvironment(seed=5)
    for _ in range(200):
        r = env.step(Actuators(fan=True, heater=True, irrigation=True))
        assert 0.0 <= r.rh_percent <= 100.0
        assert 0.0 <= r.soil_vwc <= 1.0
        assert r.par_lux >= 0.0
        assert r.co2_ppm >= 0.0
        assert r.vpd_kpa >= 0.0


def test_saturation_vapour_pressure_helper():
    env = _quiet_env(initial_temp_c=25.0)
    assert env.saturation_vapor_pressure_now() == pytest.approx(
        saturation_vapor_pressure(25.0), abs=1e-9
    )
