# Research — Smart Greenhouse Controller

How the numbers in this project were chosen, and where each one comes
from. Every setpoint in `src/smart_greenhouse_controller/crops.py` traces
to a source below. Where sources disagree (they do — greenhouse advice
depends on cultivar, stage and climate), the profile uses the
overlapping consensus and says so.

## 1. Temperature and humidity by crop

### Tomato (*Solanum lycopersicum*)

The USDA NRCS high-tunnel guide gives, for tomato, an optimum of
70–75 °F (21–24 °C) from transplant to flowering and the same to
harvest, a maximum air temperature of 85 °F (29 °C), and a venting
threshold of 75 °F (24 °C) in the transplant stage and 65 °F (18 °C)
later. Temperatures "much higher than 85 °F day / 75 °F night can
stress tomato cultivars and result in flower abortion, pollen
sterility and ripening disorders". The same guide warns that disease
problems can occur above 85% relative humidity.

A 2025 systematic review (MDPI *Horticulturae*, PRISMA, 1995–2025
literature) puts the tomato optimum at 18–25 °C, 200–300
µmol·m⁻²·s⁻¹ and 600–1100 ppm CO₂ in Mediterranean and arid zones.

**Profile used:** day 20–27 °C, night 15–18 °C, RH 60–70%.

### Lettuce (*Lactuca sativa*)

The USDA NRCS table lists leafy greens at 60–65 °F (15–18 °C)
optimum with a 75 °F (24 °C) maximum. The Cornell CEA *Hydroponic
Lettuce Handbook* lists 24 °C day / 19 °C night and 50–70% RH for
its production system. The MDPI review gives 15–22 °C, 200–250
µmol·m⁻²·s⁻¹ and 600–1100 ppm CO₂ in temperate zones, and notes
lettuce "thrives at 15–20 °C to prevent bolting".

**Profile used:** day 15–22 °C, night 10–13 °C, RH 50–70% — the
cool end of the published range, because bolting risk rises fast
above ~22 °C.

### Cucumber and pepper

USDA NRCS: cucumber 70–85 °F (21–29 °C) with a 90 °F (32 °C)
maximum and an 80 °F (27 °C) venting threshold; pepper 70–80 °F
(21–27 °C), maximum 85–90 °F. **Profiles used:** cucumber day
22–28 °C, night 17–20 °C, RH 70–85%; pepper day 21–27 °C, night
16–18 °C, RH 60–70%.

## 2. Soil moisture and irrigation thresholds

Irrigation in this project is triggered by volumetric water content
(VWC), not by a clock. The anchor study is a split-plot trial on
greenhouse cherry tomatoes (MDPI *Water* 2021, Goiano Federal
Institute, Brazil): four VWC thresholds — 0.23, 0.30, 0.37 and 0.44
m³·m⁻³ — triggered a drip system via capacitance sensors. The 0.44
treatment gave the highest fruit yield and 102% higher water-use
efficiency than 0.23; deficit irrigation raised fruit soluble solids
by ~16%. Saturation of their soil/sand mix was 0.44 m³·m⁻³, and 0.23
was "severe stress … proximity to the permanent wilting point".

A 2025 *Frontiers in Plant Science* study using leaf-turgor probes
found the no/mild-stress soil-water threshold for drip-irrigated
tomato at SWC > 20%, and severe stress below 18% (field capacity of
their silty loam was 32%).

**Profiles used:** tomato irrigate below 0.30, stop above 0.44;
lettuce 0.28–0.40; cucumber 0.32–0.45; pepper 0.30–0.43. The
tomato band (0.30–0.44) sits inside the trialled range: it starts
watering where the trial still saw good performance and stops at
the trial's best-yield threshold.

Practical context: drip emitters of 0.5–2 L·h⁻¹ per emitter, run in
short cycles (e.g. 15-minute bursts, 2–3 times daily), and a mature
tomato plant uses roughly 1 L of water per day. The model's
calibration (2 L/min into a 500 L wetted root-zone volume, 20-minute
maximum event) reproduces ~74 L/day for a 24 m² house — about
1.2 L/plant/day at 60 plants — in the same ballpark.

## 3. Light: PPFD and daily light integral (DLI)

The MDPI review's optima: lettuce 200–250 µmol·m⁻²·s⁻¹, tomato
200–300 µmol·m⁻²·s⁻¹. Supplemental lighting is switched on when
measured PPFD falls below 90% of the crop target during the
photoperiod (14 h). DLI is the time integral of PPFD
(mol·m⁻²·d⁻¹); e.g. 300 µmol·m⁻²·s⁻¹ held for 12 h is 12.96
mol·m⁻²·d⁻¹. The model converts lux to PPFD with the sunlight
factor 0.0185 µmol·m⁻²·s⁻¹ per lux; LED spectra differ, so the
factor is documented as an approximation, not a constant of nature.

## 4. CO₂ enrichment

Ambient CO₂ is ~420 ppm. The AHDB best-practice guide (drawing on
Nederhoff & Vegter 1994) states that raising glasshouse CO₂ to
1,000 ppm increases photosynthesis by about 50% over ambient at any
given light level, with the response saturating around 1,000–1,300
ppm; 800–1,000 ppm is recommended for lettuce and seedlings.
Without enrichment, a sealed glasshouse with a large leaf area can
be drawn down to ~200 ppm in summer, cutting canopy photosynthesis
by ~26%. Typical practice is estimated to raise yields 20–30%.

A 2025 factorial study on tomato in a climate-controlled greenhouse
found the highest yield (6.86 kg/plant) at 800 ppm CO₂ with 600
µmol·m⁻²·s⁻¹ light, and peak fruit weight/dry matter at 1,000 ppm.

**Profiles used:** CO₂ target 1,000 ppm (tomato, cucumber, pepper),
900 ppm (lettuce, basil). Enrichment runs only in daylight, only
while the vents are closed — venting dumps the gas outside faster
than it can be produced — and the injector is hysteresis-latched
(on below target − 50 ppm, off at target).

## 5. Vapour pressure deficit (VPD)

RH alone misleads: 70% RH is 0.55 kPa VPD at 16 °C but 1.27 kPa at
30 °C. VPD is computed with the Tetens equation for saturation
vapour pressure (FAO Irrigation and Drainage Paper 56, Allen et
al. 1998):

SVP = 0.6108 · exp(17.27·T / (T + 237.3)) kPa; VPD = SVP · (1 − RH/100).

Michigan State University floriculture specialist Erik Runkle's
framework, widely cited in CEA practice: 0.7–1.5 kPa for most plant
growth, 0.3–0.7 kPa for propagation, above 1.5 kPa is dry air.
Crop-specific practice: lettuce 0.5–0.9 kPa (tipburn risk above
~1.0 kPa), tomato 0.8–1.4 kPa. **Profiles used:** tomato
0.8–1.4, lettuce 0.5–0.9, cucumber 0.6–1.2, pepper 0.8–1.3,
basil 0.7–1.2 kPa.

## 6. Control method: hysteresis (on/off with dead-band)

Commercial greenhouse climate computers use proportional control,
but the on/off controller with hysteresis used here is the standard
first step (and what most hobby controllers actually implement):
each actuator latches on at one threshold and off at a different
one, so the relay cannot chatter around a single setpoint. The
dead-bands (±1 °C temperature, ±5% RH, 50 ppm CO₂) and the
heater/vent interlock are design choices of this project, documented
in `docs/CONTROL_DESIGN.md` — not values taken from a paper.

## 7. What this project does NOT claim

* The setpoints are production starting points from extension
  literature, not cultivar-specific recipes.
* The environment model is a first-order approximation calibrated
  to plausible water use; it is not validated against a real
  greenhouse. Its limits are listed in `docs/CONTROL_DESIGN.md`
  and in the README.
* Yield is not modelled. The project measures climate compliance,
  water and energy — not kilograms of tomatoes.

## References

1. USDA Natural Resources Conservation Service. *Controlling the
   High Tunnel Environment.*
   https://www.nrcs.usda.gov/sites/default/files/2022-10/Controlling-High-Tunnel-Environment.pdf
2. *Optimizing Microclimatic Conditions for Lettuce, Tomatoes,
   Carrots, and Beets* (systematic review, PRISMA 1995–2025).
   MDPI *Horticulturae* 2025, 16(3), 100.
   https://www.mdpi.com/2037-0164/16/3/100
3. *Horticultural Performance of Greenhouse Cherry Tomatoes
   Irrigated Automatically Based on Soil Moisture Sensor Readings.*
   MDPI *Water* 2021, 13(19), 2662.
   https://www.mdpi.com/2073-4441/13/19/2662
4. *Water status diagnosis in greenhouse drip-irrigated tomato and
   celery using leaf turgor dynamics and machine learning.*
   *Frontiers in Plant Science* 2025.
   https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1743809/full
5. AHDB. *CO₂ best practice guide: Background* (after Nederhoff &
   Vegter 1994; Besford et al. 1990).
   https://potatoes.ahdb.org.uk/knowledge-library/co2-best-practice-guide-background
6. *Effects of Elevated CO₂ and Light Intensity on Growth, Yield,
   and Nutritional Quality of Tomato in Controlled Environment
   Agriculture Systems.* American Journal of Life Science
   Innovation 2025, 4(1).
   https://journals.e-palli.com/home/index.php/ajlsi/article/download/4353/2071/27026
7. Allen, R. G., Pereira, L. S., Raes, D. & Smith, M. *Crop
   evapotranspiration — Guidelines for computing crop water
   requirements.* FAO Irrigation and Drainage Paper 56, 1998
   (Tetens equation for saturation vapour pressure).
8. Cornell Controlled Environment Agriculture. *Hydroponic Lettuce
   Handbook* (24 °C day / 19 °C night, 50–70% RH) — as summarised
   in the CEA literature; see also the VPD discussion at
   https://yakeclimate.com/resources/articles/ideal-humidity-for-greenhouse/
9. Runkle, E. (Michigan State University Extension) — VPD target
   framework 0.7–1.5 kPa, as summarised at
   https://www.marsverticalfarm.com/blog/vpd-chart-for-indoor-farms/
10. *Greenhouse Management: Temperature Guide.* Agricalc.
    https://agricalc.online/guides/greenhouse-management-guide.html
