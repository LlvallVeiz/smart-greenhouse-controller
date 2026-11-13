"""Crop climate profiles: the setpoints the controller defends.

Every number below is taken from the sources listed in
``docs/RESEARCH.md`` (USDA NRCS high-tunnel guide, Cornell CEA
Hydroponic Lettuce Handbook, the MDPI systematic review of greenhouse
microclimates, the MDPI cherry-tomato sensor-irrigation trial, AHDB
CO2 best-practice guide, and the VPD ranges summarised by Michigan
State University / Erik Runkle).  Values are production starting
points, not universal setpoints -- cultivar, growth stage and local
conditions shift them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CropProfile:
    """Climate targets and control limits for one crop."""

    name: str
    latin_name: str
    # Air temperature targets (deg C).
    temp_day_min: float
    temp_day_max: float
    temp_night_min: float
    temp_night_max: float
    # Relative humidity targets (%).
    rh_min: float
    rh_max: float
    # Soil volumetric water content (fraction, 0..1) that drives irrigation.
    soil_irrigate_below: float  # start watering when VWC falls below this
    soil_stop_above: float  # stop watering once VWC reaches this
    # CO2 enrichment target during the lit period (ppm).
    co2_target_ppm: float
    # Supplemental-light target PPFD (umol/m^2/s) and photoperiod (hours).
    ppfd_target: float
    photoperiod_hours: float
    # VPD steering band (kPa).
    vpd_min: float
    vpd_max: float
    # Irrigation limits.
    irrigation_max_minutes: int = 20
    irrigation_max_events_per_day: int = 6
    notes: str = ""
    sources: tuple[str, ...] = field(default_factory=tuple)


TOMATO = CropProfile(
    name="tomato",
    latin_name="Solanum lycopersicum",
    temp_day_min=20.0,
    temp_day_max=27.0,
    temp_night_min=15.0,
    temp_night_max=18.0,
    rh_min=60.0,
    rh_max=70.0,
    soil_irrigate_below=0.30,
    soil_stop_above=0.44,
    co2_target_ppm=1000.0,
    ppfd_target=250.0,
    photoperiod_hours=14.0,
    vpd_min=0.8,
    vpd_max=1.4,
    notes=(
        "Day 20-27 C, night 15-18 C; vent above ~29 C (85 F). "
        "VWC irrigation thresholds 0.30-0.44 m3/m3 from the cherry-tomato "
        "sensor trial (highest yield and WUE at 0.44)."
    ),
    sources=(
        "USDA NRCS, Controlling the High Tunnel Environment",
        "MDPI Horticulturae 2025 systematic review (tomato 18-25 C, 200-300 umol/m2/s, 600-1100 ppm CO2)",
        "MDPI Water 2021, cherry-tomato sensor irrigation (VWC 0.23/0.30/0.37/0.44)",
        "AHDB CO2 best practice guide (saturation ~1000-1300 ppm)",
    ),
)

LETTUCE = CropProfile(
    name="lettuce",
    latin_name="Lactuca sativa",
    temp_day_min=15.0,
    temp_day_max=22.0,
    temp_night_min=10.0,
    temp_night_max=13.0,
    rh_min=50.0,
    rh_max=70.0,
    soil_irrigate_below=0.28,
    soil_stop_above=0.40,
    co2_target_ppm=900.0,
    ppfd_target=220.0,
    photoperiod_hours=14.0,
    vpd_min=0.5,
    vpd_max=0.9,
    notes=(
        "Cool-season crop: bolts in heat. Cornell CEA handbook lists "
        "24 C day / 19 C night and 50-70% RH for its hydroponic system; "
        "the MDPI review gives 15-22 C as the temperate optimum. "
        "VPD kept low (0.5-0.9 kPa) to limit tipburn."
    ),
    sources=(
        "Cornell CEA Hydroponic Lettuce Handbook (24 C day / 19 C night, 50-70% RH)",
        "MDPI Horticulturae 2025 systematic review (lettuce 15-22 C, 200-250 umol/m2/s, 600-1100 ppm CO2)",
        "USDA NRCS high-tunnel table (leafy greens 60-65 F optimum)",
    ),
)

CUCUMBER = CropProfile(
    name="cucumber",
    latin_name="Cucumis sativus",
    temp_day_min=22.0,
    temp_day_max=28.0,
    temp_night_min=17.0,
    temp_night_max=20.0,
    rh_min=70.0,
    rh_max=85.0,
    soil_irrigate_below=0.32,
    soil_stop_above=0.45,
    co2_target_ppm=1000.0,
    ppfd_target=250.0,
    photoperiod_hours=14.0,
    vpd_min=0.6,
    vpd_max=1.2,
    notes=(
        "Warm, humid crop. USDA NRCS table: 75-85 F day, 80 F venting "
        "threshold; RH 70-85%."
    ),
    sources=(
        "USDA NRCS, Controlling the High Tunnel Environment",
        "MDPI Horticulturae 2025 systematic review",
    ),
)

PEPPER = CropProfile(
    name="pepper",
    latin_name="Capsicum annuum",
    temp_day_min=21.0,
    temp_day_max=27.0,
    temp_night_min=16.0,
    temp_night_max=18.0,
    rh_min=60.0,
    rh_max=70.0,
    soil_irrigate_below=0.30,
    soil_stop_above=0.43,
    co2_target_ppm=1000.0,
    ppfd_target=250.0,
    photoperiod_hours=14.0,
    vpd_min=0.8,
    vpd_max=1.3,
    notes="USDA NRCS table: 70-80 F optimum, 85-90 F maximum; RH 60-70%.",
    sources=("USDA NRCS, Controlling the High Tunnel Environment",),
)

BASIL = CropProfile(
    name="basil",
    latin_name="Ocimum basilicum",
    temp_day_min=20.0,
    temp_day_max=26.0,
    temp_night_min=16.0,
    temp_night_max=18.0,
    rh_min=50.0,
    rh_max=70.0,
    soil_irrigate_below=0.28,
    soil_stop_above=0.40,
    co2_target_ppm=900.0,
    ppfd_target=220.0,
    photoperiod_hours=14.0,
    vpd_min=0.7,
    vpd_max=1.2,
    notes="Warm-season herb; kept in the same band as tomato/pepper.",
    sources=("USDA NRCS, Controlling the High Tunnel Environment",),
)

PROFILES: dict[str, CropProfile] = {
    p.name: p for p in (TOMATO, LETTUCE, CUCUMBER, PEPPER, BASIL)
}


def get_profile(name: str) -> CropProfile:
    """Return the profile for ``name`` (case-insensitive).

    Raises KeyError with the list of known crops for unknown names.
    """
    key = name.strip().lower()
    if key not in PROFILES:
        raise KeyError(
            f"unknown crop {name!r}; known crops: {', '.join(sorted(PROFILES))}"
        )
    return PROFILES[key]


def list_profiles() -> list[CropProfile]:
    """All built-in crop profiles, in a stable order."""
    return [PROFILES[name] for name in sorted(PROFILES)]
