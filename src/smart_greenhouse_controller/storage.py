"""Persistence: CSV/JSON time series and JSON run configs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .simulator import SimStep, SimulationConfig, SimulationResult


def write_csv(result: SimulationResult, path: str | Path) -> Path:
    """Write the time series to CSV. Returns the path written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(result.steps[0].as_dict().keys()) if result.steps else []
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for step in result.steps:
            writer.writerow(step.as_dict())
    return path


def write_json(result: SimulationResult, path: str | Path) -> Path:
    """Write the time series + metadata to JSON. Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "crop": result.crop,
        "days": result.days,
        "seed": result.seed,
        "control_enabled": result.control_enabled,
        "dt_minutes": result.dt_minutes,
        "steps": [s.as_dict() for s in result.steps],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_csv(path: str | Path) -> list[dict]:
    """Read a CSV time series back into a list of row dicts."""
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_config(path: str | Path) -> SimulationConfig:
    """Load a run configuration from a JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return SimulationConfig.from_dict(data)


def save_config(cfg: SimulationConfig, path: str | Path) -> Path:
    """Save a run configuration to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    return path


def parse_step_row(row: dict) -> SimStep:
    """Rebuild a SimStep from a CSV/JSON row dict (strings or natives)."""
    from datetime import datetime

    def _bool(v) -> bool:
        return v is True or str(v).strip().lower() in ("true", "1", "yes")

    return SimStep(
        timestamp=datetime.fromisoformat(str(row["timestamp"])),
        day_index=int(row["day_index"]),
        minute_of_day=int(row["minute_of_day"]),
        temp_c=float(row["temp_c"]),
        rh_percent=float(row["rh_percent"]),
        soil_vwc=float(row["soil_vwc"]),
        par_lux=float(row["par_lux"]),
        co2_ppm=float(row["co2_ppm"]),
        vpd_kpa=float(row["vpd_kpa"]),
        irrigation=_bool(row["irrigation"]),
        fan=_bool(row["fan"]),
        heater=_bool(row["heater"]),
        lights=_bool(row["lights"]),
        co2=_bool(row["co2"]),
        water_used_l=float(row["water_used_l"]),
        weather=str(row["weather"]),
    )
