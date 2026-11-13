"""Closed-loop simulation engine: environment + controller, N days.

``run_simulation`` steps the greenhouse environment at a fixed timestep
(default 5 minutes), asks the controller for actuator states at every
step, and records a time series.  ``run_comparison`` runs the same
weather twice -- once with the controller enabled and once with every
actuator forced off -- so the effect of control can be measured on
identical weather (the A/B comparison in the report).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .controller import Controller
from .crops import CropProfile, get_profile
from .physics import lux_to_ppfd
from .sensors import (
    Actuators,
    GreenhouseConfig,
    GreenhouseEnvironment,
    SensorReading,
)


@dataclass
class SimStep:
    """One recorded timestep of a simulation run."""

    timestamp: datetime
    day_index: int
    minute_of_day: int
    temp_c: float
    rh_percent: float
    soil_vwc: float
    par_lux: float
    co2_ppm: float
    vpd_kpa: float
    irrigation: bool
    fan: bool
    heater: bool
    lights: bool
    co2: bool
    water_used_l: float  # cumulative
    weather: str

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "day_index": self.day_index,
            "minute_of_day": self.minute_of_day,
            "temp_c": self.temp_c,
            "rh_percent": self.rh_percent,
            "soil_vwc": self.soil_vwc,
            "par_lux": self.par_lux,
            "co2_ppm": self.co2_ppm,
            "vpd_kpa": self.vpd_kpa,
            "irrigation": self.irrigation,
            "fan": self.fan,
            "heater": self.heater,
            "lights": self.lights,
            "co2": self.co2,
            "water_used_l": round(self.water_used_l, 3),
            "weather": self.weather,
        }


@dataclass
class SimulationResult:
    """A completed run: its time series plus run metadata."""

    steps: list[SimStep] = field(default_factory=list)
    crop: str = ""
    days: int = 0
    seed: int = 0
    control_enabled: bool = True
    dt_minutes: float = 5.0
    config: GreenhouseConfig = field(default_factory=GreenhouseConfig)

    def __len__(self) -> int:
        return len(self.steps)

    def ppfd_series(self) -> list[float]:
        return [lux_to_ppfd(s.par_lux) for s in self.steps]


@dataclass
class SimulationConfig:
    """Everything needed to define one run (serialisable to JSON)."""

    crop: str = "tomato"
    days: int = 7
    seed: int = 42
    control_enabled: bool = True
    mode: str = "auto"  # controller mode: "auto" | "manual"
    dt_minutes: float = 5.0
    start_date: str = "2026-11-12"  # ISO date of day 0
    greenhouse: GreenhouseConfig = field(default_factory=GreenhouseConfig)
    manual: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "SimulationConfig":
        gh = data.get("greenhouse", {})
        return cls(
            crop=data.get("crop", "tomato"),
            days=int(data.get("days", 7)),
            seed=int(data.get("seed", 42)),
            control_enabled=bool(data.get("control_enabled", True)),
            mode=data.get("mode", "auto"),
            dt_minutes=float(data.get("dt_minutes", 5.0)),
            start_date=data.get("start_date", "2026-11-12"),
            greenhouse=GreenhouseConfig(**gh),
            manual=dict(data.get("manual", {})),
        )

    def to_dict(self) -> dict:
        return {
            "crop": self.crop,
            "days": self.days,
            "seed": self.seed,
            "control_enabled": self.control_enabled,
            "mode": self.mode,
            "dt_minutes": self.dt_minutes,
            "start_date": self.start_date,
            "greenhouse": {
                "floor_area_m2": self.greenhouse.floor_area_m2,
                "soil_depth_m": self.greenhouse.soil_depth_m,
                "irrigation_flow_l_min": self.greenhouse.irrigation_flow_l_min,
                "wetted_soil_volume_l": self.greenhouse.wetted_soil_volume_l,
                "heater_power_w": self.greenhouse.heater_power_w,
                "fan_power_w": self.greenhouse.fan_power_w,
                "lights_power_w": self.greenhouse.lights_power_w,
                "co2_flow_g_min": self.greenhouse.co2_flow_g_min,
                "thermal_tau_min": self.greenhouse.thermal_tau_min,
                "outdoor_mean_c": self.greenhouse.outdoor_mean_c,
                "outdoor_amplitude_c": self.greenhouse.outdoor_amplitude_c,
            },
            "manual": self.manual,
        }


def run_simulation(cfg: SimulationConfig) -> SimulationResult:
    """Run a closed-loop simulation and return the recorded time series."""
    profile: CropProfile = get_profile(cfg.crop)
    env = GreenhouseEnvironment(config=cfg.greenhouse, seed=cfg.seed)
    controller = Controller(profile, mode=cfg.mode, manual=cfg.manual)
    start = datetime.fromisoformat(cfg.start_date)
    steps: list[SimStep] = []
    total_steps = int(cfg.days * 24 * 60 / cfg.dt_minutes)

    for _ in range(total_steps):
        day_index = env.day_index
        minute = env.minute_of_day
        # Decide on the *current* sensor state, then step the world.
        reading = env.read_sensors()
        if cfg.control_enabled:
            act = controller.decide(reading, minute, day_index, cfg.dt_minutes)
        else:
            act = Actuators()  # everything off: the uncontrolled baseline
        new_reading = env.step(act, cfg.dt_minutes)
        timestamp = start + timedelta(days=day_index, minutes=minute)
        steps.append(
            SimStep(
                timestamp=timestamp,
                day_index=day_index,
                minute_of_day=minute,
                temp_c=new_reading.temp_c,
                rh_percent=new_reading.rh_percent,
                soil_vwc=new_reading.soil_vwc,
                par_lux=new_reading.par_lux,
                co2_ppm=new_reading.co2_ppm,
                vpd_kpa=new_reading.vpd_kpa,
                irrigation=act.irrigation,
                fan=act.fan,
                heater=act.heater,
                lights=act.lights,
                co2=act.co2,
                water_used_l=env.water_used_l,
                weather=env.weather.condition,
            )
        )

    return SimulationResult(
        steps=steps,
        crop=cfg.crop,
        days=cfg.days,
        seed=cfg.seed,
        control_enabled=cfg.control_enabled,
        dt_minutes=cfg.dt_minutes,
        config=cfg.greenhouse,
    )


def run_comparison(
    cfg: SimulationConfig,
) -> tuple[SimulationResult, SimulationResult]:
    """Run the same weather with control ON and OFF.

    The two runs share the seed, so the weather sequence is identical
    and any difference in the outcome is caused by the controller.
    """
    on_cfg = SimulationConfig(**{**cfg.to_dict(), "control_enabled": True})
    # Rebuild greenhouse config from dict (to_dict flattens it).
    on_cfg.greenhouse = GreenhouseConfig(
        **cfg.to_dict()["greenhouse"]
    )
    off_cfg = SimulationConfig(**{**cfg.to_dict(), "control_enabled": False})
    off_cfg.greenhouse = GreenhouseConfig(
        **cfg.to_dict()["greenhouse"]
    )
    return run_simulation(on_cfg), run_simulation(off_cfg)
