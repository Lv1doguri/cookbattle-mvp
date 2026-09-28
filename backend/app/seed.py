"""First-run content: shop items, the official account, and sample recipes (idempotent)."""
import secrets
import shutil
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .content import ESSENTIAL_RECIPES, OFFICIAL_EMAIL, OFFICIAL_NICKNAME, RECIPE_SEED, RECIPE_SEED_PHOTOS, SHOP_SEED
from .enums import Tier
from .models import Ingredient, Recipe, RecipeTool, ShopItem, Step, User
from .security import hash_password

SEED_PHOTOS_DIR = Path(__file__).parent / "seed_photos"


def _copy_photo(src: Path) -> Optional[str]:
    """Copies a curated sample photo into the upload dir, same as a real upload would land there."""
    if not src.exists():
        return None
    filename = f"seed-{uuid.uuid4().hex}{src.suffix}"
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, Path(settings.upload_dir) / filename)
    return filename


def _copy_seed_photo(title: str) -> Optional[str]:
    name = RECIPE_SEED_PHOTOS.get(title)
    return _copy_photo(SEED_PHOTOS_DIR / name) if name else None


def _copy_shop_photo(name: str) -> Optional[str]:
    return _copy_photo(SEED_PHOTOS_DIR / "shop" / name) if name else None


def seed_all(db: Session) -> None:
    _seed_shop(db)
    _seed_recipes(db)


def _seed_shop(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(ShopItem)) != 0:
        return
    for name, price, required_level, photo in SHOP_SEED:
        db.add(ShopItem(
            name=name, price_points=price, required_level=required_level,
            photo_filename=_copy_shop_photo(photo),
        ))
    db.commit()


def _seed_recipes(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Recipe)) != 0:
        return
    official = db.scalar(select(User).where(User.email == OFFICIAL_EMAIL))
    if official is None:
        # Nobody knows this password (random, never stored anywhere), so the account can't be logged into.
        official = User(
            email=OFFICIAL_EMAIL,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            nickname=OFFICIAL_NICKNAME,
            tier=Tier.advanced,
        )
        db.add(official)
        db.flush()

    for r in RECIPE_SEED:
        recipe = Recipe(
            author_id=official.id,
            title=r["title"],
            category=r["category"],
            cost_krw=r["cost_krw"],
            cook_minutes=r["minutes"],
            difficulty=r["difficulty"],
            win_label=r["win_label"],
            is_essential=r["title"] in ESSENTIAL_RECIPES,
            photo_filename=_copy_seed_photo(r["title"]),
            value_score=r.get("value_score"),
            calories_kcal=r.get("calories_kcal"),
            portion_label=r.get("portion_label"),
            fail_safety_label=r.get("fail_safety_label"),
            chef_tip=r.get("chef_tip"),
        )
        recipe.ingredients = [Ingredient(position=i, name=n, amount=a) for i, (n, a) in enumerate(r["ingredients"])]
        recipe.steps = [Step(position=i + 1, text=t, minutes=m) for i, (t, m) in enumerate(r["steps"])]
        recipe.tools = [RecipeTool(tool=t) for t in r["tools"]]
        db.add(recipe)
    db.commit()
