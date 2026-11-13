"""Tests for crops.py -- profiles match the researched sources."""

import pytest

from smart_greenhouse_controller.crops import (
    PROFILES,
    get_profile,
    list_profiles,
)


def test_five_profiles_exist():
    assert set(PROFILES) == {"tomato", "lettuce", "cucumber", "pepper", "basil"}


def test_tomato_bands_from_research():
    p = get_profile("tomato")
    assert (p.temp_day_min, p.temp_day_max) == (20.0, 27.0)
    assert (p.temp_night_min, p.temp_night_max) == (15.0, 18.0)
    assert (p.rh_min, p.rh_max) == (60.0, 70.0)
    assert (p.soil_irrigate_below, p.soil_stop_above) == (0.30, 0.44)
    assert p.co2_target_ppm == 1000.0
    assert (p.vpd_min, p.vpd_max) == (0.8, 1.4)


def test_lettuce_is_cooler_than_tomato():
    lettuce = get_profile("lettuce")
    tomato = get_profile("tomato")
    assert lettuce.temp_day_max < tomato.temp_day_max
    assert lettuce.temp_night_max < tomato.temp_night_min
    assert lettuce.vpd_max < tomato.vpd_max
    assert lettuce.co2_target_ppm <= tomato.co2_target_ppm


def test_cucumber_likes_humidity():
    p = get_profile("cucumber")
    assert p.rh_min == 70.0
    assert p.temp_day_min >= 22.0


def test_irrigation_band_is_ordered_for_every_crop():
    for p in list_profiles():
        assert 0.0 < p.soil_irrigate_below < p.soil_stop_above < 0.6
        assert p.temp_day_min < p.temp_day_max
        assert p.temp_night_min < p.temp_night_max
        assert p.rh_min < p.rh_max
        assert p.vpd_min < p.vpd_max
        assert p.sources, f"{p.name} must cite sources"


def test_get_profile_case_insensitive():
    assert get_profile("Tomato").name == "tomato"
    assert get_profile(" LETTUCE ").name == "lettuce"


def test_get_profile_unknown_raises_with_hint():
    with pytest.raises(KeyError, match="known crops"):
        get_profile("durian")


def test_list_profiles_sorted_and_complete():
    names = [p.name for p in list_profiles()]
    assert names == sorted(names)
    assert len(names) == 5
