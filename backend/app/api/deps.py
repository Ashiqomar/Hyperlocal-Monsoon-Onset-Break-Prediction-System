"""Shared route helpers: loading panchayats and building reviewed decisions."""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.data.crop_response import CROP_COEFFICIENTS, SUPPORTED_CROPS
from app.models import Panchayat
from app.schemas.decision import DecisionResponse
from app.schemas.geo import Crop
from app.schemas.twin import TwinResponse
from app.services.decision import build_decision
from app.services.review import ReviewStore, apply_review
from app.services.twin import build_twin


def get_panchayat(db: Session, panchayat_id: str) -> Panchayat:
    panchayat = db.get(Panchayat, panchayat_id, options=[joinedload(Panchayat.block)])
    if panchayat is None:
        raise HTTPException(status_code=404, detail=f"Panchayat '{panchayat_id}' not found")
    return panchayat


def all_panchayats(db: Session) -> list[Panchayat]:
    return list(db.scalars(select(Panchayat).options(joinedload(Panchayat.block)).order_by(Panchayat.id)))


def is_modeled(crop: Crop) -> bool:
    return crop in CROP_COEFFICIENTS


def twin_for(panchayat: Panchayat, crop: Crop | None) -> TwinResponse:
    crop = crop or Crop(panchayat.primary_crop)
    if not is_modeled(crop):
        supported = ", ".join(SUPPORTED_CROPS)
        raise HTTPException(
            status_code=422,
            detail=f"No crop-response coefficients for '{crop}'. Pass ?crop= one of: {supported}",
        )
    return build_twin(panchayat, crop, issued_on=date.today())


def decision_for(panchayat: Panchayat, crop: Crop | None, store: ReviewStore) -> DecisionResponse:
    """Today's decision for a panchayat, with any officer review applied."""
    return apply_review(build_decision(twin_for(panchayat, crop), panchayat.block), store)
