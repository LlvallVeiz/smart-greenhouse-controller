"""Tests for cli.py -- subcommands end to end via main()."""

import json

import pytest

from smart_greenhouse_controller.cli import main
from smart_greenhouse_controller.storage import save_config
from smart_greenhouse_controller.simulator import SimulationConfig


def _write_config(tmp_path, **overrides):
    cfg = SimulationConfig(crop="tomato", days=1, seed=42)
    for key, value in overrides.items():
        setattr(cfg, key, value)
    path = tmp_path / "config.json"
    save_config(cfg, path)
    return path


def test_list_crops_lists_all(capsys):
    assert main(["list-crops"]) == 0
    out = capsys.readouterr().out
    for crop in ("tomato", "lettuce", "cucumber", "pepper", "basil"):
        assert crop in out


def test_demo_prints_report(capsys):
    assert main(["demo", "--seed", "42"]) == 0
    out = capsys.readouterr().out
    assert "Tomato" in out
    assert "Water" in out


def test_simulate_writes_all_outputs(tmp_path, capsys):
    cfg_path = _write_config(tmp_path)
    out = tmp_path / "out"
    assert main(["simulate", str(cfg_path), "--out", str(out)]) == 0
    for name in ("timeseries.csv", "timeseries.json", "report.md", "dashboard.html"):
        assert (out / name).exists(), f"missing {name}"
    assert "water used" in capsys.readouterr().out


def test_simulate_with_charts(tmp_path):
    cfg_path = _write_config(tmp_path)
    out = tmp_path / "out"
    assert main(["simulate", str(cfg_path), "--out", str(out), "--charts"]) == 0
    assert (out / "climate.png").exists()
    assert (out / "soil.png").exists()


def test_compare_prints_ab_summary(tmp_path, capsys):
    cfg_path = _write_config(tmp_path)
    assert main(["compare", str(cfg_path)]) == 0
    out = capsys.readouterr().out
    assert "ON" in out and "OFF" in out
    assert "water" in out.lower()


def test_compare_with_output_dir(tmp_path):
    cfg_path = _write_config(tmp_path)
    out = tmp_path / "cmp"
    assert main(["compare", str(cfg_path), "--out", str(out)]) == 0
    assert (out / "report_control_on.md").exists()
    assert (out / "timeseries_control_on.csv").exists()
    assert (out / "timeseries_control_off.csv").exists()


def test_simulate_missing_config_returns_error(capsys):
    assert main(["simulate", "/nonexistent/config.json"]) == 2
    assert "error" in capsys.readouterr().err.lower()


def test_simulate_unknown_crop_returns_error(tmp_path, capsys):
    cfg_path = tmp_path / "bad.json"
    cfg_path.write_text(json.dumps({"crop": "durian", "days": 1}), encoding="utf-8")
    assert main(["simulate", str(cfg_path), "--out", str(tmp_path / "o")]) == 2
