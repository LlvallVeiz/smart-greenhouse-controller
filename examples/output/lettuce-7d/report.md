# Greenhouse Report — Lettuce (Lactuca sativa)

Simulated **7 days** (seed 42, dt 5 min, 2016 steps) with control **ON**. Greenhouse 24 m2, drip flow 2.0 L/min.

## Crop targets (from `docs/RESEARCH.md`)

- Temperature: day 15-22 C, night 10-13 C
- Relative humidity: 50-70%
- Soil VWC: irrigate below 0.28, stop above 0.40
- CO2 target: 900 ppm (daylight)
- Light: 220 umol/m2/s, 14 h photoperiod
- VPD band: 0.5-0.9 kPa

## Water

- Total water used: **360.0 L** (51.4 L/day)
- Irrigation events: 9 (180 min of valve-open time)
- Soil VWC: mean 0.320, min 0.266, max 0.379

## Climate compliance

- Time in temperature band: **53.1%** (78.7 h out of range over 7 days)
- Hours RH out of range: 65.2 h
- Hours VPD out of range: 64.8 h
- Mean temperature: 17.12 C, mean RH: 66.5%

## Light and CO2

- Mean DLI: **21.79 mol/m2/d** (per day: 26.7, 26.7, 15.5, 26.6, 26.7, 15.6, 14.7)
- Mean daytime CO2: 495 ppm
- Hours CO2 below target: 81.5 h

## Energy and actuator duty

- Total energy: **31.36 kWh**
  - heater: 0.00 kWh (0.0% duty)
  - fan: 17.19 kWh (85.3% duty)
  - lights: 14.17 kWh (21.1% duty)
- Irrigation duty: 1.8%, CO2 injector duty: 14.4%

## Notes

This is a simulation: the environment model is a first-order approximation (see `docs/RESEARCH.md` and `docs/CONTROL_DESIGN.md` for assumptions and limits). Numbers describe the model, not a real greenhouse.
