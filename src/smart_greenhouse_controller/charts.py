"""Matplotlib charts (PNG) for a simulation run.

Matplotlib is an optional dependency: the core package (simulation,
analysis, report, dashboard) only needs the standard library.  These
functions raise a clear error if matplotlib is not installed.
"""

from __future__ import annotations

from pathlib import Path

from .analysis import AnalysisReport
from .simulator import SimulationResult


def _require_matplotlib():
    try:
        import matplotlib
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "matplotlib is required for PNG charts; "
            "install it with: pip install matplotlib"
        ) from exc
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_climate(
    result: SimulationResult, analysis: AnalysisReport, path: str | Path
) -> Path:
    """Temperature + humidity over time, with the crop band shaded."""
    plt = _require_matplotlib()
    from .crops import get_profile

    profile = get_profile(result.crop)
    steps = result.steps
    hours = [i * result.dt_minutes / 60.0 for i in range(len(steps))]
    temps = [s.temp_c for s in steps]
    rhs = [s.rh_percent for s in steps]

    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax1.axhspan(
        profile.temp_day_min, profile.temp_day_max, color="green", alpha=0.08,
        label="day temp band",
    )
    ax1.plot(hours, temps, color="#c0392b", lw=1, label="Temperature (C)")
    ax1.set_xlabel("Hours since start")
    ax1.set_ylabel("Temperature (C)", color="#c0392b")
    ax2 = ax1.twinx()
    ax2.plot(hours, rhs, color="#2980b9", lw=1, label="Humidity (%)")
    ax2.set_ylabel("Relative humidity (%)", color="#2980b9")
    ax1.set_title(f"Climate — {profile.name} ({result.days} days, control "
                  f"{'ON' if result.control_enabled else 'OFF'})")
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_soil(
    result: SimulationResult, analysis: AnalysisReport, path: str | Path
) -> Path:
    """Soil moisture over time, with irrigation-on periods shaded."""
    plt = _require_matplotlib()
    from .crops import get_profile

    profile = get_profile(result.crop)
    steps = result.steps
    hours = [i * result.dt_minutes / 60.0 for i in range(len(steps))]
    soil = [s.soil_vwc * 100.0 for s in steps]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axhspan(
        profile.soil_irrigate_below * 100, profile.soil_stop_above * 100,
        color="green", alpha=0.10, label="target VWC band",
    )
    ax.plot(hours, soil, color="#7d6608", lw=1, label="Soil VWC (%)")
    # Shade irrigation-on intervals.
    in_event = False
    start = 0.0
    for h, s in zip(hours, steps):
        if s.irrigation and not in_event:
            in_event, start = True, h
        elif not s.irrigation and in_event:
            ax.axvspan(start, h, color="#20a145", alpha=0.25)
            in_event = False
    if in_event:
        ax.axvspan(start, hours[-1], color="#20a145", alpha=0.25)
    ax.set_xlabel("Hours since start")
    ax.set_ylabel("Soil VWC (%)")
    ax.set_title(f"Soil moisture & irrigation — {profile.name} "
                 f"(water used: {analysis.total_water_l:.1f} L)")
    ax.legend()
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_all(
    result: SimulationResult, analysis: AnalysisReport, out_dir: str | Path
) -> list[Path]:
    """Generate both standard charts into ``out_dir``."""
    out_dir = Path(out_dir)
    return [
        plot_climate(result, analysis, out_dir / "climate.png"),
        plot_soil(result, analysis, out_dir / "soil.png"),
    ]
