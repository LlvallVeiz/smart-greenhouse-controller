"""Realistic greenhouse environment model (the "plant" being controlled).

The environment is a first-order dynamic model stepped at a fixed
timestep:

* **Air temperature** follows a diurnal outdoor cycle (max ~14:00, min
  ~02:00) plus solar gain, and relaxes toward the outdoor temperature
  with a time constant; the heater adds heat and the vent/fan removes
  it (and exchanges air with the outside).
* **Relative humidity** relaxes toward a temperature-dependent level,
  rises a little while irrigating, and is pulled toward outdoor RH
  when the vent is open.
* **Soil moisture (VWC)** dries by evapotranspiration, which scales
  with VPD and light; irrigation adds water at the emitter rate and
  water drains when the soil is above field capacity.
* **PAR** is a daylight bell curve (sunrise ~06:00, sunset ~18:00)
  scaled by cloud cover, plus the grow-light contribution.
* **CO2** is drawn down by photosynthesis in daylight, rises from
  respiration at night, exchanges with outdoor air (~420 ppm) when
  venting, and rises while the CO2 injector runs.

Weather is a seeded Markov chain over sunny / cloudy / rainy days so
runs are reproducible.  Sensor readings add Gaussian noise on top of
the true state, like a real sensor node would report.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .physics import clamp, lux_to_ppfd, saturation_vapor_pressure, vapor_pressure_deficit

#: Outdoor CO2 concentration (ppm) -- current ambient level.
AMBIENT_CO2_PPM = 420.0

#: Field capacity of the (loam-like) soil used in the model, as VWC.
FIELD_CAPACITY_VWC = 0.45

#: Permanent wilting point, as VWC.
WILTING_POINT_VWC = 0.12


@dataclass
class Actuators:
    """Actuator states commanded by the controller for one timestep."""

    irrigation: bool = False
    fan: bool = False  # vent / exhaust fan
    heater: bool = False
    lights: bool = False  # supplemental grow lights
    co2: bool = False  # CO2 injector

    def as_dict(self) -> dict[str, bool]:
        return {
            "irrigation": self.irrigation,
            "fan": self.fan,
            "heater": self.heater,
            "lights": self.lights,
            "co2": self.co2,
        }


@dataclass
class SensorReading:
    """One (noisy) sensor snapshot, as a sensor node would report it."""

    temp_c: float
    rh_percent: float
    soil_vwc: float  # fraction 0..1
    par_lux: float
    co2_ppm: float
    vpd_kpa: float

    def as_dict(self) -> dict[str, float]:
        return {
            "temp_c": self.temp_c,
            "rh_percent": self.rh_percent,
            "soil_vwc": self.soil_vwc,
            "par_lux": self.par_lux,
            "co2_ppm": self.co2_ppm,
            "vpd_kpa": self.vpd_kpa,
        }


@dataclass
class WeatherDay:
    """Weather for one simulated day."""

    condition: str  # "sunny" | "cloudy" | "rainy"
    cloud_factor: float  # 1.0 = clear sky, lower = more cloud
    temp_offset_c: float  # shift of the outdoor diurnal curve
    outdoor_rh: float  # %


# Markov transition table: P(next | current). Rows sum to 1.
_WEATHER_TRANSITIONS: dict[str, dict[str, float]] = {
    "sunny": {"sunny": 0.65, "cloudy": 0.30, "rainy": 0.05},
    "cloudy": {"sunny": 0.35, "cloudy": 0.45, "rainy": 0.20},
    "rainy": {"sunny": 0.25, "cloudy": 0.45, "rainy": 0.30},
}

_WEATHER_PARAMS: dict[str, tuple[float, float, float]] = {
    # condition -> (cloud_factor, temp_offset_c, outdoor_rh %)
    "sunny": (1.00, 2.0, 55.0),
    "cloudy": (0.55, 0.0, 70.0),
    "rainy": (0.25, -2.0, 88.0),
}


class WeatherGenerator:
    """Seeded daily-weather generator (Markov chain over conditions)."""

    def __init__(self, seed: int = 42, start_condition: str = "sunny"):
        self._rng = random.Random(seed)
        self._current = start_condition

    def next_day(self) -> WeatherDay:
        probs = _WEATHER_TRANSITIONS[self._current]
        roll = self._rng.random()
        cumulative = 0.0
        nxt = self._current
        for condition, p in probs.items():
            cumulative += p
            if roll <= cumulative:
                nxt = condition
                break
        self._current = nxt
        cloud, offset, rh = _WEATHER_PARAMS[nxt]
        # Small day-to-day jitter so no two days are identical.
        cloud = clamp(cloud + self._rng.uniform(-0.05, 0.05), 0.15, 1.0)
        offset += self._rng.uniform(-1.0, 1.0)
        rh = clamp(rh + self._rng.uniform(-5.0, 5.0), 30.0, 98.0)
        return WeatherDay(nxt, cloud, offset, rh)


@dataclass
class GreenhouseConfig:
    """Physical parameters of the simulated greenhouse."""

    floor_area_m2: float = 24.0  # 6 m x 4 m hobby greenhouse
    soil_depth_m: float = 0.30
    # Irrigation: drip emitters, litres per minute while the valve is open.
    irrigation_flow_l_min: float = 2.0
    # Effective wetted root-zone volume (L) that the drip water spreads
    # into.  Drip emitters wet bulbs around the lines, not the whole bed,
    # so the VWC rise per litre is much larger than floor-area / depth
    # would suggest: 2 L/min into 500 L raises VWC by 0.004/min, i.e.
    # a 20-minute cycle adds ~0.08 VWC.
    wetted_soil_volume_l: float = 500.0
    # Actuator power ratings (W) for the energy estimate.
    heater_power_w: float = 1500.0
    fan_power_w: float = 120.0
    lights_power_w: float = 400.0
    co2_flow_g_min: float = 5.0  # CO2 mass flow while injecting
    # Thermal time constant of the greenhouse air (minutes).
    thermal_tau_min: float = 45.0
    # Outdoor climate baseline (diurnal sinusoid, max ~14:00).
    outdoor_mean_c: float = 20.0
    outdoor_amplitude_c: float = 5.0
    # Sensor noise (standard deviation) per channel.
    noise_temp_c: float = 0.2
    noise_rh_percent: float = 1.5
    noise_soil_vwc: float = 0.005
    noise_par_lux: float = 150.0
    noise_co2_ppm: float = 12.0


class GreenhouseEnvironment:
    """Stateful greenhouse: step it with actuator commands, read sensors."""

    def __init__(
        self,
        config: GreenhouseConfig | None = None,
        seed: int = 42,
        initial_temp_c: float = 20.0,
        initial_rh: float = 65.0,
        initial_soil_vwc: float = 0.35,
        initial_co2_ppm: float = 420.0,
    ):
        self.config = config or GreenhouseConfig()
        self._rng = random.Random(seed)
        self.temp_c = initial_temp_c
        self.rh_percent = initial_rh
        self.soil_vwc = initial_soil_vwc
        self.co2_ppm = initial_co2_ppm
        self.minute_of_day = 6 * 60  # start at 06:00
        self.day_index = 0
        self.weather = WeatherDay("sunny", 1.0, 0.0, 55.0)
        self._weather_gen = WeatherGenerator(seed=seed + 1)
        self.water_used_l = 0.0
        self.co2_used_g = 0.0

    # -- outdoor / solar forcing -------------------------------------------

    def outdoor_temp_c(self, minute_of_day: int) -> float:
        """Outdoor air temperature: sinusoid, max ~14:00, min ~02:00."""
        mean = self.config.outdoor_mean_c + self.weather.temp_offset_c
        amplitude = self.config.outdoor_amplitude_c
        phase = 2.0 * math.pi * (minute_of_day - 14 * 60) / (24 * 60)
        return mean + amplitude * math.cos(phase)

    def solar_par_lux(self, minute_of_day: int) -> float:
        """Daylight PAR as illuminance: bell curve 06:00-18:00."""
        sunrise, sunset = 6 * 60, 18 * 60
        if minute_of_day <= sunrise or minute_of_day >= sunset:
            return 0.0
        frac = (minute_of_day - sunrise) / (sunset - sunrise)
        bell = math.sin(math.pi * frac) ** 1.5
        return 60_000.0 * bell * self.weather.cloud_factor

    def is_daylight(self, minute_of_day: int) -> bool:
        return 6 * 60 <= minute_of_day < 18 * 60

    # -- one step ------------------------------------------------------------

    def step(
        self, actuators: Actuators, dt_minutes: float = 5.0
    ) -> SensorReading:
        """Advance the environment by ``dt_minutes`` and return a reading."""
        dt_h = dt_minutes / 60.0
        cfg = self.config

        # --- temperature: relax toward outdoor + solar gain, actuators act.
        outdoor = self.outdoor_temp_c(self.minute_of_day)
        solar_gain = self.solar_par_lux(self.minute_of_day) / 60_000.0 * 6.0
        target = outdoor + solar_gain
        tau = cfg.thermal_tau_min
        self.temp_c += (target - self.temp_c) * (dt_minutes / tau)
        if actuators.heater:
            # 1500 W heater in a 24 m2 greenhouse: ~+0.8 C per 5-min step,
            # enough to hold ~7 C above the outdoor temperature at
            # equilibrium against the thermal time constant above.
            self.temp_c += 0.8 * (cfg.heater_power_w / 1500.0) * (dt_minutes / 5.0)
        if actuators.fan:
            # Venting pulls the air ~35% of the way toward outdoor per step.
            self.temp_c += (outdoor - self.temp_c) * 0.35

        # --- humidity: warmer air holds more vapour; venting exchanges air.
        rh_target = clamp(95.0 - 1.6 * max(self.temp_c - 15.0, 0.0), 35.0, 95.0)
        self.rh_percent += (rh_target - self.rh_percent) * (dt_minutes / 90.0)
        if actuators.irrigation:
            self.rh_percent += 0.15 * (dt_minutes / 5.0)
        if actuators.fan:
            self.rh_percent += (self.weather.outdoor_rh - self.rh_percent) * 0.30
        self.rh_percent = clamp(self.rh_percent, 25.0, 99.0)

        # --- soil moisture: evapotranspiration dries, irrigation wets.
        ppfd = lux_to_ppfd(self.solar_par_lux(self.minute_of_day))
        vpd = vapor_pressure_deficit(self.temp_c, self.rh_percent)
        # Calibrated so a sunny day removes ~0.09-0.10 VWC: for the 500 L
        # wetted volume that is ~45-50 L/day, matching greenhouse tomato
        # water use of roughly 1 L/plant/day at ~60 plants per 24 m2
        # (see docs/RESEARCH.md).
        et_rate = 0.00005 * max(vpd, 0.0) * (1.0 + ppfd / 250.0)  # VWC / min
        self.soil_vwc -= et_rate * dt_minutes
        if actuators.irrigation:
            # Flow (L/min) spread over the wetted root-zone volume.
            added = (
                cfg.irrigation_flow_l_min
                * dt_minutes
                / cfg.wetted_soil_volume_l
            )
            self.soil_vwc += added
            self.water_used_l += cfg.irrigation_flow_l_min * dt_minutes
        if self.soil_vwc > FIELD_CAPACITY_VWC:
            # Drainage: excess water leaves at 10% of the excess per step.
            self.soil_vwc -= (self.soil_vwc - FIELD_CAPACITY_VWC) * 0.10
        self.soil_vwc = clamp(self.soil_vwc, 0.02, 0.60)

        # --- CO2: photosynthesis drawdown by day, respiration by night.
        if self.is_daylight(self.minute_of_day) and ppfd > 20.0:
            drawdown = 55.0 * (ppfd / 300.0) * dt_h  # ppm per hour, scaled
            self.co2_ppm -= drawdown
        else:
            self.co2_ppm += 25.0 * dt_h  # respiration
        if actuators.fan:
            self.co2_ppm += (AMBIENT_CO2_PPM - self.co2_ppm) * 0.40
        if actuators.co2:
            # Injector raises CO2 ~40 ppm per 5-min step in this volume.
            self.co2_ppm += 40.0 * (dt_minutes / 5.0)
            self.co2_used_g += cfg.co2_flow_g_min * dt_minutes
        self.co2_ppm = clamp(self.co2_ppm, 250.0, 1600.0)

        # --- advance the clock; roll the weather at midnight.
        self.minute_of_day += int(dt_minutes)
        if self.minute_of_day >= 24 * 60:
            self.minute_of_day -= 24 * 60
            self.day_index += 1
            self.weather = self._weather_gen.next_day()

        return self.read_sensors()

    def read_sensors(self) -> SensorReading:
        """Current state as noisy sensor values."""
        cfg = self.config
        par = self.solar_par_lux(self.minute_of_day)
        temp = self.temp_c + self._rng.gauss(0.0, cfg.noise_temp_c)
        rh = clamp(
            self.rh_percent + self._rng.gauss(0.0, cfg.noise_rh_percent),
            0.0,
            100.0,
        )
        soil = clamp(
            self.soil_vwc + self._rng.gauss(0.0, cfg.noise_soil_vwc), 0.0, 1.0
        )
        par_noisy = max(0.0, par + self._rng.gauss(0.0, cfg.noise_par_lux))
        co2 = max(
            0.0, self.co2_ppm + self._rng.gauss(0.0, cfg.noise_co2_ppm)
        )
        return SensorReading(
            temp_c=round(temp, 2),
            rh_percent=round(rh, 1),
            soil_vwc=round(soil, 4),
            par_lux=round(par_noisy, 0),
            co2_ppm=round(co2, 0),
            vpd_kpa=round(vapor_pressure_deficit(temp, rh), 3),
        )

    # -- helpers for tests / introspection -----------------------------------

    def true_state(self) -> dict[str, float]:
        """Noise-free internal state (for tests and calibration)."""
        return {
            "temp_c": self.temp_c,
            "rh_percent": self.rh_percent,
            "soil_vwc": self.soil_vwc,
            "co2_ppm": self.co2_ppm,
            "minute_of_day": float(self.minute_of_day),
        }

    def saturation_vapor_pressure_now(self) -> float:
        return saturation_vapor_pressure(self.temp_c)
