from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.geo import Panchayat


class Feedback(Base):
    """A farmer's reported outcome.

    Captured for eventual periodic recalibration (e.g. checking forecast
    probabilities against whether rain actually occurred, and crop-response /
    decision coefficients against what farmers did). NOT used by any model yet.
    """

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panchayat_id: Mapped[str] = mapped_column(ForeignKey("panchayats.id"), index=True)
    crop: Mapped[str] = mapped_column(String(32))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # What the farmer reported.
    rain_occurred: Mapped[bool] = mapped_column(Boolean)
    action_taken: Mapped[str] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Snapshot of the advice showing when the report was submitted. Decisions are
    # recomputed daily, so without this we could not tell later what was advised.
    # All null when the crop has no advice model.
    advised_action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    advice_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    model_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision_issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    panchayat: Mapped[Panchayat] = relationship()
