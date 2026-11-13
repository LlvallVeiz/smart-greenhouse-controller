# Greenhouse Report — Tomato (Solanum lycopersicum)

Simulated **7 days** (seed 42, dt 5 min, 2016 steps) with control **ON**. Greenhouse 24 m2, drip flow 2.0 L/min.

## Crop targets (from `docs/RESEARCH.md`)

- Temperature: day 20-27 C, night 15-18 C
- Relative humidity: 60-70%
- Soil VWC: irrigate below 0.30, stop above 0.44
- CO2 target: 1000 ppm (daylight)
- Light: 250 umol/m2/s, 14 h photoperiod
- VPD band: 0.8-1.4 kPa

## Water

- Total water used: **520.0 L** (74.3 L/day)
- Irrigation events: 13 (260 min of valve-open time)
- Soil VWC: mean 0.339, min 0.284, max 0.390

## Climate compliance

- Time in temperature band: **63.6%** (61.2 h out of range over 7 days)
- Hours RH out of range: 99.4 h
- Hours VPD out of range: 92.6 h
- Mean temperature: 21.20 C, mean RH: 66.9%

## Light and CO2

- Mean DLI: **21.79 mol/m2/d** (per day: 26.7, 26.7, 15.5, 26.6, 26.7, 15.6, 14.7)
- Mean daytime CO2: 542 ppm
- Hours CO2 below target: 78.7 h

## Energy and actuator duty

- Total energy: **31.17 kWh**
  - heater: 1.12 kWh (0.4% duty)
  - fan: 14.95 kWh (74.2% duty)
  - lights: 15.10 kWh (22.5% duty)
- Irrigation duty: 2.6%, CO2 injector duty: 16.4%

## Control ON vs OFF (identical weather, same seed)

- Water: +520.0 L (controlled 520.0 L vs baseline 0.0 L) -- the baseline waters nothing, so this is the *cost* of keeping the soil in band, not a saving
- Hours temperature out of range: -28.6 h (controlled 61.2 h vs baseline 89.8 h)
- Hours RH out of range: -62.3 h
- Hours VPD out of range: -38.6 h
- Time in temperature band: +17.1 percentage points
- Mean DLI: +0.00 mol/m2/d (supplemental lighting effect)
- Energy cost of control: 31.17 kWh over 7 days

## Notes

This is a simulation: the environment model is a first-order approximation (see `docs/RESEARCH.md` and `docs/CONTROL_DESIGN.md` for assumptions and limits). Numbers describe the model, not a real greenhouse.
