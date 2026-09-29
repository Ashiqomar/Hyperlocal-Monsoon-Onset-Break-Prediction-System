"""Mock extended-range (weeks 1-4) probabilistic rainfall forecast.

Each panchayat gets a seeded ensemble: every member simulates 28 days of daily
rainfall with a two-state (wet/dry) Markov chain and gamma-distributed wet-day
amounts, driven by the block's climatology. A per-week anomaly shared by all
members plays the role of the forecast "signal"; spread between members is the
uncertainty. Probabilities and quantiles are then read off the ensemble, so they
stay mutually consistent (e.g. a high dry-spell chance comes with a low P50).

The RNG seed is derived from the panchayat id only, so the numbers for a given
panchayat never change between calls or restarts. Python's built-in hash() is
salted per process, so crc32 is used instead.
"""

import random
import zlib
from datetime import date, timedelta

from app.models import Panchayat
from app.schemas.forecast import (
    ForecastDefinitions,
    ForecastResponse,
    RainfallQuantiles,
    WeeklyForecast,
)
from app.schemas.geo import PanchayatOut

MODEL_NAME = "synthetic-ensemble-v1"
ENSEMBLE_MEMBERS = 200
WEEKS = 4
DAYS_PER_WEEK = 7

DRY_DAY_MM = 2.5  # IMD: a rainy day has >= 2.5 mm
DRY_SPELL_MIN_DAYS = 5
HEAVY_RAIN_MM = 64.5  # IMD: heavy rain is >= 64.5 mm/day

# Wet-day amounts are strongly skewed; shape < 1 gives a realistic heavy tail.
GAMMA_SHAPE = 0.8
# Extra probability that a wet day is followed by another wet day (persistence).
WET_PERSISTENCE = 0.2


def panchayat_seed(panchayat_id: str) -> int:
    return zlib.crc32(panchayat_id.encode("utf-8"))


def _quantile(sorted_values: list[float], q: float) -> float:
    """Linearly interpolated quantile of an already-sorted list."""
    pos = (len(sorted_values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def longest_dry_run(daily_mm: list[float]) -> int:
    longest = run = 0
    for mm in daily_mm:
        run = run + 1 if mm < DRY_DAY_MM else 0
        longest = max(longest, run)
    return longest


def _simulate_week(rng: random.Random, p_wet: float, mean_mm: float, was_wet: bool) -> tuple[list[float], bool]:
    """Simulate one member's week. Returns daily rainfall and the final wet state."""
    p_wet = min(max(p_wet, 0.05), 0.85)
    p_wet_after_wet = min(p_wet + WET_PERSISTENCE, 0.95)
    # Chosen so the chain's long-run wet fraction equals p_wet.
    p_wet_after_dry = p_wet * (1 - p_wet_after_wet) / (1 - p_wet)
    scale = mean_mm / GAMMA_SHAPE

    daily: list[float] = []
    for _ in range(DAYS_PER_WEEK):
        was_wet = rng.random() < (p_wet_after_wet if was_wet else p_wet_after_dry)
        daily.append(rng.gammavariate(GAMMA_SHAPE, scale) if was_wet else 0.0)
    return daily, was_wet


def simulate_ensemble(panchayat: Panchayat) -> list[list[float]]:
    """Daily rainfall (mm) for each ensemble member: ENSEMBLE_MEMBERS x (WEEKS * 7) days.

    This is the raw ensemble behind /forecast; the digital twin classifies the
    same members into scenarios, so both endpoints stay consistent.
    """
    block = panchayat.block
    rng = random.Random(panchayat_seed(panchayat.id))

    # Local deviation from block climatology (terrain, microclimate).
    local_factor = rng.lognormvariate(0.0, 0.15)
    # Forecast signal per week, shared by all members: <1 is a weak/break
    # phase, >1 an active monsoon phase.
    week_anomaly = [rng.lognormvariate(0.0, 0.35) for _ in range(WEEKS)]

    members: list[list[float]] = []
    for _ in range(ENSEMBLE_MEMBERS):
        was_wet = rng.random() < block.rain_day_prob
        days: list[float] = []
        for w in range(WEEKS):
            # Split the anomaly between wet-day frequency and intensity so the
            # combined effect on weekly totals is ~linear, not squared.
            scale = (local_factor * week_anomaly[w]) ** 0.5
            daily, was_wet = _simulate_week(
                rng,
                p_wet=block.rain_day_prob * scale,
                mean_mm=block.rain_day_mean_mm * scale,
                was_wet=was_wet,
            )
            days.extend(daily)
        members.append(days)
    return members


def generate_forecast(panchayat: Panchayat, issued_on: date) -> ForecastResponse:
    members = simulate_ensemble(panchayat)

    weeks: list[WeeklyForecast] = []
    for w in range(WEEKS):
        week_days = [m[w * DAYS_PER_WEEK : (w + 1) * DAYS_PER_WEEK] for m in members]
        dry_spells = sum(longest_dry_run(d) >= DRY_SPELL_MIN_DAYS for d in week_days)
        heavy_rain = sum(max(d) >= HEAVY_RAIN_MM for d in week_days)
        values = sorted(sum(d) for d in week_days)
        start = w * DAYS_PER_WEEK + 1
        end = start + DAYS_PER_WEEK - 1
        weeks.append(
            WeeklyForecast(
                week=w + 1,
                lead_days_start=start,
                lead_days_end=end,
                start_date=issued_on + timedelta(days=start),
                end_date=issued_on + timedelta(days=end),
                rainfall_mm=RainfallQuantiles(
                    p10=round(_quantile(values, 0.10), 1),
                    p50=round(_quantile(values, 0.50), 1),
                    p90=round(_quantile(values, 0.90), 1),
                ),
                dry_spell_probability=round(dry_spells / ENSEMBLE_MEMBERS, 2),
                heavy_rain_probability=round(heavy_rain / ENSEMBLE_MEMBERS, 2),
            )
        )

    return ForecastResponse(
        panchayat=to_panchayat_out(panchayat),
        issued_on=issued_on,
        model=MODEL_NAME,
        ensemble_members=ENSEMBLE_MEMBERS,
        definitions=ForecastDefinitions(
            dry_day_threshold_mm=DRY_DAY_MM,
            dry_spell_min_days=DRY_SPELL_MIN_DAYS,
            heavy_rain_threshold_mm=HEAVY_RAIN_MM,
        ),
        weeks=weeks,
    )


def to_panchayat_out(p: Panchayat) -> PanchayatOut:
    return PanchayatOut(
        id=p.id,
        name=p.name,
        block_id=p.block_id,
        block_name=p.block.name,
        district=p.block.district,
        lat=p.lat,
        lon=p.lon,
        soil_type=p.soil_type,
        irrigation_type=p.irrigation_type,
        primary_crop=p.primary_crop,
    )
