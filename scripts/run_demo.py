"""Demo script: run a 3-day tomato simulation and print the report.

Usage (from the project root):

    PYTHONPATH=src python3 scripts/run_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from smart_greenhouse_controller.analysis import analyze
from smart_greenhouse_controller.report import render_report
from smart_greenhouse_controller.simulator import (
    SimulationConfig,
    run_simulation,
)


def main() -> int:
    cfg = SimulationConfig(crop="tomato", days=3, seed=42)
    result = run_simulation(cfg)
    print(render_report(result, analyze(result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
