"""Farmer outcome feedback.

NOTE: feedback is only captured and displayed for now. It is intended for
eventual *periodic recalibration* (e.g. a scheduled job comparing reported rain
against forecast probabilities, and outcomes against the crop-response and
decision coefficients). Nothing here feeds back into any model yet.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import decision_for, get_panchayat, is_modeled
from app.db.session import get_db
from app.models import Feedback, Panchayat
from app.schemas.decision import Action
from app.schemas.feedback import FarmerAction, FeedbackIn, FeedbackOut
from app.schemas.geo import Crop
from app.services.review import ReviewStore, get_review_store

router = APIRouter(prefix="/feedback", tags=["feedback"])

# Which reported actions count as following each piece of advice.
FOLLOWS_ADVICE: dict[Action, set[FarmerAction]] = {
    Action.SOW: {FarmerAction.SOWED},
    Action.SPRAY: {FarmerAction.SPRAYED},
    Action.WAIT: {FarmerAction.WAITED, FarmerAction.NOTHING},
    Action.REASSESS: {FarmerAction.WAITED, FarmerAction.NOTHING},
}


def to_out(fb: Feedback) -> FeedbackOut:
    advised = Action(fb.advised_action) if fb.advised_action else None
    action_taken = FarmerAction(fb.action_taken)
    return FeedbackOut(
        id=fb.id,
        panchayat_id=fb.panchayat_id,
        panchayat_name=fb.panchayat.name,
        block_name=fb.panchayat.block.name,
        crop=fb.crop,
        # Always written as UTC; SQLite drops the timezone on read, so restore it.
        submitted_at=fb.submitted_at if fb.submitted_at.tzinfo else fb.submitted_at.replace(tzinfo=timezone.utc),
        rain_occurred=fb.rain_occurred,
        action_taken=action_taken,
        note=fb.note,
        advised_action=advised,
        advice_status=fb.advice_status,
        model_action=fb.model_action,
        model_confidence=fb.model_confidence,
        decision_issued_on=fb.decision_issued_on,
        followed_advice=(action_taken in FOLLOWS_ADVICE[advised]) if advised else None,
    )


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    body: FeedbackIn,
    db: Session = Depends(get_db),
    store: ReviewStore = Depends(get_review_store),
) -> FeedbackOut:
    """Record a farmer's reported outcome, with a snapshot of the advice shown at the time."""
    panchayat = get_panchayat(db, body.panchayat_id)
    crop = Crop(panchayat.primary_crop)

    fb = Feedback(
        panchayat_id=panchayat.id,
        crop=crop,
        submitted_at=datetime.now(timezone.utc),
        rain_occurred=body.rain_occurred,
        action_taken=body.action_taken,
        note=(body.note or "").strip() or None,
    )
    if is_modeled(crop):
        decision = decision_for(panchayat, crop, store)
        fb.advised_action = decision.escalation.final_action
        fb.advice_status = decision.escalation.status
        fb.model_action = decision.recommendation.action
        fb.model_confidence = decision.recommendation.confidence
        fb.decision_issued_on = decision.issued_on

    db.add(fb)
    db.commit()
    db.refresh(fb)
    return to_out(fb)


@router.get("", response_model=list[FeedbackOut])
def list_feedback(
    limit: int = Query(50, ge=1, le=500),
    panchayat_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[FeedbackOut]:
    """Most recent feedback first."""
    query = (
        select(Feedback)
        .options(joinedload(Feedback.panchayat).joinedload(Panchayat.block))
        .order_by(Feedback.submitted_at.desc(), Feedback.id.desc())
        .limit(limit)
    )
    if panchayat_id:
        query = query.where(Feedback.panchayat_id == panchayat_id)
    return [to_out(fb) for fb in db.scalars(query)]
