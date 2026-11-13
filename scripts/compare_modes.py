"""Compare control ON vs OFF for a crop and print the A/B table.

Usage (from the project root):

    PYTHONPATH=src python3 scripts/compare_modes.py tomato 7
    PYTHONPATH=src python3 scripts/compare_modes.py lettuce 7 --seed 42
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from smart_greenhouse_controller.analysis import analyze, compare_runs
from smart_greenhouse_controller.simulator import (
    SimulationConfig,
    run_comparison,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Control ON vs OFF comparison")
    parser.add_argument("crop", default="tomato", nargs="?")
    parser.add_argument("days", type=int, default=7, nargs="?")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cfg = SimulationConfig(crop=args.crop, days=args.days, seed=args.seed)
    on_result, off_result = run_comparison(cfg)
    on_a, off_a = analyze(on_result), analyze(off_result)
    comp = compare_runs(on_a, off_a)
    print(f"crop: {args.crop}, {args.days} days, seed {args.seed} (identical weather)")
    print(f"water:    ON {on_a.total_water_l:.1f} L vs OFF {off_a.total_water_l:.1f} L "
          f"({comp['water_l_delta']:+.1f} L — cost of watering, baseline waters nothing)")
    print(f"temp out: ON {on_a.hours_temp_out_of_range:.1f} h vs OFF "
          f"{off_a.hours_temp_out_of_range:.1f} h ({comp['hours_temp_out_delta']:+.1f} h)")
    print(f"RH out:   ON {on_a.hours_rh_out_of_range:.1f} h vs OFF "
          f"{off_a.hours_rh_out_of_range:.1f} h ({comp['hours_rh_out_delta']:+.1f} h)")
    print(f"VPD out:  ON {on_a.hours_vpd_out_of_range:.1f} h vs OFF "
          f"{off_a.hours_vpd_out_of_range:.1f} h ({comp['hours_vpd_out_delta']:+.1f} h)")
    print(f"in band:  ON {on_a.pct_time_in_temp_band:.1f}% vs OFF "
          f"{off_a.pct_time_in_temp_band:.1f}% ({comp['pct_in_band_delta']:+.1f} pp)")
    print(f"energy (control cost): {comp['energy_kwh_controlled']:.2f} kWh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
