"""Tests for physics.py -- every expected value is hand-computed.

* SVP at 25 C: 0.6108 * exp(17.27*25 / 262.3) = 0.6108 * exp(1.6459)
  = 0.6108 * 5.186 = 3.168 kPa (textbook value: 3.17 kPa).
* VPD at 25 C / 60% RH: 3.168 * 0.40 = 1.267 kPa.
* Dew point at 25 C / 60% RH: Magnus inversion gives 16.70 C
  (textbook value ~16.7 C).
* DLI of 300 umol/m2/s for 12 h: 300 * 12 * 3600 / 1e6 = 12.96.
"""

import math

import pytest

from smart_greenhouse_controller.physics import (
    clamp,
    daily_light_integral,
    dew_point,
    lux_to_ppfd,
    ppfd_to_lux,
    saturation_vapor_pressure,
    vapor_pressure_deficit,
)


def test_svp_at_0c_is_tetens_constant():
    assert saturation_vapor_pressure(0.0) == pytest.approx(0.6108, abs=1e-9)


def test_svp_at_25c_matches_textbook():
    assert saturation_vapor_pressure(25.0) == pytest.approx(3.17, abs=0.01)


def test_svp_increases_with_temperature():
    assert saturation_vapor_pressure(30.0) > saturation_vapor_pressure(20.0) > saturation_vapor_pressure(10.0)


def test_svp_at_20c():
    # 0.6108 * exp(17.27*20/257.3) = 0.6108 * exp(1.3422) = 2.338 kPa.
    assert saturation_vapor_pressure(20.0) == pytest.approx(2.34, abs=0.01)


def test_vpd_at_25c_60rh():
    assert vapor_pressure_deficit(25.0, 60.0) == pytest.approx(1.267, abs=0.01)


def test_vpd_zero_at_saturation():
    assert vapor_pressure_deficit(22.0, 100.0) == pytest.approx(0.0, abs=1e-9)


def test_vpd_equals_svp_in_dry_air():
    assert vapor_pressure_deficit(25.0, 0.0) == pytest.approx(
        saturation_vapor_pressure(25.0), abs=1e-9
    )


def test_vpd_rejects_bad_rh():
    with pytest.raises(ValueError):
        vapor_pressure_deficit(25.0, 101.0)
    with pytest.raises(ValueError):
        vapor_pressure_deficit(25.0, -1.0)


def test_dew_point_at_25c_60rh():
    assert dew_point(25.0, 60.0) == pytest.approx(16.7, abs=0.15)


def test_dew_point_equals_temp_at_saturation():
    assert dew_point(20.0, 100.0) == pytest.approx(20.0, abs=0.05)


def test_dew_point_below_air_temp():
    assert dew_point(25.0, 40.0) < 25.0
    assert dew_point(25.0, 40.0) < dew_point(25.0, 80.0)


def test_dew_point_rejects_zero_rh():
    with pytest.raises(ValueError):
        dew_point(25.0, 0.0)


def test_dli_300_for_12h():
    ppfd = [300.0] * 12  # one value per hour
    assert daily_light_integral(ppfd, 3600.0) == pytest.approx(12.96, abs=1e-9)


def test_dli_zero_light_is_zero():
    assert daily_light_integral([0.0] * 24, 3600.0) == 0.0


def test_dli_rejects_bad_dt():
    with pytest.raises(ValueError):
        daily_light_integral([100.0], 0.0)


def test_lux_ppfd_roundtrip():
    assert lux_to_ppfd(10_000) == pytest.approx(185.0, abs=1e-9)
    assert ppfd_to_lux(185.0) == pytest.approx(10_000.0, abs=1e-6)
    assert lux_to_ppfd(0.0) == 0.0


def test_lux_ppfd_rejects_negative():
    with pytest.raises(ValueError):
        lux_to_ppfd(-5.0)
    with pytest.raises(ValueError):
        ppfd_to_lux(-5.0)


def test_clamp():
    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-3.0, 0.0, 10.0) == 0.0
    assert clamp(99.0, 0.0, 10.0) == 10.0
