from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.decision import Action, DecisionStatus
from app.schemas.geo import Crop


class FarmerAction(StrEnum):
    """What the farmer actually did (plain choices, not the model's action codes)."""

    SOWED = "sowed"
    WAITED = "waited"
    SPRAYED = "sprayed"
    NOTHING = "nothing"


class FeedbackIn(BaseModel):
    panchayat_id: str
    rain_occurred: bool = Field(description="Did it rain (meaningfully) since the advice was given?")
    action_taken: FarmerAction
    note: str | None = Field(default=None, max_length=500)


class FeedbackOut(BaseModel):
    id: int
    panchayat_id: str
    panchayat_name: str
    block_name: str
    crop: Crop
    submitted_at: datetime
    rain_occurred: bool
    action_taken: FarmerAction
    note: str | None
    advised_action: Action | None = Field(description="Final action shown when the report was submitted")
    advice_status: DecisionStatus | None
    model_action: Action | None
    model_confidence: float | None
    decision_issued_on: date | None
    followed_advice: bool | None = Field(
        description="Whether action_taken matches advised_action (derived on read; None if no advice)"
    )
