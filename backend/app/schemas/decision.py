from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.geo import Crop, PanchayatOut
from app.schemas.twin import Scenario


class Action(StrEnum):
    SOW = "SOW"
    WAIT = "WAIT"
    SPRAY = "SPRAY"
    REASSESS = "REASSESS"


class DecisionStatus(StrEnum):
    AUTO_APPROVED = "auto_approved"  # not flagged; goes out as recommended
    NEEDS_OFFICER_REVIEW = "needs_officer_review"  # flagged, not yet reviewed
    APPROVED = "approved"  # flagged, officer confirmed the recommendation
    OVERRIDDEN = "overridden"  # flagged, officer chose a different action


class EscalationReason(BaseModel):
    code: Literal["low_confidence", "high_impact_cost"]
    message: str


class OfficerReview(BaseModel):
    status: Literal[DecisionStatus.APPROVED, DecisionStatus.OVERRIDDEN]
    override_action: Action | None = None
    note: str | None = None
    reviewed_at: datetime


class Escalation(BaseModel):
    needs_officer_review: bool = Field(description="True if flagged by the escalation rules (even once reviewed)")
    reasons: list[EscalationReason]
    status: DecisionStatus
    final_action: Action = Field(description="The action to communicate: the officer's override if any, else the recommendation")
    review_id: str | None = Field(default=None, description="Review-queue id; set only for flagged decisions")
    review: OfficerReview | None = None


class ScenarioLoss(BaseModel):
    scenario: Scenario
    probability: float = Field(ge=0.0, le=1.0)
    cost_if_wrong_inr_per_ha: int = Field(ge=0, description="Loss vs a normal season if this scenario happens")
    expected_loss_inr_per_ha: int = Field(ge=0, description="probability x cost_if_wrong")


class ActionLoss(BaseModel):
    action: Action
    description: str
    expected_loss_inr_per_ha: int = Field(ge=0, description="Sum of the per-scenario expected losses")
    rank: int = Field(ge=1, le=4, description="1 = lowest expected loss")
    by_scenario: list[ScenarioLoss] = Field(min_length=4, max_length=4)


class Recommendation(BaseModel):
    action: Action
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How much the forecast supports this action (0-1). Measures the decision only; "
            "independent of crop_suitability and must not be combined with it."
        ),
    )
    confidence_basis: str
    rationale: str


class CropSuitability(BaseModel):
    """Static agronomic fit of the crop to this panchayat. Ignores the current forecast."""

    score: int = Field(
        ge=0,
        le=100,
        description=(
            "Long-term fit of the crop to soil, irrigation and rainfall climate (0-100). "
            "Independent of recommendation.confidence and must not be combined with it."
        ),
    )
    rating: str = Field(description="high (>= 70), moderate (40-69) or low (< 40)")
    soil_score: int = Field(ge=0, le=100)
    water_score: int = Field(ge=0, le=100)
    soil_type: str
    irrigation_type: str
    season_normal_rainfall_mm: int = Field(description="Block's Jun-Sep climatological rainfall")
    crop_water_range_mm: tuple[int, int] = Field(description="Seasonal rainfall range where the crop does well")


class DecisionSummary(BaseModel):
    """One map marker: the decision for a panchayat's primary crop, if it is modelled."""

    panchayat: PanchayatOut
    crop: Crop
    modeled: bool = Field(description="False if there are no crop-response coefficients for this crop")
    action: Action | None = Field(default=None, description="Final action (officer override if any)")
    status: DecisionStatus | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    suitability_score: int | None = Field(default=None, ge=0, le=100)


class DecisionResponse(BaseModel):
    panchayat: PanchayatOut
    crop: Crop
    issued_on: date
    synthetic: bool = True
    recommendation: Recommendation
    crop_suitability: CropSuitability
    escalation: Escalation
    expected_loss_table: list[ActionLoss] = Field(min_length=4, max_length=4)
