from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import all_panchayats, decision_for, get_panchayat, is_modeled
from app.db.session import get_db
from app.schemas.decision import DecisionResponse, DecisionStatus
from app.schemas.geo import Crop
from app.schemas.review import ApproveRequest, OverrideRequest, ReviewItem
from app.services.review import ReviewStore, get_review_store, parse_review_id

router = APIRouter(prefix="/review-queue", tags=["review"])


def to_item(d: DecisionResponse) -> ReviewItem:
    esc = d.escalation
    rec = d.recommendation
    return ReviewItem(
        id=esc.review_id or "",
        panchayat=d.panchayat,
        crop=d.crop,
        issued_on=d.issued_on,
        recommended_action=rec.action,
        confidence=rec.confidence,
        expected_loss_inr_per_ha=next(
            r.expected_loss_inr_per_ha for r in d.expected_loss_table if r.action == rec.action
        ),
        reasons=esc.reasons,
        status=esc.status,
        final_action=esc.final_action,
        review=esc.review,
    )


@router.get("", response_model=list[ReviewItem])
def list_review_queue(
    status: Literal["pending", "reviewed", "all"] = Query("all"),
    db: Session = Depends(get_db),
    store: ReviewStore = Depends(get_review_store),
) -> list[ReviewItem]:
    """Today's flagged decisions for each panchayat's primary crop, pending first."""
    items = [
        to_item(d)
        for p in all_panchayats(db)
        if is_modeled(Crop(p.primary_crop))
        for d in [decision_for(p, None, store)]
        if d.escalation.needs_officer_review
    ]
    pending = [i for i in items if i.status == DecisionStatus.NEEDS_OFFICER_REVIEW]
    reviewed = [i for i in items if i.status != DecisionStatus.NEEDS_OFFICER_REVIEW]
    return {"pending": pending, "reviewed": reviewed, "all": pending + reviewed}[status]


def _flagged_decision(rid: str, db: Session, store: ReviewStore) -> DecisionResponse:
    """Recompute the decision behind a review id and check it can be reviewed now."""
    try:
        panchayat_id, crop, issued_on = parse_review_id(rid)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown review item '{rid}'") from None
    if issued_on != date.today():
        raise HTTPException(status_code=409, detail="This decision is from a previous day; reload the queue")
    decision = decision_for(get_panchayat(db, panchayat_id), crop, store)
    if not decision.escalation.needs_officer_review:
        raise HTTPException(status_code=409, detail="This decision was not flagged for review")
    return decision


@router.post("/{review_id}/approve", response_model=ReviewItem)
def approve(
    review_id: str,
    body: ApproveRequest,
    db: Session = Depends(get_db),
    store: ReviewStore = Depends(get_review_store),
) -> ReviewItem:
    decision = _flagged_decision(review_id, db, store)
    store.approve(review_id, body.note)
    return to_item(decision_for(get_panchayat(db, decision.panchayat.id), decision.crop, store))


@router.post("/{review_id}/override", response_model=ReviewItem)
def override(
    review_id: str,
    body: OverrideRequest,
    db: Session = Depends(get_db),
    store: ReviewStore = Depends(get_review_store),
) -> ReviewItem:
    decision = _flagged_decision(review_id, db, store)
    if body.action == decision.recommendation.action:
        raise HTTPException(status_code=422, detail="Override action matches the recommendation; approve it instead")
    store.override(review_id, body.action, body.note)
    return to_item(decision_for(get_panchayat(db, decision.panchayat.id), decision.crop, store))
