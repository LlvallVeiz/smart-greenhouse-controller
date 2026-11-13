"""Static HTML dashboard: Chart.js charts fed by embedded JSON.

The dashboard is a single self-contained HTML file (Chart.js is loaded
from a CDN at view time, nothing is installed).  The time series is
downsampled to at most one point per 30 minutes so the file stays
small for multi-day runs.
"""

from __future__ import annotations

import json

from .analysis import AnalysisReport
from .crops import get_profile
from .simulator import SimulationResult

_CHARTJS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"


def _downsample(result: SimulationResult, max_points: int = 1500) -> list[dict]:
    steps = result.steps
    if len(steps) <= max_points:
        chosen = steps
    else:
        stride = -(-len(steps) // max_points)  # ceil division: actually cap
        chosen = steps[::stride]
    return [
        {
            "t": s.timestamp.strftime("%m-%d %H:%M"),
            "temp": s.temp_c,
            "rh": s.rh_percent,
            "soil": round(s.soil_vwc * 100.0, 1),
            "par": s.par_lux,
            "co2": s.co2_ppm,
            "vpd": s.vpd_kpa,
            "irr": 1 if s.irrigation else 0,
            "fan": 1 if s.fan else 0,
            "heat": 1 if s.heater else 0,
            "light": 1 if s.lights else 0,
        }
        for s in chosen
    ]


def render_dashboard(
    result: SimulationResult,
    analysis: AnalysisReport,
    title: str | None = None,
) -> str:
    """Render the dashboard HTML for a run."""
    profile = get_profile(result.crop)
    data = _downsample(result)
    payload = json.dumps(data)
    title = title or f"Smart Greenhouse — {profile.name.title()} ({result.days} days)"
    cards = (
        f"<div class='card'><div class='v'>{analysis.total_water_l:.1f} L</div>"
        f"<div class='l'>Water used ({analysis.water_l_per_day:.1f} L/day)</div></div>"
        f"<div class='card'><div class='v'>{analysis.pct_time_in_temp_band:.1f}%</div>"
        f"<div class='l'>Time in temperature band</div></div>"
        f"<div class='card'><div class='v'>{analysis.mean_dli:.2f}</div>"
        f"<div class='l'>Mean DLI (mol/m²/d)</div></div>"
        f"<div class='card'><div class='v'>{analysis.total_energy_kwh:.2f} kWh</div>"
        f"<div class='l'>Energy used</div></div>"
        f"<div class='card'><div class='v'>{analysis.irrigation_events}</div>"
        f"<div class='l'>Irrigation events</div></div>"
        f"<div class='card'><div class='v'>{analysis.hours_temp_out_of_range:.1f} h</div>"
        f"<div class='l'>Hours temp out of range</div></div>"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="{_CHARTJS_CDN}"></script>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; background: #f4f7f2; color: #1d2a32; }}
header {{ background: #1d2a32; color: #fff; padding: 20px 28px; }}
header h1 {{ margin: 0 0 4px; font-size: 22px; }}
header p {{ margin: 0; opacity: .8; font-size: 14px; }}
main {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }}
.card {{ background: #fff; border-radius: 10px; padding: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
.card .v {{ font-size: 26px; font-weight: 700; color: #20a145; }}
.card .l {{ font-size: 13px; color: #555; margin-top: 2px; }}
.panel {{ background: #fff; border-radius: 10px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
.panel h2 {{ margin: 0 0 8px; font-size: 16px; }}
canvas {{ max-height: 260px; }}
footer {{ text-align: center; font-size: 12px; color: #777; padding: 12px; }}
</style>
</head>
<body>
<header><h1>{title}</h1>
<p>Crop: {profile.name} ({profile.latin_name}) &middot; {result.days} days &middot; seed {result.seed} &middot; control {'ON' if result.control_enabled else 'OFF'} &middot; {len(result.steps)} steps of {result.dt_minutes:.0f} min</p></header>
<main>
<div class="cards">{cards}</div>
<div class="panel"><h2>Temperature (°C) &amp; humidity (%)</h2><canvas id="c1"></canvas></div>
<div class="panel"><h2>Soil moisture (% VWC) &amp; irrigation</h2><canvas id="c2"></canvas></div>
<div class="panel"><h2>Light (lux) &amp; CO₂ (ppm)</h2><canvas id="c3"></canvas></div>
<div class="panel"><h2>VPD (kPa)</h2><canvas id="c4"></canvas></div>
</main>
<footer>Smart Greenhouse Controller — simulation output. Chart.js loaded from CDN.</footer>
<script>
const D = {payload};
const labels = D.map(r => r.t);
function line(ctx, sets, yLabel) {{
  new Chart(ctx, {{ type: 'line', data: {{ labels, datasets: sets }},
    options: {{ responsive: true, animation: false, interaction: {{ mode: 'index', intersect: false }},
      scales: {{ y: {{ title: {{ display: true, text: yLabel }} }}, x: {{ ticks: {{ maxTicksLimit: 12 }} }} }},
      elements: {{ point: {{ radius: 0 }} }} }} }});
}}
const ds = (label, key, color, yAxisID) => ({{ label, data: D.map(r => r[key]), borderColor: color, backgroundColor: color, borderWidth: 1.5, yAxisID: yAxisID || 'y' }});
line(document.getElementById('c1'), [ds('Temperature °C', 'temp', '#c0392b'), ds('Humidity %', 'rh', '#2980b9')]);
line(document.getElementById('c2'), [ds('Soil VWC %', 'soil', '#7d6608'), ds('Irrigation on', 'irr', '#20a145')]);
line(document.getElementById('c3'), [ds('PAR (lux)', 'par', '#f39c12'), ds('CO2 (ppm)', 'co2', '#6c3483')]);
line(document.getElementById('c4'), [ds('VPD (kPa)', 'vpd', '#117a65')]);
</script>
</body>
</html>
"""
