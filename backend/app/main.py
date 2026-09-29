import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.api.feedback import router as feedback_router
from app.api.forecast import router as forecast_router
from app.api.health import router as health_router
from app.api.notify import router as notify_router
from app.api.review import router as review_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.seed import seed_if_empty
from app.db.session import SessionLocal, engine

settings = get_settings()

# Show our own INFO logs (e.g. logged WhatsApp messages) next to uvicorn's output.
_app_logger = logging.getLogger("app")
if not _app_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     [%(name)s] %(message)s"))
    _app_logger.addHandler(_handler)
    _app_logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Create tables for any registered models. Replace with Alembic migrations
    # once the schema starts evolving.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_if_empty(db)
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(forecast_router)
app.include_router(review_router)
app.include_router(notify_router)
app.include_router(feedback_router)
