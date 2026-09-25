import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from .config import settings
from .content import SHOP_SEED
from .database import Base, SessionLocal, engine
from .errors import install_error_handlers
from .models import ShopItem
from .routers import auth, battles, comments, feed, me, photos, posts, recipes, shop, users

os.makedirs(settings.upload_dir, exist_ok=True)


def init_db() -> None:
    """Create tables and seed the shop on first run (idempotent)."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(ShopItem)) == 0:
            for name, category, value_label, value_krw, price, days in SHOP_SEED:
                db.add(
                    ShopItem(
                        name=name,
                        category=category,
                        value_label=value_label,
                        value_krw=value_krw,
                        price_coins=price,
                        validity_days=days,
                    )
                )
            db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.jwt_secret in ("dev-only-change-me", "change-this-secret-in-production"):
        logging.getLogger("uvicorn.error").warning(
            "JWT_SECRET is still the default: anyone can forge login tokens. Set a real secret in .env before deploying."
        )
    yield


app = FastAPI(title="COOKUP API", lifespan=lifespan)
install_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,  # auth is a Bearer header, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

for r in (
    auth.router,
    me.router,
    users.router,
    photos.router,
    posts.router,
    comments.router,
    feed.router,
    recipes.router,
    battles.router,
    shop.router,
    shop.coupons_router,
):
    app.include_router(r)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
