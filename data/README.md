# Data

`example_7day_tomato.csv` / `example_7day_tomato.json` — the full
time series of the headline example run: tomato, 7 days, seed 42,
5-minute steps (2,016 rows), control ON, warm climate (outdoor mean
20 °C). Columns: timestamp, day_index, minute_of_day, temp_c,
rh_percent, soil_vwc, par_lux, co2_ppm, vpd_kpa, the five actuator
states, cumulative water_used_l, and the weather condition of the
day. Regenerate with
`bash examples/run_examples.sh` (output lands in
`examples/output/tomato-7d/`).
