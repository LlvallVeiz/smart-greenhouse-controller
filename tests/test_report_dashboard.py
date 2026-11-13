"""Tests for report.py, dashboard.py and charts.py."""

from smart_greenhouse_controller.analysis import analyze
from smart_greenhouse_controller.charts import plot_all, plot_climate, plot_soil
from smart_greenhouse_controller.dashboard import render_dashboard
from smart_greenhouse_controller.report import render_report
from smart_greenhouse_controller.simulator import (
    SimulationConfig,
    run_comparison,
    run_simulation,
)


def _run(days=2, seed=42):
    result = run_simulation(
        SimulationConfig(crop="tomato", days=days, seed=seed)
    )
    return result, analyze(result)


def test_report_contains_headline_numbers():
    result, analysis = _run()
    text = render_report(result, analysis)
    assert "Tomato" in text
    assert f"{analysis.total_water_l:.1f} L" in text
    assert f"{analysis.pct_time_in_temp_band:.1f}%" in text
    assert "Water" in text and "Energy" in text
    assert "simulation" in text.lower()


def test_report_with_comparison_section():
    on, off = run_comparison(SimulationConfig(crop="tomato", days=2, seed=42))
    on_a, off_a = analyze(on), analyze(off)
    from smart_greenhouse_controller.analysis import compare_runs

    comp = compare_runs(on_a, off_a)
    text = render_report(on, on_a, off_a, comp)
    assert "Control ON vs OFF" in text
    assert "identical weather" in text


def test_dashboard_is_valid_html_with_chartjs_and_data():
    result, analysis = _run()
    html = render_dashboard(result, analysis)
    assert "<!DOCTYPE html>" in html
    assert "chart.js" in html.lower()
    assert "Temperature" in html
    assert f"{analysis.total_water_l:.1f} L" in html
    # Embedded JSON payload must contain the first timestamp.
    assert result.steps[0].timestamp.strftime("%m-%d %H:%M") in html


def test_dashboard_downsamples_long_runs():
    result, analysis = _run(days=7)
    html = render_dashboard(result, analysis)
    # 7 days at 5 min = 2016 points; the payload must be capped.
    assert html.count('"t":') <= 1500


def test_charts_write_png_files(tmp_path):
    result, analysis = _run(days=2)
    p1 = plot_climate(result, analysis, tmp_path / "climate.png")
    p2 = plot_soil(result, analysis, tmp_path / "soil.png")
    assert p1.exists() and p1.stat().st_size > 1000
    assert p2.exists() and p2.stat().st_size > 1000


def test_plot_all_writes_both(tmp_path):
    result, analysis = _run(days=2)
    paths = plot_all(result, analysis, tmp_path)
    assert len(paths) == 2
    assert all(p.exists() for p in paths)
