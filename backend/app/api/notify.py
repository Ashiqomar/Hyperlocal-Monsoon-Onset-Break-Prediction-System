from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import decision_for, get_panchayat, is_modeled
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import Panchayat
from app.schemas.geo import Crop
from app.schemas.notify import NotifyMessage, NotifyResult
from app.services.forecast import generate_forecast
from app.services.notify import build_message, send
from app.services.review import ReviewStore, get_review_store

router = APIRouter(prefix="/notify", tags=["notify"])


def _message(panchayat: Panchayat, store: ReviewStore, settings: Settings) -> NotifyMessage:
    # Farmer messages always use the panchayat's primary crop.
    crop = Crop(panchayat.primary_crop)
    decision = decision_for(panchayat, crop, store) if is_modeled(crop) else None
    return build_message(panchayat, decision, generate_forecast(panchayat, date.today()), settings)


@router.get("/{panchayat_id}", response_model=NotifyMessage)
def preview_notification(
    panchayat_id: str,
    db: Session = Depends(get_db),
    store: ReviewStore = Depends(get_review_store),
    settings: Settings = Depends(get_settings),
) -> NotifyMessage:
    """Build today's WhatsApp message without sending or logging it."""
    return _message(get_panchayat(db, panchayat_id), store, settings)


@router.post("/{panchayat_id}", response_model=NotifyResult)
def send_notification(
    panchayat_id: str,
    db: Session = Depends(get_db),
    store: ReviewStore = Depends(get_review_store),
    settings: Settings = Depends(get_settings),
) -> NotifyResult:
    """Build today's message and 'send' it. For now it is only logged."""
    message = _message(get_panchayat(db, panchayat_id), store, settings)
    if not message.can_send:
        raise HTTPException(status_code=409, detail=message.blocked_reason)
    return send(message, settings)
