from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.synthetic import BLOCKS, generate_panchayats
from app.models import Block, Panchayat


def seed_if_empty(db: Session) -> None:
    """Load the synthetic dataset on first start. No-op if blocks already exist."""
    if db.scalar(select(Block.id).limit(1)) is not None:
        return

    db.add_all(
        Block(
            id=b.id,
            name=b.name,
            district=b.district,
            lat=b.lat,
            lon=b.lon,
            rain_day_prob=b.rain_day_prob,
            rain_day_mean_mm=b.rain_day_mean_mm,
        )
        for b in BLOCKS
    )
    db.flush()
    db.add_all(Panchayat(**row) for row in generate_panchayats())
    db.commit()
