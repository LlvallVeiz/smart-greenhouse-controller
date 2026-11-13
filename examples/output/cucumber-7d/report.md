# Greenhouse Report — Cucumber (Cucumis sativus)

Simulated **7 days** (seed 7, dt 5 min, 2016 steps) with control **ON**. Greenhouse 24 m2, drip flow 2.0 L/min.

## Crop targets (from `docs/RESEARCH.md`)

- Temperature: day 22-28 C, night 17-20 C
- Relative humidity: 70-85%
- Soil VWC: irrigate below 0.32, stop above 0.45
- CO2 target: 1000 ppm (daylight)
- Light: 250 umol/m2/s, 14 h photoperiod
- VPD band: 0.6-1.2 kPa

## Water

- Total water used: **560.0 L** (80.0 L/day)
- Irrigation events: 14 (280 min of valve-open time)
- Soil VWC: mean 0.355, min 0.307, max 0.418

## Climate compliance

- Time in temperature band: **61.3%** (65.0 h out of range over 7 days)
- Hours RH out of range: 99.1 h
- Hours VPD out of range: 111.6 h
- Mean temperature: 22.60 C, mean RH: 72.3%

## Light and CO2

- Mean DLI: **26.38 mol/m2/d** (per day: 26.7, 26.7, 26.1, 26.6, 26.7, 26.1, 25.7)
- Mean daytime CO2: 752 ppm
- Hours CO2 below target: 48.8 h

## Energy and actuator duty

- Total energy: **26.85 kWh**
  - heater: 6.88 kWh (2.7% duty)
  - fan: 6.44 kWh (31.9% duty)
  - lights: 13.53 kWh (20.1% duty)
- Irrigation duty: 2.8%, CO2 injector duty: 19.3%

## Notes

This is a simulation: the environment model is a first-order approximation (see `docs/RESEARCH.md` and `docs/CONTROL_DESIGN.md` for assumptions and limits). Numbers describe the model, not a real greenhouse.
