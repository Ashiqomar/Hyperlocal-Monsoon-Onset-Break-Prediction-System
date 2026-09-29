from datetime import date

from pydantic import BaseModel, Field

from app.schemas.decision import Action, DecisionStatus, EscalationReason, OfficerReview
from app.schemas.geo import Crop, PanchayatOut


class ReviewItem(BaseModel):
    id: str
    panchayat: PanchayatOut
    crop: Crop
    issued_on: date
    recommended_action: Action
    confidence: float = Field(ge=0.0, le=1.0)
    expected_loss_inr_per_ha: int = Field(description="Expected loss of the recommended action")
    reasons: list[EscalationReason]
    status: DecisionStatus
    final_action: Action
    review: OfficerReview | None = None


class ApproveRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class OverrideRequest(BaseModel):
    action: Action
    note: str = Field(min_length=3, max_length=500, description="Why the officer is overriding (required)")
