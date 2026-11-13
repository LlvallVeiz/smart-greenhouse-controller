# Smart Greenhouse Controller

End-to-end simulation of a small greenhouse: a realistic sensor
environment (temperature, humidity, soil moisture, light, CO₂),
a hysteresis controller for irrigation / ventilation / heating /
supplemental lighting / CO₂ enrichment, time-series analysis, and
Markdown + HTML reporting. Pure Python standard library for the
core (matplotlib is optional, only for PNG charts).

## Background

A greenhouse controller has to keep five variables inside crop-
specific bands at once — and the actuators fight each other:
venting cools the house but dumps enriched CO₂ outside; heating
while venting wastes energy; watering at night keeps leaves wet
and invites disease. This project models that coupled system
explicitly, with setpoints taken from real horticulture sources
(USDA NRCS, Cornell CEA, MDPI trials — see `docs/RESEARCH.md`).

**Control method: hysteresis (on/off with dead-band).** Each
actuator latches on at one threshold and off at a different one,
so a noisy sensor hovering at a setpoint cannot chatter the relay.
The heater and the vent fan are interlocked — they can never run
together, in auto mode or manual mode. Irrigation is additionally
bounded by a daytime window, a 20-minute maximum event, a daily
event cap and a cool-down. The design rationale, including what
the example runs reveal about the model's limits, is in
`docs/CONTROL_DESIGN.md`.

**Crop profiles** (day/night temperature, RH, soil VWC band, CO₂
target, light target, VPD band) for tomato, lettuce, cucumber,
pepper and basil:

| Crop | Temp day (°C) | Temp night (°C) | RH (%) | Soil VWC | CO₂ (ppm) | VPD (kPa) |
|---|---|---|---|---|---|---|
| Tomato | 20–27 | 15–18 | 60–70 | 0.30–0.44 | 1000 | 0.8–1.4 |
| Lettuce | 15–22 | 10–13 | 50–70 | 0.28–0.40 | 900 | 0.5–0.9 |
| Cucumber | 22–28 | 17–20 | 70–85 | 0.32–0.45 | 1000 | 0.6–1.2 |
| Pepper | 21–27 | 16–18 | 60–70 | 0.30–0.43 | 1000 | 0.8–1.3 |
| Basil | 20–26 | 16–18 | 50–70 | 0.28–0.40 | 900 | 0.7–1.2 |

## Project structure

```
smart-greenhouse-controller/
├── src/smart_greenhouse_controller/
│   ├── physics.py      # Tetens SVP, VPD, dew point, DLI, lux<->PPFD
│   ├── crops.py        # crop climate profiles (sourced setpoints)
│   ├── sensors.py      # greenhouse environment model + weather generator
│   ├── controller.py   # hysteresis controller, interlock, safety limits
│   ├── simulator.py    # closed-loop engine + ON/OFF comparison runs
│   ├── storage.py      # CSV/JSON time series, JSON run configs
│   ├── analysis.py     # water, compliance, DLI, energy metrics
│   ├── report.py       # Markdown report generator
│   ├── dashboard.py    # static HTML dashboard (Chart.js CDN)
│   ├── charts.py       # matplotlib PNG charts (optional dep)
│   └── cli.py          # simulate / compare / list-crops / demo
├── tests/              # pytest, 100 tests
├── docs/
│   ├── RESEARCH.md     # sourced setpoints + references
│   └── CONTROL_DESIGN.md  # hysteresis, interlock, limits, findings
├── examples/           # 3 crop configs + real outputs in output/
├── scripts/            # run_demo.py, compare_modes.py
└── data/               # canonical 7-day tomato time series
```

## Quick start

```bash
# No runtime dependencies beyond Python 3.10+ (pytest for tests).
pip install -r requirements.txt

# List the crop profiles
PYTHONPATH=src python3 -m smart_greenhouse_controller list-crops

# Quick 3-day tomato demo, printed to stdout
PYTHONPATH=src python3 -m smart_greenhouse_controller demo

# Full 7-day run from a config file (CSV + JSON + report + dashboard)
PYTHONPATH=src python3 -m smart_greenhouse_controller simulate \
    examples/config_tomato.json --out output --charts

# Control ON vs OFF on identical weather
PYTHONPATH=src python3 -m smart_greenhouse_controller compare \
    examples/config_tomato.json --out output-compare
```

Or install the `greenhouse` command: `pip install -e .`

## Example output (real runs)

### Tomato, 7 days, seed 42 — `examples/output/tomato-7d/`

24 m² greenhouse, drip 2.0 L/min, 2,016 steps of 5 minutes,
weather 3 sunny + 4 cloudy days.

```
crop:            tomato
days:            7 (seed 42, 2016 steps)
water used:      520.0 L (74.3 L/day, 13 events)
time in band:    63.6%
temp out of range: 61.2 h
mean DLI:        21.79 mol/m2/d
energy:          31.17 kWh
```

Headline details from `report.md`: soil VWC mean 0.339 (min 0.284,
max 0.390); mean temperature 21.20 °C (min 14.43, max 28.37);
mean RH 66.9%; RH out of range 99.4 h; VPD out of range 92.6 h;
mean daytime CO₂ 542 ppm (target 1,000 — enrichment loses to
ventilation, see below); DLI per day 26.7, 26.7, 15.5, 26.6, 26.7,
15.6, 14.7 (sunny ≈ 26.7, cloudy ≈ 15.5). Actuator duty: fan
74.2%, lights 22.5%, CO₂ injector 16.4%, irrigation 2.6%, heater
0.4%. Energy: heater 1.12 kWh, fan 14.95 kWh, lights 15.10 kWh.

### Control ON vs OFF (identical weather, same seed)

```
water:    ON 520.0 L vs OFF 0.0 L (+520.0 L)
temp out: ON 61.2 h vs OFF 89.8 h (-28.6 h)
RH out:   ON 99.4 h vs OFF 161.7 h (-62.3 h)
VPD out:  ON 92.6 h vs OFF 131.2 h (-38.6 h)
in band:  ON 63.6% vs OFF 46.5% (+17.1 pp)
energy (control cost): 31.17 kWh
```

Read the water line as the *cost* of control: the uncontrolled
baseline waters nothing, so the delta is positive by construction.
What control buys is climate: 28.6 fewer hours out of the
temperature band and 62.3 fewer hours out of the humidity band,
for 31.17 kWh over 7 days.

### Lettuce and cucumber (same 7-day setup)

| Run | Water | In band | Temp out | Energy |
|---|---|---|---|---|
| Lettuce, cool climate (16 °C mean) | 360.0 L (51.4 L/day, 9 events) | 53.1% | 78.7 h | 31.36 kWh |
| Cucumber, warm climate, seed 7 | 560.0 L (80.0 L/day, 14 events) | 61.3% | 65.0 h | 26.85 kWh |

## Design decisions

* **Standard library only for the core.** The simulation, control,
  analysis, report and dashboard need no third-party packages;
  matplotlib is optional (PNG charts) and Chart.js loads from CDN
  at view time.
* **Seeded weather.** A Markov chain over sunny/cloudy/rainy days
  makes every run reproducible; the ON/OFF comparison shares the
  seed, so differences are caused by the controller, not the
  weather.
* **First-order environment model, calibrated to real water use.**
  The evapotranspiration rate is tuned so tomato water use lands
  near extension practice (~1 L/plant/day): the example run uses
  74.3 L/day ≈ 1.2 L/plant/day at 60 plants per 24 m². The tuning
  is documented in `docs/CONTROL_DESIGN.md`, not hidden.
* **Honest limits, kept visible.** The model has no active cooling
  (ventilation cannot cool below outdoor temperature — 38.8 of the
  61.2 out-of-band hours in the tomato run are warm nights), no
  dehumidifier, and no yield model. It measures climate compliance,
  water and energy — not kilograms of tomatoes.

## Tests

```bash
python3 -m pytest tests/ -q
# 100 passed
```

Coverage includes hand-computed physics values (SVP 3.17 kPa at
25 °C, VPD 1.27 kPa at 25 °C/60% RH, dew point 16.7 °C, DLI
12.96 mol/m²/d for 300 µmol/m²/s × 12 h), hysteresis behaviour
(no chatter inside the dead-band, irrigation stops at the ceiling,
20-minute safety cap, window blocking), the heater/fan interlock
over a full temperature sweep, determinism, and end-to-end CLI
runs. The 7-day property test asserts control beats the
uncontrolled baseline on temperature compliance.

## Limitations and future work

* No active cooling or dehumidification — the two biggest gaps the
  example runs expose.
* Single-zone, single-crop model; no growth/yield model.
* Lux→PPFD uses the sunlight factor 0.0185; LED spectra differ.
* Weather is synthetic (seeded Markov chain), not a real location's
  data; an outdoor-temperature CSV input would be a natural next
  step, as would MQTT telemetry in the style of a real sensor node.
