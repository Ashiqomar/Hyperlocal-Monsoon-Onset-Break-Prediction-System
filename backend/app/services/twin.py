"""Scenario simulation ("digital twin") on top of the mock forecast.

Every ensemble member from the forecast is classified into one rainfall
scenario, so scenario probabilities are ensemble frequencies and always sum
to 1. Each scenario's economics then come from the crop-response coefficients.
"""

from datetime import date

from app.data.crop_response import CROP_COEFFICIENTS
from app.models import Panchayat
from app.schemas.geo import Crop
from app.schemas.twin import CropEconomics, Scenario, ScenarioOutcome, TwinResponse, TwinSummary
from app.services.forecast import (
    DAYS_PER_WEEK,
    ENSEMBLE_MEMBERS,
    MODEL_NAME,
    longest_dry_run,
    simulate_ensemble,
    to_panchayat_out,
)

# Onset: >= 20 mm over 3 consecutive days in week 1 (a common sowing criterion).
ONSET_MM = 20.0
ONSET_WINDOW_DAYS = 3
# False onset: an onset followed by a dry spell of this many days in weeks 2-4.
FALSE_ONSET_DRY_DAYS = 10
# Seasonal total vs block climatology; IMD calls +/-19% "normal".
DRY_RATIO = 0.8
WET_RATIO = 1.2
# z-score of the 10th percentile of a normal distribution.
Z_P10 = 1.2816

SCENARIO_TEXT: dict[Scenario, tuple[str, str]] = {
    Scenario.NORMAL: ("Normal", f"4-week rainfall within ±{round((1 - DRY_RATIO) * 100)}% of normal"),
    Scenario.DRY: ("Dry", f"4-week rainfall below {round(DRY_RATIO * 100)}% of normal"),
    Scenario.WET: ("Wet", f"4-week rainfall above {round(WET_RATIO * 100)}% of normal"),
    Scenario.FALSE_ONSET: (
        "False onset",
        f"≥{ONSET_MM:g} mm in {ONSET_WINDOW_DAYS} days in week 1, then a ≥{FALSE_ONSET_DRY_DAYS}-day dry spell",
    ),
}


def classify_member(days: list[float], normal_total_mm: float) -> Scenario:
    week1 = days[:DAYS_PER_WEEK]
    had_onset = any(
        sum(week1[i : i + ONSET_WINDOW_DAYS]) >= ONSET_MM for i in range(DAYS_PER_WEEK - ONSET_WINDOW_DAYS + 1)
    )
    if had_onset and longest_dry_run(days[DAYS_PER_WEEK:]) >= FALSE_ONSET_DRY_DAYS:
        return Scenario.FALSE_ONSET

    ratio = sum(days) / normal_total_mm
    if ratio < DRY_RATIO:
        return Scenario.DRY
    if ratio > WET_RATIO:
        return Scenario.WET
    return Scenario.NORMAL


def build_twin(panchayat: Panchayat, crop: Crop, issued_on: date) -> TwinResponse:
    coeffs = CROP_COEFFICIENTS[crop]
    block = panchayat.block
    members = simulate_ensemble(panchayat)
    normal_total_mm = len(members[0]) * block.rain_day_prob * block.rain_day_mean_mm

    counts = dict.fromkeys(Scenario, 0)
    for days in members:
        counts[classify_member(days, normal_total_mm)] += 1

    baseline_profit = coeffs.normal_yield_q_per_ha * coeffs.price_inr_per_q - coeffs.base_cost_inr_per_ha

    outcomes: list[ScenarioOutcome] = []
    expected_profit = 0.0
    for scenario in Scenario:
        r = coeffs.response[scenario]
        probability = counts[scenario] / ENSEMBLE_MEMBERS
        yield_q = coeffs.normal_yield_q_per_ha * r.yield_factor
        cost = coeffs.base_cost_inr_per_ha + r.extra_cost_inr
        revenue = yield_q * coeffs.price_inr_per_q
        profit = revenue - cost
        profit_p10 = revenue * max(0.0, 1 - Z_P10 * r.yield_cv) - cost
        expected_profit += probability * profit

        label, description = SCENARIO_TEXT[scenario]
        outcomes.append(
            ScenarioOutcome(
                scenario=scenario,
                label=label,
                description=description,
                probability=round(probability, 3),
                yield_impact_pct=round((r.yield_factor - 1) * 100, 1),
                expected_yield_q_per_ha=round(yield_q, 2),
                cost_impact_inr_per_ha=round(r.extra_cost_inr),
                expected_cost_inr_per_ha=round(cost),
                expected_revenue_inr_per_ha=round(revenue),
                expected_profit_inr_per_ha=round(profit),
                profit_p10_inr_per_ha=round(profit_p10),
                downside_risk_inr_per_ha=round(max(0.0, baseline_profit - profit_p10)),
            )
        )

    return TwinResponse(
        panchayat=to_panchayat_out(panchayat),
        issued_on=issued_on,
        forecast_model=MODEL_NAME,
        ensemble_members=ENSEMBLE_MEMBERS,
        economics=CropEconomics(
            crop=crop,
            normal_yield_q_per_ha=coeffs.normal_yield_q_per_ha,
            price_inr_per_q=coeffs.price_inr_per_q,
            base_cost_inr_per_ha=coeffs.base_cost_inr_per_ha,
        ),
        summary=TwinSummary(
            baseline_profit_inr_per_ha=round(baseline_profit),
            expected_profit_inr_per_ha=round(expected_profit),
            expected_change_inr_per_ha=round(expected_profit - baseline_profit),
            most_likely_scenario=max(counts, key=counts.__getitem__),
        ),
        scenarios=outcomes,
    )
