"""In-memory officer review store.

Only officer actions (approve / override) are stored; flagged decisions are
recomputed on demand, so the queue never goes stale against the forecast.
Reviews are keyed by panchayat + crop + issue date, so each day's decision
needs its own review.

Limitations: data is lost on restart and not shared between worker processes.
Swap ReviewStore for a database table before running more than one worker.
"""

import threading
from datetime import date, datetime, timezone

from app.schemas.decision import Action, DecisionResponse, DecisionStatus, OfficerReview
from app.schemas.geo import Crop


def review_id(panchayat_id: str, crop: Crop | str, issued_on: date) -> str:
    return f"{panchayat_id}:{crop}:{issued_on.isoformat()}"


def parse_review_id(value: str) -> tuple[str, Crop, date]:
    """Raises ValueError for malformed ids."""
    panchayat_id, crop, issued = value.split(":")
    return panchayat_id, Crop(crop), date.fromisoformat(issued)


class ReviewStore:
    def __init__(self) -> None:
        self._reviews: dict[str, OfficerReview] = {}
        self._lock = threading.Lock()

    def get(self, rid: str) -> OfficerReview | None:
        with self._lock:
            return self._reviews.get(rid)

    def approve(self, rid: str, note: str | None) -> OfficerReview:
        return self._put(rid, OfficerReview(status=DecisionStatus.APPROVED, note=note, reviewed_at=_now()))

    def override(self, rid: str, action: Action, note: str) -> OfficerReview:
        review = OfficerReview(status=DecisionStatus.OVERRIDDEN, override_action=action, note=note, reviewed_at=_now())
        return self._put(rid, review)

    def clear(self) -> None:
        with self._lock:
            self._reviews.clear()

    def _put(self, rid: str, review: OfficerReview) -> OfficerReview:
        with self._lock:
            self._reviews[rid] = review
        return review


def _now() -> datetime:
    return datetime.now(timezone.utc)


review_store = ReviewStore()


def get_review_store() -> ReviewStore:
    """FastAPI dependency (overridable in tests)."""
    return review_store


def apply_review(decision: DecisionResponse, store: ReviewStore) -> DecisionResponse:
    """Overlay any officer review onto a freshly computed decision."""
    esc = decision.escalation
    review = store.get(esc.review_id) if esc.review_id else None
    if review is None:
        return decision
    final_action = review.override_action or decision.recommendation.action
    escalation = esc.model_copy(update={"status": review.status, "final_action": final_action, "review": review})
    return decision.model_copy(update={"escalation": escalation})
