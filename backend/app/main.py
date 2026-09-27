import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, SessionLocal, engine
from .errors import install_error_handlers
from .routers import admin, auth, battles, entry_comments, me, photos, recipes, shop
from .seed import seed_all

os.makedirs(settings.upload_dir, exist_ok=True)


def init_db() -> None:
    """Create tables and seed first-run content (idempotent)."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_all(db)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.jwt_secret in ("dev-only-change-me", "change-this-secret-in-production"):
        logging.getLogger("uvicorn.error").warning(
            "JWT_SECRET is still the default: anyone can forge login tokens. Set a real secret in .env before deploying."
        )
    yield


app = FastAPI(title="요리왕(COOKUP) API", lifespan=lifespan)
install_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,  # auth is a Bearer header, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

for r in (auth.router, me.router, photos.router, recipes.router, battles.router, shop.router, entry_comments.router, admin.router):
    app.include_router(r)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
