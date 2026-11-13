"""Greenhouse controller: hysteresis (on/off with dead-band) logic.

Design (see ``docs/CONTROL_DESIGN.md`` for the rationale):

* Every actuator is **latched**: it turns on when its variable crosses
  the "on" threshold and only turns off when it crosses the separate
  "off" threshold.  A single threshold would chatter around the
  setpoint; the dead-band between the two thresholds is what keeps the
  relay from oscillating.
* **Interlock**: the heater and the vent fan can never be on together
  (heating while venting wastes energy).  The fan wins if both
  conditions are somehow true.
* **Irrigation** is additionally bounded by a daily window, a maximum
  continuous duration per event and a maximum number of events per
  day, so a stuck sensor cannot flood the beds.
* **CO2 enrichment** only runs in daylight while the vent is closed
  (venting would dump the gas outside) and the light level is high
  enough for photosynthesis to use it.
* **Manual mode** forces actuator states from the operator; the
  automatic logic still runs in the background for the interlock only
  (heater + fan are never both on, even in manual mode).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .crops import CropProfile
from .sensors import Actuators, SensorReading

# Dead-bands (half-widths) around the crop targets.
TEMP_HEAT_DEADBAND_C = 1.0  # heater on below min-1, off above min+1
TEMP_VENT_DEADBAND_C = 1.0  # fan on above max+1, off below max-1
RH_VENT_DEADBAND = 5.0  # fan on above rh_max+5, off below rh_max-5
CO2_DEADBAND_PPM = 50.0  # injector on below target-50, off above target


@dataclass
class ControllerState:
    """Latched (hysteresis) state, kept between decisions."""

    irrigation_on: bool = False
    fan_on: bool = False
    heater_on: bool = False
    lights_on: bool = False
    co2_on: bool = False
    irrigation_minutes_current: float = 0.0
    irrigation_events_today: int = 0
    current_day: int = 0
    # Minutes since the last irrigation event ended (cool-down guard).
    minutes_since_irrigation: float = 999.0


@dataclass
class IrrigationWindow:
    """Hours of day during which irrigation is allowed."""

    start_hour: float = 5.0
    end_hour: float = 19.0

    def allows(self, minute_of_day: int) -> bool:
        hour = minute_of_day / 60.0
        return self.start_hour <= hour < self.end_hour


class Controller:
    """Hysteresis controller for one crop profile."""

    def __init__(
        self,
        profile: CropProfile,
        mode: str = "auto",
        irrigation_window: IrrigationWindow | None = None,
        manual: dict[str, bool] | None = None,
    ):
        if mode not in ("auto", "manual"):
            raise ValueError(f"mode must be 'auto' or 'manual', got {mode!r}")
        self.profile = profile
        self.mode = mode
        self.window = irrigation_window or IrrigationWindow()
        self.manual = dict(manual or {})
        self.state = ControllerState()

    # -- public API ----------------------------------------------------------

    def decide(
        self,
        reading: SensorReading,
        minute_of_day: int,
        day_index: int,
        dt_minutes: float = 5.0,
    ) -> Actuators:
        """Decide actuator states for this timestep.

        ``minute_of_day`` drives the photoperiod and irrigation window;
        ``day_index`` resets the daily irrigation-event counter.
        """
        if day_index != self.state.current_day:
            self.state.current_day = day_index
            self.state.irrigation_events_today = 0

        if self.mode == "manual":
            act = Actuators(
                irrigation=bool(self.manual.get("irrigation", False)),
                fan=bool(self.manual.get("fan", False)),
                heater=bool(self.manual.get("heater", False)),
                lights=bool(self.manual.get("lights", False)),
                co2=bool(self.manual.get("co2", False)),
            )
            return self._apply_interlock(act)

        is_day = self._is_day(minute_of_day)
        temp_min, temp_max = self._temp_band(minute_of_day)
        act = Actuators(
            irrigation=self._decide_irrigation(reading, minute_of_day, dt_minutes),
            fan=self._decide_fan(reading, temp_max),
            heater=self._decide_heater(reading, temp_min),
            lights=self._decide_lights(reading, minute_of_day),
            co2=False,  # decided after the fan, because CO2 needs it closed
        )
        act.co2 = self._decide_co2(reading, act.fan, is_day)
        return self._apply_interlock(act)

    def set_manual(self, **overrides: bool) -> None:
        """Set manual actuator overrides (only used in manual mode)."""
        self.manual.update(overrides)

    def set_mode(self, mode: str) -> None:
        if mode not in ("auto", "manual"):
            raise ValueError(f"mode must be 'auto' or 'manual', got {mode!r}")
        self.mode = mode

    # -- helpers ---------------------------------------------------------------

    def _is_day(self, minute_of_day: int) -> bool:
        return 6 * 60 <= minute_of_day < 18 * 60

    def _temp_band(self, minute_of_day: int) -> tuple[float, float]:
        """(min, max) air-temperature target for this time of day."""
        p = self.profile
        if self._is_day(minute_of_day):
            return p.temp_day_min, p.temp_day_max
        return p.temp_night_min, p.temp_night_max

    def _decide_irrigation(
        self, reading: SensorReading, minute_of_day: int, dt_minutes: float
    ) -> bool:
        p = self.profile
        st = self.state
        if st.irrigation_on:
            st.irrigation_minutes_current += dt_minutes
            st.minutes_since_irrigation = 0.0
        else:
            st.minutes_since_irrigation += dt_minutes

        # Stop conditions always win over start conditions.
        stop = (
            reading.soil_vwc >= p.soil_stop_above
            or st.irrigation_minutes_current >= p.irrigation_max_minutes
            or not self.window.allows(minute_of_day)
        )
        if st.irrigation_on and stop:
            st.irrigation_on = False
            st.irrigation_minutes_current = 0.0
            return False
        if st.irrigation_on:
            return True

        # Start conditions: dry soil, inside the window, quota left.
        start = (
            reading.soil_vwc < p.soil_irrigate_below
            and self.window.allows(minute_of_day)
            and st.irrigation_events_today < p.irrigation_max_events_per_day
            and st.minutes_since_irrigation >= 10.0
        )
        if start:
            st.irrigation_on = True
            st.irrigation_minutes_current = 0.0
            st.irrigation_events_today += 1
            return True
        return False

    def _decide_fan(self, reading: SensorReading, temp_max: float) -> bool:
        st = self.state
        if st.fan_on:
            # Stay on until temperature AND humidity are back in band.
            if (
                reading.temp_c <= temp_max - TEMP_VENT_DEADBAND_C
                and reading.rh_percent <= self.profile.rh_max - RH_VENT_DEADBAND
            ):
                st.fan_on = False
        elif (
            reading.temp_c >= temp_max + TEMP_VENT_DEADBAND_C
            or reading.rh_percent >= self.profile.rh_max + RH_VENT_DEADBAND
        ):
            st.fan_on = True
        return st.fan_on

    def _decide_heater(self, reading: SensorReading, temp_min: float) -> bool:
        st = self.state
        if st.heater_on:
            if reading.temp_c >= temp_min + TEMP_HEAT_DEADBAND_C:
                st.heater_on = False
        elif reading.temp_c <= temp_min - TEMP_HEAT_DEADBAND_C:
            st.heater_on = True
        return st.heater_on

    def _decide_lights(self, reading: SensorReading, minute_of_day: int) -> bool:
        from .physics import lux_to_ppfd

        p = self.profile
        # Photoperiod: 06:00 + photoperiod_hours, e.g. 06:00-20:00.
        photo_end = 6 * 60 + int(p.photoperiod_hours * 60)
        if not (6 * 60 <= minute_of_day < photo_end):
            self.state.lights_on = False
            return False
        ppfd = lux_to_ppfd(reading.par_lux)
        # Hysteresis on light level: on below 90% of target, off at target.
        if self.state.lights_on:
            if ppfd >= p.ppfd_target:
                self.state.lights_on = False
        elif ppfd < 0.9 * p.ppfd_target:
            self.state.lights_on = True
        return self.state.lights_on

    def _decide_co2(
        self, reading: SensorReading, fan_on: bool, is_day: bool
    ) -> bool:
        p = self.profile
        st = self.state
        if not is_day or fan_on:
            st.co2_on = False
            return False
        if st.co2_on:
            if reading.co2_ppm >= p.co2_target_ppm:
                st.co2_on = False
        elif reading.co2_ppm <= p.co2_target_ppm - CO2_DEADBAND_PPM:
            st.co2_on = True
        return st.co2_on

    @staticmethod
    def _apply_interlock(act: Actuators) -> Actuators:
        """Heater and fan must never run together; the fan wins."""
        if act.fan and act.heater:
            act.heater = False
        return act
