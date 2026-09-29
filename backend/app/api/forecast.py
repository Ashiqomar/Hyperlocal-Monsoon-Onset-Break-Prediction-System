from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import all_panchayats, decision_for, get_panchayat, is_modeled, twin_for
from app.db.session import get_db
from app.schemas.decision import DecisionResponse, DecisionSummary
from app.schemas.forecast import ForecastResponse
from app.schemas.geo import Crop, PanchayatOut
from app.schemas.twin import TwinResponse
from app.services.forecast import generate_forecast, to_panchayat_out
from app.services.review import ReviewStore, get_review_store

router = APIRouter(tags=["forecast"])

CropOverride = Query(None, description="Override the panchayat's primary crop")


@router.get("/panchayats", response_model=list[PanchayatOut])
def list_panchayats(db: Session = Depends(get_db)) -> list[PanchayatOut]:
    return [to_panchayat_out(p) for p in all_panchayats(db)]


@router.get("/forecast/{panchayat_id}", response_model=ForecastResponse)
def get_forecast(panchayat_id: str, db: Session = Depends(get_db)) -> ForecastResponse:
    return generate_forecast(get_panchayat(db, panchayat_id), issued_on=date.today())


@router.get("/twin/{panchayat_id}", response_model=TwinResponse, tags=["twin"])
def get_twin(panchayat_id: str, crop: Crop | None = CropOverride, db: Session = Depends(get_db)) -> TwinResponse:
    return twin_for(get_panchayat(db, panchayat_id), crop)


@router.get("/decisions", response_model=list[DecisionSummary], tags=["decision"])
def list_decisions(
    db: Session = Depends(get_db), store: ReviewStore = Depends(get_review_store)
) -> list[DecisionSummary]:
    """Final action for every panchayat's primary crop, for the dashboard map."""
    summaries: list[DecisionSummary] = []
    for p in all_panchayats(db):
        crop = Crop(p.primary_crop)
        if not is_modeled(crop):
            summaries.append(DecisionSummary(panchayat=to_panchayat_out(p), crop=crop, modeled=False))
            continue
        decision = decision_for(p, crop, store)
        summaries.append(
            DecisionSummary(
                panchayat=decision.panchayat,
                crop=crop,
                modeled=True,
                action=decision.escalation.final_action,
                status=decision.escalation.status,
                confidence=decision.recommendation.confidence,
                suitability_score=decision.crop_suitability.score,
            )
        )
    return summaries


@router.get("/decision/{panchayat_id}", response_model=DecisionResponse, tags=["decision"])
def get_decision(
    panchayat_id: str,
    crop: Crop | None = CropOverride,
    db: Session = Depends(get_db),
    store: ReviewStore = Depends(get_review_store),
) -> DecisionResponse:
    return decision_for(get_panchayat(db, panchayat_id), crop, store)
