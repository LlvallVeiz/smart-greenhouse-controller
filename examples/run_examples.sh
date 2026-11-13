#!/usr/bin/env bash
# Reproduce every example output in examples/output/ from scratch.
# Run from the project root.
set -euo pipefail
export PYTHONPATH=src
python3 -m smart_greenhouse_controller simulate examples/config_tomato.json --out examples/output/tomato-7d --charts
python3 -m smart_greenhouse_controller compare examples/config_tomato.json --out examples/output/tomato-7d-compare
python3 -m smart_greenhouse_controller simulate examples/config_lettuce.json --out examples/output/lettuce-7d --charts
python3 -m smart_greenhouse_controller simulate examples/config_cucumber.json --out examples/output/cucumber-7d
echo "All example outputs regenerated."
