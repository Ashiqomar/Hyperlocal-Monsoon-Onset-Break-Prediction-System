"""Hardcoded crop-response coefficients for the scenario simulation.

Illustrative, per-hectare, Maharashtra kharif figures: yields are near state
averages, prices near the 2025-26 MSP, costs near typical cost of cultivation.
Replace with agronomist-validated values before using them for real decisions.
"""

from dataclasses import dataclass

from app.schemas.geo import Crop
from app.schemas.twin import Scenario


@dataclass(frozen=True)
class ScenarioResponse:
    yield_factor: float  # yield relative to a normal season
    extra_cost_inr: float  # added cost per ha (re-sowing, sprays, pumping)
    yield_cv: float  # coefficient of variation of yield within the scenario


@dataclass(frozen=True)
class CropCoefficients:
    normal_yield_q_per_ha: float
    price_inr_per_q: float
    base_cost_inr_per_ha: float
    response: dict[Scenario, ScenarioResponse]


N, D, W, F = Scenario.NORMAL, Scenario.DRY, Scenario.WET, Scenario.FALSE_ONSET

CROP_COEFFICIENTS: dict[Crop, CropCoefficients] = {
    # Deep roots make it fairly drought-tolerant; waterlogging and boll rot hurt
    # in excess rain. Re-sowing Bt seed after a false onset is expensive.
    Crop.COTTON: CropCoefficients(
        normal_yield_q_per_ha=12.0,
        price_inr_per_q=7710,
        base_cost_inr_per_ha=55_000,
        response={
            N: ScenarioResponse(1.00, 0, 0.10),
            D: ScenarioResponse(0.70, 4_000, 0.25),
            W: ScenarioResponse(0.80, 5_000, 0.20),
            F: ScenarioResponse(0.85, 8_000, 0.20),
        },
    ),
    # Sensitive to moisture stress at pod fill and to waterlogging (plus yellow
    # mosaic / stem fly in wet spells). Seedlings die in a post-onset dry spell.
    Crop.SOYBEAN: CropCoefficients(
        normal_yield_q_per_ha=12.0,
        price_inr_per_q=5328,
        base_cost_inr_per_ha=38_000,
        response={
            N: ScenarioResponse(1.00, 0, 0.10),
            D: ScenarioResponse(0.60, 3_000, 0.25),
            W: ScenarioResponse(0.75, 4_000, 0.20),
            F: ScenarioResponse(0.80, 7_000, 0.20),
        },
    ),
    # Water-loving, so tolerates excess well; dry spells need costly pumping,
    # and a false onset delays nursery and transplanting.
    Crop.PADDY: CropCoefficients(
        normal_yield_q_per_ha=30.0,
        price_inr_per_q=2369,
        base_cost_inr_per_ha=50_000,
        response={
            N: ScenarioResponse(1.00, 0, 0.10),
            D: ScenarioResponse(0.65, 6_000, 0.25),
            W: ScenarioResponse(0.95, 2_000, 0.15),
            F: ScenarioResponse(0.85, 5_000, 0.20),
        },
    ),
}

SUPPORTED_CROPS: tuple[Crop, ...] = tuple(CROP_COEFFICIENTS)
