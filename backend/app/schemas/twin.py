from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.geo import Crop, PanchayatOut


class Scenario(StrEnum):
    NORMAL = "normal"
    DRY = "dry"
    WET = "wet"
    FALSE_ONSET = "false_onset"


class CropEconomics(BaseModel):
    """Per-hectare assumptions for a normal season."""

    crop: Crop
    normal_yield_q_per_ha: float
    price_inr_per_q: int
    base_cost_inr_per_ha: int


class ScenarioOutcome(BaseModel):
    scenario: Scenario
    label: str
    description: str
    probability: float = Field(ge=0.0, le=1.0, description="Share of forecast ensemble members in this scenario")
    yield_impact_pct: float = Field(description="Change in yield vs a normal season, e.g. -30.0")
    expected_yield_q_per_ha: float
    cost_impact_inr_per_ha: int = Field(description="Extra cost vs a normal season (re-sowing, sprays, irrigation)")
    expected_cost_inr_per_ha: int
    expected_revenue_inr_per_ha: int
    expected_profit_inr_per_ha: int
    profit_p10_inr_per_ha: int = Field(description="Profit in a 1-in-10 bad outcome within this scenario")
    downside_risk_inr_per_ha: int = Field(
        ge=0.0, description="How far the 1-in-10 bad outcome falls below the normal-season expected profit"
    )


class TwinSummary(BaseModel):
    baseline_profit_inr_per_ha: int = Field(description="Expected profit in a normal season")
    expected_profit_inr_per_ha: int = Field(description="Probability-weighted expected profit across scenarios")
    expected_change_inr_per_ha: int = Field(description="Expected profit minus baseline")
    most_likely_scenario: Scenario


class TwinResponse(BaseModel):
    panchayat: PanchayatOut
    issued_on: date
    forecast_model: str
    ensemble_members: int
    synthetic: bool = True
    economics: CropEconomics
    summary: TwinSummary
    scenarios: list[ScenarioOutcome] = Field(min_length=4, max_length=4)
