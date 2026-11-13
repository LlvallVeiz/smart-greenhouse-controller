"""Command-line interface.

Subcommands:

* ``simulate``  -- run one configuration for N days, write CSV/JSON,
  Markdown report, HTML dashboard and (optionally) PNG charts.
* ``compare``   -- run the same weather with control ON and OFF and
  print the A/B summary.
* ``list-crops`` -- print the built-in crop profiles and their targets.
* ``demo``      -- a quick 3-day tomato run printed to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import analyze, compare_runs
from .charts import plot_all
from .crops import get_profile, list_profiles
from .dashboard import render_dashboard
from .report import render_report
from .simulator import SimulationConfig, run_comparison, run_simulation
from .storage import load_config, save_config, write_csv, write_json


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="greenhouse",
        description="Smart greenhouse controller: simulate, control and analyse.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_sim = sub.add_parser("simulate", help="run a simulation from a config file")
    p_sim.add_argument("config", help="JSON config file (see examples/)")
    p_sim.add_argument("--days", type=int, default=None, help="override days")
    p_sim.add_argument("--seed", type=int, default=None, help="override seed")
    p_sim.add_argument("--out", default="output", help="output directory")
    p_sim.add_argument("--charts", action="store_true", help="also render PNG charts")

    p_cmp = sub.add_parser("compare", help="control ON vs OFF on identical weather")
    p_cmp.add_argument("config", help="JSON config file")
    p_cmp.add_argument("--days", type=int, default=None, help="override days")
    p_cmp.add_argument("--out", default=None, help="optional output directory for reports")

    sub.add_parser("list-crops", help="list built-in crop profiles")

    p_demo = sub.add_parser("demo", help="quick 3-day tomato demo on stdout")
    p_demo.add_argument("--seed", type=int, default=42)

    return parser


def _cmd_simulate(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.days is not None:
        cfg.days = args.days
    if args.seed is not None:
        cfg.seed = args.seed
    result = run_simulation(cfg)
    analysis = analyze(result)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(result, out / "timeseries.csv")
    write_json(result, out / "timeseries.json")
    (out / "report.md").write_text(
        render_report(result, analysis), encoding="utf-8"
    )
    (out / "dashboard.html").write_text(
        render_dashboard(result, analysis), encoding="utf-8"
    )
    if args.charts:
        plot_all(result, analysis, out)
    print(f"crop:            {result.crop}")
    print(f"days:            {result.days} (seed {result.seed}, {len(result.steps)} steps)")
    print(f"water used:      {analysis.total_water_l:.1f} L "
          f"({analysis.water_l_per_day:.1f} L/day, {analysis.irrigation_events} events)")
    print(f"time in band:    {analysis.pct_time_in_temp_band:.1f}%")
    print(f"temp out of range: {analysis.hours_temp_out_of_range:.1f} h")
    print(f"mean DLI:        {analysis.mean_dli:.2f} mol/m2/d")
    print(f"energy:          {analysis.total_energy_kwh:.2f} kWh")
    print(f"output:          {out}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.days is not None:
        cfg.days = args.days
    on_result, off_result = run_comparison(cfg)
    on_a, off_a = analyze(on_result), analyze(off_result)
    comp = compare_runs(on_a, off_a)
    print(f"crop: {cfg.crop}, {cfg.days} days, seed {cfg.seed} (identical weather)")
    print(f"water:    ON {on_a.total_water_l:.1f} L vs OFF {off_a.total_water_l:.1f} L "
          f"({comp['water_l_delta']:+.1f} L)")
    print(f"temp out: ON {on_a.hours_temp_out_of_range:.1f} h vs OFF "
          f"{off_a.hours_temp_out_of_range:.1f} h ({comp['hours_temp_out_delta']:+.1f} h)")
    print(f"RH out:   ON {on_a.hours_rh_out_of_range:.1f} h vs OFF "
          f"{off_a.hours_rh_out_of_range:.1f} h ({comp['hours_rh_out_delta']:+.1f} h)")
    print(f"VPD out:  ON {on_a.hours_vpd_out_of_range:.1f} h vs OFF "
          f"{off_a.hours_vpd_out_of_range:.1f} h ({comp['hours_vpd_out_delta']:+.1f} h)")
    print(f"in band:  ON {on_a.pct_time_in_temp_band:.1f}% vs OFF "
          f"{off_a.pct_time_in_temp_band:.1f}% ({comp['pct_in_band_delta']:+.1f} pp)")
    print(f"energy (control cost): {comp['energy_kwh_controlled']:.2f} kWh")
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        write_csv(on_result, out / "timeseries_control_on.csv")
        write_csv(off_result, out / "timeseries_control_off.csv")
        (out / "report_control_on.md").write_text(
            render_report(on_result, on_a, off_a, comp), encoding="utf-8"
        )
        (out / "dashboard_control_on.html").write_text(
            render_dashboard(on_result, on_a), encoding="utf-8"
        )
        print(f"output: {out}")
    return 0


def _cmd_list_crops(_args: argparse.Namespace) -> int:
    for p in list_profiles():
        print(
            f"{p.name:10s} day {p.temp_day_min:.0f}-{p.temp_day_max:.0f} C, "
            f"night {p.temp_night_min:.0f}-{p.temp_night_max:.0f} C, "
            f"RH {p.rh_min:.0f}-{p.rh_max:.0f}%, "
            f"soil {p.soil_irrigate_below:.2f}-{p.soil_stop_above:.2f} VWC, "
            f"CO2 {p.co2_target_ppm:.0f} ppm, VPD {p.vpd_min:.1f}-{p.vpd_max:.1f} kPa"
        )
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    cfg = SimulationConfig(crop="tomato", days=3, seed=args.seed)
    result = run_simulation(cfg)
    analysis = analyze(result)
    print(render_report(result, analysis))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "simulate":
            return _cmd_simulate(args)
        if args.command == "compare":
            return _cmd_compare(args)
        if args.command == "list-crops":
            return _cmd_list_crops(args)
        if args.command == "demo":
            return _cmd_demo(args)
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
