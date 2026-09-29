from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    district: Mapped[str] = mapped_column(String(64))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    # Monsoon-season (Jun-Sep) climatology used to drive the mock forecast.
    rain_day_prob: Mapped[float] = mapped_column(Float)
    rain_day_mean_mm: Mapped[float] = mapped_column(Float)

    panchayats: Mapped[list["Panchayat"]] = relationship(back_populates="block")


class Panchayat(Base):
    __tablename__ = "panchayats"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    block_id: Mapped[str] = mapped_column(ForeignKey("blocks.id"), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    # Stored as plain strings (portable across SQLite/Postgres); values are
    # validated against the enums in app.schemas.geo.
    soil_type: Mapped[str] = mapped_column(String(32))
    irrigation_type: Mapped[str] = mapped_column(String(32))
    primary_crop: Mapped[str] = mapped_column(String(32))

    block: Mapped[Block] = relationship(back_populates="panchayats")
