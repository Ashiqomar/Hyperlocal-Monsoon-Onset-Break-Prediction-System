from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.decision import Action, DecisionStatus
from app.schemas.geo import Crop


class TranslationPlaceholder(BaseModel):
    language: str = Field(description="ISO 639-1 code, e.g. 'mr' for Marathi")
    language_name: str
    status: Literal["pending"] = "pending"
    text: str | None = Field(default=None, description="Filled in once a translation service is wired up")


class NotifyMessage(BaseModel):
    panchayat_id: str
    crop: Crop
    channel: Literal["whatsapp"] = "whatsapp"
    language: str = "en"
    text: str = Field(description="WhatsApp-formatted text (*bold*), in English")
    char_count: int
    decision_status: DecisionStatus | None = Field(description="None when the crop has no advice model yet")
    final_action: Action | None = None
    farmer_url: str
    translations: list[TranslationPlaceholder]
    can_send: bool
    blocked_reason: str | None = None


class Delivery(BaseModel):
    channel: Literal["whatsapp"] = "whatsapp"
    provider: Literal["log"] = Field(default="log", description="'log' until Twilio is wired up")
    status: Literal["logged"] = "logged"
    logged_at: datetime


class NotifyResult(BaseModel):
    message: NotifyMessage
    delivery: Delivery
