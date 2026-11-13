"""Tests for storage.py -- CSV/JSON/config round trips."""

from smart_greenhouse_controller.simulator import (
    SimulationConfig,
    run_simulation,
)
from smart_greenhouse_controller.storage import (
    load_config,
    parse_step_row,
    read_csv,
    save_config,
    write_csv,
    write_json,
)


def test_csv_roundtrip(tmp_path):
    result = run_simulation(SimulationConfig(crop="tomato", days=1, seed=42))
    path = write_csv(result, tmp_path / "series.csv")
    rows = read_csv(path)
    assert len(rows) == 288
    assert rows[0]["crop"] if "crop" in rows[0] else True
    assert float(rows[0]["temp_c"]) == result.steps[0].temp_c
    assert rows[-1]["water_used_l"] == str(round(result.steps[-1].water_used_l, 3))


def test_json_roundtrip(tmp_path):
    import json

    result = run_simulation(SimulationConfig(crop="lettuce", days=1, seed=1))
    path = write_json(result, tmp_path / "series.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["crop"] == "lettuce"
    assert payload["days"] == 1
    assert len(payload["steps"]) == 288
    assert payload["steps"][0]["temp_c"] == result.steps[0].temp_c


def test_config_save_load_roundtrip(tmp_path):
    cfg = SimulationConfig(crop="cucumber", days=4, seed=77)
    path = save_config(cfg, tmp_path / "cfg.json")
    loaded = load_config(path)
    assert loaded.crop == "cucumber"
    assert loaded.days == 4
    assert loaded.seed == 77
    assert loaded.greenhouse.floor_area_m2 == cfg.greenhouse.floor_area_m2


def test_parse_step_row_rebuilds_step(tmp_path):
    result = run_simulation(SimulationConfig(crop="tomato", days=1, seed=42))
    path = write_csv(result, tmp_path / "series.csv")
    row = read_csv(path)[10]
    step = parse_step_row(row)
    assert step.temp_c == result.steps[10].temp_c
    assert step.irrigation == result.steps[10].irrigation
    assert step.timestamp == result.steps[10].timestamp
