# Control Design — Smart Greenhouse Controller

Why the controller is built the way it is, what each limit protects
against, and what the example runs reveal about the model's limits.

## 1. Hysteresis instead of a single threshold

Every actuator is **latched**: it switches on when its variable
crosses the "on" threshold and only switches off when it crosses a
separate "off" threshold. The gap between the two is the dead-band.

| Actuator | ON when | OFF when | Dead-band |
|---|---|---|---|
| Irrigation | soil VWC < irrigate-below (e.g. 0.30) | soil VWC ≥ stop-above (e.g. 0.44) | 0.14 VWC |
| Heater | temp ≤ band-min − 1 °C | temp ≥ band-min + 1 °C | 2 °C |
| Fan (temperature) | temp ≥ band-max + 1 °C | temp ≤ band-max − 1 °C | 2 °C |
| Fan (humidity) | RH ≥ rh-max + 5% | RH ≤ rh-max − 5% | 10% RH |
| Grow lights | PPFD < 90% of target | PPFD ≥ target | 10% of target |
| CO₂ injector | CO₂ ≤ target − 50 ppm | CO₂ ≥ target | 50 ppm |

A single threshold would chatter: a noisy sensor hovering at the
setpoint would toggle the relay every timestep. The tests in
`tests/test_controller.py` pin this down — e.g. irrigation started
at VWC 0.25 must still be running at 0.32, must stop at 0.45, and
must not restart at 0.35.

## 2. Interlock: heater and fan never run together

Heating while venting is pure waste. The controller enforces it in
`Controller._apply_interlock`, and it applies in manual mode too:
if the operator forces both on, the fan wins and the heater is cut.
A 7-day simulation test asserts the pair is never on together.

## 3. Irrigation safety limits

A stuck moisture sensor must not flood the beds, so irrigation is
bounded three ways:

1. **Time window** — default 05:00–19:00. Night watering keeps
   leaves wet and invites disease.
2. **Maximum event duration** — the crop profile's
   `irrigation_max_minutes` (default 20 min). One event raises VWC
   by ~0.08, so the 0.30 → 0.44 band is normally crossed by two
   back-to-back events, not one.
3. **Maximum events per day** (default 6) plus a 10-minute
   cool-down between events.

The example runs show the duration cap doing its job: in the 7-day
tomato run all 13 events end on the 20-minute cap (soil peaks at
0.390, below the 0.44 ceiling) — the ceiling is a backstop, the cap
is the working limit.

## 4. CO₂ enrichment only when it can work

Enrichment is disabled at night (no photosynthesis), disabled while
the fan runs (venting dumps the gas), and hysteresis-latched around
the target. Consequence visible in the example run: because the fan
runs 74% of the time, daytime CO₂ averages only 542 ppm against the
1,000 ppm target — the model reproduces the real-world conflict
between ventilation and enrichment. Commercial growers solve it by
enriching only when the house is sealed; this controller does the
same by construction.

## 5. Environment model and its calibration

The environment (`sensors.py`) is a first-order model, not a
physics simulation:

* Temperature relaxes toward outdoor + solar gain with a 45-minute
  time constant; heater +0.8 °C per 5-min step; fan pulls 35% of the
  way to outdoor per step.
* Humidity relaxes toward a temperature-dependent level and is
  pulled toward outdoor RH when venting.
* Soil dries by evapotranspiration scaling with VPD and light;
  irrigation adds water at the emitter rate into a 500 L wetted
  root-zone volume.
* CO₂ is drawn down by photosynthesis in daylight, rises from
  respiration at night, exchanges with outdoor air when venting.

Calibration target: tomato water use ≈ 1 L/plant/day (extension
practice, see `docs/RESEARCH.md`). The 7-day tomato run uses
74.3 L/day for a 24 m² house ≈ 1.2 L/plant/day at 60 plants — in
the right ballpark. The evapotranspiration coefficient was tuned
to hit this, and the tuning is stated here rather than hidden.

## 6. What the example runs reveal (honest limits)

* **Night temperature is the weak spot.** In the tomato run, 38.8
  of the 61.2 out-of-band hours are at night: on warm evenings the
  outdoor air stays above the 18 °C night maximum, and passive
  ventilation cannot cool below outdoor temperature. Only active
  cooling (or a colder climate) fixes that.
* **The house runs humid.** Night RH drifts toward 90%+, so the
  fan works hard (74% duty) and RH is still out of band 99.4 h in
  7 days — better than the uncontrolled 161.7 h, but far from
  perfect. A dehumidifier actuator is the obvious next addition.
* **Lettuce needs a cool climate.** In the default 20 °C-mean
  climate the lettuce run stays in band only 11% of the time; with
  the cooler 16 °C-mean climate in `examples/config_lettuce.json`
  it reaches 53%. Cool-season crops in a warm climate need active
  cooling — the model makes that visible instead of hiding it.
* **DLI is weather-driven.** Sunny days give ~26.7 mol/m²/d,
  cloudy days ~15.5; supplemental lights (22.5% duty) lift the
  cloudy days but cannot match full sun.

## 7. Modes

* `auto` — the hysteresis logic above.
* `manual` — operator-forced actuator states (interlock still
  enforced). Useful for testing one actuator in isolation.
* `control_enabled=False` — the uncontrolled baseline used by the
  `compare` command: same weather, every actuator off.
